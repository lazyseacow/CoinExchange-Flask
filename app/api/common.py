from sqlalchemy.exc import SQLAlchemyError

from app.api import api
from app.models.models import *
from flask import jsonify, current_app

from app.utils.response_code import RET


@api.route('/symbols', methods=['GET'])
def get_all_symbols():
    try:
        symbols = Symbols.query.all()

        symbol_list = []
        currency_list = ['USDT']
        for symbol in symbols:
            # print(symbol.symbol)
            symbol_list.append(symbol.symbol)
            currency_list.append(symbol.base_currency)

        data = {
            'symbols': symbol_list,
            'currencys': currency_list,
        }
        return jsonify(re_code=RET.OK, data=data, msg='数据获取成功')

    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error('数据库操作异常:' + str(e))
        return jsonify(re_code=RET.DBERR, msg='数据库操作异常')

    except Exception as e:
        current_app.logger.error(e)
        return jsonify(re_code=RET.SERVERERR, msg='服务器异常')
