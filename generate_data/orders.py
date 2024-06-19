import random
import datetime
import uuid

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

order_types = ['market', 'limit']
sides = ['buy', 'sell']
symbols = ["BTC/USDT", "ETH/USDT", "LTC/USDT", "ETC/USDT", "XRP/USDT", "BCH/USDT", "TRX/USDT", "XMR/USDT", "DASH/USDT", "EOS/USDT", "LINK/USDT", "XLM/USDT", "ZEC/USDT", "UNI/USDT", "DOGE/USDT", "QRL/USDT", "ZUGA/USDT", "XTZ/USDT", "IOTA/USDT"]
statuses = ['pending', 'filled', 'canceled']
user_ids = [16, 17, 18, 19, 23, 24, 25, 28]


def random_date(start, end):
    return start + (end - start) * random.random()


start_date = datetime.datetime(2023, 1, 1)
end_date = datetime.datetime(2024, 6, 13)

# 连接数据库
connection = pymysql.connect(**db_config)

try:
    with connection.cursor() as cursor:
        for i in range(10000):
            order_type = random.choice(order_types)
            side = random.choice(sides)
            symbol = random.choice(symbols)
            price = round(random.uniform(0.1, 10000.0), 8)
            executed_price = round(random.uniform(0.1, 10000.0), 8)
            quantity = round(random.uniform(0.1, 10000.0), 8)
            status = random.choice(statuses)
            user_id = random.choice(user_ids)
            created_at = random_date(start_date, end_date)
            update_at = random_date(created_at, end_date)  # 确保 update_at 大于 created_at

            if order_types == 'market':
                price = 0

            sql = (
                "INSERT INTO orders (order_type, side, symbol, price, executed_price, quantity, status, created_at, update_at, user_id, order_uuid) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)")
            cursor.execute(sql, (
            order_type, side, symbol, price, executed_price, quantity, status, created_at.strftime('%Y-%m-%d %H:%M:%S'),
            update_at.strftime('%Y-%m-%d %H:%M:%S'), user_id, str(uuid.uuid4())))

    # 提交事务
    connection.commit()
finally:
    connection.close()
