from datetime import datetime

from sqlalchemy import UniqueConstraint
from cryptography import fernet
from sqlalchemy.orm import backref
from werkzeug.security import generate_password_hash, check_password_hash

from app import db


# 交易对列表
class Symbols(db.Model):
    """
    交易对表
    """
    __tablename__ = 'symbols'

    symbol_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    symbol = db.Column(db.String(255), unique=True, index=True)
    base_currency = db.Column(db.String(255))
    quote_currency = db.Column(db.String(255))
    # price_precision = db.Column(db.Integer)


# 用户信息服务
class User(db.Model):
    """
    用户表
    """
    __tablename__ = 'user'

    user_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(255))
    email = db.Column(db.String(255), unique=True, index=True)
    phone = db.Column(db.String(255), unique=True, index=True)
    _password_hash = db.Column(db.String(256))
    join_time = db.Column(db.DateTime, default=datetime.now())
    last_seen = db.Column(db.DateTime, default=datetime.now())

    erc20_address = db.Column(db.String(255))
    erc20_private_key = db.Column(db.String(255))

    trc20_address = db.Column(db.String(255))
    trc20_private_key = db.Column(db.String(255))

    user_authentications = db.relationship('UserAuthentication', backref='user', lazy='dynamic')
    user_activity_logs = db.relationship('UserActivityLogs', backref='user', lazy='dynamic')
    wallets = db.relationship('Wallet', backref='user', lazy='dynamic')
    wallet_operations = db.relationship('WalletOperations', backref='user', lazy='dynamic')
    bind_wallets = db.relationship('BindWallets', backref='user', lazy='dynamic')
    entrustments = db.relationship('Entrustment', backref='user', lazy='dynamic')
    orders = db.relationship('Orders', backref='user', lazy='dynamic')
    depositswithdrawals = db.relationship('DepositsWithdrawals', backref='user', lazy='dynamic')

    @classmethod
    def log_user_info(cls, username, email, phone, _password_hash, join_time, last_seen):
        user = cls(username=username, email=email, phone=phone, _password_hash=_password_hash, join_time=join_time, last_seen=last_seen)
        user.save()

    def save(self):
        """保存数据"""
        db.session.add(self)
        db.session.commit()

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
        self.last_seen = datetime.now()
        db.session.add(self)

    def to_json(self):
        return {
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
    auth_type = db.Column(db.Enum('email', 'phone'))
    auth_status = db.Column(db.Enum('success', 'failed'))
    auth_account = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.now())

    user_id = db.Column(db.Integer, db.ForeignKey('user.user_id'), nullable=False)

    @classmethod
    def log_auth(cls, user_id, auth_type, auth_status, auth_account):
        auth = cls(user_id=user_id, auth_type=auth_type, auth_status=auth_status, auth_account=auth_account)
        auth.save()

    def save(self):
        """保存数据"""
        db.session.add(self)
        db.session.commit()

    def to_json(self):
        return {
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
    setting_type = db.Column(db.Enum('ip_whitelist', 'transaction_limit', 'two_factor_authentication', 'account lockout policy'))
    setting_value = db.Column(db.String(255))
    enabled = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.now())
    updated_at = db.Column(db.DateTime, default=datetime.now())
    UniqueConstraint(setting_type, setting_value)

    user_id = db.Column(db.Integer, db.ForeignKey('user.user_id'), nullable=False)

    def save(self):
        """保存数据"""
        db.session.add(self)
        db.session.commit()

    def to_json(self):
        return {
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

    @classmethod
    def log_activity(cls, user_id, activity_type, activity_details):
        log = cls(user_id=user_id, activity_type=activity_type, activity_details=activity_details)
        log.save()

    def save(self):
        """保存数据"""
        db.session.add(self)
        db.session.commit()

    def to_json(self):
        return {
            'activity_type': self.activity_type,
            'activity_time': self.activity_time,
            'activity_details': self.activity_details
        }


# 钱包服务
class PayPassword(db.Model):
    """
    支付密码表:用于存储用户的支付密码，可能需要多个支付密码表
    """
    __tablename__ = 'pay_password'
    pay_password_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    _pay_password_hash = db.Column(db.String(255))
    update_at = db.Column(db.DateTime, default=datetime.now())
    user_id = db.Column(db.Integer, db.ForeignKey('user.user_id'), nullable=False, index=True)

    @property
    def password(self):
        raise AttributeError('密码不可访问')

    @password.setter
    def password(self, password):
        """
        生成hash密码
        """
        self._pay_password_hash = generate_password_hash(password)

    def verify_password(self, password):
        """
        验证密码
        :param password:
        :return: 验证成功返回True，失败返回False
        """
        if self._pay_password_hash is None:
            return False
        return check_password_hash(self._pay_password_hash, password)

    def update_at(self):
        self.update_at = datetime.now()
        db.session.add(self)


class BindWallets(db.Model):
    """
    钱包绑定表:用于存储用户的加密货币钱包地址，可能需要多个钱包绑定表
    """
    __tablename__ = 'bind_wallets'

    bind_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    symbol = db.Column(db.String(255))
    address = db.Column(db.String(255))
    # private_key = db.Column(db.String(255))
    agreement_type = db.Column(db.String(255))
    comment = db.Column(db.Text(255))
    created_at = db.Column(db.DateTime, default=datetime.now())
    user_id = db.Column(db.Integer, db.ForeignKey('user.user_id'), nullable=False)

    def to_json(self):
        return {
            'bind_id': self.bind_id,
            'symbol': self.symbol,
            'address': self.address,
            # 'private_key': self.private_key,
            'agreement_type': self.agreement_type,
            # 'comment': self.comment,
            # 'created_at': self.created_at
        }


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

    # order = db.Column(db.Integer, db.ForeignKey('Orders.order_id'), nullable=False)

    @classmethod
    def log_transaction(cls, user_id, symbol, balance, frozen_balance):
        transaction = cls(user_id=user_id, symbol=symbol, balance=balance, frozen_balance=frozen_balance)
        transaction.save()

    def save(self):
        """保存数据"""
        db.session.add(self)
        db.session.commit()

    def to_json(self):
        return {
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
    symbol = db.Column(db.String(255), index=True)
    operation_type = db.Column(db.String(255))
    operation_time = db.Column(db.DateTime, default=datetime.now())
    amount = db.Column(db.DECIMAL(18, 8))
    status = db.Column(db.String(255), index=True)

    user_id = db.Column(db.Integer, db.ForeignKey('user.user_id'), nullable=False, index=True)

    @classmethod
    def log_operation(cls, user_id, symbol, operation_type, amount, status):
        operation = cls(user_id=user_id, symbol=symbol, operation_type=operation_type, amount=amount, status=status)
        operation.save()

    def save(self):
        """保存数据"""
        db.session.add(self)
        db.session.commit()

    def to_json(self):
        return {
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

    def save(self):
        """保存数据"""
        db.session.add(self)
        db.session.commit()

    def to_json(self):
        return {
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

    def save(self):
        """保存数据"""
        db.session.add(self)
        db.session.commit()

    def to_json(self):
        return {
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
    status = db.Column(db.Enum('unpaid', 'pending', 'completed', 'failed'))
    transaction_id = db.Column(db.String(255))
    fee = db.Column(db.DECIMAL(18, 8))
    finally_amount = db.Column(db.DECIMAL(18, 8))
    create_at = db.Column(db.DateTime, default=datetime.now())
    update_at = db.Column(db.DateTime, default=datetime.now())

    user_id = db.Column(db.Integer, db.ForeignKey('user.user_id'), nullable=False)

    def to_json(self):
        return {
            'transaction_type': self.transaction_type,
            'symbol': self.symbol,
            'amount': self.amount,
            'status': self.status,
            'transaction_id': self.transaction_id,
            'create_at': self.create_at,
            'update_at': self.update_at
        }


class Fees(db.Model):
    """
    交易费率:用于存储交易费率信息
    """
    __tablename__ = 'fees'
    fee_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    currency = db.Column(db.String(255))
    fee_rate = db.Column(db.DECIMAL(18, 8))
    create_at = db.Column(db.DateTime, default=datetime.now())
    update_at = db.Column(db.DateTime, default=datetime.now())

    def to_json(self):
        return {
            'currency': self.currency,
            'fee_rate': self.fee_rate,
        }


class Orders(db.Model):
    """
    法币订单:用于存储用户提交的买卖订单交易
    """
    __tablename__ = 'orders'

    order_id = db.Column(db.Integer, primary_key=True, autoincrement=True, index=True)
    order_type = db.Column(db.Enum('market', 'limit'))
    side = db.Column(db.Enum('buy', 'sell'))
    symbol = db.Column(db.String(255), index=True)
    price = db.Column(db.DECIMAL(18, 8))
    executed_price = db.Column(db.DECIMAL(18, 8))
    quantity = db.Column(db.DECIMAL(18, 8))
    status = db.Column(db.Enum('pending', 'filled', 'canceled', 'rejected'), index=True)
    created_at = db.Column(db.DateTime, default=datetime.now(), index=True)
    update_at = db.Column(db.DateTime, default=datetime.now(), index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.user_id'), nullable=False, index=True)

    def save(self):
        """保存数据"""
        db.session.add(self)
        db.session.commit()

    def to_json(self):
        return {
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
    transaction_uuid = db.Column(db.String(255), index=True)
    buyer_order_id = db.Column(db.Integer, db.ForeignKey('orders.order_id'), nullable=False)
    seller_oeder_id = db.Column(db.Integer, db.ForeignKey('orders.order_id'), nullable=False)
    amount = db.Column(db.DECIMAL(18, 8))
    price = db.Column(db.DECIMAL(18, 8))
    created_at = db.Column(db.DateTime, default=datetime.now())

    def save(self):
        """保存数据"""
        db.session.add(self)
        db.session.commit()

    def to_json(self):
        return {
            'buyer_order_id': self.buyer_order_id,
            'seller_oeder_id': self.seller_oeder_id,
            'amout': self.amout,
            'price': self.price,
            'create_at': self.create_at
        }


class Entrustment(db.Model):
    """
    委托单:用于记录用户在交易市场中的委托单信息，包括买入和卖出订单
    """
    __tablename__ = 'entrustment'
    entrustment_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    symbol = db.Column(db.String(255))
    entrustment_type = db.Column(db.Enum('buy', 'sell'))
    side = db.Column(db.Enum('buy', 'sell'))
    price = db.Column(db.DECIMAL(18, 8))
    quantity = db.Column(db.DECIMAL(18, 8))
    status = db.Column(db.Enum('pending', 'filled', 'canceled', 'rejected'), index=True)
    create_at = db.Column(db.DateTime, default=datetime.now(), index=True)
    update_at = db.Column(db.DateTime, default=datetime.now())
    stop_profit_percentage = db.Column(db.DECIMAL(18, 8))
    stop_loss_percentage = db.Column(db.DECIMAL(18, 8))

    user_id = db.Column(db.Integer, db.ForeignKey('user.user_id'), nullable=False, index=True)


# 用户后台管理模块
class Admins(db.Model):
    """
    管理员表:用于存储管理员的信息，包括用户名、密码等
    """
    __tablename__ = 'admins'

    admin_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(255), unique=True)
    password = db.Column(db.String(255))
    role = db.Column(db.String(255), index=True, default='admin')
    create_at = db.Column(db.DateTime, default=datetime.now())
    update_at = db.Column(db.DateTime, default=datetime.now())


class Roles(db.Model):
    """
    角色表:用于定义用户的角色，包括管理员、普通用户等
    """
    __tablename__ = 'roles'

    role_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    role_name = db.Column(db.String(255))
    permissions = db.Column(db.Text())  # 以JSON格式存储

    def save(self):
        """保存数据"""
        db.session.add(self)
        db.session.commit()

    def to_json(self):
        return {
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

    def save(self):
        """保存数据"""
        db.session.add(self)
        db.session.commit()

    def to_json(self):
        return {
            'user_id': self.user_id,
            'rold_id': self.rold_id
        }


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

    def save(self):
        """保存数据"""
        db.session.add(self)
        db.session.commit()

    def to_json(self):
        return {
            'audit_type': self.audit_type,
            'audit_status': self.audit_status,
            'audit_detail': self.audit_detail,
            'create_at': self.create_at
        }