import json
import time
import logging
from decimal import Decimal
from web3 import Web3
import redis
from sqlalchemy.exc import SQLAlchemyError
from app import create_app
from app.models.models import *
from app.utils.celery_logger import setup_logger
from app.utils.LatestPriceFromRedis import get_price_from_redis

celery = create_app().celery
redis_conn = redis.Redis(host='localhost', port=6379, db=1)
logger = setup_logger('celery_task', r'logs/celery_task.log', logging.DEBUG)
MAX_RETRY_TIME = 3


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
                    continue

                process_order_result = match_orders(order_data_json)
                if not process_order_result:
                    redis_conn.zadd('delayed_order_queue', {json.dumps(order_data_json): time.time() + 60})
                else:
                    redis_conn.sadd('is_filled', order_id)
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


@celery.task(name='eth_withdrawal')
def eth_withdrawal():
    # 连接到以太坊节点
    w3 = Web3(Web3.HTTPProvider('https://holesky.infura.io/v3/44730e4603114c5abc5f8caa9f2e8116'))
    # 账户和私钥
    account = '0x76d243848d6A5dEAF70e52f3aecaCc4d0CAc944E'
    private_key = '0xe480b45a428e5f370cf93da276ecdfd85de624a39d033e4cac4c3d67373e4711'
    logger.debug(f"Connected to Ethereum node: {w3.is_connected()}")
    withdrawal = None
    wallet = None
    initial_amount = None
    # nonce = w3.eth.get_transaction_count(account, 'pending') - 1
    while True:
        try:
            withdrawal_info_list = redis_conn.lrange('ETH_withdrawal_requests', 0, -1)
            if not withdrawal_info_list:
                time.sleep(3)
                continue
            redis_conn.ltrim('ETH_withdrawal_requests', len(withdrawal_info_list), -1)

            for withdrawal_info in withdrawal_info_list:
                withdrawal_info = json.loads(withdrawal_info.decode('utf-8'))

                user_id = withdrawal_info['user_id']
                symbol = withdrawal_info['symbol']
                withdrawal_id = withdrawal_info['withdrawal_id']
                to_address = withdrawal_info['to_address']
                initial_amount = Decimal(withdrawal_info['amount']).quantize(Decimal('0.00000000'))
                amount_in_ether = Decimal(withdrawal_info['finally_amount']).quantize(Decimal('0.00000000'))

                withdrawal = Withdrawal.query.with_for_update().get(withdrawal_id)
                wallet = Wallet.query.with_for_update().filter_by(user_id=user_id, symbol=symbol).first()
                if wallet.balance < amount_in_ether:
                    withdrawal.status = 'failed'

                nonce = w3.eth.get_transaction_count(account, 'pending')
                tx = {
                    'nonce': nonce,
                    'to': to_address,
                    'value': w3.to_wei(amount_in_ether, 'ether'),
                    'gas': 21000,
                    'gasPrice': w3.to_wei('1.2', 'gwei'),
                    'chainId': 17000,
                }
                signed_tx = w3.eth.account.sign_transaction(tx, private_key)
                tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
                # logger.debug(f"Transaction sent: {tx_hash.hex()}  withdrawal_info is {withdrawal_info}")

                wallet.frozen_balance -= initial_amount
                withdrawal.nonce = nonce
                withdrawal.transation_hash = tx_hash.hex()
                withdrawal.status = 'processing'
                withdrawal.update_at = datetime.now()
                db.session.commit()
                # logger.debug(f"Withdrawal processed: {withdrawal_info['withdrawal_id']}")

                withdrawal_info['timestamp'] = int(datetime.now().timestamp())
                withdrawal_info['transation_hash'] = tx_hash.hex()
                redis_conn.rpush('ETH_transation_hash', json.dumps(withdrawal_info))
                logger.debug(f"Submit withdrawal processed: {withdrawal_info['withdrawal_id']}")
        except Exception as e:
            withdrawal.status = 'failed'
            wallet.frozen_balance -= initial_amount
            wallet.balance += initial_amount
            db.session.commit()
            logger.debug(f"Error processing withdrawal: {e}")


@celery.task(name='listen transation hash')
def listen_transation_hash():
    # 连接到以太坊节点
    w3 = Web3(Web3.HTTPProvider('https://holesky.infura.io/v3/44730e4603114c5abc5f8caa9f2e8116'))
    transation_info = {}
    retry_time = 0
    while True:
        try:
            transation_info_encoded = redis_conn.lpop('ETH_transation_hash')
            if transation_info_encoded:
                transation_info = json.loads(transation_info_encoded.decode('utf-8'))

                user_id = transation_info['user_id']
                symbol = transation_info['symbol']
                tx_hash = transation_info['transation_hash']
                withdrawal_id = transation_info['withdrawal_id']
                retry_time = transation_info['retry_time']
                initial_amount = Decimal(transation_info['amount']).quantize(Decimal('0.00000000'))

                if retry_time >= MAX_RETRY_TIME:
                    wallet = Wallet.query.with_for_update().filter_by(user_id=user_id, symbol=symbol).first()
                    wallet.frozen_balance -= initial_amount
                    withdrawal = Withdrawal.query.with_for_update().get(withdrawal_id)
                    withdrawal.status = 'failed'
                    withdrawal.update_at = datetime.now()
                    db.session.commit()
                    logger.debug(f"Listen withdrawal failed: {withdrawal_id}")
                    continue

                transation = w3.eth.get_transaction(tx_hash)
                if transation and transation.blockNumber:
                    receipt = w3.eth.get_transaction_receipt(tx_hash)
                    if receipt:
                        wallet = Wallet.query.with_for_update().filter_by(user_id=user_id, symbol=symbol).first()
                        if receipt.status == 1:
                            wallet.frozen_balance -= initial_amount
                            withdrawal = Withdrawal.query.with_for_update().get(withdrawal_id)
                            withdrawal.status = 'completed'
                            withdrawal.update_at = datetime.now()
                            db.session.commit()
                            logger.debug(f"Withdrawal completed: {withdrawal_id}")
                        elif receipt.status == 0:
                            wallet.balance += initial_amount
                            wallet.frozen_balance -= initial_amount
                            withdrawal = Withdrawal.query.with_for_update().get(withdrawal_id)
                            withdrawal.status = 'failed'
                            withdrawal.update_at = datetime.now()
                            db.session.commit()
                            logger.debug(f"Withdrawal failed: {withdrawal_id}")
                    else:
                        redis_conn.rpush('ETH_transation_hash', json.dumps(transation_info))
                        continue
                else:
                    # transation_info['retry_time'] = retry_time + 1
                    redis_conn.rpush('ETH_transation_hash', json.dumps(transation_info))
                    logger.debug(f"transaction not yet confirmed: {withdrawal_id}")
                    continue
            else:
                time.sleep(3)
        except SQLAlchemyError as e:
            redis_conn.rpush('ETH_transation_hash', json.dumps(transation_info))
            db.session.rollback()
            logger.debug(f"数据库异常: {e}")
        except Exception as e:
            transation_info['retry_time'] = retry_time + 1
            redis_conn.rpush('ETH_transation_hash', json.dumps(transation_info))
            logger.debug(f"Error processing transation hash: {e}")


if __name__ == '__main__':
    process_orders.delay()
    process_delayed_orders.delay()
    eth_withdrawal.delay()
    listen_transation_hash.delay()


