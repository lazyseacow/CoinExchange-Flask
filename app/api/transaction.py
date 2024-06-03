import requests
from flask import current_app, jsonify, request
from flask_jwt_extended import jwt_required
from sqlalchemy.exc import SQLAlchemyError

from app import db
from app.api import api
from app.api.verify import auth
from app.models import *
from app.utils.binance_market import get_tricker_price
from app.utils.response_code import RET


@api.route('/orders', methods=['POST'])
@jwt_required()
def orders():
    user_id = auth.get_userinfo()
    if not User.query.filter_by(user_id=user_id):
        return jsonify(code=RET.NODATA, msg='用户不存在')

    data = request.get_json()

    if not data:
        return jsonify(re_code=RET.PARAMERR, msg='参数错误')

    order_type = data.get('order_type')
    symbol = data.get('symbol')
    quantity = data.get('quantity')
    if not all([symbol, quantity, order_type]):
        return jsonify(re_code=RET.PARAMERR, msg='参数错误')

    try:
        base_currency, quote_currency = symbol.split('/')
    except ValueError as e:
        current_app.logger.exception('交易对格式错误:' + str(e))
        return jsonify(re_code=RET.PARAMERR, msg='交易对格式错误')

    try:
        price = get_tricker_price(symbol)
    except requests.RequestException as e:
        current_app.logger.exception('获取价格失败:' + str(e))
        return jsonify(re_code=RET.NODATA, msg='获取价格失败')

    try:
        if order_type == 'sell':
            base_wallet = Wallet.query.filter_by(user_id=user_id, symbol=base_currency).first()
            quote_wallet = Wallet.query.filter_by(user_id=user_id, symbol=quote_currency).first()
            if not base_wallet or base_wallet.balance < quantity:
                WalletOperations.log_operation(user_id=user_id, symbol=base_currency, operation_type='sell', amount=quantity * price, status='failed')
                return jsonify(re_code=RET.NODATA, msg='余额不足')

            # db.session.begin()
            base_wallet.balance -= quantity
            quote_wallet.balance += price * quantity
            db.session.commit()

        elif order_type == 'buy':
            base_wallet = Wallet.query.filter_by(user_id=user_id, symbol=base_currency).first()
            quote_wallet = Wallet.query.filter_by(user_id=user_id, symbol=quote_currency).first()
            if not quote_wallet or quote_wallet.balance < price * quantity:
                WalletOperations.log_operation(user_id=user_id, symbol=base_currency, operation_type='sell', amount=quantity * price, status='failed')
                return jsonify(re_code=RET.NODATA, msg='余额不足')

            # db.session.begin()
            base_wallet.balance += quantity
            quote_wallet.balance -= quantity * price
            db.session.commit()

        wallet_operations = WalletOperations(user_id=user_id, symbol=quote_currency, operation_type=order_type, amount=-(quantity * price), status='success')
        order = Orders(user_id=user_id, symbol=symbol, order_type=order_type, price=price, executed_price=price, quantity=quantity, status='pending')
        db.session.add(wallet_operations, order)
        db.session.commit()
        return jsonify(re_code=RET.OK, msg='交易成功')

    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error('数据库操作异常:' + str(e))
        return jsonify(re_code=RET.DBERR, msg='数据库操作异常')
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(re_code=RET.SERVERERR, msg='服务器异常')
