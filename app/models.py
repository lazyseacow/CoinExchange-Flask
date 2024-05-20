from datetime import datetime

from flask import current_app
from itsdangerous import Serializer, SignatureExpired, BadSignature
from werkzeug.security import generate_password_hash, check_password_hash

from . import db


class User:
    """
    用户表
    """
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, index=True)
    phone = db.Column(db.String(255), unique=True, index=True)
    password_hash = db.Column(db.String(128))
    join_time = db.Column(db.DateTime, default=datetime.utcnow)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def password(self):
        raise AttributeError('密码不可访问')

    @password.setter
    def password(self, password):
        """
        生成hash密码
        """
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        """
        验证密码
        :param password:
        :return: 验证成功返回True，失败返回Flase
        """
        return check_password_hash(self.password_hash, password)

    def generate_user_token(self, expiration=43200):
        """
        生成确认身份的token
        :param expiration: 有效期限，默认12h
        :return: 加密过的token
        """
        s = Serializer(current_app.config['SECRET_KEY'], expires_in=expiration)
        return s.dumps({'id': self.id, 'mail': self.email}).decode('utf-8')

    @staticmethod
    def verify_user_token(token):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.load(token)
        except SignatureExpired:
            return None
        except BadSignature:
            return None
        user = User.query.get(data['id'])
        return user

    def update_last_seen(self):
        self.last_seen = datetime.utcnow()
        db.session.add(self)

    def to_json(self):
        return {
            'user_id': self.id,
            'nickname': self.nickname,
            'email': self.email
        }

    def __repr__(self):
        return '<User %r>' % self.nickname