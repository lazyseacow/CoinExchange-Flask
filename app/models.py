from datetime import datetime

from sqlalchemy import UniqueConstraint
from cryptography import fernet
from werkzeug.security import generate_password_hash, check_password_hash

from . import db


# 用户信息服务
class User(db.Model):
    """
    用户表
    """
    __tablename__ = 'user'

    user_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(255))
    email = db.Column(db.String(255), index=True)
    phone = db.Column(db.String(255), unique=True, index=True)
    _password_hash = db.Column(db.String(256))
    join_time = db.Column(db.DateTime, default=datetime.now())
    last_seen = db.Column(db.DateTime, default=datetime.now())

    @property
    def password(self):
        raise AttributeError('密码不可访问')

    @password.setter
    def password(self, password):
        """
        生成hash密码
        """
        self._password_hash = generate_password_hash(password)

    def verify_password(self, password):
        """
        验证密码
        :param password:
        :return: 验证成功返回True，失败返回False
        """
        if self._password_hash is None:
            return False
        return check_password_hash(self._password_hash, password)

    def update_last_seen(self):
        self.last_seen = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        db.session.add(self)

    def to_json(self):
        return {
            'user_id': self.id,
            'phone': self.phone,
            'email': self.email
        }

    def __repr__(self):
        return '<User %r>' % self.username


class UserAuthentication(db.Model):
    """
    用户身份验证表:用来存储用户的登录方法和相关的的安全设置
    """
    __tablename__ = 'user_authentication'

    auth_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    auth_type = db.Column(db.String(255))
    auth_key = db.Column(db.String(255))
    enabled = db.Column(db.Boolean, default=True)

    user_id = db.Column(db.Integer, db.ForeignKey('user.user_id'), nullable=False)

    def to_json(self):
        return {
            'auth_id': self.auth_id,
            'auth_type': self.auth_type,
            'auth_key': self.auth_key,
            'enabled': self.enabled
        }


class UserSecuritySettings(db.Model):
    """
    用户安全设置表:用于存储用户的安全相关设置，比如IP白名单、交易限额
    """
    __tablename__ = 'user_security_settings'

    setting_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    setting_type = db.Column(db.Enum('ip_whitelist', 'transaction_limit'))
    setting_value = db.Column(db.String(255))

    user_id = db.Column(db.Integer, db.ForeignKey('user.user_id'), nullable=False)

    def to_json(self):
        return {
            'setting_id': self.setting_id,
            'setting_type': self.setting_type,
            'setting_value': self.setting_value
        }


class UserActivityLogs(db.Model):
    """
    用户活动日志表:用于记录用户的关键活动和交易，有助于审计和安全监控
    """
    __tablename__ = 'user_activity_logs'

    log_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    activity_type = db.Column(db.String(255))
    activity_time = db.Column(db.DateTime, default=datetime.now())
    activity_details = db.Column(db.String(255))

    user_id = db.Column(db.Integer, db.ForeignKey('user.user_id'), nullable=False)

    def to_json(self):
        return {
            'log_id': self.log_id,
            'activity_type': self.activity_type,
            'activity_time': self.activity_time,
            'activity_details': self.activity_details
        }


class APIKeys(db.Model):
    """
    API密钥表:对接第三方API的密钥管理
    TODO:未来根据第三方平台对密钥进行加密保存
    """

    __tablename__ = 'api_keys'

    key_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    api_key = db.Column(db.String(255))
    api_secret = db.Column(db.String(255))
    permissions = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.now())

    user_id = db.Column(db.Integer, db.ForeignKey('user.user_id'), nullable=False)

    def to_json(self):
        return {
            'key_id': self.key_id,
            'api_key': self.api_key,
            'api_secret': self.api_secret,
            'permissions': self.permissions,
            'created_at': self.created_at
        }


# 钱包服务
class Wallet(db.Model):
    """
    钱包表:管理用户的加密货币余额与交易，可能需要多个钱包表
    """
    __tablename__ = 'wallet'

    wallet_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    symbol = db.Column(db.String(255))
    balance = db.Column(db.DECIMAL(18, 8), default=0.0)
    frozen_balance = db.Column(db.DECIMAL(18, 8), default=0.0)

    user_id = db.Column(db.Integer, db.ForeignKey('user.user_id'), nullable=False)

    def to_json(self):
        return {
            'wallet_id': self.wallet_id,
            'symbol': self.symbol,
            'balance': self.balance,
            'frozen_balance': self.frozen_balance
        }


class WalletOperations(db.Model):
    """
    钱包操作日志表:记录钱包的所有操作活动，如充值、提款等
    """
    __tablename__ = 'wallet_operations'

    operation_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    operation_type = db.Column(db.String(255))
    operation_time = db.Column(db.DateTime, default=datetime.now())
    amount = db.Column(db.DECIMAL(18, 8))
    status = db.Column(db.String(255))

    user_id = db.Column(db.Integer, db.ForeignKey('user.user_id'), nullable=False)

    def to_json(self):
        return {
            'operation_id': self.operation_id,
            'operation_type': self.operation_type,
            'operation_time': self.operation_time,
            'amount': self.amount,
            'status': self.status
        }


