from __future__ import (absolute_import, division, print_function,
                        unicode_literals)
import datetime  # For datetime objects
import os.path  # To manage paths
import sys  # To find out the script name (in argv[0])
import backtrader as bt
import backtrader.feeds as btfeeds
from backtrader.feeds import GenericCSVData


# 数据准备
class GenericCSV_My(GenericCSVData):

    # 添加 自定义指标 行到从基类继承的行中
    lines = ('ema_5','ema_60')

    # GenericCSVData 中的 openinterest 索引为 7 ... 添加 1
    # 将参数添加到从基类继承的参数中
    params = (('ema_5',3),('ema_60',4))

#初始策略
class TestStrategy(bt.Strategy):
    def log(self, txt, dt=None):
        dt = dt or self.datas[0].datetime.date(0)
        print('%s, %s' % (dt.isoformat(), txt))

    def __init__(self):
        # print("init")
        self.dataclose = self.datas[0].close
        self.order = None

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status in [order.Completed]:
            if order.isbuy():
                self.log('BUY EXECUTED, %.2f' % order.executed.price)
            elif order.issell():
                self.log('SELL EXECUTED, %.2f' % order.executed.price)

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('Order Canceled/Margin/Rejected')

        self.order = None

    def next(self):
        self.log('Close, %.2f' % self.dataclose[0])

        if self.order:
            return

        if not self.position:
            if self.dataclose[0] > 1.01*self.datas[0].ema_5[0]:
                self.log('BUY CREATE, %.2f' % self.dataclose[0])
                # self.order = self.buy()  # 之前的买入方式
                self.order = self.order_target_percent(target=1.0)  # 全仓买入
        else:
            if self.dataclose[0] < self.datas[0].ema_5[0]:
                self.log('SELL CREATE, %.2f' % self.dataclose[0])
                # self.order = self.sell()  # 之前的卖出方式
                self.order = self.order_target_percent(target=0.0)  # 全仓卖出
        


if __name__ == '__main__':
    cerebro = bt.Cerebro()
    cerebro.addstrategy(TestStrategy)

    modpath = os.path.dirname(os.path.abspath(sys.argv[0]))
    datapath = os.path.join(modpath, '..\data_prepared\system_双均线策略\prepared_data_params.csv')

    data = GenericCSV_My(
        dataname=datapath,

        fromdate=datetime.datetime(2024, 1, 1),
        todate=datetime.datetime(2024, 12, 31),

        dtformat=('%Y-%m-%d'),

        datetime=1,
        close=2,
        high=5,
        low=6,
        open=7,
        volume=-1,
        openinterest=-1
    )

    cerebro.adddata(data)
    cerebro.broker.setcash(100000.0)

    print('Starting Portfolio Value: %.2f' % cerebro.broker.getvalue())

    cerebro.run()

    print('Final Portfolio Value: %.2f' % cerebro.broker.getvalue())

    cerebro.plot(volume=False)