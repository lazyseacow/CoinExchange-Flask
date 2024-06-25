import os
import re
from flask import current_app, jsonify, request
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity, create_refresh_token, get_jwt
from flask_jwt_extended.exceptions import NoAuthorizationError
from jwt import ExpiredSignatureError
from sqlalchemy.exc import SQLAlchemyError

import config
from app import redis_conn
from app.api import api
from app.models.models import *
from app.utils.response_code import RET
from app.utils.generate_account import generate_erc20_account, generate_trc20_account, generate_btc_account
from app.utils.generate_qr_code import generate_qr_code
from app.utils.generate_captcha_img import generate_captcha_text, generate_captcha_image
from config import currency_list
from app.auth.verify import token_auth, sign_auth


@api.route('/register', methods=['POST'])
def Register():
    username = request.json.get('username')
    email = request.json.get('email')
    phone = request.json.get('phone')
    password = request.json.get('password')

    if not all([username, email, phone, password]):
        return jsonify(errno=RET.PARAMERR, msg='参数不完整')

    user = User()
    digital_wallet = DigitalWallet()
    pay_password = PayPassword()

    phone_exist = user.query.filter_by(phone=phone).first()
    email_exist = user.query.filter_by(email=email).first()

    if not re.match(r'\d{11}$', phone):
        return jsonify(re_code=RET.PARAMERR, msg='手机号码格式错误')
    if not re.match(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$', email):
        return jsonify(re_code=RET.PARAMERR, msg='邮箱格式错误')

    if phone_exist or email_exist:
        return jsonify(re_code=RET.DATAEXIST, msg='手机号码或邮箱已注册')

    erc20_address, erc20_private_key = generate_erc20_account()
    trc20_address, trc20_private_key = generate_trc20_account()
    btc_address, btc_private_key = generate_btc_account()
    eth_address, eth_private_key = generate_erc20_account()

    user.username = username
    user.email = email
    user.phone = phone
    user.password = password
    user.join_time = datetime.now()
    user.last_seen = datetime.now()
    db.session.add(user)
    db.session.flush()

    digital_wallet.user_id = user.user_id
    digital_wallet.erc20_address = erc20_address
    digital_wallet.trc20_address = trc20_address
    digital_wallet.erc20_private_key = erc20_private_key
    digital_wallet.trc20_private_key = trc20_private_key
    digital_wallet.btc_address = btc_address
    digital_wallet.btc_private_key = btc_private_key
    digital_wallet.eth_address = eth_address
    digital_wallet.eth_private_key = eth_private_key

    db.session.add(digital_wallet)

    try:
        db.session.commit()
        pay_password.password = password
        pay_password.user_id = user.user_id
        for currency in currency_list:
            wallet = Wallet(user_id=user.user_id, symbol=currency, balance=0.0, frozen_balance=0.0)
            db.session.add(wallet)
        db.session.add(pay_password)
        db.session.commit()

    except Exception as e:
        current_app.logger.debug('/register' + str(e))
        db.session.rollback()
        return jsonify(re_code=RET.DBERR, msg='注册失败')

    return jsonify(re_code=RET.OK, msg='注册成功')


@api.route('/captcha', methods=['GET'])
def get_captcha():
    text = generate_captcha_text()
    # 将text保存到redis的set中，有效期一分钟
    redis_conn.setex(f'captcha_{request.remote_addr}', 60, text)
    img = generate_captcha_image(text)
    return jsonify(re_code=RET.OK, msg='验证码发送成功', img=img)


@api.route('/login', methods=['POST'])
def Login():
    """
    login
    :return: 返回响应，保持登录状态
    """

    account = request.json.get('account')
    password = request.json.get('password')
    captcha = request.json.get('captcha')
    user_activity_logs = UserActivityLogs()
    if not all([account, password]):
        return jsonify(re_code=RET.PARAMERR, msg='账号或密码不能为空')

    try:
        if re.match(r'\d{11}$', account):
            user = User.query.filter_by(phone=account).first()
        elif re.match(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$', account):
            user = User.query.filter_by(email=account).first()
        else:
            return jsonify(re_code=RET.PARAMERR, msg='账户名格式错误')

        if not user:
            return jsonify(re_code=RET.USERERR, msg='用户不存在')

        if not user.verify_password(password):
            return jsonify(re_code=RET.PWDERR, msg='账户名或密码错误')

        if not redis_conn.get(f'captcha_{request.remote_addr}'):
            return jsonify(re_code=RET.NODATA, msg='验证码过期')
        elif redis_conn.get(f'captcha_{request.remote_addr}') != captcha.encode('utf-8'):
            return jsonify(re_code=RET.PARAMERR, msg='验证码错误')

        user.update_last_seen()
        db.session.flush()
        user_activity_logs.log_activity(user.user_id, 'login', request.remote_addr)

    except Exception as e:
        current_app.logger.debug('/login' + str(e))
        return jsonify(re_code=RET.DBERR, msg='查询用户失败')

    access_token = create_access_token(identity=user.user_id, fresh=True)
    refresh_token = create_refresh_token(identity=user.user_id)

    user_info = {
        'username': user.username,
        'email': user.email,
        'phone': user.phone,
        'join_time': user.join_time,
    }
    return jsonify(re_code=RET.OK, msg='登录成功', data=user_info, access_token=access_token, refresh_token=refresh_token)


@api.route('/logout', methods=['POST'])
@jwt_required()
def Logout():
    """
    用户在登录状态点击退出登录时，需要清除用户的登录状态
    :return:
    """
    current_user_id = token_auth.get_userinfo()
    if User.query.filter_by(user_id=current_user_id):
        user_activity_logs = UserActivityLogs()
        user_activity_logs.log_activity(current_user_id, 'logout', request.remote_addr)
        return jsonify(re_code=RET.OK, msg='退出成功')
    else:
        return jsonify(re_code=RET.NODATA, msg='退出失败')


@api.route("/token/refresh", methods=["POST"])
@jwt_required(refresh=True)
def Refresh():
    # 检查令牌是否过期
    current_token = get_jwt()
    if current_token['exp'] < datetime.now().timestamp():
        return jsonify(re_code=RET.SESSIONERR, msg='token已过期，请重新登录')
    identity = get_jwt_identity()
    access_token = create_access_token(identity=identity)

    return jsonify(re_code=RET.OK, msg='刷新成功', access_token=access_token)


@api.route('/modifypassowrd', methods=['POST'])
@jwt_required()
def ModifyPassowrd():
    current_user_id = token_auth.get_userinfo()
    current_password = request.json.get('current_password')
    new_password = request.json.get('new_password')
    timestamp = request.json.get('timestamp')
    x_signature = request.json.get('x_signature')

    encrypt_data = f'{current_password}+{new_password}+{timestamp}'
    if not sign_auth.verify_signature(data=encrypt_data, timestamp=timestamp, provided_signature=x_signature):
        return jsonify(re_code=RET.SIGNERR, msg='签名错误')

    user = User().query.filter_by(user_id=current_user_id).first()
    if not user:
        return jsonify(re_code=RET.USERERR, msg='找不到该用户')

    if not user.verify_password(current_password):
        return jsonify(re_code=RET.PWDERR, msg='密码不正确')

    if user.verify_password(new_password):
        return jsonify(re_code=RET.DATAERR, msg='新密码与旧密码相同')

    user.password = new_password
    try:
        db.session.commit()
        user_activity_logs = UserActivityLogs()
        user_activity_logs.log_activity(current_user_id, 'modify password', request.remote_addr)
        return jsonify(re_code=RET.OK, msg='密码修改成功')
    except Exception as e:
        current_app.logger.debug('/modifypassowrd' + str(e))
        db.session.rollback()
        return jsonify(re_code=RET.DBERR, msg='密码修改失败')


@api.route('/resetpassowrd', methods=['POST'])
# @jwt_required()
def ResetPassword():
    # current_user_id = token_auth.get_userinfo()
    phone = request.json.get('phone')
    new_password = request.json.get('new_password')
    timestamp = request.json.get('timestamp')
    x_signature = request.json.get('x_signature')

    encrypt_data = f'{phone}+{new_password}+{timestamp}'
    if not sign_auth.verify_signature(data=encrypt_data, timestamp=timestamp, provided_signature=x_signature):
        return jsonify(re_code=RET.SIGNERR, msg='签名错误')

    user = User().query.filter_by(phone=phone).first()

    if not user:
        return jsonify(re_code=RET.USERERR, msg='找不到该用户')

    if user.verify_password(new_password):
        return jsonify(re_code=RET.DATAERR, msg='新密码与旧密码相同')

    user.password = new_password
    try:
        user_activity_logs = UserActivityLogs()
        user_activity_logs.log_activity(user.user_id, 'reset password', request.remote_addr)
        db.session.commit()
        return jsonify(re_code=RET.OK, msg='密码修改成功')
    except Exception as e:
        current_app.logger.debug('/resetpassowrd' + str(e))
        user.rollback()
        return jsonify(re_code=RET.OK, msg='密码修改失败')


@api.route('/realname', methods=['POST'])
@jwt_required()
def realname():
    current_user_id = token_auth.get_userinfo()
    user = User().query.filter_by(user_id=current_user_id).first()

    # 获取用户的真实姓名、证件类型、证件照、证件号
    real_name = request.form.get('real_name')
    document_type = request.form.get('document_type')
    id_card = request.form.get('id_card')
    identification_photo = request.files.get('identification_photo')
    timestamp = request.form.get('timestamp')
    x_signature = request.form.get('x_signature')
    if not all([real_name, document_type, id_card, timestamp, x_signature]):
        return jsonify(re_code=RET.PARAMERR, msg='参数错误')

    encrypt_data = f'{real_name}+{document_type}+{id_card}+{identification_photo.filename}+{timestamp}'
    if not sign_auth.verify_signature(data=encrypt_data, timestamp=timestamp, provided_signature=x_signature):
        return jsonify(re_code=RET.SIGNERR, msg='签名错误')

    if not user:
        return jsonify(re_code=RET.USERERR, msg='找不到该用户')
    if user.user_authentications.first():
        return jsonify(re_code=RET.DATAEXIST, msg='该用户已提交实名认证')

    if identification_photo.filename:
        static = current_app.config['IMAGE_PATH']
        if not os.path.exists(static):
            os.makedirs(static)
        # 构建文件名，这里简单地使用了原文件名，实际应用中可能需要处理文件名冲突
        filename = f'{datetime.now().strftime("%Y%m%d%H%M%S")}-' + identification_photo.filename
        file_path = os.path.join(static, filename)
        # 保存文件到服务器
        identification_photo.save(file_path)
    else:
        return jsonify(re_code=RET.PARAMERR, msg='请上传证件照')

    if not identification_photo.filename.endswith(('.jpg', '.png', '.jpeg')):
        return jsonify(re_code=RET.PARAMERR, msg='证件照格式错误')

    user_authentication = UserAuthentication(user_id=user.user_id, document_type=document_type, id_card=id_card, status='reviewing', real_name=real_name, auth_image=file_path)
    db.session.add(user_authentication)
    try:
        db.session.commit()
        return jsonify(re_code=RET.OK, msg='实名认证已提交')
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.debug('/realname' + str(e))
        return jsonify(re_code=RET.DBERR, msg='实名认证提交失败')
    except Exception as e:
        current_app.logger.debug('/realname' + str(e))
        return jsonify(re_code=RET.UNKOWNERR, msg='实名认证提交失败')


@api.route('/realname/status', methods=['GET'])
@jwt_required()
def realname_status():
    current_user_id = token_auth.get_userinfo()
    user = User().query.filter_by(user_id=current_user_id).first()

    if not user:
        return jsonify(re_code=RET.USERERR, msg='找不到该用户')

    auth_data = user.user_authentications.first()

    if not auth_data:
        return jsonify(re_code=RET.DATAERR, msg='该用户未实名认证')

    return jsonify(re_code=RET.OK, msg='查询成功', data=auth_data.to_json())
