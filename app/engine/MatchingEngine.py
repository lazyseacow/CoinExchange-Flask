from sortedcontainers import SortedDict
from celery import Celery


class MatchingEngine:
    def __init__(self):
        self.buy_orders = SortedDict()  # 高到低排序
        self.sell_orders = SortedDict()  # 低到高排序

    def add_order(self, order):
        if order.side == 'buy':
            self.match_order(order, self.sell_orders)
            if order.quantity > 0:
                self.buy_orders.setdefault(order.price, []).append(order)
        elif order.side == 'sell':
            self.match_order(order, self.buy_orders)
            if order.quantity > 0:
                self.sell_orders.setdefault(order.price, []).append(order)

    def match_order(self, order, opposite_orders):
        while order.quantity > 0 and opposite_orders:
            best_price = opposite_orders.peekitem(0 if order.side == 'sell' else -1)[0]
            if (order.side == 'buy' and order.price < best_price) or (order.side == 'sell' and order.price > best_price):
                break
            self.execute_trade(order, opposite_orders.pop(best_price))

    def execute_trade(self, order, matching_orders):
        # 这里处理匹配订单的交易逻辑
        pass
