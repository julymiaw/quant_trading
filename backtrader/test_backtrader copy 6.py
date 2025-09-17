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
        ('param_columns_map', {}),  # 映射字段名
        ('param_columns', []),      # 原始字段名列表
        ('select_func', None),
        ('risk_control_func', None),
    )

    def log(self, txt, dt=None, doprint=False):
        if self.params.printlog or doprint:
            dt = dt or self.datas[0].datetime.date(0)
            print('%s, %s' % (dt.isoformat(), txt))

    def __init__(self):
        self.dataclose = {d._name: d.close for d in self.datas}
        self.orders = {}
        self.val_start = self.broker.getvalue()
        self.comm_info = {}
        self.param_map = self.params.param_columns_map
        self.param_keys = self.params.param_columns
        self.select_func = self.params.select_func
        self.risk_control_func = self.params.risk_control_func

    def notify_order(self, order):
        stock = order.data._name

        if order.status in [order.Submitted, order.Accepted]:
            self.log(f'ORDER SUBMITTED {stock}, {order.info}', doprint=True)
            return

        if order.status == order.Completed and order.executed is not None:
            if order.isbuy():
                self.log(
                    f'BUY EXECUTED {stock}, Price: {order.executed.price:.2f}, Cost: {getattr(order.executed, "cost", 0):.2f}, Comm {order.executed.comm:.2f}',
                    doprint=True)
            elif order.issell():
                self.log(
                    f'SELL EXECUTED {stock}, Price: {order.executed.price:.2f}, Cost: {getattr(order.executed, "cost", 0):.2f}, Comm {order.executed.comm:.2f}',
                    doprint=True)
            self.comm_info[stock] = self.comm_info.get(stock, 0) + order.executed.comm

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log(f'ORDER CANCELED {stock}, Status: {order.Status[order.status]}', doprint=True)

        self.orders[stock] = None  # 清除该股票的订单记录`

    def next(self):
        date = self.datas[0].datetime.date(0)
        params = {}
        candidates = []
        current_holdings = []

        for d in self.datas:
            stock = d._name
            param_values = {key: getattr(d, self.param_map.get(key, key).split('.')[-1], [None])[0]
                            for key in self.param_keys}
            param_values["system.close"] = self.dataclose[stock][0]
            params[stock] = param_values

            self.log(f'{stock}, Close, {params[stock]["system.close"]:.2f}')
            candidates.append(stock)

            if self.getposition(d):
                current_holdings.append(stock)

        # 先执行所有卖出逻辑
        safe_holdings = self.risk_control_func(current_holdings, params, date)
        position_count = 3
        selected_stocks = self.select_func(candidates, params, position_count, current_holdings, date)

        for stock in current_holdings:
            if stock not in safe_holdings or stock not in selected_stocks:
                d = next(data for data in self.datas if data._name == stock)
                if not self.orders.get(stock):
                    self.log(f'SELL CREATE {stock}, {self.dataclose[stock][0]:.2f}', doprint=True)
                    self.orders[stock] = self.order_target_percent(d, target=0)

        # 再执行所有买入逻辑
        buy_candidates = [s for s in selected_stocks if s not in current_holdings]
        print(date, buy_candidates)

        if buy_candidates:
            cash_per_stock = self.broker.get_cash() / len(buy_candidates)
            for stock in buy_candidates:
                d = next(data for data in self.datas if data._name == stock)
                if not self.orders.get(stock):
                    self.log(f'BUY CREATE {stock}, {self.dataclose[stock][0]:.2f}', doprint=True)
                    self.orders[stock] = self.order_target_percent(d, target=0.9)


    def stop(self):
        self.pnl = round(self.broker.getvalue() - self.val_start, 2)
        print('策略收益: {}'.format(self.pnl))
        for data_name, comm in self.comm_info.items():
            print(f'{data_name} total comm: {comm:.2f}')


if __name__ == '__main__':
    cerebro = bt.Cerebro()

    modpath = os.path.dirname(os.path.abspath(sys.argv[0]))

    # 使用 system_双均线策略 的数据
    datapath = os.path.join(modpath, '..\data_prepared\system_双均线策略\prepared_data_params.csv')
    jsonpath = os.path.join(modpath, '..\data_prepared\system_双均线策略\prepared_data.json')  # json 文件路径

    # 或者使用 system_MACD策略 的数据，取消注释以切换
    # datapath = os.path.join(modpath, '..\data_prepared\system_MACD策略\prepared_data_params.csv')
    # jsonpath = os.path.join(modpath, '..\data_prepared\system_MACD策略\prepared_data.json')  # json 文件路径

    # 或者使用 system_小市值策略 的数据，取消注释以切换
    # datapath = os.path.join(modpath, '..\data_prepared\system_小市值策略\prepared_data_params.csv')
    # jsonpath = os.path.join(modpath, '..\data_prepared\system_小市值策略\prepared_data.json')  # json 文件路径

    # 从 json 文件读取配置
    with open(jsonpath, 'r', encoding='utf-8') as f:
        json_data = json.load(f)

        # 提取函数定义字符串
        select_func_code = json_data.get('select_func', '')
        risk_control_func_code = json_data.get('risk_control_func', '')

        # 创建函数容器
        local_funcs = {}
        exec(select_func_code, {}, local_funcs)
        exec(risk_control_func_code, {}, local_funcs)

        # 提取函数对象
        select_func = local_funcs.get('select_func')
        risk_control_func = local_funcs.get('risk_control_func')

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

    cerebro.addstrategy(
        TestStrategy,
        printlog=True,
        param_columns_map=param_columns_map,
        param_columns=param_columns,
        select_func=select_func,
        risk_control_func=risk_control_func
    )

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
    won_total = trade_analyzer.get('won', {}).get('total', 0)
    lost_total = trade_analyzer.get('lost', {}).get('total', 0)

    print(f'盈利次数: {won_total}')
    print(f'亏损次数: {lost_total}')

    cerebro.plot(volume=False, iplot=False)