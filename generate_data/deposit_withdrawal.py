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

transaction_types = ['deposit', 'withdrawal']
symbols = ["USDT", "BTC", "ETH", "LTC", "ETC", "XRP", "BCH", "TRX", "XMR", "DASH", "EOS", "LINK", "XLM", "ZEC", "UNI", "DOGE", "QRL", "ZUGA", "XTZ", "IOTA"]
statuses = ['unpaid', 'pending', 'completed', 'failed']
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
            transaction_type = random.choice(transaction_types)
            symbol = random.choice(symbols)
            amount = round(random.uniform(0.1, 10000.0), 8)
            status = random.choice(statuses)
            transaction_id = f'txid_{random.randint(10000, 99999)}'
            user_id = random.choice(user_ids)
            create_at = random_date(start_date, end_date)
            update_at = random_date(create_at, end_date)

            sql = ("INSERT INTO deposits_withdrawals (transaction_type, symbol, amount, status, transaction_id, user_id, create_at, update_at) "
                   "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)")
            cursor.execute(sql, (transaction_type, symbol, amount, status, transaction_id, user_id, create_at, update_at))

    # 提交事务
    connection.commit()
finally:
    connection.close()