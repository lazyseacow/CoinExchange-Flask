import random
import re
from flask import current_app, jsonify, request
from app import redis_conn
from app.models import User
from app.utils.response_code import RET
from app.utils.email import send_email
from . import api


@api.route('/mailcode', methods=['POST'])
def send_mail_code():
    phone = request.json.get('phone')
    email = request.json.get('email')

    if not all([phone, email]):
        return jsonify(re_code=RET.PARAMERR, msg='请填写完整的注册信息')

    # 邮箱匹配正则
    # ^[a-zA-Z0-9_.-]+@[a-zA-Z0-9-]+(\.[a-zA-Z0-9-]+)*\.[a-zA-Z0-9]{2,6}$
    # 手机号匹配正则
    # ^0\d{2,3}\d{7,8}$|^1[358]\d{9}$|^147\d{8}$

    if not re.match(r'^[a-zA-Z0-9_.-]+@[a-zA-Z0-9-]+(\.[a-zA-Z0-9-]+)*\.[a-zA-Z0-9]{2,6}$', email):
        return jsonify(re_code=RET.PARAMERR, msg='邮箱格式不正确')

    try:
        user_mail = User.query.filter_by(email=email).first()
        user_phone = User.query.filter_by(phone=phone).first()
    except Exception as e:
        current_app.logger.debug(e)
        return jsonify(re_code=RET.DBERR, msg='数据库查询错误')
    if user_mail or user_phone:
        return jsonify(re_code=RET.DATAEXIST, msg='邮箱或昵称已存在')

    # 生成邮箱验证码
    email_code = random.randint(1000, 9999)
    current_app.logger.debug(f'邮箱验证码为：{email_code}')

    try:
        redis_conn.setex('email_code_%s' + email, 1800, email_code)     # 30分钟过期
    except Exception as e:
        current_app.logger.debug(e)
        return jsonify(re_code=RET.DBERR, msg='存储邮箱验证码失败')

    send_email(
        to=email,
        phone=phone,
        mailcode=email_code
    )

    return jsonify(re_code=RET.OK, msg='验证码发送成功')
