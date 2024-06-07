import json
import time
import logging
from sqlalchemy.exc import SQLAlchemyError
import redis
from app import create_app
from app.models.models import *
from confluent_kafka import Consumer, KafkaError
from app.utils.celery_logger import setup_logger
from app.utils.LatestPriceFromRedis import get_price_from_redis

# celery = Celery('task', broker='redis://localhost:6379/0')
celery = create_app().celery
redis_conn = redis.Redis(host='localhost', port=6379, db=1)
logger = setup_logger('celery_task', 'logs/celery_task.log', logging.DEBUG)
MAX_RETRY_COUNT = 5


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
    latest_prices = {}
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
            if stream_name and '@miniTicker' in stream_name:
                symbol = message['data']['s']
                price = message['data']['c']
                redis_conn.hset('latest_prices', symbol, price)
    except Exception as e:
        logger.debug(f"Error consuming messages: {e}")


@celery.task(name='process_orders')
def process_orders():
    try:
        while True:
            order_data = redis_conn.lpop('order_queue')

            if order_data:
                order_data_json = json.loads(order_data.decode('utf-8'))
                order_id = order_data_json['order_id']
                # match_orders(order_data_json)

                if redis_conn.sismember('is_processed', order_id):
                    logger.info(f"Order {order_id} has been processed")
                    continue

                process_order_result = match_orders(order_data_json)
                if not process_order_result:
                    redis_conn.rpush('order_queue', json.dumps(order_data_json))
                    # logger.info(f"Order {order_data_json['order_id']} requeued in order_queue.")
                else:
                    redis_conn.sadd('is_processed', order_id)
                    logger.info(f"Order {order_id} processed successfully.")
            else:
                time.sleep(1)
    except Exception as e:
        logger.debug(f"Error processing order: {e}")
        # print(f"Error processing order: {e}")


# @celery.task(name='match_orders')
def match_orders(order_data):
    order_id = order_data['order_id']
    user_id = order_data['user_id']
    symbol = order_data['symbol']
    side = order_data['side']
    price = order_data['price']
    quantity = order_data['quantity']
    base_currency, quote_currency = symbol.split('/')
    # latest_price = redis_conn.hget('latest_prices', base_currency+quote_currency)   # 获取最新价格
    latest_price = get_price_from_redis(redis_conn, base_currency + quote_currency)
    # logger.info(f"order_{order_id}: latest_price_{latest_price}")

    try:
        order = Orders.query.get(order_id)
        if side == 'buy':
            base_wallet = Wallet.query.filter_by(user_id=user_id, symbol=base_currency).first()
            quote_wallet = Wallet.query.filter_by(user_id=user_id, symbol=quote_currency).first()
            if not quote_wallet or quote_wallet.balance < quantity * latest_price:
                WalletOperations.log_operation(user_id=user_id, symbol=symbol, operation_type='buy', amount=quantity, status='failed')
                order.status = 'canceled'
                db.session.commit()
                return True

            if latest_price <= price:
                # 订单匹配成功，执行交易
                base_wallet.balance += quantity
                quote_wallet.balance -= quantity * latest_price

                WalletOperations.log_operation(user_id=user_id, symbol=symbol, operation_type='buy', amount=quantity, status='success')
                order.executed_price = latest_price
                order.status = 'filled'
                order.update_at = datetime.now()
                db.session.commit()
                return True

            else:
                # 订单未匹配，将订单放入优先队列
                # redis_conn.rpush('order_queue', json.dumps(order_data))
                return False
        elif side == 'sell':
            base_wallet = Wallet.query.filter_by(user_id=user_id, symbol=base_currency).first()
            quote_wallet = Wallet.query.filter_by(user_id=user_id, symbol=quote_currency).first()
            if not base_wallet or base_wallet.balance < quantity:
                WalletOperations.log_operation(user_id=user_id, symbol=base_currency, operation_type=side, amount=quantity * price, status='failed')
                order.status = 'canceled'
                db.session.commit()
                return True

            if latest_price >= price:
                # 订单匹配成功，执行交易
                base_wallet.balance -= quantity
                quote_wallet.balance += quantity * price

                WalletOperations.log_operation(user_id=user_id, symbol=symbol, operation_type=side, amount=quantity, status='success')
                order.executed_price = latest_price
                order.status = 'filled'
                order.update_at = datetime.now()
                db.session.commit()
                return True

            else:
                # redis_conn.rpush('order_queue', json.dumps(order_data))
                return False

    except SQLAlchemyError as e:
        logger.debug(f"SQL Error: {e}")
        db.session.rollback()
        return False
    except Exception as e:
        logger.debug(f"Error matching order id_{order_id}: {e}")
        return False


if __name__ == '__main__':
    fetch_latest_price.delay()
    process_orders.delay()
    # process_filled_orders.delay()
