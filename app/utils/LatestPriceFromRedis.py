import decimal

# from app import redis_conn


def get_price_from_redis(redis_conn, symbol):
    # 从 Redis 获取价格，假设 symbol 是您的货币对标识
    price_data = redis_conn.hget('latest_prices', symbol)
    if price_data is not None:
        # 将 byte 数据转换为字符串
        price_str = price_data.decode('utf-8')
        # 将字符串转换为 decimal.Decimal
        return decimal.Decimal(price_str)
    else:
        # 如果在 Redis 中没有找到对应的价格信息，返回 None 或默认值
        return None