class WalletEventsLogs(db.Model):
    """
    钱包事件日志表:用户记录与钱包相关的所有重要安全事件，如登陆尝试、非法操作尝试、重要设置修改等
    """
    __tablename__ = 'wallet_events_logs'

    event_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    event_type = db.Column(db.String(255))
    event_time = db.Column(db.DateTime, default=datetime.now())
    description = db.Column(db.String(255))
    ip_address = db.Column(db.String(255))
    user_agent = db.Column(db.String(255))
    is_suspicious = db.Column(db.Boolean, default=False)

    wallet_id = db.Column(db.Integer, db.ForeignKey('wallet.wallet_id'), nullable=False)

    def to_json(self):
        return {
            'event_id': self.event_id,
            'event_type': self.event_type,
            'event_time': self.event_time,
            'description': self.description,
            'ip_address': self.ip_address,
        }


class SecurityPolicies(db.Model):
    """
    安全策略表:用户定义和管理钱包的安全策略，如每日提款限额、交易确认等
    """
    __tablename__ = 'security_policies'

    policy_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    policy_type = db.Column(db.String(255))
    policy_details = db.Column(db.String(255))
    enabled = db.Column(db.Boolean, default=True)
    create_at = db.Column(db.DateTime, default=datetime.now())

    wallet_id = db.Column(db.Integer, db.ForeignKey('wallet.wallet_id'), nullable=False)

    def to_json(self):
        return {
            'policy_id': self.policy_id,
            'policy_type': self.policy_type,
            'policy_details': self.policy_details,
            'enabled': self.enabled,
            'create_at': self.create_at
        }


# 法币交易服务
class DepositsWithdrawals(db.Model):
    """
    充值与提现:管理用户的法币和数字货币的存款和提款操作
    """
    __tablename__ = 'deposits_withdrawals'

    record_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    transaction_type = db.Column(db.Enum('deposit', 'withdrawal'))
    symbol = db.Column(db.String(255))
    amount = db.Column(db.DECIMAL(18, 8))
    status = db.Column(db.Enum('pending', 'completed', 'failed'))
    transaction_id = db.Column(db.String(255))
    create_at = db.Column(db.DateTime, default=datetime.now())
    update_at = db.Column(db.DateTime, default=datetime.now())

    user_id = db.Column(db.Integer, db.ForeignKey('user.user_id'), nullable=False)

    def to_json(self):
        return {
            'record_id': self.record_id,
            'transaction_type': self.transaction_type,
            'symbol': self.symbol,
            'amount': self.amount,
            'status': self.status,
            'transaction_id': self.transaction_id,
            'create_at': self.create_at,
            'update_at': self.update_at
        }


class Orders(db.Model):
    """
    法币订单:用于存储用户提交的买卖订单交易
    """
    __tablename__ = 'orders'

    order_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    order_type = db.Column(db.Enum('buy', 'sell'))
    symbol = db.Column(db.String(255))
    price = db.Column(db.DECIMAL(18, 8))
    quantity = db.Column(db.DECIMAL(18, 8))
    status = db.Column(db.Enum('open', 'filled', 'partially_filled', 'canceled'))
    create_at = db.Column(db.DateTime, default=datetime.now())
    update_at = db.Column(db.DateTime, default=datetime.now())

    user_id = db.Column(db.Integer, db.ForeignKey('user.user_id'), nullable=False)

    def to_json(self):
        return {
            'order_id': self.order_id,
            'order_type': self.order_type,
            'symbol': self.symbol,
            'price': self.price,
            'quantity': self.quantity,
            'status': self.status,
            'create_at': self.create_at,
            'update_at': self.update_at
        }


class Transactions(db.Model):
    """
    交易记录:记录所有完成的交易，包括买卖双方的订单匹配结果
    """
    __tablename__ = 'transactions'

    transaction_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    buyer_order_id = db.Column(db.Integer, db.ForeignKey('orders.order_id'), nullable=False)
    seller_oeder_id = db.Column(db.Integer, db.ForeignKey('orders.order_id'), nullable=False)
    amout = db.Column(db.DECIMAL(18, 8))
    price = db.Column(db.DECIMAL(18, 8))
    create_at = db.Column(db.DateTime, default=datetime.now())


# 用户后台管理模块
class Roles(db.Model):
    """
    角色表:用于定义用户的角色，包括管理员、普通用户等
    """
    __tablename__ = 'roles'

    role_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    role_name = db.Column(db.String(255))
    permissions = db.Column(db.Text())  # 以JSON格式存储

    def to_json(self):
        return {
            'role_id': self.role_id,
            'role_name': self.role_name,
            'permissions': self.permissions
        }


class UserRoles(db.Model):
    """
    用户角色表:用于关联用户和角色，一个用户可以有多个角色
    """
    __tablename__ = 'user_roles'

    user_role_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.user_id'), nullable=False)
    rold_id = db.Column(db.Integer, db.ForeignKey('roles.role_id'), nullable=False)


class Companies(db.Model):
    """
    审计与合规表:用于管理和跟踪合规性审核，特别是处理大额交易和敏感操作时
    """
    __tablename__ = 'companies'

    audit_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    audit_type = db.Column(db.Enum('large_transaction', 'sensitive_operation', 'account_verification'))
    audit_status = db.Column(db.Enum('pending', 'approved', 'rejected'))
    audit_detail = db.Column(db.Text())     # 以JSON格式存储
    create_at = db.Column(db.DateTime, default=datetime.now())
