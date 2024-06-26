from flask import current_app, jsonify, request
from flask_jwt_extended import jwt_required, create_access_token
from sqlalchemy.exc import SQLAlchemyError

from app import redis_conn
from app.api import api
from app.auth.verify import token_auth
from app.models.models import *
from app.utils.response_code import RET


@api.route('/admin/login', methods=['POST'])
def admin_login():
    username = request.json.get('username')
    password = request.json.get('password')
    captcha = request.json.get('captcha')
    if not all([username, password]):
        return jsonify(re_code=RET.PARAMERR, msg='参数错误')

    admin = Admins.query.filter_by(username=username).first()
    if not admin:
        return jsonify(re_code=RET.NODATA, msg='用户不存在')
    if password != admin.password:
        return jsonify(re_code=RET.PWDERR, msg='密码错误')

    if not redis_conn.get(f'captcha_{request.remote_addr}'):
        return jsonify(re_code=RET.NODATA, msg='验证码过期')
    elif redis_conn.get(f'captcha_{request.remote_addr}') != captcha.encode('utf-8'):
        return jsonify(re_code=RET.PARAMERR, msg='验证码错误')

    if admin.role != 'admin':
        return jsonify(re_code=RET.ROLEERR, msg='用户权限错误')

    identity = {
        "admin_id": admin.admin_id,
        "username": username,
        "role": admin.role
    }
    access_token = create_access_token(identity=identity)

    return jsonify(re_code=RET.OK, msg='登录成功', access_token=access_token)


@api.route('/admin/orderlist', methods=['POST'])
@jwt_required()
def admin_order_list():
    admin_identity = token_auth.get_userinfo()
    admin = Admins.query.filter_by(admin_id=admin_identity['admin_id']).first()
    if admin_identity['role'] != 'admin' or not admin:
        return jsonify(re_code=RET.ROLEERR, msg='用户权限错误')

    symbol = request.json.get('symbol')
    order_type = request.json.get('order_type')
    order_uuid = request.json.get('order_uuid')
    side = request.json.get('side')
    status = request.json.get('status')
    page = request.json.get('page')
    per_page = current_app.config['PAGE_SIZE']

    query = Orders.query

    if symbol:
        query = query.filter(Orders.symbol == symbol)
    if order_type:
        query = query.filter(Orders.order_type == order_type)
    if side:
        query = query.filter(Orders.side == side)
    if status:
        query = query.filter(Orders.status == status)
    if order_uuid:
        query = query.filter(Orders.order_uuid == order_uuid)

    order_info = query.paginate(page=page, per_page=per_page, error_out=False)
    order_item = order_info.items

    order_list = []
    for order in order_item:
        order_data = {
            'order_uuid': order.order_uuid,
            'order_id': order.order_id,
            'symbol': order.symbol,
            'side': order.side,
            'order_type': order.order_type,
            'quantity': order.quantity,
            'price': order.price,
            'status': order.status,
            'created_at': order.created_at.isoformat() if order.created_at else None
        }
        order_list.append(order_data)

    return jsonify(re_code=RET.OK, msg='查询成功', data={
        'orders': order_list,
        'total_page': order_info.pages,
        'current_page': order_info.page,
        'per_page': per_page,
        'total_count': order_info.total
    })


