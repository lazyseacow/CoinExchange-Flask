import base64
import re
from datetime import timedelta
import qrcode
from io import BytesIO
from flask import current_app, jsonify, request
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity, create_refresh_token, get_jwt
from flask_jwt_extended.exceptions import NoAuthorizationError
from jwt import ExpiredSignatureError

from app.api import api
from app.models.models import *
from app.utils.response_code import RET
from app.utils.generate_account import generate_erc20_account, generate_trc20_account
from app.utils.generate_qr_code import generate_qr_code
from config import currency_list
from app.api.verify import auth


@api.route('/register', methods=['POST'])
def Register():
    username = request.json.get('username')
    email = request.json.get('email')
    phone = request.json.get('phone')
    password = request.json.get('password')

    if not all([username, email, phone, password]):
        return jsonify(errno=RET.PARAMERR, msg='参数不完整')

    user = User()
    pay_password = PayPassword()

    phone_exist = user.query.filter_by(phone=phone).first()
    email_exist = user.query.filter_by(email=email).first()

    if phone_exist or email_exist:
        return jsonify(re_code=RET.DATAEXIST, msg='手机号码或邮箱已注册')

    erc20_address, erc20_private_key = generate_erc20_account()
    trc20_address, trc20_private_key = generate_trc20_account()
    user.username = username
    user.email = email
    user.phone = phone
    user.password = password
    user.join_time = datetime.now()
    user.last_seen = datetime.now()
    user.erc20_address = erc20_address
    user.erc20_private_key = erc20_private_key
    user.trc20_address = trc20_address
    user.trc20_private_key = trc20_private_key

    db.session.add(user)
    db.session.flush()

    try:
        user.save()
        pay_password.password = password
        pay_password.user_id = user.user_id
        for currency in currency_list:
            wallet = Wallet(user_id=user.user_id, symbol=currency, balance=0.0, frozen_balance=0.0)
            db.session.add(wallet)
        db.session.add(pay_password)
        db.session.commit()

    except Exception as e:
        current_app.logger.debug(e)
        db.session.rollback()
        return jsonify(re_code=RET.DBERR, msg='注册失败')

    return jsonify(re_code=RET.OK, msg='注册成功')


@api.route('/login', methods=['POST'])
def Login():
    """
    login
    TODO:添加图片验证码
    :return: 返回响应，保持登录状态
    """

    account = request.json.get('account')
    password = request.json.get('password')
    user = User()
    user_auth = UserAuthentication()
    user_activity_logs = UserActivityLogs()
    auth_type = ''
    auth_status = 'success'
    if not all([account, password]):
        return jsonify(re_code=RET.PARAMERR, msg='账号或密码不能为空')

    try:
        if re.match(r'\d{11}$', account):
            auth_type = 'phone'
            user = User.query.filter_by(phone=account).first()
        elif re.match(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$', account):
            auth_type = 'email'
            user = User.query.filter_by(email=account).first()
        else:
            return jsonify(re_code=RET.PARAMERR, msg='账户名格式错误')

        if not user:
            return jsonify(re_code=RET.NODATA, msg='用户不存在')

        if not user.verify_password(password):
            auth_status = 'failed'
            user_auth.log_auth(user.user_id, auth_type, auth_status, account)
            return jsonify(re_code=RET.PWDERR, msg='账户名或密码错误')

        user.update_last_seen()
        db.session.flush()
        user_auth.log_auth(user.user_id, auth_type, auth_status, account)
        user_activity_logs.log_activity(user.user_id, 'login', request.remote_addr)

    except Exception as e:
        current_app.logger.debug(e)
        return jsonify(re_code=RET.DBERR, msg='查询用户失败')

    access_token = create_access_token(identity=user.user_id, fresh=True)
    refresh_token = create_refresh_token(identity=user.user_id)

    erc_20_qr_code = generate_qr_code(user.erc20_address)
    trc_20_qr_code = generate_qr_code(user.trc20_address)


    user_info = {
        'username': user.username,
        'email': user.email,
        'phone': user.phone,
        'join_time': user.join_time,
        'erc20_address': user.erc20_address,
        'erc_20_qr_code': erc_20_qr_code,
        'trc20_address': user.trc20_address,
        'trc_20_qr_code': trc_20_qr_code,

    }
    return jsonify(re_code=RET.OK, msg='登录成功', data=user_info, access_token=access_token, refresh_token=refresh_token)


@api.errorhandler(NoAuthorizationError)
def handle_no_authorization(e):
    return jsonify(re_code=RET.SESSIONERR, msg='缺少授权，请提供令牌')


@api.errorhandler(ExpiredSignatureError)
def handle_expired_error(e):
    return jsonify(re_code=RET.SESSIONERR, msg='token已过期，请重新登录')


@api.route('/logout', methods=['POST'])
@jwt_required()
def Logout():
    """
    用户在登录状态点击退出登录时，需要清除用户的登录状态
    :return:
    """
    current_user_id = auth.get_userinfo()
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
    """
    修改用户密码
    :return:
    """
    current_user_id = auth.get_userinfo()
    current_password = request.json.get('current_password')
    new_password = request.json.get('new_password')
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
        current_app.logger.debug(e)
        db.session.rollback()
        return jsonify(re_code=RET.DBERR, msg='密码修改失败')


@api.route('/resetpassowrd', methods=['POST'])
# @jwt_required()
def ResetPassword():
    # current_user_id = auth.get_userinfo()
    phone = request.json.get('phone')
    new_password = request.json.get('new_password')

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
        current_app.logger.debug(e)
        user.rollback()
        return jsonify(re_code=RET.OK, msg='密码修改失败')
