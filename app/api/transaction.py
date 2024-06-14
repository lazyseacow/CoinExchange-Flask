import json
from decimal import Decimal

from PIL import Image
from flask import current_app, jsonify, request
from flask_jwt_extended import jwt_required
from pyzbar import pyzbar
from sqlalchemy.exc import SQLAlchemyError

from app import redis_conn
from app.api import api
from app.api.verify import auth
from app.models.models import *
from app.utils.response_code import RET
from app.utils.LatestPriceFromRedis import get_price_from_redis


@api.route('/latestprice', methods=['POST'])
def get_latest_price():
    try:
        symbol = request.get_json().get('symbol')
        return jsonify(re_code=RET.OK, latest_price=get_price_from_redis(redis_conn, symbol))
    except SQLAlchemyError as e:
        current_app.logger.error(e)
        return jsonify(re_code=RET.DBERR, msg='查询错误')
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(re_code=RET.UNKOWNERR, msg='未知错误')


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
        base_wallet = Wallet.query.filter_by(user_id=user_id, symbol=base_currency).first()
        quote_wallet = Wallet.query.filter_by(user_id=user_id, symbol=quote_currency).first()

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
                db.session.commit()

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
                db.session.commit()

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
        order.update_at = datetime.now()
        db.session.commit()
        UserActivityLogs.log_activity(user_id, 'cancel_order', f'取消订单{order_id}')
        return jsonify(re_code=RET.OK, msg='订单取消成功')

    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error('数据库操作异常:' + str(e))
        return jsonify(re_code=RET.DBERR, msg='数据库操作异常')

    except Exception as e:
        current_app.logger.error(e)
        return jsonify(re_code=RET.SERVERERR, msg='服务器异常')


@api.route('/modifypaypwd', methods=['POST'])
@jwt_required()
def modify_pay_password():
    user_id = auth.get_userinfo()
    user = User.query.filter_by(user_id=user_id).first()
    if not user:
        return jsonify(re_code=RET.NODATA, msg='用户不存在')

    old_pwd = request.json.get('old_password')
    new_pwd = request.json.get('new_password')

    pay_password = PayPassword.query.filter_by(user_id=user_id).first()
    if not pay_password.verify_password(old_pwd):
        return jsonify(re_code=RET.PWDERR, msg='旧密码错误')

    if pay_password.verify_password(new_pwd):
        return jsonify(re_code=RET.PWDERR, msg='新密码与旧密码相同')

    pay_password.password = new_pwd
    pay_password.update_at()

    try:
        db.session.commit()
        user_activity_logs = UserActivityLogs()
        user_activity_logs.log_activity(user_id, 'modify pay password', request.remote_addr)
        return jsonify(re_code=RET.OK, msg='修改成功')
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error('数据库操作异常:' + str(e))
        return jsonify(re_code=RET.DBERR, msg='数据库操作异常')
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(re_code=RET.SERVERERR, msg='服务器异常')


@api.route('/bindwallet', methods=['POST'])
@jwt_required()
def bind_wallet():
    user_id = auth.get_userinfo()
    user = User.query.filter_by(user_id=user_id).first()
    if not user:
        return jsonify(re_code=RET.NODATA, msg='用户不存在')

    if 'wallet_qr' not in request.files:
        return jsonify(re_code=RET.PARAMERR, msg='请上传钱包二维码')

    currency = request.form.get('currency')
    agreement_type = request.form.get('agreement_type')
    wallet_address = request.form.get('wallet_address')
    wallet_qr = request.files.get('wallet_qr')
    comment = request.form.get('comment')

    if not all([currency, agreement_type, wallet_address, wallet_qr.filename]):
        return jsonify(re_code=RET.PARAMERR, msg='参数错误')

    if wallet_qr.filename == '':
        return jsonify(re_code=RET.PARAMERR, msg='请选择图片')

    if BindWallets.query.filter_by(user_id=user_id, address=wallet_address).first():
        return jsonify(re_code=RET.DATAEXIST, msg='钱包地址已存在')

    try:
        if wallet_qr:
            image = Image.open(wallet_qr.stream)
            decoded_objects = pyzbar.decode(image)
            qr_data = [obj.data.decode('utf-8') for obj in decoded_objects]
            # print(type(wallet_address), type(qr_data[0]))

            if wallet_address != qr_data[0]:
                return jsonify(re_code=RET.PARAMERR, msg='钱包地址与二维码不匹配')

            bind_wallets = BindWallets(symbol=currency, address=wallet_address, agreement_type=agreement_type, comment=comment, user_id=user_id)
            db.session.add(bind_wallets)
            db.session.commit()
            return jsonify(re_code=RET.OK, msg='绑定成功')

    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error('数据库操作异常:' + str(e))
        return jsonify(re_code=RET.DBERR, msg='数据库操作异常')
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(re_code=RET.SERVERERR, msg='服务器异常')





