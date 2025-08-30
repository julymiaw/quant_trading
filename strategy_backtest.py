#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
量化交易系统 - 策略回测脚本
文件名: strategy_backtest.py
虚拟环境: quant_trading
Python版本: 3.10.x (推荐)

使用Backtrader框架实现策略回测，从数据库加载策略定义，执行回测并存储结果
"""

import backtrader as bt
import pandas as pd
import numpy as np
import pymysql
import json
import os
import uuid
import logging
import traceback
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
import argparse
import warnings
from pathlib import Path

# 忽略matplotlib的警告
warnings.filterwarnings("ignore", category=UserWarning, module="matplotlib")

# 设置中文字体支持
plt.rcParams["font.sans-serif"] = ["SimHei"]  # 用来正常显示中文标签
plt.rcParams["axes.unicode_minus"] = False  # 用来正常显示负号


class ConfigManager:
    """配置管理类"""

    @staticmethod
    def load_config(config_file: str = "config.json") -> Dict[str, Any]:
        """加载配置文件"""
        if not os.path.exists(config_file):
            raise FileNotFoundError(f"配置文件不存在: {config_file}")

        with open(config_file, "r", encoding="utf-8") as f:
            config = json.load(f)

        # 验证必需配置
        required_sections = ["database", "backtest"]
        for section in required_sections:
            if section not in config:
                raise ValueError(f"配置文件缺少必需的section: {section}")

        return config


class DatabaseManager:
    """数据库管理类"""

    def __init__(self, config: Dict[str, Any]):
        """
        初始化数据库管理器

        Args:
            config: 配置字典
        """
        self.config = config
        self.connection = None

        # 配置日志
        log_level = config.get("system", {}).get("log_level", "INFO")
        logging.basicConfig(
            level=getattr(logging, log_level),
            format="%(asctime)s - %(levelname)s - %(message)s",
        )
        self.logger = logging.getLogger(__name__)

    def connect_database(self):
        """连接数据库，尝试多种认证方式"""
        db_config = self.config["database"]

        # 获取默认转换器并进行自定义
        conv = pymysql.converters.conversions.copy()
        conv[datetime.date] = pymysql.converters.escape_date

        # 尝试多种连接方式
        connection_methods = [
            {
                "name": "标准连接",
                "params": {
                    "host": db_config["host"],
                    "port": db_config.get("port", 3306),
                    "user": db_config["user"],
                    "password": db_config["password"],
                    "database": db_config["database"],
                    "charset": db_config.get("charset", "utf8mb4"),
                    "autocommit": False,
                    "conv": conv,
                },
            },
            {
                "name": "兼容模式连接",
                "params": {
                    "host": db_config["host"],
                    "port": db_config.get("port", 3306),
                    "user": db_config["user"],
                    "password": db_config["password"],
                    "database": db_config["database"],
                    "charset": db_config.get("charset", "utf8mb4"),
                    "autocommit": False,
                    "auth_plugin_map": {
                        "caching_sha2_password": "mysql_native_password"
                    },
                    "ssl_disabled": True,
                    "conv": conv,
                },
            },
        ]

        for method in connection_methods:
            try:
                self.logger.info(f"尝试{method['name']}...")
                self.connection = pymysql.connect(**method["params"])
                self.logger.info(f"{method['name']}成功")
                return
            except Exception as e:
                self.logger.warning(f"{method['name']}失败: {e}")
                continue

        # 所有方法都失败
        raise Exception("所有数据库连接方式都失败，请检查配置和数据库状态")

    def close_database(self):
        """关闭数据库连接"""
        if self.connection:
            self.connection.close()
            self.logger.info("数据库连接已关闭")

    def get_strategy_by_id(self, strategy_id: str) -> Dict[str, Any]:
        """通过ID获取策略基本信息"""
        try:
            cursor = self.connection.cursor(pymysql.cursors.DictCursor)
            query = """
            SELECT s.strategy_id, s.strategy_name, s.strategy_type, 
                   s.creator_id, s.strategy_desc
            FROM Strategy s
            WHERE s.strategy_id = %s
            """
            cursor.execute(query, (strategy_id,))
            strategy = cursor.fetchone()

            if not strategy:
                self.logger.warning(f"未找到策略ID: {strategy_id}")
                return {}

            return strategy
        except Exception as e:
            self.logger.error(f"获取策略信息失败: {e}")
            raise
        finally:
            if cursor:
                cursor.close()

    def get_strategy_conditions(self, strategy_id: str) -> List[Dict[str, Any]]:
        """获取策略的条件设置"""
        try:
            cursor = self.connection.cursor(pymysql.cursors.DictCursor)
            query = """
            SELECT sc.condition_id, sc.strategy_id, sc.indicator_id, 
                   sc.condition_type, sc.threshold_min, sc.threshold_max,
                   sc.signal_action, sc.condition_order,
                   ti.indicator_name, ti.calculation_method, ti.default_period
            FROM StrategyCondition sc
            JOIN TechnicalIndicator ti ON sc.indicator_id = ti.indicator_id
            WHERE sc.strategy_id = %s
            ORDER BY sc.condition_order
            """
            cursor.execute(query, (strategy_id,))
            conditions = cursor.fetchall()

            if not conditions:
                self.logger.warning(f"策略 {strategy_id} 没有定义条件")
                return []

            return conditions
        except Exception as e:
            self.logger.error(f"获取策略条件失败: {e}")
            raise
        finally:
            if cursor:
                cursor.close()

    def get_stock_data(
        self, stock_code: str, start_date: str, end_date: str
    ) -> pd.DataFrame:
        """获取指定股票的历史数据"""
        try:
            cursor = self.connection.cursor()
            query = """
            SELECT stock_code, trade_date, open_price, high_price, low_price,
                   close_price, volume, amount
            FROM StockMarketData
            WHERE stock_code = %s AND trade_date BETWEEN %s AND %s
            ORDER BY trade_date
            """
            cursor.execute(query, (stock_code, start_date, end_date))
            results = cursor.fetchall()

            if not results:
                self.logger.warning(
                    f"未找到股票 {stock_code} 在 {start_date} 至 {end_date} 的数据"
                )
                return pd.DataFrame()

            columns = [
                "stock_code",
                "date",
                "open",
                "high",
                "low",
                "close",
                "volume",
                "amount",
            ]
            df = pd.DataFrame(results, columns=columns)

            # 转换日期列为datetime类型
            df["date"] = pd.to_datetime(df["date"])

            # 确保数值列为数值类型
            numeric_cols = ["open", "high", "low", "close", "volume", "amount"]
            for col in numeric_cols:
                df[col] = pd.to_numeric(df[col])

            return df
        except Exception as e:
            self.logger.error(f"获取股票数据失败: {e}")
            raise
        finally:
            if cursor:
                cursor.close()

    def get_all_strategies(self) -> List[Dict[str, Any]]:
        """获取所有可用的策略"""
        try:
            cursor = self.connection.cursor(pymysql.cursors.DictCursor)
            query = """
            SELECT s.strategy_id, s.strategy_name, s.strategy_type, 
                   s.creator_id, s.strategy_desc, COUNT(sc.condition_id) as condition_count
            FROM Strategy s
            LEFT JOIN StrategyCondition sc ON s.strategy_id = sc.strategy_id
            GROUP BY s.strategy_id
            HAVING condition_count > 0
            ORDER BY s.strategy_id
            """
            cursor.execute(query)
            strategies = cursor.fetchall()

            if not strategies:
                self.logger.warning("未找到可用的策略")
                return []

            return strategies
        except Exception as e:
            self.logger.error(f"获取策略列表失败: {e}")
            raise
        finally:
            if cursor:
                cursor.close()

    def save_backtest_report(self, report_data: Dict[str, Any]) -> str:
        """保存回测报告到数据库"""
        try:
            cursor = self.connection.cursor()

            # 生成UUID作为报告ID
            report_id = str(uuid.uuid4())

            query = """
            INSERT INTO BacktestReport (
                report_id, strategy_id, user_id, start_date, end_date,
                initial_fund, final_fund, total_return, annual_return,
                max_drawdown, sharpe_ratio, win_rate, profit_loss_ratio,
                trade_count, report_generate_time, report_status
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            """

            params = (
                report_id,
                report_data["strategy_id"],
                report_data["user_id"],
                report_data["start_date"],
                report_data["end_date"],
                report_data["initial_fund"],
                report_data["final_fund"],
                report_data["total_return"],
                report_data["annual_return"],
                report_data["max_drawdown"],
                report_data.get("sharpe_ratio"),
                report_data.get("win_rate"),
                report_data.get("profit_loss_ratio"),
                report_data["trade_count"],
                datetime.now(),
                "completed",
            )

            cursor.execute(query, params)
            self.connection.commit()

            self.logger.info(f"成功保存回测报告: {report_id}")

            # 记录系统日志
            self.log_operation(
                report_data["user_id"],
                "backtest",
                f"完成策略{report_data['strategy_id']}的回测",
                "success",
            )

            return report_id
        except Exception as e:
            if self.connection:
                self.connection.rollback()
            self.logger.error(f"保存回测报告失败: {e}")
            raise
        finally:
            if cursor:
                cursor.close()

    def log_operation(
        self, user_id: str, operation_type: str, content: str, result: str
    ) -> None:
        """记录系统操作日志"""
        try:
            cursor = self.connection.cursor()

            query = """
            INSERT INTO SystemLog (
                log_id, operator_id, operator_role, operation_type, 
                operation_content, operation_result
            ) VALUES (
                %s, %s, %s, %s, %s, %s
            )
            """

            # 获取用户角色
            role_query = "SELECT user_role FROM User WHERE user_id = %s"
            cursor.execute(role_query, (user_id,))
            role_result = cursor.fetchone()
            user_role = role_result[0] if role_result else "system"

            log_id = str(uuid.uuid4())
            params = (log_id, user_id, user_role, operation_type, content, result)

            cursor.execute(query, params)
            self.connection.commit()

        except Exception as e:
            if self.connection:
                self.connection.rollback()
            self.logger.error(f"记录系统日志失败: {e}")
        finally:
            if cursor:
                cursor.close()


class DynamicBacktestStrategy(bt.Strategy):
    """动态回测策略类，可根据数据库中的策略条件动态配置"""

    params = (
        ("strategy_conditions", []),  # 策略条件列表
        ("debug_mode", False),  # 调试模式
    )

    def __init__(self):
        """初始化策略"""
        self.order = None  # 当前订单
        self.buyprice = None  # 买入价格
        self.buycomm = None  # 买入手续费

        # 计算所需的技术指标
        self.indicators = {}
        self.setup_indicators()

        # 初始化交易记录
        self.trades = []

        # 日志
        self.logger = logging.getLogger(__name__)

    def setup_indicators(self):
        """根据策略条件设置技术指标"""
        # 用于记录已添加的指标，避免重复添加
        added_indicators = set()

        for condition in self.params.strategy_conditions:
            indicator_id = condition["indicator_id"]

            # 如果指标已添加，则跳过
            if indicator_id in added_indicators:
                continue

            # 根据指标类型添加相应的技术指标
            if indicator_id == "RSI":
                period = condition.get("default_period", 14)
                self.indicators[indicator_id] = bt.indicators.RSI(
                    self.data.close, period=period
                )

            elif indicator_id == "MACD":
                self.indicators[indicator_id] = bt.indicators.MACD(
                    self.data.close, period_me1=12, period_me2=26, period_signal=9
                )
                self.indicators["MACD_signal"] = self.indicators[indicator_id].signal

            elif indicator_id == "BOLL":
                period = condition.get("default_period", 20)
                self.indicators[indicator_id] = bt.indicators.BollingerBands(
                    self.data.close, period=period
                )
                self.indicators["BOLL_top"] = self.indicators[indicator_id].top
                self.indicators["BOLL_mid"] = self.indicators[indicator_id].mid
                self.indicators["BOLL_bot"] = self.indicators[indicator_id].bot

            elif indicator_id.startswith("MA"):
                # 例如MA5、MA20等
                period = int(indicator_id[2:])
                self.indicators[indicator_id] = bt.indicators.SMA(
                    self.data.close, period=period
                )

            elif indicator_id == "VOLUME_MA":
                period = condition.get("default_period", 10)
                self.indicators[indicator_id] = bt.indicators.SMA(
                    self.data.volume, period=period
                )

            # 将指标添加到已添加集合中
            added_indicators.add(indicator_id)

    def check_conditions(self, action_type):
        """检查指定动作类型的所有条件是否满足"""
        conditions_met = True

        # 找出所有指定动作类型的条件
        action_conditions = [
            c
            for c in self.params.strategy_conditions
            if c["signal_action"] == action_type
        ]

        if not action_conditions:
            return False

        for condition in action_conditions:
            indicator_id = condition["indicator_id"]
            condition_type = condition["condition_type"]
            threshold_min = condition.get("threshold_min")
            threshold_max = condition.get("threshold_max")

            # 获取指标当前值
            if indicator_id in self.indicators:
                indicator_value = self.indicators[indicator_id][0]

                # 根据条件类型检查条件
                if condition_type == "greater":
                    if threshold_min is not None and not (
                        indicator_value > threshold_min
                    ):
                        conditions_met = False
                        break

                elif condition_type == "less":
                    if threshold_max is not None and not (
                        indicator_value < threshold_max
                    ):
                        conditions_met = False
                        break

                elif condition_type == "between":
                    if threshold_min is not None and threshold_max is not None:
                        if not (threshold_min <= indicator_value <= threshold_max):
                            conditions_met = False
                            break

                elif condition_type == "cross_up":
                    # 交叉上穿需要检查前一天和当前的值
                    if indicator_id.startswith("MA"):
                        # 例如：MA5上穿MA20
                        # 假设condition的threshold_min中存储了被上穿的指标
                        cross_indicator = threshold_min
                        if cross_indicator in self.indicators:
                            # 检查昨天的交叉情况
                            if len(self) > 1:  # 确保有足够的数据点
                                yesterday_indicator = self.indicators[indicator_id][-1]
                                yesterday_cross = self.indicators[cross_indicator][-1]
                                today_indicator = self.indicators[indicator_id][0]
                                today_cross = self.indicators[cross_indicator][0]

                                if not (
                                    yesterday_indicator < yesterday_cross
                                    and today_indicator > today_cross
                                ):
                                    conditions_met = False
                                    break
                            else:
                                conditions_met = False
                                break

                elif condition_type == "cross_down":
                    # 类似cross_up的逻辑，但方向相反
                    if indicator_id.startswith("MA"):
                        cross_indicator = threshold_max
                        if cross_indicator in self.indicators:
                            if len(self) > 1:
                                yesterday_indicator = self.indicators[indicator_id][-1]
                                yesterday_cross = self.indicators[cross_indicator][-1]
                                today_indicator = self.indicators[indicator_id][0]
                                today_cross = self.indicators[cross_indicator][0]

                                if not (
                                    yesterday_indicator > yesterday_cross
                                    and today_indicator < today_cross
                                ):
                                    conditions_met = False
                                    break
                            else:
                                conditions_met = False
                                break
            else:
                # 如果指标不存在，条件不满足
                conditions_met = False
                break

        return conditions_met

    def next(self):
        """每个数据点的主策略逻辑"""
        # 如果有未完成的订单，不操作
        if self.order:
            return

        # 检查是否满足买入条件
        if not self.position:  # 当前没有持仓
            if self.check_conditions("buy"):
                self.log(f"买入信号触发, 价格: {self.data.close[0]}")
                self.order = self.buy()
        else:  # 当前有持仓
            # 检查是否满足卖出条件
            if self.check_conditions("sell"):
                self.log(f"卖出信号触发, 价格: {self.data.close[0]}")
                self.order = self.sell()

    def notify_order(self, order):
        """订单状态更新通知"""
        if order.status in [order.Submitted, order.Accepted]:
            # 订单提交或接受，不做操作
            return

        # 检查订单是否完成
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(
                    f"买入执行成功: 价格: {order.executed.price}, "
                    f"成本: {order.executed.value}, "
                    f"手续费: {order.executed.comm}"
                )
                self.buyprice = order.executed.price
                self.buycomm = order.executed.comm
            else:  # 卖出
                profit = (order.executed.price - self.buyprice) * order.executed.size
                self.log(
                    f"卖出执行成功: 价格: {order.executed.price}, "
                    f"成本: {order.executed.value}, "
                    f"手续费: {order.executed.comm}, "
                    f"利润: {profit}"
                )

            # 记录交易
            self.trades.append(
                {
                    "type": "buy" if order.isbuy() else "sell",
                    "price": order.executed.price,
                    "size": order.executed.size,
                    "value": order.executed.value,
                    "commission": order.executed.comm,
                    "date": self.data.datetime.date(0),
                }
            )

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log(f"订单取消/保证金不足/拒绝: {order.status}")

        # 重置订单
        self.order = None

    def notify_trade(self, trade):
        """交易完成通知"""
        if not trade.isclosed:
            return

        self.log(f"交易利润: 毛利润: {trade.pnl}, 净利润: {trade.pnlcomm}")

    def log(self, txt, dt=None):
        """日志函数"""
        dt = dt or self.data.datetime.date(0)
        if self.params.debug_mode:
            print(f"{dt.isoformat()}, {txt}")


class BacktestEngine:
    """回测引擎，封装Backtrader的回测逻辑"""

    def __init__(self, config: Dict[str, Any], db_manager: DatabaseManager):
        """
        初始化回测引擎

        Args:
            config: 配置字典
            db_manager: 数据库管理器实例
        """
        self.config = config
        self.db_manager = db_manager
        self.logger = logging.getLogger(__name__)

    def run_backtest(
        self,
        strategy_id: str,
        stock_code: str,
        start_date: str,
        end_date: str,
        initial_cash: float = 100000.0,
        user_id: str = "admin_001",
    ) -> Dict[str, Any]:
        """
        运行回测

        Args:
            strategy_id: 策略ID
            stock_code: 股票代码
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            initial_cash: 初始资金
            user_id: 用户ID

        Returns:
            回测结果字典
        """
        # 1. 获取策略信息
        strategy_info = self.db_manager.get_strategy_by_id(strategy_id)
        if not strategy_info:
            raise ValueError(f"未找到策略ID: {strategy_id}")

        # 2. 获取策略条件
        strategy_conditions = self.db_manager.get_strategy_conditions(strategy_id)
        if not strategy_conditions:
            raise ValueError(f"策略 {strategy_id} 没有定义条件")

        # 3. 获取股票数据
        stock_data = self.db_manager.get_stock_data(stock_code, start_date, end_date)
        if stock_data.empty:
            raise ValueError(
                f"未找到股票 {stock_code} 在 {start_date} 至 {end_date} 的数据"
            )

        # 4. 创建Backtrader Cerebro引擎
        cerebro = bt.Cerebro()

        # 5. 添加数据
        data = self.prepare_data_feed(stock_data)
        cerebro.adddata(data)

        # 6. 设置初始资金
        cerebro.broker.setcash(initial_cash)

        # 设置手续费，千分之五
        cerebro.broker.setcommission(commission=0.0005)

        # 7. 添加策略
        cerebro.addstrategy(
            DynamicBacktestStrategy,
            strategy_conditions=strategy_conditions,
            debug_mode=self.config.get("backtest", {}).get("debug_mode", False),
        )

        # 8. 添加分析器
        cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name="sharpe")
        cerebro.addanalyzer(bt.analyzers.DrawDown, _name="drawdown")
        cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name="trades")
        cerebro.addanalyzer(bt.analyzers.Returns, _name="returns")

        # 9. 运行回测
        self.logger.info(f"开始运行策略 {strategy_id} 在 {stock_code} 上的回测...")
        results = cerebro.run()
        strat = results[0]

        # 10. 分析结果
        backtest_result = self.analyze_results(
            strat, strategy_id, stock_code, start_date, end_date, initial_cash, user_id
        )

        # 11. 保存结果到数据库
        report_id = self.db_manager.save_backtest_report(backtest_result)
        backtest_result["report_id"] = report_id

        # 12. 绘制结果图表
        if self.config.get("backtest", {}).get("plot_results", True):
            self.plot_results(cerebro, strategy_info["strategy_name"], stock_code)

        return backtest_result

    def prepare_data_feed(self, stock_data: pd.DataFrame) -> bt.feeds.PandasData:
        """
        准备Backtrader可用的数据格式

        Args:
            stock_data: 股票数据DataFrame

        Returns:
            Backtrader PandasData对象
        """
        # 确保索引是日期
        stock_data = stock_data.set_index("date")

        # 创建PandasData对象
        data = bt.feeds.PandasData(
            dataname=stock_data,
            # -1表示自动从索引中获取日期
            datetime=-1,
            open=stock_data.columns.get_loc("open"),
            high=stock_data.columns.get_loc("high"),
            low=stock_data.columns.get_loc("low"),
            close=stock_data.columns.get_loc("close"),
            volume=stock_data.columns.get_loc("volume"),
            openinterest=-1,  # 不使用持仓量
        )

        return data

    def analyze_results(
        self,
        strat,
        strategy_id: str,
        stock_code: str,
        start_date: str,
        end_date: str,
        initial_cash: float,
        user_id: str,
    ) -> Dict[str, Any]:
        """
        分析回测结果

        Args:
            strat: 策略实例
            strategy_id: 策略ID
            stock_code: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            initial_cash: 初始资金
            user_id: 用户ID

        Returns:
            回测结果字典
        """
        # 获取分析器结果
        sharpe = strat.analyzers.sharpe.get_analysis()
        drawdown = strat.analyzers.drawdown.get_analysis()
        trades = strat.analyzers.trades.get_analysis()
        returns = strat.analyzers.returns.get_analysis()

        # 计算最终资金
        final_value = strat.broker.getvalue()

        # 计算总收益率
        total_return = (final_value / initial_cash) - 1.0

        # 计算年化收益率
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        years = (end - start).days / 365.25
        annual_return = ((1 + total_return) ** (1 / years)) - 1 if years > 0 else 0

        # 最大回撤
        max_drawdown = drawdown.get("max", {}).get("drawdown", 0) / 100

        # 夏普比率
        sharpe_ratio = sharpe.get("sharperatio", 0)

        # 交易统计
        total_trades = trades.get("total", {}).get("total", 0)
        won_trades = trades.get("won", {}).get("total", 0)
        lost_trades = trades.get("lost", {}).get("total", 0)

        # 胜率
        win_rate = won_trades / total_trades if total_trades > 0 else 0

        # 盈亏比
        avg_won = trades.get("won", {}).get("pnl", {}).get("average", 0)
        avg_lost = trades.get("lost", {}).get("pnl", {}).get("average", 0)
        profit_loss_ratio = abs(avg_won / avg_lost) if avg_lost != 0 else 0

        # 构建结果字典
        result = {
            "strategy_id": strategy_id,
            "user_id": user_id,
            "start_date": start_date,
            "end_date": end_date,
            "initial_fund": initial_cash,
            "final_fund": final_value,
            "total_return": total_return,
            "annual_return": annual_return,
            "max_drawdown": max_drawdown,
            "sharpe_ratio": sharpe_ratio,
            "win_rate": win_rate,
            "profit_loss_ratio": profit_loss_ratio,
            "trade_count": total_trades,
            "stock_code": stock_code,
        }

        return result

    def plot_results(self, cerebro: bt.Cerebro, strategy_name: str, stock_code: str):
        """
        绘制回测结果图表

        Args:
            cerebro: Cerebro实例
            strategy_name: 策略名称
            stock_code: 股票代码
        """
        try:
            cerebro.plot(
                style="candlestick",
                barup="red",
                bardown="green",
                grid=True,
                subplot=True,
                title=f"{strategy_name} - {stock_code}回测结果",
            )

            self.logger.info("回测结果图表已显示，请查看弹出的窗口")

        except Exception as e:
            self.logger.error(f"绘制回测结果图表失败: {e}")

    def run_monte_carlo_simulation(
        self,
        strategy_id: str,
        stock_code: str,
        start_date: str,
        end_date: str,
        initial_cash: float = 100000.0,
        simulations: int = 50,
        user_id: str = "admin_001",
    ) -> Dict[str, Any]:
        """
        运行蒙特卡洛模拟

        Args:
            strategy_id: 策略ID
            stock_code: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            initial_cash: 初始资金
            simulations: 模拟次数
            user_id: 用户ID

        Returns:
            模拟结果字典
        """
        self.logger.info(
            f"开始运行蒙特卡洛模拟，策略: {strategy_id}, 股票: {stock_code}, 模拟次数: {simulations}"
        )

        # 获取股票数据
        stock_data = self.db_manager.get_stock_data(stock_code, start_date, end_date)
        if stock_data.empty:
            raise ValueError(
                f"未找到股票 {stock_code} 在 {start_date} 至 {end_date} 的数据"
            )

        # 获取策略信息
        strategy_info = self.db_manager.get_strategy_by_id(strategy_id)
        if not strategy_info:
            raise ValueError(f"未找到策略ID: {strategy_id}")

        # 获取策略条件
        strategy_conditions = self.db_manager.get_strategy_conditions(strategy_id)
        if not strategy_conditions:
            raise ValueError(f"策略 {strategy_id} 没有定义条件")

        # 存储每次模拟的结果
        results = []

        for i in range(simulations):
            # 创建新的Cerebro实例
            cerebro = bt.Cerebro()

            # 添加数据
            data = self.prepare_data_feed(stock_data.copy())
            cerebro.adddata(data)

            # 设置初始资金
            cerebro.broker.setcash(initial_cash)

            # 设置手续费
            cerebro.broker.setcommission(commission=0.0005)

            # 添加策略，每次模拟可能稍微调整参数
            cerebro.addstrategy(
                DynamicBacktestStrategy,
                strategy_conditions=strategy_conditions,
                debug_mode=False,
            )

            # 添加分析器
            cerebro.addanalyzer(bt.analyzers.DrawDown, _name="drawdown")
            cerebro.addanalyzer(bt.analyzers.Returns, _name="returns")

            # 运行模拟
            sim_results = cerebro.run()
            strat = sim_results[0]

            # 获取关键指标
            drawdown = strat.analyzers.drawdown.get_analysis()
            returns = strat.analyzers.returns.get_analysis()

            # 计算最终资金
            final_value = strat.broker.getvalue()

            # 计算总收益率
            total_return = (final_value / initial_cash) - 1.0

            # 最大回撤
            max_drawdown = drawdown.get("max", {}).get("drawdown", 0) / 100

            # 将结果添加到列表
            results.append(
                {
                    "simulation": i + 1,
                    "total_return": total_return,
                    "max_drawdown": max_drawdown,
                    "final_value": final_value,
                }
            )

            if (i + 1) % 10 == 0:
                self.logger.info(f"已完成 {i + 1}/{simulations} 次模拟")

        # 分析蒙特卡洛模拟结果
        df_results = pd.DataFrame(results)

        # 计算统计量
        avg_return = df_results["total_return"].mean()
        std_return = df_results["total_return"].std()
        avg_drawdown = df_results["max_drawdown"].mean()
        worst_drawdown = df_results["max_drawdown"].max()

        # 计算置信区间
        return_95_ci = (
            avg_return - 1.96 * std_return / np.sqrt(simulations),
            avg_return + 1.96 * std_return / np.sqrt(simulations),
        )

        # 统计有多少次模拟的最大回撤小于15%
        drawdown_under_15 = (df_results["max_drawdown"] < 0.15).sum() / simulations

        # 构建结果字典
        monte_carlo_result = {
            "strategy_id": strategy_id,
            "stock_code": stock_code,
            "simulations": simulations,
            "avg_return": avg_return,
            "std_return": std_return,
            "return_95_ci_low": return_95_ci[0],
            "return_95_ci_high": return_95_ci[1],
            "avg_drawdown": avg_drawdown,
            "worst_drawdown": worst_drawdown,
            "prob_drawdown_under_15": drawdown_under_15,
            "simulation_results": df_results.to_dict(orient="records"),
        }

        # 绘制蒙特卡洛模拟结果
        self.plot_monte_carlo_results(
            monte_carlo_result, strategy_info["strategy_name"], stock_code
        )

        return monte_carlo_result

    def plot_monte_carlo_results(
        self, results: Dict[str, Any], strategy_name: str, stock_code: str
    ):
        """
        绘制蒙特卡洛模拟结果

        Args:
            results: 模拟结果字典
            strategy_name: 策略名称
            stock_code: 股票代码
        """
        try:
            # 创建图表
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))

            # 绘制收益率分布
            df_results = pd.DataFrame(results["simulation_results"])
            ax1.hist(df_results["total_return"] * 100, bins=20, alpha=0.7, color="blue")
            ax1.axvline(
                results["avg_return"] * 100,
                color="red",
                linestyle="dashed",
                linewidth=2,
            )
            ax1.set_title(f"{strategy_name} - 收益率分布")
            ax1.set_xlabel("总收益率 (%)")
            ax1.set_ylabel("频率")
            ax1.grid(True)

            # 绘制最大回撤分布
            ax2.hist(
                df_results["max_drawdown"] * 100, bins=20, alpha=0.7, color="green"
            )
            ax2.axvline(
                results["avg_drawdown"] * 100,
                color="red",
                linestyle="dashed",
                linewidth=2,
            )
            ax2.axvline(15, color="black", linestyle="dashed", linewidth=2)
            ax2.set_title(f"{strategy_name} - 最大回撤分布")
            ax2.set_xlabel("最大回撤 (%)")
            ax2.set_ylabel("频率")
            ax2.grid(True)

            plt.tight_layout()

            # 添加文字说明
            fig.text(
                0.5,
                0.01,
                f"平均收益率: {results['avg_return']*100:.2f}% | "
                f"95%置信区间: [{results['return_95_ci_low']*100:.2f}%, {results['return_95_ci_high']*100:.2f}%] | "
                f"平均最大回撤: {results['avg_drawdown']*100:.2f}% | "
                f"最大回撤<15%的概率: {results['prob_drawdown_under_15']*100:.1f}%",
                ha="center",
                fontsize=12,
            )

            # 保存图表
            output_dir = self.config.get("backtest", {}).get(
                "output_dir", "backtest_results"
            )
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)

            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            filename = (
                f"{output_dir}/{strategy_name}_{stock_code}_MonteCarlo_{timestamp}.png"
            )
            plt.savefig(filename)
            self.logger.info(f"蒙特卡洛模拟结果图表已保存至: {filename}")

            # 关闭图表
            plt.close()

        except Exception as e:
            self.logger.error(f"绘制蒙特卡洛模拟结果图表失败: {e}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="量化交易系统 - 策略回测脚本")
    parser.add_argument("--strategy", type=str, help="策略ID")
    parser.add_argument("--stock", type=str, help="股票代码")
    parser.add_argument("--start", type=str, help="开始日期 (YYYY-MM-DD)")
    parser.add_argument("--end", type=str, help="结束日期 (YYYY-MM-DD)")
    parser.add_argument("--cash", type=float, default=100000.0, help="初始资金")
    parser.add_argument("--user", type=str, default="admin_001", help="用户ID")
    parser.add_argument("--montecarlo", action="store_true", help="运行蒙特卡洛模拟")
    parser.add_argument("--simulations", type=int, default=50, help="蒙特卡洛模拟次数")
    parser.add_argument("--list", action="store_true", help="列出所有可用策略")

    args = parser.parse_args()

    print("🚀 量化交易系统 - 策略回测脚本")
    print("文件名: strategy_backtest.py")
    print("虚拟环境: quant_trading")
    print("推荐Python版本: 3.10.x")
    print("=" * 60)

    try:
        # 1. 加载配置
        print("📄 加载配置文件...")
        config = ConfigManager.load_config("config.json")
        print("✅ 配置文件加载成功")

        # 2. 创建数据库管理器
        db_manager = DatabaseManager(config)

        # 3. 连接数据库
        print("🔌 连接数据库...")
        db_manager.connect_database()
        print("✅ 数据库连接成功")

        # 4. 创建回测引擎
        backtest_engine = BacktestEngine(config, db_manager)

        # 5. 根据参数执行不同操作
        if args.list:
            # 列出所有可用策略
            strategies = db_manager.get_all_strategies()
            if strategies:
                print("\n📋 可用策略列表:")
                print("=" * 80)
                print(
                    f"{'策略ID':<12} | {'策略名称':<20} | {'类型':<10} | {'条件数':<8} | {'描述'}"
                )
                print("-" * 80)
                for strat in strategies:
                    strategy_type = (
                        "内置" if strat["strategy_type"] == "builtin" else "自定义"
                    )
                    print(
                        f"{strat['strategy_id']:<12} | {strat['strategy_name']:<20} | {strategy_type:<10} | {strat['condition_count']:<8} | {strat.get('strategy_desc', '')[:40]}"
                    )
                print("=" * 80)
            else:
                print("❌ 未找到可用策略")

        elif args.strategy and args.stock:
            # 设置默认日期范围（如果未提供）
            if not args.start:
                args.start = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
            if not args.end:
                args.end = datetime.now().strftime("%Y-%m-%d")

            print(f"\n📈 回测配置:")
            print(f"  策略ID: {args.strategy}")
            print(f"  股票代码: {args.stock}")
            print(f"  时间范围: {args.start} 至 {args.end}")
            print(f"  初始资金: {args.cash}")

            if args.montecarlo:
                # 运行蒙特卡洛模拟
                print(f"\n🔄 开始运行蒙特卡洛模拟 ({args.simulations}次)...")
                monte_carlo_results = backtest_engine.run_monte_carlo_simulation(
                    args.strategy,
                    args.stock,
                    args.start,
                    args.end,
                    args.cash,
                    args.simulations,
                    args.user,
                )

                # 显示蒙特卡洛模拟结果摘要
                print("\n📊 蒙特卡洛模拟结果:")
                print(f"  平均收益率: {monte_carlo_results['avg_return']*100:.2f}%")
                print(f"  收益率标准差: {monte_carlo_results['std_return']*100:.2f}%")
                print(
                    f"  95%置信区间: [{monte_carlo_results['return_95_ci_low']*100:.2f}%, {monte_carlo_results['return_95_ci_high']*100:.2f}%]"
                )
                print(f"  平均最大回撤: {monte_carlo_results['avg_drawdown']*100:.2f}%")
                print(
                    f"  最坏情况回撤: {monte_carlo_results['worst_drawdown']*100:.2f}%"
                )
                print(
                    f"  最大回撤<15%的概率: {monte_carlo_results['prob_drawdown_under_15']*100:.1f}%"
                )

            else:
                # 运行标准回测
                print("\n🔄 开始运行回测...")
                backtest_results = backtest_engine.run_backtest(
                    args.strategy,
                    args.stock,
                    args.start,
                    args.end,
                    args.cash,
                    args.user,
                )

                # 显示回测结果
                print("\n📊 回测结果:")
                print(f"  报告ID: {backtest_results['report_id']}")
                print(f"  初始资金: {backtest_results['initial_fund']:.2f}")
                print(f"  最终资金: {backtest_results['final_fund']:.2f}")
                print(f"  总收益率: {backtest_results['total_return']*100:.2f}%")
                print(f"  年化收益率: {backtest_results['annual_return']*100:.2f}%")
                print(f"  最大回撤: {backtest_results['max_drawdown']*100:.2f}%")

                # 安全处理可能为None的值
                sharpe_ratio = backtest_results.get("sharpe_ratio")
                if sharpe_ratio is not None:
                    print(f"  夏普比率: {sharpe_ratio:.4f}")
                else:
                    print(f"  夏普比率: 不适用")

                win_rate = backtest_results.get("win_rate")
                if win_rate is not None:
                    print(f"  胜率: {win_rate*100:.2f}%")
                else:
                    print(f"  胜率: 不适用")

                profit_loss_ratio = backtest_results.get("profit_loss_ratio")
                if profit_loss_ratio is not None:
                    print(f"  盈亏比: {profit_loss_ratio:.4f}")
                else:
                    print(f"  盈亏比: 不适用")

                print(f"  总交易次数: {backtest_results['trade_count']}")

        else:
            print("\n❓ 请指定策略ID和股票代码，或使用--list参数查看可用策略")
            print(
                "示例: python strategy_backtest.py --strategy STRAT_001 --stock 000001.SZ"
            )
            print("查看帮助: python strategy_backtest.py --help")

        print("\n🎉 策略回测脚本执行完成！")

    except FileNotFoundError as e:
        print(f"❌ 配置文件错误: {e}")
        print("💡 请运行 python test_database_connection.py 生成配置文件")
    except ValueError as e:
        print(f"❌ 参数错误: {e}")
    except Exception as e:
        error_msg = f"处理过程中发生错误: {e}"
        print(f"❌ {error_msg}")
        logging.error(traceback.format_exc())

    finally:
        if "db_manager" in locals():
            db_manager.close_database()


def show_usage():
    """显示使用说明"""
    print(
        """
📖 策略回测脚本使用说明:

1️⃣ 列出所有可用策略:
   python strategy_backtest.py --list

2️⃣ 运行标准回测:
   python strategy_backtest.py --strategy STRAT_001 --stock 000001.SZ --start 2023-01-01 --end 2023-12-31 --cash 100000

3️⃣ 运行蒙特卡洛模拟:
   python strategy_backtest.py --strategy STRAT_001 --stock 000001.SZ --montecarlo --simulations 100

📋 参数说明:
   --strategy     : 策略ID
   --stock        : 股票代码
   --start        : 开始日期 (YYYY-MM-DD)，默认为一年前
   --end          : 结束日期 (YYYY-MM-DD)，默认为今天
   --cash         : 初始资金，默认为100000
   --user         : 用户ID，默认为admin_001
   --montecarlo   : 启用蒙特卡洛模拟
   --simulations  : 蒙特卡洛模拟次数，默认为50
   --list         : 列出所有可用策略
   --help         : 显示帮助信息

⚠️ 注意事项:
   - 回测结果会保存到数据库的BacktestReport表中
   - 图表结果会保存到backtest_results目录
   - 使用蒙特卡洛模拟可以评估策略的稳健性
   - 策略需要在数据库中预先定义
    """
    )


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and (sys.argv[1] == "--help" or sys.argv[1] == "-h"):
        show_usage()
    else:
        main()
