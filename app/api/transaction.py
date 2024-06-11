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
        return jsonify(re_code=RET.NODATA, msg='用户不存在')

    data = request.get_json()
    if not data:
        return jsonify(re_code=RET.PARAMERR, msg='参数错误')

    order_type = data.get('order_type')
    side = data.get('side')
    symbol = data.get('symbol')
    quantity = data.get('quantity')
    price = data.get('price') if data.get('price') else 0
    base_currency, quote_currency = symbol.split('/')

    if not all([symbol, quantity, order_type]):
        return jsonify(re_code=RET.PARAMERR, msg='参数错误')

    try:
        latest_price = get_price_from_redis(redis_conn, base_currency+quote_currency)
        wallets = Wallet.query.filter(Wallet.user_id == user_id, Wallet.symbol.in_([base_currency, quote_currency])).with_for_update().all()
        wallet_dict = {wallet.symbol: wallet for wallet in wallets}

        base_wallet = wallet_dict.get(base_currency)
        quote_wallet = wallet_dict.get(quote_currency)

        log_operations = []

        if order_type == 'market':
            if side == 'sell':
                if not base_wallet or base_wallet.balance < quantity:
                    log_operations.append(WalletOperations.log_operation(user_id=user_id, symbol=base_currency, operation_type=side, amount=quantity, status='failed'))
                    db.session.add_all(log_operations)
                    db.session.commit()
                    return jsonify(re_code=RET.NODATA, msg='余额不足')

                base_wallet.balance -= quantity
                quote_wallet.balance += latest_price * quantity

                log_operations.append(WalletOperations(user_id=user_id, symbol=base_currency, operation_type=side, amount=-quantity, status='success'))
                log_operations.append(WalletOperations(user_id=user_id, symbol=quote_currency, operation_type=side, amount=quantity * latest_price, status='success'))
                log_operations.append(Orders(user_id=user_id, symbol=symbol, side=side, order_type=order_type, executed_price=latest_price, quantity=quantity, status='filled'))
                db.session.add_all(log_operations)
                db.session.commit()
                return jsonify(re_code=RET.OK, msg='交易成功')

            elif side == 'buy':
                if not quote_wallet or quote_wallet.balance < latest_price * quantity:
                    log_operations.append(WalletOperations.log_operation(user_id=user_id, symbol=base_currency, operation_type=side, amount=quantity * latest_price, status='failed'))
                    db.session.add_all(log_operations)
                    db.session.commit()
                    return jsonify(re_code=RET.NODATA, msg='余额不足')

                base_wallet.balance += quantity
                quote_wallet.balance -= quantity * latest_price

                log_operations.append(WalletOperations(user_id=user_id, symbol=base_currency, operation_type=side, amount=quantity, status='success'))
                log_operations.append(WalletOperations(user_id=user_id, symbol=quote_currency, operation_type=side, amount=-(quantity * latest_price), status='success'))
                log_operations.append(Orders(user_id=user_id, symbol=symbol, side=side, order_type=order_type, executed_price=latest_price, quantity=quantity, status='filled'))

                db.session.add_all(log_operations)
                db.session.commit()
                return jsonify(re_code=RET.OK, msg='交易成功')

        elif order_type == 'limit':
            order = Orders(user_id=user_id, symbol=symbol, side=side, order_type=order_type, price=price,
                           quantity=quantity, status='pending')
            db.session.add(order)
            db.session.flush()

            if side == 'sell':
                if not base_wallet or base_wallet.balance < quantity:
                    log_operations.append(WalletOperations(user_id=user_id, symbol=base_currency, operation_type=side, amount=quantity, status='failed'))
                    db.session.add_all(log_operations)
                    db.session.commit()
                    return jsonify(re_code=RET.NODATA, msg='余额不足')
            elif side == 'buy':
                if not quote_wallet or quote_wallet.balance < price * quantity:
                    log_operations.append(WalletOperations(user_id=user_id, symbol=base_currency, operation_type=side, amount=quantity * price, status='failed'))
                    db.session.add_all(log_operations)
                    db.session.commit()
                    return jsonify(re_code=RET.NODATA, msg='余额不足')

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


@api.route('/orderlist', methods=['POST'])
@jwt_required()
def orderlist():
    user_id = auth.get_userinfo()
    user = User.query.filter_by(user_id=user_id).first()
    if not user:
        return jsonify(re_code=RET.NODATA, msg='用户不存在')

    symbol = request.json.get('symbol')
    order_type = request.json.get('order_type')
    side = request.json.get('side')
    status = request.json.get('status')
    page = request.json.get('page')
    per_page = current_app.config['PAGE_SIZE']

    if not status:
        order_info = Orders.query.filter_by(user_id=user_id, symbol=symbol, side=side, order_type=order_type).paginate(page=page, per_page=per_page, error_out=False)
    else:
        order_info = Orders.query.filter_by(user_id=user_id, symbol=symbol, side=side, order_type=order_type, status=status).paginate(page=page, per_page=per_page, error_out=False)
    order_item = order_info.items

    order_list = []
    for order in order_item:
        order_data = {
            'order_id': order.order_id,
            'symbol': order.symbol,
            'side': order.side,
            'quantity': order.quantity,
            'order_type': order.order_type,
            'price': order.price,
            'status': order.status,
            'created_at': order.created_at.isoformat() if order.created_at else None
        }
        order_list.append(order_data)
    # order = Orders.query.get(order_id)
    return jsonify(re_code=RET.OK, msg='查询成功', data={
        'orders': order_list,
        'total_page': order_info.pages,
        'current_page': order_info.page,
        'per_page': current_app.config['PAGE_SIZE'],
        'total_count': order_info.total
    })


@api.route('/cancelorder', methods=['POST'])
@jwt_required()
def cancel_order():
    user_id = auth.get_userinfo()
    user = User.query.filter_by(user_id=user_id).first()
    if not user:
        return jsonify(re_code=RET.NODATA, msg='用户不存在')

    order_id = request.json.get('order_id')

    order = Orders.query.get(order_id)
    if order.user_id != user_id:
        return jsonify(re_code=RET.NODATA, msg='订单不属于当前用户')

    if not order:
        return jsonify(re_code=RET.NODATA, msg='订单不存在')
    if order.status == 'filled':
        return jsonify(re_code=RET.NODATA, msg='订单已成交，无法取消')
    if order.status == 'canceled':
        return jsonify(re_code=RET.NODATA, msg='订单已取消')

    try:
        redis_conn.sadd('is_canceled', order_id)
        order.status = 'canceled'
        db.session.commit()
        UserActivityLogs.log_activity(user_id, 'cancel_order', f'取消订单{order_id}', datetime.now())
        return jsonify(re_code=RET.OK, msg='订单取消成功')

    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error('数据库操作异常:' + str(e))
        return jsonify(re_code=RET.DBERR, msg='数据库操作异常')

    except Exception as e:
        current_app.logger.error(e)
        return jsonify(re_code=RET.SERVERERR, msg='服务器异常')

