from jqdatasdk import *
auth('15097755879','Asdfghjkl021216')
data = get_price('000001.XSHE', start_date='2025-01-01', end_date='2025-01-31', frequency='daily')
print(type(data))

def load_data(security, start_date, end_date):
    """
    获取数据
    """
    auth('15097755879','Asdfghjkl021216')
    data = get_price(security, start_date=start_date, end_date=end_date, frequency='daily')
    prices = data['close'].to_numpy()
    highs = data['high'].to_numpy()
    lows = data['low'].to_numpy()
    opens = data['open'].to_numpy()
    closes = data['close'].to_numpy()
    return prices, highs, lows, opens, closes