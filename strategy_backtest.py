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

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 数据库默认设置
DB_DEFAULTS = {
    "host": "localhost",
    "port": 3306,
    "user": "root",
    "database": "quantitative_trading",
    "charset": "utf8mb4",
}

# 回测默认设置
BACKTEST_DEFAULTS = {
    "output_dir": "backtest_results",
    "plot_results": True,
    "debug_mode": False,
}


def load_config(config_file: str = "config.json") -> Dict[str, Any]:
    """加载配置文件"""
    if not os.path.exists(config_file):
        raise FileNotFoundError(f"配置文件不存在: {config_file}")

    with open(config_file, "r", encoding="utf-8") as f:
        config = json.load(f)

    # 验证必需配置
    if "db_password" not in config:
        raise ValueError("配置文件缺少数据库密码")

    return config


class DatabaseManager:
    """数据库管理类"""

    def __init__(self, db_password: str):
        """
        初始化数据库管理器

        Args:
            db_password: 数据库密码
        """
        self.db_password = db_password
        self.connection = None
        self.logger = logger

    def connect_database(self):
        """连接数据库"""
        try:
            self.logger.info("连接数据库...")

            # 获取默认转换器并进行自定义
            conv = pymysql.converters.conversions.copy()
            conv[datetime.date] = pymysql.converters.escape_date

            # 添加数值类型转换
            conv[pymysql.FIELD_TYPE.DECIMAL] = float
            conv[pymysql.FIELD_TYPE.NEWDECIMAL] = float

            # 使用标准连接方式
            self.connection = pymysql.connect(
                host=DB_DEFAULTS["host"],
                port=DB_DEFAULTS["port"],
                user=DB_DEFAULTS["user"],
                password=self.db_password,
                database=DB_DEFAULTS["database"],
                charset=DB_DEFAULTS["charset"],
                autocommit=False,
                conv=conv,
            )

            self.logger.info("数据库连接成功")

        except Exception as e:
            self.logger.error(f"连接数据库失败: {e}")
            raise

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
                   ti.indicator_name, ti.calculation_method, ti.default_period,
                   ti.indicator_type  -- 添加指标类型
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

    def get_index_stocks(self, index_code: str) -> List[str]:
        """获取指数成分股列表"""
        try:
            cursor = self.connection.cursor()
            query = """
            SELECT DISTINCT stock_code 
            FROM IndexComponent 
            WHERE index_code = %s
            """
            cursor.execute(query, (index_code,))
            results = cursor.fetchall()

            if not results:
                self.logger.warning(f"未找到指数 {index_code} 的成分股")
                return []

            # 返回股票代码列表
            return [row[0] for row in results]
        except Exception as e:
            self.logger.error(f"获取指数成分股失败: {e}")
            return []
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
                report_id, strategy_id, user_id, stock_code, start_date, end_date,
                initial_fund, final_fund, total_return, annual_return,
                max_drawdown, sharpe_ratio, win_rate, profit_loss_ratio,
                trade_count, report_generate_time, report_status
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            """

            params = (
                report_id,
                report_data["strategy_id"],
                report_data["user_id"],
                report_data["stock_code"],  # 确保这个位置与SQL中的位置匹配
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
        ("fundamental_data", {}),  # 基本面数据
        ("debug_mode", False),  # 调试模式
    )

    def __init__(self):
        """初始化策略"""
        self.order = None  # 当前订单
        self.buyprice = None  # 买入价格
        self.buycomm = None  # 买入手续费

        # 日志
        self.logger = logger

        # 计算所需的技术指标
        self.indicators = {}
        # 初始化基本面数据
        self.fundamental_data = self.params.fundamental_data

        self.setup_indicators()

        # 初始化交易记录
        self.trades = []

    def setup_indicators(self):
        """根据策略条件设置技术指标"""
        # 用于记录已添加的指标，避免重复添加
        added_indicators = set()
        # 分别存储技术指标和基本面指标
        self.indicators = {}  # 技术指标
        self.fundamental_data = {}  # 基本面指标

        for condition in self.params.strategy_conditions:
            indicator_id = condition["indicator_id"]
            indicator_type = condition.get(
                "indicator_type", "technical"
            )  # 获取指标类型

            # 如果指标已添加，则跳过
            if indicator_id in added_indicators:
                continue

            # 根据指标类型分别处理
            if indicator_type == "technical":
                self._setup_technical_indicator(indicator_id, condition)
            elif indicator_type == "fundamental":
                # 对于基本面指标，只记录需要加载，稍后在run_backtest中处理
                self.fundamental_data[indicator_id] = None
                self.logger.info(
                    f"基本面指标 {indicator_id} 将在策略初始化后从数据库加载"
                )

            # 将指标添加到已添加集合中
            added_indicators.add(indicator_id)

    def _setup_technical_indicator(self, indicator_id, condition):
        """设置技术指标"""
        # 根据指标ID设置相应的技术指标
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
        elif indicator_id.startswith("MA") and indicator_id[2:].isdigit():
            # 确保是真正的移动平均线指标，而不是MARKET_CAP等
            period = int(indicator_id[2:])
            self.indicators[indicator_id] = bt.indicators.SMA(
                self.data.close, period=period
            )
        elif indicator_id == "VOLUME_MA":
            period = condition.get("default_period", 10)
            self.indicators[indicator_id] = bt.indicators.SMA(
                self.data.volume, period=period
            )

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
            indicator_type = condition.get("indicator_type", "technical")
            condition_type = condition["condition_type"]
            threshold_min = condition.get("threshold_min")
            threshold_max = condition.get("threshold_max")

            # 区分基本面指标和技术指标
            if indicator_type == "technical" and indicator_id in self.indicators:
                # 处理技术指标
                indicator_value = self.indicators[indicator_id][0]
            elif (
                indicator_type == "fundamental"
                and indicator_id in self.fundamental_data
            ):
                # 处理基本面指标
                current_date = self.data.datetime.date(0)
                indicator_value = self._get_fundamental_value(
                    indicator_id, current_date
                )
                if indicator_value is None:
                    # 基本面数据不可用，条件不满足
                    conditions_met = False
                    break
            else:
                # 指标不存在，条件不满足
                conditions_met = False
                break

            # 根据条件类型检查条件
            if condition_type == "greater":
                if threshold_min is not None and not (indicator_value > threshold_min):
                    conditions_met = False
                    break
            elif condition_type == "less":
                if threshold_max is not None and not (indicator_value < threshold_max):
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

    def _get_fundamental_value(self, indicator_id, date):
        """获取特定日期的基本面数据值"""
        if (
            indicator_id not in self.fundamental_data
            or self.fundamental_data[indicator_id] is None
        ):
            return None

        # 将日期转为字符串作为字典键
        date_str = date.strftime("%Y-%m-%d")

        # 从预先加载的基本面数据中查找
        return self.fundamental_data[indicator_id].get(date_str, None)

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

    def __init__(self, db_manager: DatabaseManager):
        """
        初始化回测引擎

        Args:
            db_manager: 数据库管理器实例
        """
        self.db_manager = db_manager
        self.logger = logger

    def run_backtest(
        self,
        strategy_id: str,
        stock_code: str,
        start_date: str,
        end_date: str,
        initial_cash: float = 100000.0,
        user_id: str = "admin_001",
        debug_mode: bool = False,
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
            debug_mode: 调试模式

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
        # 检查是否需要基本面数据
        needs_fundamental = False
        for condition in strategy_conditions:
            if condition.get("indicator_type") == "fundamental":
                needs_fundamental = True
                break

        # 如果需要，加载基本面数据
        fundamental_data = {}
        if needs_fundamental:
            self.logger.info("检测到基本面指标，正在加载基本面数据...")
            fundamental_data = self._load_fundamental_data(
                stock_code, start_date, end_date, strategy_conditions
            )

        # 在添加策略时传入基本面数据
        cerebro.addstrategy(
            DynamicBacktestStrategy,
            strategy_conditions=strategy_conditions,
            fundamental_data=fundamental_data,  # 添加基本面数据
            debug_mode=debug_mode,
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
        if BACKTEST_DEFAULTS["plot_results"]:
            self.plot_results(cerebro, strategy_info["strategy_name"], stock_code)

        return backtest_result

    def _load_fundamental_data(
        self, stock_code, start_date, end_date, strategy_conditions
    ):
        """加载基本面数据"""
        fundamental_data = {}

        # 获取所有需要的基本面指标
        needed_indicators = []
        for condition in strategy_conditions:
            if condition.get("indicator_type") == "fundamental":
                needed_indicators.append(condition["indicator_id"])

        # 为每个指标加载数据
        for indicator_id in needed_indicators:
            if indicator_id == "MARKET_CAP":
                # 从StockValuation表加载市值数据
                data = self._load_market_cap_data(stock_code, start_date, end_date)
            elif indicator_id == "PB_RATIO":
                # 从StockValuation表加载市净率数据
                data = self._load_pb_ratio_data(stock_code, start_date, end_date)
            elif indicator_id == "DEBT_RATIO":
                # 从BalanceSheet表加载负债率数据
                data = self._load_debt_ratio_data(stock_code, start_date, end_date)
            elif indicator_id == "CURRENT_RATIO":
                # 从BalanceSheet表加载流动比率数据
                data = self._load_current_ratio_data(stock_code, start_date, end_date)
            else:
                self.logger.warning(f"未知的基本面指标: {indicator_id}")
                data = {}

            fundamental_data[indicator_id] = data

        return fundamental_data

    def _load_market_cap_data(self, stock_code, start_date, end_date):
        """从StockValuation表加载市值数据"""
        try:
            cursor = self.db_manager.connection.cursor(pymysql.cursors.DictCursor)
            query = """
            SELECT trade_date, market_cap
            FROM StockValuation
            WHERE stock_code = %s AND trade_date BETWEEN %s AND %s
            ORDER BY trade_date
            """
            cursor.execute(query, (stock_code, start_date, end_date))
            results = cursor.fetchall()

            # 将结果转换为日期-值字典
            data = {
                row["trade_date"].strftime("%Y-%m-%d"): row["market_cap"]
                for row in results
            }

            # 如果数据为空，记录警告
            if not data:
                self.logger.warning(
                    f"未找到股票 {stock_code} 在 {start_date} 至 {end_date} 的市值数据"
                )

            return data
        except Exception as e:
            self.logger.error(f"加载市值数据失败: {e}")
            return {}
        finally:
            if cursor:
                cursor.close()

    def _load_pb_ratio_data(self, stock_code, start_date, end_date):
        """从StockValuation表加载市净率数据"""
        try:
            cursor = self.db_manager.connection.cursor(pymysql.cursors.DictCursor)
            query = """
            SELECT trade_date, pb_ratio
            FROM StockValuation
            WHERE stock_code = %s AND trade_date BETWEEN %s AND %s
            ORDER BY trade_date
            """
            cursor.execute(query, (stock_code, start_date, end_date))
            results = cursor.fetchall()

            # 将结果转换为日期-值字典
            data = {
                row["trade_date"].strftime("%Y-%m-%d"): row["pb_ratio"]
                for row in results
            }

            if not data:
                self.logger.warning(
                    f"未找到股票 {stock_code} 在 {start_date} 至 {end_date} 的市净率数据"
                )

            return data
        except Exception as e:
            self.logger.error(f"加载市净率数据失败: {e}")
            return {}
        finally:
            if cursor:
                cursor.close()

    def _load_debt_ratio_data(self, stock_code, start_date, end_date):
        """从BalanceSheet表加载负债率数据"""
        try:
            cursor = self.db_manager.connection.cursor(pymysql.cursors.DictCursor)
            query = """
            SELECT report_date, total_liab, total_assets
            FROM BalanceSheet
            WHERE stock_code = %s AND report_date BETWEEN %s AND %s
            ORDER BY report_date
            """
            cursor.execute(query, (stock_code, start_date, end_date))
            results = cursor.fetchall()

            # 计算负债率并转换为日期-值字典
            data = {}
            for row in results:
                if row["total_assets"] and row["total_assets"] != 0:
                    debt_ratio = row["total_liab"] / row["total_assets"]
                    data[row["report_date"].strftime("%Y-%m-%d")] = debt_ratio

            if not data:
                self.logger.warning(
                    f"未找到股票 {stock_code} 在 {start_date} 至 {end_date} 的负债率数据"
                )

            return data
        except Exception as e:
            self.logger.error(f"加载负债率数据失败: {e}")
            return {}
        finally:
            if cursor:
                cursor.close()

    def _load_current_ratio_data(self, stock_code, start_date, end_date):
        """从BalanceSheet表加载流动比率数据"""
        try:
            cursor = self.db_manager.connection.cursor(pymysql.cursors.DictCursor)
            query = """
            SELECT report_date, current_assets, current_liab
            FROM BalanceSheet
            WHERE stock_code = %s AND report_date BETWEEN %s AND %s
            ORDER BY report_date
            """
            cursor.execute(query, (stock_code, start_date, end_date))
            results = cursor.fetchall()

            # 计算流动比率并转换为日期-值字典
            data = {}
            for row in results:
                if row["current_liab"] and row["current_liab"] != 0:
                    current_ratio = row["current_assets"] / row["current_liab"]
                    data[row["report_date"].strftime("%Y-%m-%d")] = current_ratio

            if not data:
                self.logger.warning(
                    f"未找到股票 {stock_code} 在 {start_date} 至 {end_date} 的流动比率数据"
                )

            return data
        except Exception as e:
            self.logger.error(f"加载流动比率数据失败: {e}")
            return {}
        finally:
            if cursor:
                cursor.close()

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
        绘制回测结果图表并保存到文件

        Args:
            cerebro: Cerebro实例
            strategy_name: 策略名称
            stock_code: 股票代码
        """
        try:
            # 设置图表输出目录
            output_dir = BACKTEST_DEFAULTS["output_dir"]
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)

            # 生成文件名（策略名称_股票代码_时间戳.png）
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            filename = f"{output_dir}/{strategy_name}_{stock_code}_{timestamp}.png"

            # 绘制图表并获取返回值
            figs = cerebro.plot(
                style="candlestick",
                barup="red",
                bardown="green",
                grid=True,
                subplot=True,
                title=f"{strategy_name} - {stock_code}回测结果",
            )

            # 保存图表
            if figs and len(figs) > 0 and len(figs[0]) > 0:
                fig = figs[0][0]  # 获取图表对象
                fig.savefig(filename, dpi=300)  # 保存为高分辨率图片
                self.logger.info(f"回测结果图表已保存至: {filename}")
            else:
                self.logger.warning("回测图表对象为空，无法保存图表")

        except Exception as e:
            self.logger.error(f"绘制回测结果图表失败: {e}")
            self.logger.error(traceback.format_exc())


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="量化交易系统 - 策略回测脚本")
    parser.add_argument("--strategy", type=str, help="策略ID")
    parser.add_argument("--stock", type=str, help="股票代码")
    parser.add_argument("--index", type=str, help="使用指定指数的成分股进行回测")
    parser.add_argument(
        "--stocks",
        type=str,
        help="指定多只股票代码，用逗号分隔",
    )
    parser.add_argument("--start", type=str, help="开始日期 (YYYY-MM-DD)")
    parser.add_argument("--end", type=str, help="结束日期 (YYYY-MM-DD)")
    parser.add_argument("--cash", type=float, default=100000.0, help="初始资金")
    parser.add_argument("--user", type=str, default="admin_001", help="用户ID")
    parser.add_argument("--list", action="store_true", help="列出所有可用策略")
    parser.add_argument(
        "--config", type=str, default="config.json", help="配置文件路径"
    )
    parser.add_argument("--debug", action="store_true", help="开启调试模式")

    args = parser.parse_args()

    logger.info("量化交易系统 - 策略回测脚本启动")

    try:
        # 1. 加载配置
        logger.info("加载配置文件...")
        config = load_config(args.config)
        logger.info("配置文件加载成功")

        # 2. 创建数据库管理器
        db_manager = DatabaseManager(config["db_password"])

        # 3. 连接数据库
        logger.info("连接数据库...")
        db_manager.connect_database()
        logger.info("数据库连接成功")

        # 4. 创建回测引擎
        backtest_engine = BacktestEngine(db_manager)

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

        elif args.strategy:
            # 设置默认日期范围（如果未提供）
            if not args.start:
                args.start = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
            if not args.end:
                args.end = datetime.now().strftime("%Y-%m-%d")

            # 确定要处理的股票列表
            stock_codes = []

            if args.index:
                # 从数据库获取指数成分股
                logger.info(f"获取指数 {args.index} 的成分股...")
                stock_codes = db_manager.get_index_stocks(args.index)
                logger.info(f"将使用{len(stock_codes)}只指数成分股进行回测")

            elif args.stocks:
                # 处理多只股票参数
                stock_codes = args.stocks.split(",")
                logger.info(f"将使用指定的{len(stock_codes)}只股票进行回测")

            elif args.stock:
                # 单只股票模式
                stock_codes = [args.stock]

            else:
                print("\n❓ 请指定股票代码(--stock)、多只股票(--stocks)或指数(--index)")
                return

            # 批量回测所有股票
            all_results = []
            for i, stock_code in enumerate(stock_codes):
                logger.info(f"正在回测第{i+1}/{len(stock_codes)}只股票: {stock_code}")
                try:
                    result = backtest_engine.run_backtest(
                        args.strategy,
                        stock_code,
                        args.start,
                        args.end,
                        args.cash,
                        args.user,
                        args.debug,
                    )
                    all_results.append(result)
                except Exception as e:
                    logger.error(f"回测股票{stock_code}时出错: {e}")

            # 显示汇总结果
            if all_results:
                # 计算平均结果
                avg_return = sum(r["total_return"] for r in all_results) / len(
                    all_results
                )
                best_stock = max(all_results, key=lambda x: x["total_return"])
                worst_stock = min(all_results, key=lambda x: x["total_return"])

                print("\n📊 批量回测汇总结果:")
                print(f"  总共回测: {len(all_results)}/{len(stock_codes)}只股票")
                print(f"  平均收益率: {avg_return*100:.2f}%")
                print(
                    f"  最佳股票: {best_stock['stock_code']} (收益率: {best_stock['total_return']*100:.2f}%)"
                )
                print(
                    f"  最差股票: {worst_stock['stock_code']} (收益率: {worst_stock['total_return']*100:.2f}%)"
                )
        else:
            print("\n❓ 请指定策略ID和股票代码，或使用--list参数查看可用策略")
            print(
                "示例: python strategy_backtest.py --strategy STRAT_001 --stock 000001.SZ"
            )
            print("查看帮助: python strategy_backtest.py --help")

        logger.info("策略回测脚本执行完成！")

    except FileNotFoundError as e:
        logger.error(f"配置文件错误: {e}")
        print(f"❌ 配置文件错误: {e}")
        print("💡 请运行 python connection_tester.py 生成配置文件")
    except ValueError as e:
        logger.error(f"参数错误: {e}")
        print(f"❌ 参数错误: {e}")
    except Exception as e:
        error_msg = f"处理过程中发生错误: {e}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        print(f"❌ {error_msg}")

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

