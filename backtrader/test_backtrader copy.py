import datetime
import os.path
import sys
import backtrader as bt
import pandas as pd


class MyPandasData(bt.feeds.PandasData):
    lines = ('ema_5', 'ema_60',)
    params = (
        ('ema_5', -1),
        ('ema_60', -1),
    )


class TestStrategy(bt.Strategy):
    def log(self, txt, dt=None, doprint=False):
        if doprint:
            dt = dt or self.datas[0].datetime.date(0)
            print('%s, %s' % (dt.isoformat(), txt))

    def __init__(self):
        self.dataclose = {d._name: d.close for d in self.datas}
        self.order = None

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            self.log(f'ORDER SUBMITTED {order.data._name}, {order.info}', doprint=True)
            return

        if order.status in [order.Completed] and order.executed is not None:
            if order.isbuy():
                self.log(
                    f'BUY EXECUTED {order.data._name}, Price: {order.executed.price:.2f}, Cost: {getattr(order.executed, "cost", 0):.2f}, Comm {order.executed.comm:.2f}',
                    doprint=True)
            elif order.issell():
                self.log(
                    f'SELL EXECUTED {order.data._name}, Price: {order.executed.price:.2f}, Cost: {getattr(order.executed, "cost", 0):.2f}, Comm {order.executed.comm:.2f}',
                    doprint=True)

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log(f'ORDER CANCELED {order.data._name}, Status: {order.Status[order.status]}', doprint=True)

        self.order = None

    def next(self):
        for d in self.datas:
            self.log(f'{d._name}, Close, {self.dataclose[d._name][0]:.2f}')

            if self.order:
                return

            if not self.getposition(d):
                if self.dataclose[d._name][0] > 1.01 * d.ema_5[0]:  # 放宽买入条件
                    self.log(f'BUY CREATE {d._name}, {self.dataclose[d._name][0]:.2f}', doprint=True)
                    self.order = self.order_target_percent(d, target=0.99)  # 留一些现金
            else:
                if self.dataclose[d._name][0] < d.ema_5[0]:  # 放宽卖出条件
                    self.log(f'SELL CREATE {d._name}, {self.dataclose[d._name][0]:.2f}', doprint=True)
                    self.order = self.order_target_percent(d, target=0.0)


if __name__ == '__main__':
    cerebro = bt.Cerebro()
    cerebro.addstrategy(TestStrategy)

    modpath = os.path.dirname(os.path.abspath(sys.argv[0]))
    datapath = os.path.join(modpath, '..\data_prepared\system_双均线策略\prepared_data_params.csv')

    # 使用 pandas 读取 CSV 文件
    df = pd.read_csv(datapath, index_col=1, parse_dates=True)

    # 按照 ts_code 分组
    grouped = df.groupby(df['ts_code'])

    for name, group in grouped:
        # 创建只包含所需列的 DataFrame
        data = pd.DataFrame({
            'datetime': group.index,
            'open': group['system.open'].values,
            'close': group['system.close'].values,
            'high': group['system.high'].values,
            'low': group['system.low'].values,
            'ema_5': group['system.ema_5'].values,
            'ema_60': group['system.ema_60'].values,
        })

        data = MyPandasData(
            dataname=data,
            name=name,  # 将股票代码设置为 data 的 name 属性
            datetime=0,
            open=1,
            close=2,
            high=3,
            low=4,
            volume=-1,  # 没有成交量数据
            openinterest=-1,
            ema_5=5,
            ema_60=6,
        )
        cerebro.adddata(data)

    cerebro.broker.setcash(100000.0)
    cerebro.broker.setcommission(commission=0.001)

    print('Starting Portfolio Value: %.2f' % cerebro.broker.getvalue())

    cerebro.run()

    print('Final Portfolio Value: %.2f' % cerebro.broker.getvalue())

    cerebro.plot(volume=False)