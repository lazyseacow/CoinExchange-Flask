import decimal
import json
import asyncio
import time
import redis
import redis.asyncio as aioredis


def get_price_from_redis(redis_conn, symbol):
    # 格式化symbol以匹配Redis中的键
    formatted_symbol = f"{symbol.lower()}@ticker"
    try:
        # Correctly await the hget call to get the price data
        price_data = redis_conn.hget('binance_data', formatted_symbol)
        if price_data is not None:
            # Since price_data is already a bytes object, directly decode it
            price_json = json.loads(price_data.decode('utf-8'))
            price = decimal.Decimal(price_json['data']['c'])
            return price
        else:
            # If there is no price data in Redis, return None or a default value
            return None
    except Exception as e:
        print(e)
        return None
