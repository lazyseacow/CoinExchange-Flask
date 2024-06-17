import json
import time
import logging
from decimal import Decimal

from sqlalchemy.exc import SQLAlchemyError
import redis
from app import create_app
from app.models.models import *
from confluent_kafka import Consumer, KafkaError
from app.utils.celery_logger import setup_logger
from app.utils.LatestPriceFromRedis import get_price_from_redis

celery = create_app().celery
redis_conn = redis.Redis(host='localhost', port=6379, db=1)
logger = setup_logger('celery_task', r'D:\pyproject\CoinExchange-Flask/logs/celery_task.log', logging.DEBUG)


def kafka_consumer_setup():
    """设置 Kafka 消费者"""
    conf = {
        'bootstrap.servers': "localhost:9092",
        'group.id': "my-group",
        'auto.offset.reset': 'latest'
    }
    consumer = Consumer(conf)
    consumer.subscribe(['binance_topic'])  # 订阅的主题
    return consumer


@celery.task(name='fetch_latest_price')
def fetch_latest_price():
    consumer = kafka_consumer_setup()
    try:
        while True:
            msg = consumer.poll(timeout=1.0)
            if msg is None:
                continue
            if msg.error():
                if msg.error().code() != KafkaError._PARTITION_EOF:
                    logger.debug(f"Khuska error: {msg.error()}")
                    # print(f"Khuska error: {msg.error()}")
                continue  # 忽略错误和分区结尾消息

            # 解析消息
            message = json.loads(msg.value().decode('utf-8'))
            stream_name = message.get('stream')
            if stream_name and '@ticker' in stream_name:
                symbol = message['data']['s']
                price = message['data']['c']
                redis_conn.hset('latest_prices', symbol, price)
    except Exception as e:
        logger.debug(f"Error consuming messages: {e}")


@celery.task(name='process_orders')
def process_orders():
    try:
        while True:
            order_data_list = redis_conn.lrange('order_queue', 0, -1)
            if not order_data_list:
                time.sleep(3)
                continue

            redis_conn.ltrim('order_queue', len(order_data_list), -1)
            for order_data in order_data_list:
                order_data_json = json.loads(order_data.decode('utf-8'))
                order_id = order_data_json['order_id']

                if redis_conn.sismember('is_filled', order_id) or redis_conn.sismember('is_canceled', order_id):
                    logger.info(f"Order {order_id} has been processed")
                    continue

                start_time_price = time.time()
                process_order_result = match_orders(order_data_json)
                end_time_price = time.time()
                logger.info(f"Order {order_id} processed in {end_time_price - start_time_price} seconds.")
                if not process_order_result:
                    # redis_conn.rpush('order_queue', json.dumps(order_data_json))
                    # logger.info(f"Order {order_data_json['order_id']} requeued in order_queue.")
                    redis_conn.zadd('delayed_order_queue', {json.dumps(order_data_json): time.time() + 60})
                else:
                    redis_conn.sadd('is_filled', order_id)
                    logger.info(f"Order {order_id} processed successfully.")
            else:
                time.sleep(1)
    except Exception as e:
        logger.debug(f"Error processing order: {e}")


# @celery.task(name='match_orders')
def match_orders(order_data):
    order_id = order_data['order_id']
    user_id = order_data['user_id']
    symbol = order_data['symbol']
    side = order_data['side']
    price = Decimal(order_data['price'])
    quantity = Decimal(order_data['quantity'])
    base_currency, quote_currency = symbol.split('/')
    latest_price = get_price_from_redis(redis_conn, base_currency + quote_currency)
    logger.info(f'type of price/quantity/latest_price: {type(price)}/{type(quantity)}/{type(latest_price)}')
    try:
        base_wallet = Wallet.query.filter_by(user_id=user_id, symbol=base_currency).first()
        quote_wallet = Wallet.query.filter_by(user_id=user_id, symbol=quote_currency).first()

        with db.session.begin_nested():
            log_wallet_operations = []
            if side == 'buy':
                if not quote_wallet or quote_wallet.balance < quantity * latest_price:
                    log_wallet_operations.append(
                        WalletOperations.log_operation(user_id=user_id, symbol=symbol, operation_type='buy',
                                                       amount=quantity, status='failed'))
                    order = Orders.query.get(order_id)
                    order.status = 'canceled'
                    db.session.add_all(log_wallet_operations)
                    db.session.commit()
                    return True

                if latest_price <= price:
                    order = Orders.query.get(order_id)
                    # 订单匹配成功，执行交易
                    base_wallet.balance += quantity
                    quote_wallet.balance -= quantity * latest_price

                    log_wallet_operations.append(
                        WalletOperations(user_id=user_id, symbol=base_currency, operation_type=side, amount=quantity,
                                         status='success'))
                    log_wallet_operations.append(
                        WalletOperations(user_id=user_id, symbol=quote_currency, operation_type=side,
                                         amount=-(quantity * latest_price), status='success'))
                    order.executed_price = latest_price
                    order.status = 'filled'
                    order.update_at = datetime.now()
                    db.session.add_all(log_wallet_operations)
                    db.session.commit()
                    return True
                return False
            elif side == 'sell':
                if not base_wallet or base_wallet.balance < quantity:
                    log_wallet_operations.append(
                        WalletOperations.log_operation(user_id=user_id, symbol=symbol, operation_type='sell',
                                                       amount=quantity, status='failed'))
                    order = Orders.query.get(order_id)
                    order.status = 'canceled'
                    db.session.add_all(log_wallet_operations)
                    db.session.commit()
                    return True

                if latest_price >= price:
                    order = Orders.query.get(order_id)
                    # 订单匹配成功，执行交易
                    base_wallet.balance -= quantity
                    quote_wallet.balance += quantity * price

                    log_wallet_operations.append(
                        WalletOperations(user_id=user_id, symbol=base_currency, operation_type=side, amount=-quantity,
                                         status='success'))
                    log_wallet_operations.append(
                        WalletOperations(user_id=user_id, symbol=quote_currency, operation_type=side,
                                         amount=quantity * price, status='success'))
                    order.executed_price = latest_price
                    order.status = 'filled'
                    order.update_at = datetime.now()
                    db.session.add_all(log_wallet_operations)
                    db.session.commit()
                    return True
                return False

    except SQLAlchemyError as e:
        logger.debug(f"SQL Error: {e}")
        db.session.rollback()
        return False
    except Exception as e:
        logger.debug(f"Error matching order id {order_id}: {e}")
        return False


@celery.task(name='process_delayed_orders')
def process_delayed_orders():
    try:
        while True:
            current_time = time.time()
            delayed_orders = redis_conn.zrangebyscore('delayed_order_queue', 0, current_time)
            if not delayed_orders:
                time.sleep(1)
                continue

            redis_conn.zremrangebyscore('delayed_order_queue', 0, current_time)
            for order_data in delayed_orders:
                order_data_json = json.loads(order_data.decode('utf-8'))
                redis_conn.rpush('order_queue', json.dumps(order_data_json))
            time.sleep(1)
    except Exception as e:
        logger.debug(f"Error processing delayed orders: {e}")


if __name__ == '__main__':
    fetch_latest_price.delay()
    process_orders.delay()
    process_delayed_orders.delay()
    # process_filled_orders.delay()