@api.route('/admin/alluser', methods=['GET'])
@jwt_required()
def get_all_user():
    admin_identity = token_auth.get_userinfo()
    admin = Admins.query.filter_by(admin_id=admin_identity['admin_id']).first()
    if admin_identity['role'] != 'admin' and admin:
        return jsonify(re_code=RET.ROLEERR, msg='用户权限错误')

    # page = request.json.get('page')
    user_id = request.args.get('uid')
    phone = request.args.get('phone')
    email = request.args.get('email')
    erc20_address = request.args.get('erc20_address')
    trc20_address = request.args.get('trc20_address')
    page = int(request.args.get('page'))
    per_page = current_app.config['PAGE_SIZE']

    query = User.query
    if user_id:
        query = query.filter_by(user_id=user_id)
    if phone:
        query = query.filter_by(phone=phone)
    if email:
        query = query.filter_by(email=email)
    if erc20_address or trc20_address:
        query = query.join(DigitalWallet)
        if erc20_address:
            query = query.filter_by(erc20_address=erc20_address)
        if trc20_address:
            query = query.filter_by(trc20_address=trc20_address)
    user_paginate = query.paginate(page=page, per_page=per_page, error_out=False)
    user_info = user_paginate.items

    user_list = []
    for user in user_info:
        last_login = user.user_activity_logs.filter_by(activity_type='login').order_by(UserActivityLogs.activity_time.desc()).first()
        user_data = {
            'user_id': user.user_id,
            'username': user.username,
            'email': user.email,
            'phone': user.phone,
            'erc20_address': user.digital_wallet.first().erc20_address,
            'trc20_address': user.digital_wallet.first().trc20_address,
            'join_time': user.join_time.isoformat() if user.join_time else None,
            'last_login_ip': last_login.activity_details if last_login else None,
            'last_seen': user.last_seen.isoformat() if user.last_seen else None
        }
        user_list.append(user_data)
    data = {
        'users': user_list,
        'total_page': user_paginate.pages,
        'current_page': user_paginate.page,
        'per_page': per_page,
        'total_count': user_paginate.total
    }
    return jsonify(re_code=RET.OK, msg='查询成功', data=data)


# 资产列表
@api.route('/admin/allwallet/<int:page>', methods=['GET'])
@jwt_required()
def get_all_wallet(page):
    admin_identity = token_auth.get_userinfo()
    admin = Admins.query.filter_by(admin_id=admin_identity['admin_id']).first()

    if admin_identity['role'] != 'admin' or not admin:
        return jsonify(re_code=RET.ROLEERR, msg='用户权限错误')

    currency = request.args.get('currency')
    user_id = request.args.get('uid')
    per_page = current_app.config['PAGE_SIZE']

    query = Wallet.query
    if currency:
        query = query.filter(Wallet.symbol == currency)
    if user_id:
        query = query.filter(Wallet.user_id == user_id)

    # 查询所有钱包信息并进行分页
    wallets_pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    wallets = wallets_pagination.items

    # 提取所有钱包的 user_id
    user_ids = [wallet.user_id for wallet in wallets]

    # 使用 user_id 批量查询用户信息
    users = User.query.filter(User.user_id.in_(user_ids)).all()
    user_dict = {user.user_id: user for user in users}

    wallet_list = []
    for wallet in wallets:
        user = user_dict.get(wallet.user_id)
        wallet_data = {
            'user_id': wallet.user_id,
            'account': user.phone if user else '',
            'username': user.username if user else '',
            'wallet_type': '',
            'symbol': wallet.symbol,
            'balance': wallet.balance,
            'frozen_balance': wallet.frozen_balance
        }
        wallet_list.append(wallet_data)

    data = {
        'wallets_data': wallet_list,
        'total_page': wallets_pagination.pages,
        'current_page': wallets_pagination.page,
        'per_page': per_page,
        'total_count': wallets_pagination.total
    }

    return jsonify(re_code=RET.OK, msg='查询成功', data=data)


