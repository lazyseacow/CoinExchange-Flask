import json
import uuid
from decimal import Decimal, ROUND_DOWN

from flask import current_app, jsonify, request
from flask_jwt_extended import jwt_required
from sqlalchemy.exc import SQLAlchemyError

from app import redis_conn
from app.api import api
from app.auth.verify import token_auth, sign_auth
from app.models.models import *
from app.utils.response_code import RET
from app.utils.LatestPriceFromRedis import get_price_from_redis


@api.route('/latestprice', methods=['POST'])
def get_latest_price():
    try:
        symbol = request.get_json().get('symbol')
        return jsonify(re_code=RET.OK, latest_price=get_price_from_redis(redis_conn, symbol))
    except SQLAlchemyError as e:
        current_app.logger.error("/latestprice" + str(e))
        return jsonify(re_code=RET.DBERR, msg='查询错误')
    except Exception as e:
        current_app.logger.error("/latestprice" + str(e))
        return jsonify(re_code=RET.UNKOWNERR, msg='未知错误')


@api.route('/orders', methods=['POST'])
@jwt_required()
def orders():
    user_id = token_auth.get_userinfo()
    if not User.query.filter_by(user_id=user_id).first():
        return jsonify(re_code=RET.NODATA, msg='用户不存在')

    data = request.get_json()
    order_type = data.get('order_type')
    side = data.get('side')
    symbol = data.get('symbol')
    quantity = data.get('quantity')
    formatted_quantity = Decimal(quantity).quantize(Decimal('0.00000000'))
    price = data.get('price')
    formatted_price = Decimal(price).quantize(Decimal('0.00000000'))
    base_currency, quote_currency = symbol.split('/')
    timestamp = data.get('timestamp')
    x_signature = data.get('x_signature')
    if not all([symbol, quantity, order_type, timestamp, x_signature]):
        # print(symbol, quantity, order_type, timestamp, x_signature)
        return jsonify(re_code=RET.PARAMERR, msg='参数错误')
    encrypt_data = f'{order_type}+{side}+{symbol}+{formatted_quantity}+{formatted_price}+{timestamp}'
    # print(encrypt_data)
    if not sign_auth.verify_signature(encrypt_data, timestamp, x_signature):
        return jsonify(re_code=RET.SIGNERR, msg='签名错误')

    try:
        latest_price = get_price_from_redis(redis_conn, base_currency+quote_currency)
        order_uuid = str(uuid.uuid4())
        log_operations = []

        if order_type == 'market':
            base_wallet = Wallet.query.filter_by(user_id=user_id, symbol=base_currency).with_for_update().first()
            quote_wallet = Wallet.query.filter_by(user_id=user_id, symbol=quote_currency).with_for_update().first()
            if side == 'sell':
                if not base_wallet or base_wallet.balance < formatted_quantity:
                    log_operations.append(WalletOperations.log_operation(user_id=user_id, symbol=base_currency, operation_type=side, amount=quantity, status='failed'))
                    db.session.add_all(log_operations)
                    db.session.commit()
                    return jsonify(re_code=RET.NODATA, msg='余额不足')

                base_wallet.balance -= formatted_quantity
                quote_wallet.balance += latest_price * formatted_quantity
                # db.session.commit()

                log_operations.append(WalletOperations(user_id=user_id, symbol=base_currency, operation_type=side, amount=-formatted_quantity, status='success'))
                log_operations.append(WalletOperations(user_id=user_id, symbol=quote_currency, operation_type=side, amount=formatted_quantity * latest_price, status='success'))
                log_operations.append(Orders(order_uuid=order_uuid, user_id=user_id, symbol=symbol, side=side, order_type=order_type, executed_price=latest_price, quantity=formatted_quantity, status='filled'))
                db.session.add_all(log_operations)
                db.session.commit()
                return jsonify(re_code=RET.OK, msg='交易成功')

            elif side == 'buy':
                if not quote_wallet or quote_wallet.balance < latest_price * formatted_quantity:
                    log_operations.append(WalletOperations.log_operation(user_id=user_id, symbol=base_currency, operation_type=side, amount=formatted_quantity * latest_price, status='failed'))
                    db.session.add_all(log_operations)
                    db.session.commit()
                    return jsonify(re_code=RET.NODATA, msg='余额不足')

                base_wallet.balance += formatted_quantity
                quote_wallet.balance -= formatted_quantity * latest_price
                # db.session.commit()

                log_operations.append(WalletOperations(user_id=user_id, symbol=base_currency, operation_type=side, amount=formatted_quantity, status='success'))
                log_operations.append(WalletOperations(user_id=user_id, symbol=quote_currency, operation_type=side, amount=-(formatted_quantity * latest_price), status='success'))
                log_operations.append(Orders(order_uuid=order_uuid, user_id=user_id, symbol=symbol, side=side, order_type=order_type, executed_price=latest_price, quantity=formatted_quantity, status='filled'))

                db.session.add_all(log_operations)
                db.session.commit()
                return jsonify(re_code=RET.OK, msg='交易成功')

        elif order_type == 'limit':
            order = Orders(user_id=user_id, symbol=symbol, side=side, order_type=order_type, price=formatted_price,
                           quantity=formatted_quantity, status='pending', order_uuid=order_uuid)
            db.session.add(order)
            db.session.flush()

            base_wallet = Wallet.query.filter_by(user_id=user_id, symbol=base_currency).first()
            quote_wallet = Wallet.query.filter_by(user_id=user_id, symbol=quote_currency).first()
            if side == 'sell':
                if not base_wallet or base_wallet.balance < formatted_quantity:
                    log_operations.append(WalletOperations(user_id=user_id, symbol=base_currency, operation_type=side, amount=formatted_quantity, status='failed'))
                    db.session.add_all(log_operations)
                    db.session.commit()
                    return jsonify(re_code=RET.NODATA, msg='余额不足')
            elif side == 'buy':
                if not quote_wallet or quote_wallet.balance < formatted_price * formatted_quantity:
                    log_operations.append(WalletOperations(user_id=user_id, symbol=base_currency, operation_type=side, amount=formatted_quantity * formatted_price, status='failed'))
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
            return jsonify(re_code=RET.OK, msg='限价委托订单添加成功')

        elif order_type == 'stop loss':
            order = Orders(user_id=user_id, symbol=symbol, side=side, order_type=order_type, price=formatted_price,
                           quantity=formatted_quantity, status='pending', order_uuid=order_uuid)
            db.session.add(order)
            db.session.flush()

            base_wallet = Wallet.query.filter_by(user_id=user_id, symbol=base_currency).first()

            if not base_wallet or base_wallet.balance < formatted_quantity:
                log_operations.append(WalletOperations(user_id=user_id, symbol=base_currency, operation_type=side, amount=formatted_quantity, status='failed'))
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
            return jsonify(re_code=RET.OK, msg='止损委托订单添加成功')

        elif order_type == 'stop profit':
            order = Orders(user_id=user_id, symbol=symbol, side=side, order_type=order_type, price=formatted_price,
                           quantity=formatted_quantity, status='pending', order_uuid=order_uuid)
            db.session.add(order)
            db.session.flush()

            base_wallet = Wallet.query.filter_by(user_id=user_id, symbol=base_currency).first()

            if not base_wallet or base_wallet.balance < formatted_quantity:
                log_operations.append(WalletOperations(user_id=user_id, symbol=base_currency, operation_type=side, amount=formatted_quantity, status='failed'))
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
            return jsonify(re_code=RET.OK, msg='止盈委托订单添加成功')

    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error("/orders" + str(e))
        return jsonify(re_code=RET.DBERR, msg='数据库操作异常')
    except Exception as e:
        current_app.logger.error("/orders" + str(e))
        return jsonify(re_code=RET.SERVERERR, msg='服务器异常')


