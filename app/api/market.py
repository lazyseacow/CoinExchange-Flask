import time
from flask_jwt_extended import jwt_required
from flask import request, jsonify, current_app
import requests
from app.api.verify import auth
from app.api import api
from app.models import User
from app.utils.response_code import RET


@api.route('/klines', methods=['GET'])
@jwt_required()
def get_klines_from_binance():
    user_id = auth.get_userinfo()
    user = User.query.filter_by(user_id=user_id).first()
    if not user:
        return jsonify(re_code=RET.USERERR, msg='用户不存在')

    symbol = request.args.get('symbol')
    interval = request.args.get('interval')
    timeZone = request.args.get('timeZone', default=0, type=int)
    limit = request.args.get('limit', default=500, type=int)
    startTime = request.args.get('startTime')
    endTime =  request.args.get('endTime')

    binance_klines_url = 'https://api1.binance.com/api/v3/klines'
    params = {
        'symbol': symbol,
        'interval': interval,
        'timeZone': timeZone,
        'limit': limit
    }

    if startTime:
        params['startTime'] = startTime
    if endTime:
        params['endTime'] = endTime

    try:
        response = requests.get(url=binance_klines_url, params=params)
        response.raise_for_status()
        return jsonify(re_code=RET.OK, data=response.json())
    except requests.RequestException as e:
        current_app.logger.error(e)
        return jsonify(re_code=RET.THIRDERR, msg='获取数据失败')