# 账变记录
@api.route('/admin/walletlog', methods=['GET'])
@jwt_required()
def get_wallet_record():
    admin_identity = token_auth.get_userinfo()
    admin = Admins.query.filter_by(admin_id=admin_identity['admin_id']).first()
    if admin_identity['role'] != 'admin' or not admin:
        return jsonify(re_code=RET.ROLEERR, msg='用户权限错误')

    user_id = request.args.get('uid')
    symbol = request.args.get('currency')
    operation_type = request.args.get('operation_type')
    status = request.args.get('status')
    page = int(request.args.get('page'))
    per_page = current_app.config['PAGE_SIZE']

    if not page:
        return jsonify(re_code=RET.PARAMERR, msg='参数错误')

    query = WalletOperations.query
    if symbol:
        query = query.filter_by(symbol=symbol)
    if user_id:
        query = query.filter_by(user_id=user_id)
    if status:
        query = query.filter_by(status=status)
    if operation_type:
        query = query.filter_by(operation_type=operation_type)

    wallet_operations_pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    wallet_operations_info = wallet_operations_pagination.items

    wallet_operations_list = []
    for wallet_operations in wallet_operations_info:
        wallet_data = {
            'operation_id': wallet_operations.operation_id,
            'symbol': wallet_operations.symbol,
            'operation_type': wallet_operations.operation_type,
            'operation_time': wallet_operations.operation_time.isoformat() if wallet_operations.operation_time else None,
            'amount': wallet_operations.amount,
            'status': wallet_operations.status,
            'wallet_type': '',
            'account': wallet_operations.user.phone
        }
        wallet_operations_list.append(wallet_data)
    data = {
        'wallet_operations_data': wallet_operations_list,
        'total_page': wallet_operations_pagination.pages,
        'current_page': wallet_operations_pagination.page,
        'per_page': per_page,
        'total_count': wallet_operations_pagination.total
    }
    return jsonify(re_code=RET.OK, msg='查询成功', data=data)


@api.route('/admin/payandcash', methods=['POST'])
@jwt_required()
def get_pay_and_cash():
    admin_identity = token_auth.get_userinfo()
    admin = Admins.query.filter_by(admin_id=admin_identity['admin_id']).first()
    if admin_identity['role'] != 'admin' or not admin:
        return jsonify(re_code=RET.ROLEERR, msg='用户权限错误')

    user_id = request.json.get('uid')
    status = request.json.get('status')
    transaction_type = request.json.get('transaction_type')
    currency = request.json.get('currency')
    start_time = request.json.get('start_time')
    end_time = request.json.get('end_time')
    page = int(request.json.get('page'))
    per_page = current_app.config['PAGE_SIZE']

    query = DepositsWithdrawals.query
    if user_id:
        query = query.filter_by(user_id=user_id)
    if status:
        query = query.filter_by(status=status)
    if transaction_type:
        query = query.filter_by(transaction_type=transaction_type)
    if currency:
        query = query.filter_by(symbol=currency)
    if start_time:
        try:
            start_time = datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S')
            query = query.filter(DepositsWithdrawals.create_at >= start_time)
        except ValueError:
            return jsonify(re_code=RET.PARAMERR, msg='开始时间格式错误，请使用YYYY-MM-DD HH:MM:SS格式')
    if end_time:
        try:
            end_time = datetime.strptime(end_time, '%Y-%m-%d %H:%M:%S')
            query = query.filter(DepositsWithdrawals.create_at <= end_time)
        except ValueError:
            return jsonify(re_code=RET.PARAMERR, msg='结束时间格式错误，请使用YYYY-MM-DD HH:MM:SS格式')

    deposits_withdrawal_pagination = query.order_by(DepositsWithdrawals.create_at.desc()).paginate(page=page, per_page=per_page, error_out=False)
    deposits_withdrawal_info = deposits_withdrawal_pagination.items

    deposits_withdrawal_list = []
    for deposits_withdrawal in deposits_withdrawal_info:
        deposits_withdrawal_data = {
            'record_id': deposits_withdrawal.record_id,
            'transaction_type': deposits_withdrawal.transaction_type,
            'symbol': deposits_withdrawal.symbol,
            'amount': deposits_withdrawal.amount,
            'fee': deposits_withdrawal.fee,
            'finally_amount': deposits_withdrawal.finally_amount,
            'status': deposits_withdrawal.status,
            'transaction_id': deposits_withdrawal.transaction_id,
            'create_at': deposits_withdrawal.create_at.isoformat() if deposits_withdrawal.create_at else None,
            'update_at': deposits_withdrawal.update_at.isoformat() if deposits_withdrawal.update_at else None,
            'account': deposits_withdrawal.user.phone,
        }
        deposits_withdrawal_list.append(deposits_withdrawal_data)

    data = {
        'deposits_withdrawal_data': deposits_withdrawal_list,
        'total_page': deposits_withdrawal_pagination.pages,
        'current_page': deposits_withdrawal_pagination.page,
        'per_page': per_page,
        'total_count': deposits_withdrawal_pagination.total
    }
    return jsonify(re_code=RET.OK, msg='查询成功', data=data)


