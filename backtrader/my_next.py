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