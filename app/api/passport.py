from datetime import datetime, timedelta
from flask import current_app, jsonify, request
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity, create_refresh_token, decode_token
from flask_httpauth import HTTPBasicAuth
from app import db
from app.api import api
from app.models import User
from app.utils.response_code import RET


auth = HTTPBasicAuth()


@api.route('/register', methods=['POST'])
def signin():
    nickname = request.json.get('nickname')
    email = request.json.get('email')
    phone = request.json.get('phone')
    password = request.json.get('password')

    if not all([email, phone, password]):
        return jsonify(errno=RET.PARAMERR, msg='参数不完整')

    user = User()
    phone_exist = user.query.filter_by(phone=phone).first()

    if phone_exist:
        return jsonify(re_code=RET.DATAEXIST, msg='手机号已注册')

    user.nickname = nickname
    user.email = email
    user.phone = phone
    user.password_hash = user.set_password_hash(password)
    user.join_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    user.last_seen = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    try:
        db.session.add(user)
        db.session.commit()
    except Exception as e:
        current_app.logger.debug(e)
        db.session.rollback()
        return jsonify(re_code=RET.DBERR, msg='注册失败')

    return jsonify(re_code=RET.OK, msg='注册成功')


@api.route('/login', methods=['POST'])
def login():
    """
    login
    TODO:添加图片验证码
    :return: 返回响应，保持登录状态
    """

    phone = request.json.get('phone')
    password = request.json.get('password')

    if not all([phone, password]):
        return jsonify(re_code=RET.PARAMERR, msg='账号或密码不能为空')

    try:
        user = User.query.filter_by(phone=phone).first()
    except Exception as e:
        current_app.logger.debug(e)
        return jsonify(re_code=RET.DBERR, msg='查询用户失败')

    if not user:
        return jsonify(re_code=RET.NODATA, msg='用户不存在', user=user)

    if not user.verify_password(password):
        return jsonify(re_code=RET.PWDERR, msg='账户名或密码错误')

    user.update_last_seen()
    access_token = create_access_token(identity=user.phone, expires_delta=timedelta(seconds=10), fresh=True)
    refresh_token = create_refresh_token(identity=user.phone)
    return jsonify(re_code=RET.OK, msg='登录成功', access_token=access_token, refresh_token=refresh_token)


@api.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    """
    用户在登录状态点击退出登录时，需要清除用户的登录状态
    :return:
    """
    current_user_phone = get_jwt_identity()
    if User.query.filter_by(phone=current_user_phone):
        return jsonify(re_code=RET.OK, msg='退出成功')
    else:
        return jsonify(re_code=RET.NODATA, msg='退出失败')


@api.route("/refresh", methods=["POST"])
@jwt_required(refresh=True)
def refresh():
    identity = get_jwt_identity()
    access_token = create_access_token(identity=identity)
    return jsonify(access_token=access_token)


@api.route('/protected', methods=['POST'])
@jwt_required()
def protected():
    """
    logout
    :return:
    """
    current_user_phone = get_jwt_identity()
    if User.query.filter_by(phone=current_user_phone):
        return jsonify(msg='身份认证成功')
    else:
        return jsonify(msg='身份认证失败')