@api.route('/admin/digitalwallet', methods=['GET'])
@jwt_required()
def admin_digital_wallet():
    admin_identity = token_auth.get_userinfo()
    admin = Admins.query.filter_by(admin_id=admin_identity['admin_id']).first()
    if admin_identity['role'] != 'admin' or not admin:
        return jsonify(re_code=RET.ROLEERR, msg='用户权限错误')

    symbol = request.args.get('symbol')
    agreement_type = request.args.get('agreement_type')
    user_id = request.args.get('uid')
    per_page = current_app.config['PAGE_SIZE']

    query = BindWallets.query

    if user_id:
        query = query.filter_by(user_id=user_id)
    if symbol:
        query = query.filter_by(symbol=symbol)
    if agreement_type:
        query = query.filter_by(agreement_type=agreement_type)

    digital_wallets_pagination = query.paginate(page=1, per_page=per_page, error_out=False)
    digital_wallets = digital_wallets_pagination.items

    # if not digital_wallets:
    #     return jsonify(re_code=RET.NODATA, msg='用户钱包信息不存在', data=digital_wallets)
    digital_wallets_list = []
    for digital_wallet in digital_wallets:
        digital_wallet_data = {
            'bind_id': digital_wallet.bind_id,
            'symbol': digital_wallet.symbol,
            'address': digital_wallet.address,
            'agreement_type': digital_wallet.agreement_type,
            'comment': digital_wallet.comment,
            'create_at': digital_wallet.created_at.isoformat() if digital_wallet.created_at else None,
        }
        digital_wallets_list.append(digital_wallet_data)
    data = {
        'digital_wallets': digital_wallets_list,
        'total_page': digital_wallets_pagination.pages,
        'current_page': digital_wallets_pagination.page,
        'per_page': per_page,
        'total_count': digital_wallets_pagination.total
    }
    return jsonify(re_code=RET.OK, msg='查询成功', data=data)


@api.route('/admin/deleteuser', methods=['POST'])
@jwt_required()
def delete_user():
    admin_identity = token_auth.get_userinfo()
    admin = Admins.query.filter_by(admin_id=admin_identity['admin_id']).first()
    if admin_identity['role'] != 'admin' or not admin:
        return jsonify(re_code=RET.ROLEERR, msg='用户权限错误')
    user_id = request.json.get('uid')
    if not user_id:
        return jsonify(re_code=RET.PARAMERR, msg='参数错误')
    user = User.query.get(user_id)
    if not user:
        return jsonify(re_code=RET.NODATA, msg='用户不存在')

    try:
        db.session.delete(user)
        db.session.commit()
    except SQLAlchemyError as e:
        current_app.logger.error('/admin/deleteuser：' + str(e))
        db.session.rollback()
        return jsonify(re_code=RET.DBERR, msg='数据库操作失败')
    except Exception as e:
        current_app.logger.error('/admin/deleteuser：' + str(e))
        db.session.rollback()
        return jsonify(re_code=RET.DBERR, msg='删除失败')
    return jsonify(re_code=RET.OK, msg='删除成功')


@api.route('/admin/realnameinfo', methods=['GET'])
@jwt_required()
def realname_info():
    admin_identity = token_auth.get_userinfo()
    admin = Admins.query.filter_by(admin_id=admin_identity['admin_id']).first()
    if admin_identity['role'] != 'admin' or not admin:
        return jsonify(re_code=RET.ROLEERR, msg='用户权限错误')

    status = request.args.get('status')
    page = int(request.args.get('page'))
    per_page = current_app.config['PAGE_SIZE']

    query = UserAuthentication.query
    if status:
        query = query.filter_by(status=status)

    real_name_info_pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    real_name_info = real_name_info_pagination.items

    realname_info_list = []
    for realname_info in real_name_info:
        realname_info_data = realname_info.to_json()
        realname_info_data['user_id'] = realname_info.user.user_id
        realname_info_data['account'] = realname_info.user.phone
        realname_info_list.append(realname_info_data)

    data = {
        'realname_info': realname_info_list,
        'total_page': real_name_info_pagination.pages,
        'current_page': real_name_info_pagination.page,
        'per_page': per_page,
        'total_count': real_name_info_pagination.total
    }
    return jsonify(re_code=RET.OK, msg='查询成功', data=data)


