from flask_jwt_extended import get_jwt_identity


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


auth = Auth()
