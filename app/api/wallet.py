from flask import current_app, jsonify, request
from flask_jwt_extended import jwt_required
from sqlalchemy.exc import SQLAlchemyError

from app.api import api
from app.models.models import *
from app.utils.response_code import RET
from app.auth.verify import token_auth, sign_auth


@api.route('/walletsinfo', methods=['POST'])
@jwt_required()
def get_wallets_info():
    """
    获取钱包中所有货币信息
    :return:
    """
    user_id = token_auth.get_userinfo()
    user = User.query.filter_by(user_id=user_id).first()
    if not user:
        return jsonify(re_code=RET.NODATA, msg='用户不存在')

    try:
        symbol = request.json.get('symbol', '')
        timestamp = request.json.get('timestamp')
        x_signature = request.json.get('x_signature')
        encrypt_data = f'{symbol}+{timestamp}'
        if not sign_auth.verify_signature(encrypt_data, timestamp, x_signature):
            return jsonify(re_code=RET.SIGNERR, msg='签名错误')

        query = Wallet.query
        if symbol:
            query = query.filter_by(symbol=symbol)

        wallets = query.filter_by(user_id=user_id).all()

        if not wallets:
            return jsonify(re_code=RET.NODATA, msg='用户钱包信息不存在')
        wallet_info = [wallet.to_json() for wallet in wallets]
        return jsonify(re_code=RET.OK, msg='OK', data=wallet_info)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(re_code=RET.DBERR, msg='钱包查询失败')


@api.route('/modifypaypwd', methods=['POST'])
@jwt_required()
def modify_pay_password():
    user_id = token_auth.get_userinfo()
    user = User.query.filter_by(user_id=user_id).first()
    if not user:
        return jsonify(re_code=RET.NODATA, msg='用户不存在')

    old_pwd = request.json.get('old_password')
    new_pwd = request.json.get('new_password')
    timestamp = request.json.get('timestamp')
    x_signature = request.json.get('x_signature')
    encrypt_data = f'{old_pwd}+{new_pwd}+{timestamp}'
    if not sign_auth.verify_signature(encrypt_data, timestamp, x_signature):
        return jsonify(re_code=RET.SIGNERR, msg='签名错误')

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
    user_id = token_auth.get_userinfo()
    user = User.query.filter_by(user_id=user_id).first()
    if not user:
        return jsonify(re_code=RET.NODATA, msg='用户不存在')

    currency = request.json.get('currency')
    agreement_type = request.json.get('agreement_type')
    wallet_address = request.json.get('wallet_address')
    comment = request.json.get('comment', '')
    pay_pwd = request.json.get('pay_pwd')
    timestamp = request.json.get('timestamp')
    x_signature = request.json.get('x_signature')
    encrypt_data = f'{currency}+{agreement_type}+{wallet_address}+{comment}+{pay_pwd}+{timestamp}'

    if not all([currency, agreement_type, wallet_address]):
        return jsonify(re_code=RET.PARAMERR, msg='参数错误')

    if not sign_auth.verify_signature(encrypt_data, timestamp, x_signature):
        return jsonify(re_code=RET.SIGNERR, msg='签名错误')

    if not PayPassword.query.filter_by(user_id=user_id).first().verify_password(pay_pwd):
        return jsonify(re_code=RET.PWDERR, msg='支付密码错误')

    if BindWallets.query.filter_by(user_id=user_id, address=wallet_address).first():
        return jsonify(re_code=RET.DATAEXIST, msg='钱包地址已存在')

    try:
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


@api.route('/digitalwallet', methods=['POST'])
@jwt_required()
def digital_wallet():
    user_id = token_auth.get_userinfo()
    user = User.query.filter_by(user_id=user_id).first()

    if not user:
        return jsonify(re_code=RET.NODATA, msg='用户不存在')

    symbol = request.json.get('symbol', '')
    agreement_type = request.json.get('agreement_type', '')
    timestamp = request.json.get('timestamp')
    x_signature = request.json.get('x_signature')
    encrypt_data = f'{symbol}+{agreement_type}+{timestamp}'
    print(encrypt_data)

    if not sign_auth.verify_signature(encrypt_data, timestamp, x_signature):
        return jsonify(re_code=RET.SIGNERR, msg='签名错误')

    query = BindWallets.query.filter_by(user_id=user_id)

    if symbol:
        query = query.filter_by(symbol=symbol)
    if agreement_type:
        query = query.filter_by(agreement_type=agreement_type)

    digital_wallets = query.order_by(BindWallets.created_at.desc()).all()
    if not digital_wallet:
        return jsonify(re_code=RET.NODATA, msg='用户钱包信息不存在')
    digital_wallet_info = [wallet.to_json() for wallet in digital_wallets]
    return jsonify(re_code=RET.OK, msg='获取数字钱包成功', data=digital_wallet_info)
