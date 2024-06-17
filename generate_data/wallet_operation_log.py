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

operation_types = ['sell', 'buy']
symbols = ["USDT", "BTC", "ETH", "LTC", "ETC", "XRP", "BCH", "TRX", "XMR", "DASH", "EOS", "LINK", "XLM", "ZEC", "UNI", "DOGE", "QRL", "ZUGA", "XTZ", "IOTA"]
statuses = ['success', 'failed']
# operation_time = [datetime.datetime(2023, 1, 1), datetime.datetime(2024, 6, 13)]
user_ids = [8, 9, 10, 11]


def random_date(start, end):
    return start + (end - start) * random.random()


start_date = datetime.datetime(2023, 1, 1)
end_date = datetime.datetime(2024, 6, 13)

# 连接数据库
connection = pymysql.connect(**db_config)

try:
    with connection.cursor() as cursor:
        for i in range(10000):  # 生成50条数据
            operation_type = random.choice(operation_types)
            symbol = random.choice(symbols)
            amount = round(random.uniform(0.1, 10000.0), 8)
            status = random.choice(statuses)
            user_id = random.choice(user_ids)
            operation_time = random_date(start_date, end_date)

            if operation_types == 'buy':
                amount = -amount

            sql = ("INSERT INTO wallet_operations (operation_type, symbol, amount, status, user_id, operation_time) "
                   "VALUES (%s, %s, %s, %s, %s, %s)")
            cursor.execute(sql, (operation_type, symbol, amount, status, user_id, operation_time))

    # 提交事务
    connection.commit()
finally:
    connection.close()
