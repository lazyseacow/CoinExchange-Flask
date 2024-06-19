from flask_jwt_extended import get_jwt_identity
import hashlib
import hmac
import base64
import time

import config


class Auth:
    def __init__(self):
        self.user_id = None

    def get_userinfo(self):
        """
        使用 get_jwt_identity解析token获取user_id
        :return:
        """
        self.user_id = get_jwt_identity()
        return self.user_id


class ApiSignature:
    def __init__(self):
        self.secret_key = config.BaseConfig.SECRET_KEY.encode('utf-8')

    def generate_signature(self, data):
        """
        生成签名
        :param data: 需要签名的数据
        :return: base64编码的签名字符串
        """
        message = data.encode('utf-8')
        signature = hmac.new(self.secret_key, message, hashlib.sha256).digest()
        signature_base64 = base64.b64encode(signature).decode()
        return signature_base64

    def verify_signature(self, data, timestamp, provided_signature):
        """
        验证签名
        :param provided_signature: 前端提供的签名
        :param data: 原始数据
        :param timestamp: 客户端提供的时间戳
        :return: 布尔值，指示签名是否有效
        """
        tolerance = 300
        # if time.time() - float(timestamp) > tolerance:
        #     return False
        message = data.encode('utf-8')
        expected_signature = hmac.new(self.secret_key, message, hashlib.sha256).digest()
        expected_signature_base64 = base64.b64encode(expected_signature).decode()
        return hmac.compare_digest(expected_signature_base64, provided_signature)


token_auth = Auth()
sign_auth = ApiSignature()