@api.route('/admin/auditinfo', methods=['POST'])
@jwt_required()
def audit_info():
    admin_identity = token_auth.get_userinfo()
    admin = Admins.query.filter_by(admin_id=admin_identity['admin_id']).first()
    if admin_identity['role'] != 'admin' or not admin:
        return jsonify(re_code=RET.ROLEERR, msg='用户权限错误')

    auth_id = request.json.get('auth_id')
    status = request.json.get('status')

    try:
        if status == 'delete':
            UserAuthentication.query.filter_by(auth_id=auth_id).delete()
            db.session.commit()
            return jsonify(re_code=RET.OK, msg='删除成功')
        else:
            UserAuthentication.query.filter_by(auth_id=auth_id).update({'status': status})
            db.session.commit()
            return jsonify(re_code=RET.OK, msg='审核成功')
    except SQLAlchemyError as e:
        current_app.logger.error('/admin/auditinfo：' + str(e))
        db.session.rollback()
        return jsonify(re_code=RET.DBERR, msg='数据库操作失败')
    except Exception as e:
        current_app.logger.error('/admin/auditinfo：' + str(e))
        db.session.rollback()
        return jsonify(re_code=RET.UNKOWNERR, msg='修改失败')


@api.route('/admin/addsettings', methods=['POST'])
@jwt_required()
def withdrawal_setting():
    admin_identity = token_auth.get_userinfo()
    admin = Admins.query.filter_by(admin_id=admin_identity['admin_id']).first()
    if admin_identity['role'] != 'admin' or not admin:
        return jsonify(re_code=RET.ROLEERR, msg='用户权限错误')

    currency = request.json.get('currency')
    min_amount = request.json.get('min_amount')
    max_amount = request.json.get('max_amount')
    fee_rate = request.json.get('fee_rate')
    min_fee = request.json.get('min_fee')

    setting = WithdrawalSettings.query.filter_by(currency=currency).first()
    if not setting:
        if not all([currency, min_amount, max_amount, fee_rate, min_fee]):
            return jsonify(re_code=RET.PARAMERR, msg='参数错误')
        setting = WithdrawalSettings(currency=currency, min_amount=min_amount, max_amount=max_amount, fee_rate=fee_rate, min_fee=min_fee)
        db.session.add(setting)
        msg = '添加成功'
    else:
        if min_amount:
            setting.min_amount = min_amount
        if max_amount:
            setting.max_amount = max_amount
        if fee_rate:
            setting.fee_rate = fee_rate
        if min_fee:
            setting.min_fee = min_fee
        msg = '修改成功'

    db.session.commit()
    return jsonify(re_code=RET.OK, msg=msg)


@api.route('/admin/displaysettings', methods=['GET'])
@jwt_required()
def display_withdrawal_settings():
    admin_identity = token_auth.get_userinfo()
    admin = Admins.query.filter_by(admin_id=admin_identity['admin_id']).first()
    if admin_identity['role'] != 'admin' or not admin:
        return jsonify(re_code=RET.ROLEERR, msg='用户权限错误')

    withdrawal_settings = WithdrawalSettings.query.all()

    withdrawal_settings_list = []
    for withdrawal_setting in withdrawal_settings:
        withdrawal_settings_data = withdrawal_setting.to_json()
        withdrawal_settings_list.append(withdrawal_settings_data)

    return jsonify(re_code=RET.OK, msg='查询成功', data=withdrawal_settings_list)





