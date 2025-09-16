import datetime
import os.path
import sys
import backtrader as bt
import pandas as pd
import json  # 导入 json 模块

def create_dynamic_data_class(lines):
    class DynamicPandasData(bt.feeds.PandasData):
        lines = tuple(lines)
        params = tuple((line, -1) for line in lines)

    return DynamicPandasData

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

    def next(self):
        # 记录所有符合买入条件的股票
        buy_candidates = []
        candidates = []

        for d in self.datas:
            self.log(f'{d._name}, Close, {self.dataclose[d._name][0]:.2f}')

            if self.order:
                return

            # 风险控制卖出条件：ema_60 > close
            if self.getposition(d):
                if d.ema_60[0] > self.dataclose[d._name][0]:
                    self.log(f'SELL CREATE (Risk Control) {d._name}, {self.dataclose[d._name][0]:.2f}', doprint=True)
                    self.order = self.order_target_percent(d, target=0.0)
                    continue  # 卖出后，不再进行买入判断

            # 原始的买入卖出条件
            if not self.getposition(d):
                if d.ema_5 and self.dataclose[d._name][0] > 1.01 * d.ema_5[0]:  # 放宽买入条件
                    buy_candidates.append(d)
            else:
                if d.ema_5 and self.dataclose[d._name][0] < d.ema_5[0]:  # 放宽卖出条件
                    self.log(f'SELL CREATE {d._name}, {self.dataclose[d._name][0]:.2f}', doprint=True)
                    self.order = self.order_target_percent(d, target=0.0)

        # 买入操作
        if buy_candidates:
            # 计算每只股票的分配资金
            cash_per_stock = self.broker.get_cash() / len(buy_candidates)
            for d in buy_candidates:
                # 计算买入的股数
                size = cash_per_stock / self.dataclose[d._name][0]
                self.log(f'BUY CREATE {d._name}, {self.dataclose[d._name][0]:.2f}', doprint=True)
                self.order = self.order_target_percent(d, target=0.99) # 留一些现金

    def stop(self):
        self.pnl = round(self.broker.getvalue() - self.val_start, 2)
        print('策略收益: {}'.format(self.pnl))
        for data_name, comm in self.comm_info.items():
            print(f'{data_name} total comm: {comm:.2f}')


if __name__ == '__main__':
    cerebro = bt.Cerebro()
    cerebro.addstrategy(TestStrategy, printlog=True)

    modpath = os.path.dirname(os.path.abspath(sys.argv[0]))

    # 使用 system_双均线策略 的数据
    datapath = os.path.join(modpath, '..\data_prepared\system_双均线策略\prepared_data_params.csv')
    jsonpath = os.path.join(modpath, '..\data_prepared\system_双均线策略\prepared_data.json')  # json 文件路径

    # 或者使用 system_MACD策略 的数据，取消注释以切换
    # datapath = os.path.join(modpath, '..\data_prepared\system_MACD策略\prepared_data_params.csv')
    # jsonpath = os.path.join(modpath, '..\data_prepared\system_MACD策略\prepared_data.json')  # json 文件路径

    # 从 json 文件读取配置
    with open(jsonpath, 'r', encoding='utf-8') as f:
        json_data = json.load(f)
        param_columns = json_data['param_columns']
        param_columns_map = {col: col for col in param_columns}  # 默认映射
        # 允许在 json 中自定义列名映射，例如：{"system.close": "close_price"}
        if 'column_mapping' in json_data:
            param_columns_map.update(json_data['column_mapping'])

    df = pd.read_csv(datapath, index_col=1, parse_dates=True)
    grouped = df.groupby(df['ts_code'])

    for name, group in grouped:
        available_columns = group.columns.tolist()
        required_columns = ['system.open', 'system.close', 'system.high', 'system.low'] + param_columns
        missing_columns = [col for col in required_columns if param_columns_map.get(col, col) not in available_columns]

        if missing_columns:
            raise ValueError(f"CSV 文件缺少以下列: {missing_columns}")

        data = pd.DataFrame({
            'datetime': group.index,
            'open': group[param_columns_map.get('system.open', 'system.open')].values,
            'close': group[param_columns_map.get('system.close', 'system.close')].values,
            'high': group[param_columns_map.get('system.high', 'system.high')].values,
            'low': group[param_columns_map.get('system.low', 'system.low')].values,
        })

        for col in param_columns:
            data[col.split('.')[-1]] = group[param_columns_map.get(col, col)].values

        # 动态创建数据类
        lines = [col.split('.')[-1] for col in param_columns]
        DynamicDataClass = create_dynamic_data_class(lines)

        feed_kwargs = {
            'dataname': data,
            'name': name,
            'datetime': 0,
            'open': 1,
            'close': 2,
            'high': 3,
            'low': 4,
            'volume': -1,
            'openinterest': -1,
        }

        for line in lines:
            if line in data.columns:
                feed_kwargs[line] = data.columns.get_loc(line)

        data_feed = DynamicDataClass(**feed_kwargs)
        cerebro.adddata(data_feed)

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