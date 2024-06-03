import re
from datetime import datetime, timedelta
from flask import current_app, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask_httpauth import HTTPBasicAuth
from app import db
from app.api import api
from app.models import *
from app.utils.response_code import RET
from config import currency_list
from app.api.verify import auth


@api.route('/walletsinfo', methods=['GET'])
@jwt_required()
def get_wallets_info():
    """
    获取钱包中所有货币信息
    :return:
    """
    user_id = auth.get_userinfo()
    user = User.query.filter_by(user_id=user_id).first()
    if not user:
        return jsonify(re_code=RET.NODATA, msg='用户不存在')

    try:
        wallets = User.query.get(user_id).wallets.all()
        if not wallets:
            return jsonify(re_code=RET.NODATA, msg='用户钱包信息不存在')
        wallet_info = [wallet.to_json() for wallet in wallets]
        return jsonify(re_code=RET.OK, msg='OK', data=wallet_info)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(re_code=RET.DBERR, msg='钱包查询失败')
