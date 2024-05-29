import time

from flask import request, jsonify
import requests

from app.api import api
from app.utils.response_code import RET


@api.route('/klines', methods=['GET'])
def get_klines_from_binance():
    symbol = request.args.get('symbol')
    interval = request.args.get('interval')
    timeZone = request.args.get('timeZone', default=0, type=int)
    limit = request.args.get('limit', default=500, type=int)
    startTime = request.args.get('startTime')
    endTime =  request.args.get('endTime')

    binance_klines_url = 'https://api1.binance.com/api/v3/uiKlines'
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

    response = requests.get(url=binance_klines_url, params=params)
    if response.status_code == 200:
        return jsonify(re_code=RET.OK, data=response.json())
    else:
        return jsonify(re_code=RET.THIRDERR, msg='获取数据失败')
