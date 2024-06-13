import logging
from datetime import datetime
from logging.handlers import RotatingFileHandler

import redis
from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_sqlalchemy import SQLAlchemy
# from flask_mail import Mail
from config import APP_ENV, config
from app.tasks.celery_utils import make_celery


db = SQLAlchemy()
# mail = Mail()

redis_conn = None


def setupLogging(level):
    """
    创建日志记录
    """
    # 设置日志的记录等级
    logging.basicConfig(level=level)
    # 创建日志记录器，指明日志保存的路径、每个日志文件的最大大小、保存的日志文件个数上限
    # TODO: 这里的日志记录可以根据日期命名文件名，方便查看每天的日志记录
    file_log_handler = RotatingFileHandler(f"D:/pyproject/CoinExchange-Flask/logs/{datetime.now().strftime('%Y-%m-%d')}.log", maxBytes=1024 * 1024 * 100, backupCount=10)
    # 创建日志记录的格式                 日志等级    输入日志信息的文件名 行数    日志信息
    formatter = logging.Formatter('%(asctime)s - %(levelname)s %(filename)s:%(lineno)d\n %(message)s')
    # 为刚创建的日志记录器设置日志记录格式
    file_log_handler.setFormatter(formatter)
    # 为全局添加日志记录器
    logging.getLogger().addHandler(file_log_handler)


def create_app():
    """
    工厂函数，创建APP实例
    :return app实例
    """
    setupLogging(config[APP_ENV].LOGGING_LEVEL)

    app = Flask(__name__)
    app.config.from_object(config[APP_ENV])
    # app.config['JWT_SECRET_KEY'] = config[APP_ENV].JWT_SECRET_KEY
    # app.config['JWT_ACCESS_TOKEN_EXPIRES'] = config[APP_ENV].JWT_ACCESS_TOKEN_EXPIRES
    # app.config['JWT_REFRESH_TOKEN_EXPIRES'] = config[APP_ENV].JWT_REFRESH_TOKEN_EXPIRES

    jwt = JWTManager(app)

    CORS(app, resources=r'/*')

    # app.after_request(after_request)

    # 创建Redis数据库连接对象
    global redis_conn
    redis_conn = redis.StrictRedis(host=app.config['REDIS_HOST'], port=app.config['REDIS_PORT'], db=app.config['REDIS_DB'])

    db.init_app(app)
    # mail.init_app(app)

    # 注册api_v1_0 蓝图
    from app.api import api
    app.register_blueprint(api)

    celery = make_celery(app)
    app.celery = celery
    return app
