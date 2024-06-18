import random
import datetime

import pymysql

# 数据库配置
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '123456',
    'database': 'coinexchange',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

symbols = ["USDT", "BTC", "ETH", "LTC", "ETC", "XRP", "BCH", "TRX", "XMR", "DASH", "EOS", "LINK", "XLM", "ZEC", "UNI", "DOGE", "QRL", "ZUGA", "XTZ", "IOTA"]
user_ids = [16, 17, 18, 19, 21, 22, 23, 24, 25]


# 连接数据库
connection = pymysql.connect(**db_config)

try:
    with connection.cursor() as cursor:
        for user_id in user_ids:  # 遍历每个用户
            for symbol in symbols:
                balance = round(random.uniform(0.1, 10000.0), 8)
                frozen_balance = round(random.uniform(0.1, 10000.0), 8)

                sql = ("INSERT INTO wallet (symbol, balance, frozen_balance, user_id) "
                       "VALUES (%s, %s, %s, %s)")
                cursor.execute(sql, (symbol, balance, frozen_balance, user_id))

    # 提交事务
    connection.commit()
finally:
    connection.close()
