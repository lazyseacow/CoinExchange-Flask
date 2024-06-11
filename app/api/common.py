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
        for symbol in symbols:
            # print(symbol.symbol)
            symbol_list.append(symbol.symbol)

        data = {
            'symbols': symbol_list,
            'side': ['买入', '卖出'],
            'order_type': ['市价委托', '限价委托'],
            'status': ['挂单', '成交', '取消']
        }
        return jsonify(re_code=RET.OK, data=data, msg='交易对获取成功')

    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error('数据库操作异常:' + str(e))
        return jsonify(re_code=RET.DBERR, msg='数据库操作异常')

    except Exception as e:
        current_app.logger.error(e)
        return jsonify(re_code=RET.SERVERERR, msg='服务器异常')



