import datetime
import os.path
import sys
import backtrader as bt
import pandas as pd
from my_next import next



class MyPandasData(bt.feeds.PandasData):
    lines = ('ema_5', 'ema_60',)
    params = (
        ('ema_5', -1),
        ('ema_60', -1),
    )


class TestStrategy(bt.Strategy):
    params = (
        ('printlog', False),
    )

    def log(self, txt, dt=None, doprint=False):
        if self.params.printlog or doprint:
            dt = dt or self.datas[0].datetime.date(0)
            print('%s, %s' % (dt.isoformat(), txt))

    def __init__(self):
        self.dataclose = {d._name: d.close for d in self.datas}
        self.order = None
        self.val_start = self.broker.getvalue()
        self.comm_info = {}

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
            self.comm_info[order.data._name] = self.comm_info.get(order.data._name, 0) + order.executed.comm

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log(f'ORDER CANCELED {order.data._name}, Status: {order.Status[order.status]}', doprint=True)

        self.order = None

    next = next

    def stop(self):
        self.pnl = round(self.broker.getvalue() - self.val_start, 2)
        print('策略收益: {}'.format(self.pnl))
        for data_name, comm in self.comm_info.items():
            print(f'{data_name} total comm: {comm:.2f}')


if __name__ == '__main__':
    cerebro = bt.Cerebro()
    cerebro.addstrategy(TestStrategy, printlog=True)

    modpath = os.path.dirname(os.path.abspath(sys.argv[0]))
    datapath = os.path.join(modpath, '..\data_prepared\system_双均线策略\prepared_data_params.csv')

    df = pd.read_csv(datapath, index_col=1, parse_dates=True)
    grouped = df.groupby(df['ts_code'])

    for name, group in grouped:
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
            name=name,
            datetime=0,
            open=1,
            close=2,
            high=3,
            low=4,
            volume=-1,
            openinterest=-1,
            ema_5=5,
            ema_60=6,
        )
        cerebro.adddata(data)

    cerebro.broker.setcash(100000.0)
    cerebro.broker.setcommission(commission=0.001)
    cerebro.addanalyzer(bt.analyzers.TimeReturn, _name='returns')   # 时间回报率
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')  # 夏普比率
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown') # 回撤
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trade_analyzer')

    print('Starting Portfolio Value: %.2f' % cerebro.broker.getvalue())

    results = cerebro.run()
    strategy = results[0]

    print('Final Portfolio Value: %.2f' % cerebro.broker.getvalue())

    # 打印分析结果
    # print('夏普比率:', strategy.analyzers.sharpe.get_analysis()['sharperatio'])
    print('最大回撤:', strategy.analyzers.drawdown.get_analysis()['max']['drawdown'])

    # 交易分析器
    trade_analyzer = strategy.analyzers.trade_analyzer.get_analysis()
    print('盈利次数: {}'.format(trade_analyzer['won']['total']))
    print('亏损次数: {}'.format(trade_analyzer['lost']['total']))

    cerebro.plot(volume=False, iplot=False)