import logging


class BaseConfig:
    # 配置redis数据库
    REDIS_HOST = '127.0.0.1'
    REDIS_PORT = 6379
    REDIS_DB = 1

    # 配置mongodb数据库

    # 配置


class TestingConfig(BaseConfig):
    DEBUG = True
    LOGGING_LEVEL = logging.DEBUG
    SQLALCHEMY_DATABASE_URI = "mysql+pymysql://Bean:124127@127.0.0.1:3306/test"


class DevelopmentConfig(BaseConfig):
    DEBUG = False
    LOGGING_LEVEL = logging.WARNING
    SQLALCHEMY_DATABASE_URI = "mysql+pymysql://Bean:124127@127.0.0.1:3306/test"


config = {
    "testing": TestingConfig,
    "development": DevelopmentConfig,
}
