from datetime import datetime

from flask import current_app
from sqlalchemy import UniqueConstraint
from werkzeug.security import generate_password_hash, check_password_hash

from . import db


class User(db.Model):
    """
    用户表
    """
    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True)
    nickname = db.Column(db.String(255))
    email = db.Column(db.String(255), index=True)
    phone = db.Column(db.String(255), unique=True, index=True)
    password_hash = db.Column(db.String(256))
    join_time = db.Column(db.DateTime, default=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    last_seen = db.Column(db.DateTime, default=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

    @property
    def password(self):
        raise AttributeError('密码不可访问')

    def set_password_hash(self, password):
        """
        生成hash密码
        """
        return generate_password_hash(password)

    def verify_password(self, password):
        """
        验证密码
        :param password:
        :return: 验证成功返回True，失败返回False
        """
        return check_password_hash(self.password_hash, password)

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
        return '<User %r>' % self.phone


class Coin(db.Model):
    """
    币种表
    """
    __tablename__ = 'coin'

    name = db.Column(db.String(255), primary_key=True, nullable=False)
    can_auto_withdraw = db.Column(db.Integer, nullable=True)
    can_recharge = db.Column(db.Integer, nullable=True)
    can_transfer = db.Column(db.Integer, nullable=True)
    can_withdraw = db.Column(db.Integer, nullable=True)
    cny_rate = db.Column(db.Float, nullable=False)
    enable_rpc = db.Column(db.Integer, nullable=True)
    is_platform_coin = db.Column(db.Integer, nullable=True)
    max_tx_fee = db.Column(db.Float, nullable=False)
    max_withdraw_amount = db.Column(db.DECIMAL(18, 8), comment='最大提币数量', nullable=True)
    min_tx_fee = db.Column(db.Float, nullable=False)
    min_withdraw_amount = db.Column(db.DECIMAL(18, 8), comment='最小提币数量', nullable=True)
    name_cn = db.Column(db.String(255), nullable=False)
    sort = db.Column(db.Integer, nullable=False)
    status = db.Column(db.Integer, nullable=True)
    unit = db.Column(db.String(255), nullable=False)
    usd_rate = db.Column(db.Float, nullable=False)
    withdraw_threshold = db.Column(db.DECIMAL(18, 8), comment='提现阈值', nullable=True)
    has_legal = db.Column(db.Boolean, default=False, nullable=False)
    cold_wallet_address = db.Column(db.String(255), nullable=True)
    miner_fee = db.Column(db.DECIMAL(18, 8), comment='矿工费', server_default=db.text('0.00000000'))
    withdraw_scale = db.Column(db.Integer, default=4, comment='提币精度', nullable=True)

    def __repr__(self):
        return f'<Coin {self.name}>'


class ExchangeCoin(db.Model):
    __tablename__ = 'exchange_coin'

    symbol = db.Column(db.String(255), primary_key=True, nullable=False)
    base_coin_scale = db.Column(db.Integer, nullable=False)
    base_symbol = db.Column(db.String(255), nullable=True)
    coin_scale = db.Column(db.Integer, nullable=False)
    coin_symbol = db.Column(db.String(255), nullable=True)
    enable = db.Column(db.Integer, nullable=False)
    fee = db.Column(db.DECIMAL(8, 4), comment='交易手续费', nullable=True)
    sort = db.Column(db.Integer, nullable=False)
    enable_market_buy = db.Column(db.Integer, default=1, comment='是否启用市价买', nullable=False)
    enable_market_sell = db.Column(db.Integer, default=1, comment='是否启用市价卖', nullable=False)
    min_sell_price = db.Column(db.DECIMAL(18, 8), comment='最低挂单卖价', server_default=db.text('0.00000000'), nullable=False)
    flag = db.Column(db.Integer, default=0, nullable=False)
    max_trading_order = db.Column(db.Integer, default=0, comment='最大允许同时交易的订单数，0表示不限制', nullable=False)
    max_trading_time = db.Column(db.Integer, default=0, comment='委托超时自动下架时间，单位为秒，0表示不过期', nullable=False)
    instrument = db.Column(db.String(20), comment='交易类型，B2C2特有', nullable=True)
    min_turnover = db.Column(db.DECIMAL(18, 8), comment='最小挂单成交额', server_default=db.text('0.00000000'), nullable=False)

    def __repr__(self):
        return f'<ExchangeCoin {self.symbol}>'


class OtcCoin(db.Model):
    __tablename__ = 'otc_coin'

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    buy_min_amount = db.Column(db.DECIMAL(18, 8), comment='买入广告最低发布数量', nullable=True)
    is_platform_coin = db.Column(db.Integer, nullable=True)
    jy_rate = db.Column(db.DECIMAL(18, 6), comment='交易手续费率', nullable=True)
    name = db.Column(db.String(255), nullable=False)
    name_cn = db.Column(db.String(255), nullable=False)
    sell_min_amount = db.Column(db.DECIMAL(18, 8), comment='卖出广告最低发布数量', nullable=True)
    sort = db.Column(db.Integer, nullable=False)
    status = db.Column(db.Integer, nullable=True)
    unit = db.Column(db.String(255), nullable=False)

    def __repr__(self):
        return f'<OtcCoin {self.name}>'


class Country(db.Model):
    __tablename__ = 'country'

    zh_name = db.Column(db.String(255), primary_key=True, nullable=False)
    area_code = db.Column(db.String(255), nullable=True)
    en_name = db.Column(db.String(255), nullable=True)
    language = db.Column(db.String(255), nullable=True)
    local_currency = db.Column(db.String(255), nullable=True)
    sort = db.Column(db.Integer, nullable=False)

    def __repr__(self):
        return f'<Country {self.zh_name}>'


class Admin(db.Model):
    __tablename__ = 'admin'

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    avatar = db.Column(db.String(255), nullable=True)
    email = db.Column(db.String(255), nullable=True)
    enable = db.Column(db.Integer, nullable=True)
    last_login_ip = db.Column(db.String(255), nullable=True)
    last_login_time = db.Column(db.DateTime, nullable=True)
    mobile_phone = db.Column(db.String(255), nullable=False)
    password = db.Column(db.String(255), nullable=True)
    qq = db.Column(db.String(255), nullable=True)
    real_name = db.Column(db.String(255), nullable=False)
    role_id = db.Column(db.BigInteger, nullable=False)
    status = db.Column(db.Integer, nullable=True)
    username = db.Column(db.String(255), nullable=False, unique=True)
    department_id = db.Column(db.BigInteger, nullable=False)

    # 添加外键约束
    # department = db.relationship('Department', backref='admins', cascade='all, delete-orphan')

    __table_args__ = (UniqueConstraint('username', name='UK_gfn44sntic2k93auag97juyij'), {})

    def __repr__(self):
        return f'<Admin {self.username}>'


class AdminPermission(db.Model):
    __tablename__ = 'admin_permission'

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    title = db.Column(db.String(255), nullable=True)
    name = db.Column(db.String(255), nullable=True)
    parent_id = db.Column(db.BigInteger, nullable=True)
    sort = db.Column(db.Integer, nullable=True)
    description = db.Column(db.String(255), nullable=True)

    def __repr__(self):
        return f'<AdminPermission {self.name}>'


class AdminRole(db.Model):
    __tablename__ = 'admin_role'

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    description = db.Column(db.String(255), nullable=True)
    role = db.Column(db.String(255), nullable=False)

    def __repr__(self):
        return f'<AdminRole {self.role}>'


class AdminRolePermission(db.Model):
    __tablename__ = 'admin_role_permission'

    role_id = db.Column(db.BigInteger, db.ForeignKey('admin_role.id', ondelete='CASCADE'), primary_key=True)
    rule_id = db.Column(db.BigInteger, db.ForeignKey('admin_permission.id', ondelete='CASCADE'), primary_key=True)

    __table_args__ = (db.UniqueConstraint('role_id', 'rule_id'), {})