@api.route('/orderlist', methods=['POST'])
@jwt_required()
def orderlist():
    user_id = token_auth.get_userinfo()
    user = User.query.filter_by(user_id=user_id).first()
    if not user:
        return jsonify(re_code=RET.NODATA, msg='用户不存在')

    symbol = request.json.get('symbol', '')
    order_type = request.json.get('order_type', '')
    side = request.json.get('side', '')
    status = request.json.get('status', '')
    page = request.json.get('page')
    timestamp = request.json.get('timestamp')
    x_signature = request.json.get('x_signature')
    per_page = current_app.config['PAGE_SIZE']

    encrypt_data = f'{symbol}+{order_type}+{side}+{status}+{page}+{timestamp}'
    if not sign_auth.verify_signature(encrypt_data, timestamp, x_signature):
        return jsonify(re_code=RET.SIGNERR, msg='签名错误')

    query = Orders.query.filter_by(user_id=user_id)
    if symbol:
        query = query.filter(Orders.symbol == symbol)
    if order_type:
        query = query.filter(Orders.order_type == order_type)
    if side:
        query = query.filter(Orders.side == side)
    if status:
        query = query.filter(Orders.status == status)

    order_info = query.order_by(Orders.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    order_item = order_info.items

    order_list = []
    for order in order_item:
        order_data = {
            'order_uuid': order.order_uuid,
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
    user_id = token_auth.get_userinfo()
    user = User.query.filter_by(user_id=user_id).first()
    if not user:
        return jsonify(re_code=RET.NODATA, msg='用户不存在')

    order_id = request.json.get('order_id')

    order = Orders.query.with_for_update().get(order_id)
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
        order.update_at = datetime.now()
        db.session.commit()
        UserActivityLogs.log_activity(user_id, 'cancel_order', f'取消订单{order_id}')
        return jsonify(re_code=RET.OK, msg='订单取消成功')

    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error("/cancelorder" + str(e))
        return jsonify(re_code=RET.DBERR, msg='数据库操作异常')

    except Exception as e:
        current_app.logger.error("/cancelorder" + str(e))
        return jsonify(re_code=RET.SERVERERR, msg='服务器异常')


@api.route('/feerate', methods=['GET'])
@jwt_required()
def fees():
    user_id = token_auth.get_userinfo()
    user = User.query.filter_by(user_id=user_id).first()
    if not user:
        return jsonify(re_code=RET.NODATA, msg='用户不存在')
    try:
        fees = Fees.query.all()
        return jsonify(re_code=RET.OK, msg='查询成功', data=[fee.to_json() for fee in fees])
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error("/fees" + str(e))
        return jsonify(re_code=RET.DBERR, msg='数据库操作异常')
    except Exception as e:
        current_app.logger.error("/fees" + str(e))
        return jsonify(re_code=RET.SERVERERR, msg='服务器异常')


@api.route('/withdrawal', methods=['POST'])
@jwt_required()
def withdrawal():
    user_id = token_auth.get_userinfo()
    user = User.query.filter_by(user_id=user_id).first()
    if not user:
        return jsonify(re_code=RET.NODATA, msg='用户不存在')

    try:
        symbol = request.json.get('symbol')
        amount = Decimal(request.json.get('amount')).quantize(Decimal('0.00000000'))
        fee = Decimal(request.json.get('fee')).quantize(Decimal('0.00000000'))
        finally_amount = Decimal(request.json.get('finally_amount')).quantize(Decimal('0.00000000'))
        address = request.json.get('address')
        pay_pwd = request.json.get('pay_pwd')
        timestamp = request.json.get('timestamp')
        x_signature = request.json.get('x_signature')
        encrypt_data = f'{symbol}+{amount}+{fee}+{finally_amount}+{address}+{pay_pwd}+{timestamp}'

        if not all([symbol, fee, amount, finally_amount, address, pay_pwd]):
            return jsonify(re_code=RET.PARAMERR, msg='参数错误')

        if not sign_auth.verify_signature(encrypt_data, timestamp, x_signature):
            return jsonify(re_code=RET.SIGNERR, msg='签名错误')

        if not BindWallets.query.filter_by(address=address).first():
            return jsonify(re_code=RET.DATAERR, msg='提现地址错误')

        if finally_amount != amount - fee:
            return jsonify(re_code=RET.PARAMERR, msg='提现金额错误')

        pay_password = PayPassword.query.filter_by(user_id=user_id).first()
        if not pay_password.verify_password(pay_pwd):
            return jsonify(re_code=RET.PWDERR, msg='支付密码错误')

        wallet = Wallet.query.with_for_update().filter_by(user_id=user_id, symbol=symbol).first()
        if wallet.balance < finally_amount:
            return jsonify(re_code=RET.DATAERR, msg='余额不足')

        wallet.balance -= amount

        deposits_withdrawals = DepositsWithdrawals(user_id=user_id, transaction_id=str(uuid.uuid4()), transaction_type='withdrawal', symbol=symbol, amount=amount, finally_amount=finally_amount, fee=fee, status='pending', create_at=datetime.now(), update_at=datetime.now())
        wallet_log = WalletOperations(user_id=user_id, symbol=symbol, operation_type='withdrawal', operation_time=datetime.now(), amount=-amount, status='success')
        db.session.add_all([deposits_withdrawals, wallet_log])
        db.session.commit()
        return jsonify(re_code=RET.OK, msg='提现申请成功')

    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error("/withdrawal" + str(e))
        return jsonify(re_code=RET.DBERR, msg='数据库操作异常')
    except Exception as e:
        current_app.logger.error("/withdrawal" + str(e))
        return jsonify(re_code=RET.SERVERERR, msg='服务器异常')









