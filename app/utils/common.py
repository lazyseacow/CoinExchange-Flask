from functools import wraps
from flask import session, jsonify, g
from .response_code import RET


def login_required(view_func):
    """
    登录校验装饰器
    :param view_func:函数名
    :return: 闭包函数名
    """

    @wraps(view_func)
    def wrapper(*args, **kwargs):
        # 从session中获取user_id
        user_id = session.get('user_id')
        if not user_id:
            return jsonify(re_code=RET.SESSIONERR, msg='用户未登录')

        else:
            g.user_id = user_id
            return view_func(*args, **kwargs)

    return wrapper
