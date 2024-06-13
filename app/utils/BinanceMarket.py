from decimal import Decimal
import requests


def get_tricker_price(symbol):
    url = 'https://api.binance.com/api/v3/ticker/price'
    base_currency, quote_currency = symbol.split('/')
    params = {
        'symbol': base_currency + quote_currency,
    }
    response = requests.get(url, params=params)
    price = Decimal(response.json()['price'])
    return price


def get_24hr_ticker_price(symbol):
    url = 'https://api.binance.com/api/v3/ticker/24hr'
    # base_currency, quote_currency = symbol.split('/')
    params = {
        'symbol': symbol,
    }
    response = requests.get(url, params=params)
    print(response)
    # price = Decimal(response.json()['priceChangePercent'])

