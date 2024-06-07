import json
from decimal import Decimal
from flask import current_app, jsonify, request
from flask_jwt_extended import jwt_required
from sqlalchemy.exc import SQLAlchemyError

from app import redis_conn
from app.api import api
from app.api.verify import auth
from app.models.models import *
from app.utils.response_code import RET
from app.utils.LatestPriceFromRedis import get_price_from_redis


@api.route('/orders', methods=['POST'])
@jwt_required()
def orders():
    user_id = auth.get_userinfo()
    if not User.query.filter_by(user_id=user_id).first():
        return jsonify(code=RET.NODATA, msg='用户不存在')

    data = request.get_json()
    if not data:
        return jsonify(code=RET.PARAMERR, msg='参数错误')

    order_type = data.get('order_type')
    side = data.get('side')
    symbol = data.get('symbol')
    quantity = data.get('quantity')
    price = data.get('price') if data.get('price') else 0
    base_currency, quote_currency = symbol.split('/')

    if not all([symbol, quantity, order_type]):
        return jsonify(code=RET.PARAMERR, msg='参数错误')

    try:
        latest_price = get_price_from_redis(redis_conn, base_currency+quote_currency)
        if order_type == 'market':
            if side == 'sell':
                base_wallet = Wallet.query.filter_by(user_id=user_id, symbol=base_currency).first()
                quote_wallet = Wallet.query.filter_by(user_id=user_id, symbol=quote_currency).first()
                if not base_wallet or base_wallet.balance < quantity:
                    WalletOperations.log_operation(user_id=user_id, symbol=base_currency, operation_type=side, amount=quantity, status='failed')
                    return jsonify(re_code=RET.NODATA, msg='余额不足')

                base_wallet.balance -= quantity
                quote_wallet.balance += latest_price * quantity

                wallet_operations_base = WalletOperations(user_id=user_id, symbol=base_currency, operation_type=side, amount=-quantity, status='success')
                wallet_operations_quote = WalletOperations(user_id=user_id, symbol=quote_currency, operation_type=side, amount=quantity * latest_price, status='success')
                order = Orders(user_id=user_id, symbol=symbol, side=side, order_type=order_type, executed_price=latest_price, quantity=quantity, status='filled')
                db.session.add_all([wallet_operations_base, wallet_operations_quote, order])
                db.session.commit()
                return jsonify(re_code=RET.OK, msg='交易成功')

            elif side == 'buy':
                base_wallet = Wallet.query.filter_by(user_id=user_id, symbol=base_currency).first()
                quote_wallet = Wallet.query.filter_by(user_id=user_id, symbol=quote_currency).first()
                if not quote_wallet or quote_wallet.balance < latest_price * quantity:
                    WalletOperations.log_operation(user_id=user_id, symbol=base_currency, operation_type=side, amount=quantity * latest_price, status='failed')
                    return jsonify(re_code=RET.NODATA, msg='余额不足')

                base_wallet.balance += quantity
                quote_wallet.balance -= quantity * latest_price

                wallet_operations_base = WalletOperations(user_id=user_id, symbol=base_currency, operation_type=side, amount=quantity, status='success')
                wallet_operations_quote = WalletOperations(user_id=user_id, symbol=quote_currency, operation_type=side, amount=-(quantity * latest_price), status='success')
                order = Orders(user_id=user_id, symbol=symbol, side=side, order_type=order_type, executed_price=latest_price, quantity=quantity, status='filled')
                db.session.add_all([wallet_operations_base, wallet_operations_quote, order])
                db.session.commit()
                return jsonify(re_code=RET.OK, msg='交易成功')

        elif order_type == 'limit':
            order = Orders(user_id=user_id, symbol=symbol, side=side, order_type=order_type, price=price,
                           quantity=quantity, status='pending')
            db.session.add(order)
            db.session.flush()

            order_data = {
                'order_id': order.order_id,
                'user_id': user_id,
                'symbol': symbol,
                'side': side,
                'order_type': order_type,
                'quantity': quantity,
                'price': price,
                'status': 'pending'
            }
            db.session.commit()

            redis_conn.rpush(f'order_queue', json.dumps(order_data))
            # redis_conn.expire(f'order_queue', 86400)
            return jsonify(re_code=RET.OK, msg='市价委托订单添加成功')

    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error('数据库操作异常:' + str(e))
        return jsonify(re_code=RET.DBERR, msg='数据库操作异常')
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(re_code=RET.SERVERERR, msg='服务器异常')


@api.route('/cancel_order/int:<order_id>', methods=['POST'])
@jwt_required()
def cancel_order(order_id):
    user_id = auth.get_userinfo()
    if not User.query.filter_by(user_id=user_id).first():
        return jsonify(code=RET.NODATA, msg='用户不存在')
    if not redis_conn.exists(f'order_{order_id}'):
        return jsonify(code=RET.NODATA, msg='订单不存在')
