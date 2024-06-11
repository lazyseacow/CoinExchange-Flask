from flask import current_app, jsonify, request
from flask_jwt_extended import jwt_required, create_access_token
from sqlalchemy.exc import SQLAlchemyError

from app import redis_conn
from app.api import api
from app.api.verify import auth
from app.models.models import *
from app.utils.response_code import RET


@api.route('/admin/login', methods=['POST'])
def admin_login():
    username = request.json.get('username')
    password = request.json.get('password')
    if not all([username, password]):
        return jsonify(re_code=RET.PARAMERR, msg='参数错误')

    admin = Admins.query.filter_by(username=username).first()
    print(type(password), type(admin.password))
    if not admin:
        return jsonify(re_code=RET.NODATA, msg='用户不存在')
    if password != admin.password:
        return jsonify(re_code=RET.PWDERR, msg='密码错误')
    if admin.role != 'admin':
        return jsonify(re_code=RET.ROLEERR, msg='用户权限错误')

    identity = {
        "user_id": admin.admin_id,
        "username": username,
        "role": admin.role
    }
    access_token = create_access_token(identity=identity)

    return jsonify(re_code=RET.OK, msg='登录成功', access_token=access_token)


# 登录
@api.route('/admin/orderlist', methods=['POST'])
@jwt_required()
def admin_order_list():
    admin_identity = auth.get_userinfo()
    admin = Admins.query.filter_by(admin_id=admin_identity['user_id']).first()
    if admin_identity['role'] != 'admin' and admin:
        return jsonify(re_code=RET.ROLEERR, msg='用户权限错误')

    symbol = request.json.get('symbol')
    order_type = request.json.get('order_type')
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

    order_info = query.paginate(page=page, per_page=per_page, error_out=False)
    order_item = order_info.items

    order_list = []
    for order in order_item:
        order_data = {
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


# 币币交易
@api.route('/admin/alluser', methods=['POST'])
@jwt_required()
def get_all_user():
    user_identity = auth.get_userinfo()
    admin = Admins.query.filter_by(admin_id=user_identity['user_id']).first()
    if user_identity['role'] != 'admin' and admin:
        return jsonify(re_code=RET.ROLEERR, msg='用户权限错误')

    user_info = User.query.all()
    user_list = []
    for user in user_info:
        last_login = user.user_activity_logs.order_by(UserActivityLogs.activity_time.desc()).first()
        user_data = {
            'user_id': user.user_id,
            'username': user.username,
            'email': user.email,
            'phone': user.phone,
            'join_time': user.join_time.isoformat() if user.join_time else None,
            'last_login_ip': last_login.activity_details if last_login else None,
            'last_seen': user.last_seen.isoformat() if user.last_seen else None
        }
        user_list.append(user_data)
    return jsonify(re_code=RET.OK, msg='查询成功', data=user_list)


# 资产列表
@api.route('/admin/allwallet/<int:page>', methods=['GET'])
@jwt_required()
def get_all_wallet(page):
    admin_identity = auth.get_userinfo()
    admin = Admins.query.filter_by(admin_id=admin_identity['user_id']).first()

    if admin_identity['role'] != 'admin' and admin:
        return jsonify(re_code=RET.ROLEERR, msg='用户权限错误')

    per_page = current_app.config['PAGE_SIZE']

    # 查询所有钱包信息并进行分页
    wallets_pagination = Wallet.query.paginate(page=page, per_page=per_page, error_out=False)
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


@api.route('/admin/assetrecord/<int:page>', methods=['GET'])
@jwt_required()
def get_asset_record(page):
    admin_identity = auth.get_userinfo()
    admin = Admins.query.filter_by(admin_id=admin_identity['user_id']).first()
    if admin_identity['role'] != 'admin' and admin:
        return jsonify(re_code=RET.ROLEERR, msg='用户权限错误')

    per_page = current_app.config['PAGE_SIZE']

    wallet_operations_pagination = WalletOperations.query.paginate(page=page, per_page=per_page, error_out=False)
    wallet_operations = wallet_operations_pagination.items

    user_ids = [wallet_operation.user_id for wallet_operation in wallet_operations]

    # 使用 user_id 批量查询用户信息
    users = User.query.filter(User.user_id.in_(user_ids)).all()
    user_dict = {user.user_id: user for user in users}

    wallet_operation_list = []
    for wallet_operation in wallet_operations:
        user = user_dict.get(wallet_operation.user_id)
        wallet_operation_data = {
            'operation_id': wallet_operation.operation_id,
            'symbol': wallet_operation.symbol,
            'operation_type': wallet_operation.operation_type,
            'operation_time': wallet_operation.operation_time.isoformat() if wallet_operation.operation_time else None,
            'amount': wallet_operation.amount,
            'status': wallet_operation.status,
            'wallet_type': '',
            'account': user.phone if user else ''
        }
        wallet_operation_list.append(wallet_operation_data)

    data = {
        'wallet_operations_data': wallet_operation_list,
        'total_page': wallet_operations_pagination.pages,
        'current_page': wallet_operations_pagination.page,
        'per_page': per_page,
        'total_count': wallet_operations_pagination.total
    }
    return jsonify(re_code=RET.OK, msg='查询成功', data=data)