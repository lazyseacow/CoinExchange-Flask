import json
import time
import logging
from decimal import Decimal

import redis
from sqlalchemy.exc import SQLAlchemyError
import redis.asyncio as aioredis
from app import create_app
from app.models.models import *
from app.utils.celery_logger import setup_logger
from app.utils.LatestPriceFromRedis import get_price_from_redis

celery = create_app().celery
redis_conn = redis.Redis(host='localhost', port=6379, db=1)
logger = setup_logger('celery_task', r'logs/celery_task.log', logging.DEBUG)


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


def match_orders(order_data):
    order_id = order_data['order_id']
    user_id = order_data['user_id']
    symbol = order_data['symbol']
    order_type = order_data['order_type']
    side = order_data['side']
    price = Decimal(order_data['price'])
    quantity = Decimal(order_data['quantity'])
    base_currency, quote_currency = symbol.split('/')
    latest_price = get_price_from_redis(redis_conn, base_currency + quote_currency)

    try:
        log_wallet_operations = []
        if order_type == 'limit':
            if side == 'buy' and latest_price <= price:
                base_wallet = Wallet.query.filter_by(user_id=user_id, symbol=base_currency).with_for_update().first()
                quote_wallet = Wallet.query.filter_by(user_id=user_id, symbol=quote_currency).with_for_update().first()
                if not quote_wallet or quote_wallet.balance < quantity * latest_price:
                    log_wallet_operations.append(
                        WalletOperations.log_operation(user_id=user_id, symbol=symbol, operation_type='buy',
                                                       amount=quantity, status='failed'))
                    order = Orders.query.get(order_id)
                    order.status = 'canceled'
                    db.session.add_all(log_wallet_operations)
                    db.session.commit()
                    return True

                order = Orders.query.with_for_update().get(order_id)
                # 订单匹配成功，执行交易
                base_wallet.balance += quantity
                quote_wallet.balance -= quantity * latest_price
                db.session.commit()

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

            elif side == 'sell' and latest_price >= price:
                base_wallet = Wallet.query.filter_by(user_id=user_id, symbol=base_currency).with_for_update().first()
                quote_wallet = Wallet.query.filter_by(user_id=user_id, symbol=quote_currency).with_for_update().first()
                if not quote_wallet or quote_wallet.balance < quantity * latest_price:
                    log_wallet_operations.append(
                        WalletOperations.log_operation(user_id=user_id, symbol=symbol, operation_type='buy',
                                                       amount=quantity, status='failed'))
                    order = Orders.query.with_for_update().get(order_id)
                    order.status = 'canceled'
                    db.session.add_all(log_wallet_operations)
                    db.session.commit()
                    return True

                order = Orders.query.with_for_update().get(order_id)
                # 订单匹配成功，执行交易
                base_wallet.balance -= quantity
                quote_wallet.balance += quantity * latest_price
                db.session.commit()

                log_wallet_operations.append(
                    WalletOperations(user_id=user_id, symbol=base_currency, operation_type=side, amount=-quantity,
                                     status='success'))
                log_wallet_operations.append(
                    WalletOperations(user_id=user_id, symbol=quote_currency, operation_type=side,
                                     amount=quantity * latest_price, status='success'))
                order.executed_price = latest_price
                order.status = 'filled'
                order.update_at = datetime.now()
                db.session.add_all(log_wallet_operations)
                db.session.commit()
                return True
            return False

        elif order_type == 'stop loss' and latest_price <= price:
            base_wallet = Wallet.query.filter_by(user_id=user_id, symbol=base_currency).with_for_update().first()
            quote_wallet = Wallet.query.filter_by(user_id=user_id, symbol=quote_currency).with_for_update().first()
            if not quote_wallet or quote_wallet.balance < quantity * latest_price:
                log_wallet_operations.append(
                    WalletOperations.log_operation(user_id=user_id, symbol=symbol, operation_type='buy',
                                                   amount=quantity, status='failed'))
                order = Orders.query.with_for_update().get(order_id)
                order.status = 'canceled'
                db.session.add_all(log_wallet_operations)
                db.session.commit()
                return True

            order = Orders.query.with_for_update().get(order_id)
            # 订单匹配成功，执行交易
            base_wallet.balance -= quantity
            quote_wallet.balance += quantity * latest_price

            log_wallet_operations.append(
                WalletOperations(user_id=user_id, symbol=base_currency, operation_type=side, amount=-quantity,
                                 status='success'))
            log_wallet_operations.append(
                WalletOperations(user_id=user_id, symbol=quote_currency, operation_type=side,
                                 amount=quantity * latest_price, status='success'))

            order.executed_price = latest_price
            order.status = 'filled'
            order.update_at = datetime.now()
            db.session.add_all(log_wallet_operations)
            db.session.commit()
            return True
        elif order_type == 'stop profit' and latest_price >= price:
            base_wallet = Wallet.query.filter_by(user_id=user_id, symbol=base_currency).with_for_update().first()
            quote_wallet = Wallet.query.filter_by(user_id=user_id, symbol=quote_currency).with_for_update().first()
            if not quote_wallet or quote_wallet.balance < quantity * latest_price:
                log_wallet_operations.append(
                    WalletOperations.log_operation(user_id=user_id, symbol=symbol, operation_type='buy',
                                                   amount=quantity, status='failed'))
                order = Orders.query.with_for_update().get(order_id)
                order.status = 'canceled'
                db.session.add_all(log_wallet_operations)
                db.session.commit()
                return True

            order = Orders.query.with_for_update().get(order_id)
            # 订单匹配成功，执行交易
            base_wallet.balance -= quantity
            quote_wallet.balance += quantity * latest_price
            db.session.commit()

            log_wallet_operations.append(
                WalletOperations(user_id=user_id, symbol=base_currency, operation_type=side, amount=-quantity,
                                 status='success'))
            log_wallet_operations.append(
                WalletOperations(user_id=user_id, symbol=quote_currency, operation_type=side,
                                 amount=quantity * latest_price, status='success'))

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
    process_orders.delay()
    process_delayed_orders.delay()
    # process_filled_orders.delay()
