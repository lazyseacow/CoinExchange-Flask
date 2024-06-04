import logging

from redis import StrictRedis


class BaseConfig:
    SQLALCHEMY_COMMIT_ON_TEARDOWN = True
    # 是否开启跟踪
    SQLALCHEMY_TRACK_MODIFICATIONS = True
    JWT_SECRET_KEY = "h1f56j19im1k61wa7p3r0"
    # 数据库配置
    SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://root:123456@127.0.0.1:3306/coinexchange'

    # 配置redis数据库
    REDIS_HOST = '127.0.0.1'
    REDIS_PORT = 6379
    REDIS_DB = 1
    # 配置session数据存储到redis数据库
    SESSION_TYPE = 'redis'
    # 指定存储session数据的redis的位置
    SESSION_REDIS = StrictRedis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)
    # 开启session数据的签名，意思是让session数据不以明文形式存储
    SESSION_USE_SIGNER = True
    # 設置session的会话的超时时长 ：一天,全局指定
    PERMANENT_SESSION_LIFETIME = 3600 * 24

    # 配置mongodb数据库

    # QQ邮箱配置
    MAIL_DEBUG = True             # 开启debug，便于调试看信息
    MAIL_SUPPRESS_SEND = False    # 发送邮件，为True则不发送
    MAIL_SERVER = 'smtp.qq.com'   # 邮箱服务器
    MAIL_PORT = 465               # 端口
    MAIL_USE_SSL = True           # 重要，qq邮箱需要使用SSL
    MAIL_USE_TLS = False          # 不需要使用TLS
    MAIL_USERNAME = 'ymp13437540086@163.com'  # 填邮箱
    MAIL_PASSWORD = 'ttvnyuzklhqbjeg'      # 填授权码
    FLASK_MAIL_SENDER = 'testing！<ymp13437540086@163.com>'   # 邮件发送方
    FLASK_MAIL_SUBJECT_PREFIX = '[testing]'     # 邮件标题
    # MAIL_DEFAULT_SENDER = 'xxx@qq.com'  # 填邮箱，默认发送者


class TestingConfig(BaseConfig):
    DEBUG = True
    LOGGING_LEVEL = logging.DEBUG
    SQLALCHEMY_DATABASE_URI = "mysql+pymysql://root:123456@127.0.0.1:3306/coinexchange"


class DevelopmentConfig(BaseConfig):
    DEBUG = False
    LOGGING_LEVEL = logging.WARNING
    SQLALCHEMY_DATABASE_URI = "mysql+pymysql://root:123456@127.0.0.1:3306/coinexchange"


APP_ENV = "testing"

config = {
    "testing": TestingConfig,
    "development": DevelopmentConfig,
}

# 数字货币支持种类
currency_list = ["USDT", "BTC", "ETH", "LTC", "ETC", "XRP", "BCH", "TRX", "XMR", "DASH", "EOS", "LINK", "XLM", "ZEC", "UNI", "DOGE", "QRL", "ZUGA", "XTZ", "IOTA"]
