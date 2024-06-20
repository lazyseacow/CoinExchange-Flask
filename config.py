import logging
from datetime import timedelta

from redis import StrictRedis


class BaseConfig:
    SQLALCHEMY_COMMIT_ON_TEARDOWN = True
    # 是否开启跟踪
    SQLALCHEMY_TRACK_MODIFICATIONS = True

    JWT_SECRET_KEY = "h1f56j19im1k61wa7p3r0"
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(days=30)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=3)

    # 签名密钥
    SECRET_KEY = "你好hello안녕하세요こんにちは."

    # 分页器配置
    PAGE_SIZE = 10

    # 数据库配置
    SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://root:123456@127.0.0.1:3306/coinexchange'
    SQLALCHEMY_ENGINE_OPTIONS = {
        'isolation_level': 'SERIALIZABLE'  # 可选 'READ COMMITTED', 'REPEATABLE READ', 'SERIALIZABLE'
    }

    # 配置redis数据库
    REDIS_HOST = '127.0.0.1'
    REDIS_PORT = 6379
    REDIS_DB = 1

    # 配置celery
    BROKER_URL = 'redis://localhost:6379/0'
    broker_connection_retry_on_startup = True


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
subscribe_trade = {
    "method": "SUBSCRIBE",
    "params": [
        "btcusdt@ticker",
        "ethusdt@ticker",
        "ltcusdt@ticker",
        "etcusdt@ticker",
        "xrpusdt@ticker",
        "bchusdt@ticker",
        "trxusdt@ticker",
        "xmrusdt@ticker",
        "dashusdt@ticker",
        "eosusdt@ticker",
        "linkusdt@ticker",
        "xlmusdt@ticker",
        "zecusdt@ticker",
        "uniusdt@ticker",
        "dogeusdt@ticker",
        "qrlusdt@ticker",
        "zugausdt@ticker",
        "xtzusdt@ticker",
        "iotausdt@ticker"
        # "shibusdt@ticker"
    ]
}