2️⃣ 运行单只股票回测:
   python strategy_backtest.py --strategy STRAT_001 --stock 000001.SZ --start 2023-01-01 --end 2023-12-31

3️⃣ 运行多只股票回测:
   python strategy_backtest.py --strategy STRAT_001 --stocks 000001.SZ,600519.SH

4️⃣ 使用指数成分股回测:
   python strategy_backtest.py --strategy STRAT_001 --index 000300.SH

📋 参数说明:
   --strategy     : 策略ID
   --stock        : 股票代码
   --stocks       : 多只股票代码(逗号分隔)
   --index        : 指数代码(将使用其成分股)
   --start        : 开始日期 (YYYY-MM-DD)，默认为一年前
   --end          : 结束日期 (YYYY-MM-DD)，默认为今天
   --cash         : 初始资金，默认为100000
   --user         : 用户ID，默认为admin_001
   --list         : 列出所有可用策略
   --config       : 配置文件路径，默认为config.json
   --debug        : 开启调试模式
   --help         : 显示帮助信息

⚠️ 注意事项:
   - 回测结果会保存到数据库的BacktestReport表中
   - 图表结果会保存到backtest_results目录
   - 策略需要在数据库中预先定义
    """
    )


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and (sys.argv[1] == "--help" or sys.argv[1] == "-h"):
        show_usage()
    else:
        main()
