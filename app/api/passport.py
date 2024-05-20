from flask import g, current_app, jsonify, request, make_response, Flask
# import bs64
from flask_httpauth import HTTPBasicAuth
from app import db, redis_conn
from app.api import api
from app.models import User
from app.utils.response_code import RET


auth = HTTPBasicAuth()


@api.route('/signin', methods=['POST'])
def signin():
    email = request.json.get('email')
    phone = request.json.get('phone')
    password = request.json.get('password')

    if not all([email, phone, password]):
        return jsonify(errno=RET.PARAMERR, errmsg='参数不完整')

    user = User()
    user.email = email
    user.phone = phone
    user.password = password

    try:
        db.session.add(user)
        db.session.commit()
    except Exception as e:
        current_app.logger.debug(e)
        db.session.rollback()
        return jsonify(re_code=RET.DBERR, errmsg='注册失败')

    return jsonify(re_code=RET.OK, errmsg='注册成功')


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
        return jsonify(re_code=RET.PARAMERR, errmsg='参数不完整')

    try:
        user = User.query.filter_by(phone=phone).first()
    except Exception as e:
        current_app.logger.debug(e)
        return jsonify(re_code=RET.DBERR, errmsg='查询用户失败')

    if not user:
        return jsonify(re_code=RET.NODATA, errmsg='用户不存在', user=user)

    if not user.verify_password(password):
        return jsonify(re_code=RET.PWDERR, errmsg='账户名或密码错误')

    user.update_last_seen()
    token = user.generate_user_token()
    return jsonify(re_code=RET.OK, errmsg='登录成功', token=token)


@auth.verify_password
def verify_password(email_or_token, password):
    if request.path == '/login':
        user = User.query.filter_by(email=email_or_token).first()
        if not user or not user.verify_password(password):
            return False
    else:
        user = User.verify_user_token(email_or_token)
        if not user:
            return False
    g.user = user
    return True


@auth.verify_password
def unauthorized():
    return make_response(jsonify({'error': 'Unauthorized access'}), 401)


@api.route('/')
@auth.login_required()
def get_resource():
    return jsonify({'data': 'Hello, %s!' % g.user.email})
