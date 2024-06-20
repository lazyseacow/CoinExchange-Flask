# -*- coding: utf-8 -*-
import os
import logging
from datetime import datetime
from logging.handlers import RotatingFileHandler


def setupLogging(level, log_type):
    """
    创建日志记录
    """
    # 确定日志目录的路径，这里假设所有日志都放在项目根目录下的logs文件夹
    log_directory = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
    os.makedirs(log_directory, exist_ok=True)

    # 创建日志文件的完整路径
    log_file_path = os.path.join(log_directory, f"{datetime.now().strftime('%Y-%m-%d')}-{log_type}.log")

    # 获取根Logger
    logger = logging.getLogger()
    logger.setLevel(level)

    # 检查是否已经有handler存在，防止重复添加
    if not logger.handlers:
        # 创建RotatingFileHandler处理器
        file_log_handler = RotatingFileHandler(log_file_path, maxBytes=1024 * 1024 * 100, backupCount=10, encoding='utf-8')
        # 创建日志记录的格式
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s')
        file_log_handler.setFormatter(formatter)
        # 为Logger添加Handler
        logger.addHandler(file_log_handler)
    else:
        # 可选：更新现有handler的文件路径（高级用法）
        logger.handlers[0].baseFilename = log_file_path

    return logger
