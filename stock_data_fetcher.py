#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
量化交易系统 - 股票数据获取脚本
文件名: stock_data_fetcher.py
虚拟环境: quant_trading
Python版本: 3.10.x (推荐)

使用配置文件管理敏感信息，支持安全的股票数据获取和数据库操作
增强功能: 回测数据准备与完整性检查
"""

import tushare as ts
import pymysql
import pandas as pd
import numpy as np
import json
import os
import time  # 添加time模块用于API调用间隔
from datetime import datetime, timedelta, date
import logging
import uuid
import traceback
from typing import List, Dict, Any, Optional, Tuple, Set
from pathlib import Path
import argparse  # 添加命令行参数支持


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
        required_sections = ["database", "tushare"]
        for section in required_sections:
            if section not in config:
                raise ValueError(f"配置文件缺少必需的section: {section}")

        # 添加回测配置的默认值
        if "backtest" not in config:
            config["backtest"] = {
                "min_history_days": 365,  # 至少1年数据
                "preferred_history_days": 1095,  # 建议3年数据
                "batch_query_interval": 1,  # API调用间隔(秒)
                "data_check_threshold": 0.9,  # 数据完整性阈值(90%)
            }

        return config


class StockDataManager:
    """股票数据管理类"""

    def __init__(self, config: Dict[str, Any]):
        """
        初始化股票数据管理器

        Args:
            config: 配置字典
        """
        self.config = config
        self.connection = None

        # 配置日志级别
        log_level = config.get("system", {}).get("log_level", "INFO")
        logging.basicConfig(
            level=getattr(logging, log_level),
            format="%(asctime)s - %(levelname)s - %(message)s",
        )
        self.logger = logging.getLogger(__name__)

        # 初始化Tushare
        ts.set_token(config["tushare"]["token"])
        self.pro = ts.pro_api()

    def connect_database(self):
        """连接数据库，尝试多种认证方式"""
        db_config = self.config["database"]

        # 获取默认转换器并进行自定义
        conv = pymysql.converters.conversions.copy()
        conv[datetime.date] = pymysql.converters.escape_date

        # 添加自定义的数值类型转换
        conv[pymysql.FIELD_TYPE.DECIMAL] = float
        conv[pymysql.FIELD_TYPE.NEWDECIMAL] = float

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
                    # 使用完整的转换器配置
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
                    # 使用完整的转换器配置
                    "conv": conv,
                },
            },
            {
                "name": "强制原生认证",
                "params": {
                    "host": db_config["host"],
                    "port": db_config.get("port", 3306),
                    "user": db_config["user"],
                    "password": db_config["password"],
                    "database": db_config["database"],
                    "charset": db_config.get("charset", "utf8mb4"),
                    "autocommit": False,
                    "auth_plugin_map": {
                        "caching_sha2_password": "mysql_native_password",
                        "sha256_password": "mysql_native_password",
                    },
                    "ssl_disabled": True,
                    "local_infile": True,
                    # 使用完整的转换器配置
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

    def get_stock_data(
        self,
        ts_codes: List[str] = None,
        start_date: str = None,
        end_date: str = None,
        trade_date: str = None,
    ) -> pd.DataFrame:
        """获取股票行情数据"""
        try:
            if trade_date:
                self.logger.info(f"获取{trade_date}的全部股票数据")
                df = self.pro.daily(trade_date=trade_date)
            elif ts_codes:
                ts_code_str = ",".join(ts_codes)
                self.logger.info(
                    f"获取股票{ts_code_str}从{start_date}到{end_date}的数据"
                )
                df = self.pro.daily(
                    ts_code=ts_code_str, start_date=start_date, end_date=end_date
                )
            else:
                raise ValueError("必须指定ts_codes或trade_date参数")

            if df.empty:
                self.logger.warning("未获取到股票数据")
                return pd.DataFrame()

            self.logger.info(f"成功获取{len(df)}条股票数据")
            return df

        except Exception as e:
            self.logger.error(f"获取股票数据失败: {e}")
            raise

    def process_stock_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """处理股票数据，转换为数据库格式"""
        if df.empty:
            return df

        # 重命名列
        column_mapping = {
            "ts_code": "stock_code",
            "trade_date": "trade_date",
            "open": "open_price",
            "high": "high_price",
            "low": "low_price",
            "close": "close_price",
            "pre_close": "pre_close_price",
            "change": "change_amount",
            "pct_chg": "change_percent",
            "vol": "volume",
            "amount": "amount",
        }

        processed_df = df.rename(columns=column_mapping)

        # 数据类型转换
        processed_df["trade_date"] = pd.to_datetime(processed_df["trade_date"]).dt.date
        processed_df["change_percent"] = processed_df["change_percent"] / 100
        processed_df["volume"] = processed_df["volume"] * 100
        processed_df["amount"] = processed_df["amount"] * 1000

        # 添加元数据
        processed_df["data_source"] = "tushare"
        processed_df["collect_time"] = datetime.now()

        # 处理缺失值
        processed_df = processed_df.fillna(0)

        # 选择需要的列
        required_columns = [
            "stock_code",
            "trade_date",
            "open_price",
            "high_price",
            "low_price",
            "close_price",
            "pre_close_price",
            "change_amount",
            "change_percent",
            "volume",
            "amount",
            "data_source",
            "collect_time",
        ]

        processed_df = processed_df[required_columns]
        self.logger.info(f"数据处理完成，处理了{len(processed_df)}条记录")
        return processed_df

    def insert_stock_data(self, df: pd.DataFrame) -> int:
        """批量插入股票数据"""
        if df.empty:
            self.logger.warning("没有数据需要插入")
            return 0

        try:
            cursor = self.connection.cursor()

            insert_sql = """
            INSERT INTO StockMarketData (
                stock_code, trade_date, open_price, high_price, low_price,
                close_price, pre_close_price, change_amount, change_percent,
                volume, amount, data_source, collect_time
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            ) ON DUPLICATE KEY UPDATE
                open_price = VALUES(open_price),
                high_price = VALUES(high_price),
                low_price = VALUES(low_price),
                close_price = VALUES(close_price),
                pre_close_price = VALUES(pre_close_price),
                change_amount = VALUES(change_amount),
                change_percent = VALUES(change_percent),
                volume = VALUES(volume),
                amount = VALUES(amount),
                collect_time = VALUES(collect_time)
            """

            # 批量处理数据
            batch_size = self.config.get("system", {}).get("batch_size", 1000)
            total_inserted = 0

            for i in range(0, len(df), batch_size):
                batch_df = df.iloc[i : i + batch_size]
                data_list = [tuple(row) for _, row in batch_df.iterrows()]

                cursor.executemany(insert_sql, data_list)
                batch_inserted = cursor.rowcount
                total_inserted += batch_inserted

                self.logger.info(
                    f"批次 {i//batch_size + 1}: 插入{batch_inserted}条记录"
                )

            self.connection.commit()
            self.logger.info(f"总计成功插入/更新{total_inserted}条股票数据")
            return total_inserted

        except Exception as e:
            if self.connection:
                self.connection.rollback()
            self.logger.error(f"插入股票数据失败: {e}")
            raise
        finally:
            if cursor:
                cursor.close()

    def get_latest_stock_prices(self, stock_codes: List[str] = None) -> pd.DataFrame:
        """通过LatestStockPrice视图获取最新股价"""
        try:
            cursor = self.connection.cursor()

            if stock_codes:
                placeholders = ",".join(["%s"] * len(stock_codes))
                query_sql = f"""
                SELECT stock_code, latest_date, latest_price, 
                       change_percent, volume
                FROM LatestStockPrice 
                WHERE stock_code IN ({placeholders})
                ORDER BY stock_code
                """
                cursor.execute(query_sql, stock_codes)
            else:
                query_sql = """
                SELECT stock_code, latest_date, latest_price, 
                       change_percent, volume
                FROM LatestStockPrice 
                ORDER BY change_percent DESC
                LIMIT 50
                """
                cursor.execute(query_sql)

            results = cursor.fetchall()

            if not results:
                self.logger.warning("未查询到最新股价数据")
                return pd.DataFrame()

            columns = ["股票代码", "最新日期", "最新价格", "涨跌幅(%)", "成交量"]
            df = pd.DataFrame(results, columns=columns)

            # 处理DECIMAL类型数据，转换为float
            df["涨跌幅(%)"] = pd.to_numeric(df["涨跌幅(%)"], errors="coerce") * 100
            df["最新价格"] = pd.to_numeric(df["最新价格"], errors="coerce")
            df["成交量"] = pd.to_numeric(df["成交量"], errors="coerce").astype("Int64")

            # 格式化显示
            df["涨跌幅(%)"] = df["涨跌幅(%)"].round(2)
            df["最新价格"] = df["最新价格"].round(3)

            self.logger.info(f"查询到{len(df)}只股票的最新价格")
            return df

        except Exception as e:
            self.logger.error(f"查询最新股价失败: {e}")
            raise
        finally:
            if cursor:
                cursor.close()

    # ========== 以下为新增的回测数据准备相关函数 ==========

    def get_stock_list(self, list_status="L") -> List[str]:
        """
        获取股票列表

        Args:
            list_status: 上市状态 L(上市)、D(退市)、P(暂停上市)，默认L

        Returns:
            股票代码列表
        """
        try:
            df = self.pro.stock_basic(
                exchange="",
                list_status=list_status,
                fields="ts_code,symbol,name,area,industry,list_date",
            )
            if df.empty:
                self.logger.warning(f"未获取到股票列表")
                return []

            stock_list = df["ts_code"].tolist()
            self.logger.info(f"成功获取{len(stock_list)}只股票信息")
            return stock_list
        except Exception as e:
            self.logger.error(f"获取股票列表失败: {e}")
            return []

    def get_available_trade_dates(self, start_date: str, end_date: str) -> List[str]:
        """
        获取指定日期范围内的交易日

        Args:
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)

        Returns:
            交易日列表
        """
        try:
            df = self.pro.trade_cal(
                exchange="SSE", start_date=start_date, end_date=end_date, is_open=1
            )
            if df.empty:
                self.logger.warning(f"未获取到{start_date}至{end_date}的交易日信息")
                return []

            trade_dates = df["cal_date"].tolist()
            self.logger.info(f"成功获取{len(trade_dates)}个交易日")
            return trade_dates
        except Exception as e:
            self.logger.error(f"获取交易日失败: {e}")
            return []

    def check_stock_data_completeness(
        self, stock_code: str, start_date: str, end_date: str
    ) -> Tuple[float, int, int]:
        """
        检查指定股票在指定日期范围内的数据完整性

        Args:
            stock_code: 股票代码
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)

        Returns:
            (完整性比率, 现有交易日数, 应有交易日数)
        """
        try:
            cursor = self.connection.cursor()

            # 将日期转换为tushare格式
            start_date_ts = start_date.replace("-", "")
            end_date_ts = end_date.replace("-", "")

            # 获取该时间段内应有的交易日
            trade_dates = self.get_available_trade_dates(start_date_ts, end_date_ts)
            expected_days = len(trade_dates)

            if expected_days == 0:
                return 0.0, 0, 0

            # 查询实际有数据的交易日
            query = """
            SELECT COUNT(DISTINCT trade_date) 
            FROM StockMarketData 
            WHERE stock_code = %s 
            AND trade_date BETWEEN %s AND %s
            """
            cursor.execute(query, (stock_code, start_date, end_date))
            actual_days = cursor.fetchone()[0]

            # 计算完整性比率
            completeness_ratio = (
                actual_days / expected_days if expected_days > 0 else 0.0
            )

            return completeness_ratio, actual_days, expected_days

        except Exception as e:
            self.logger.error(f"检查数据完整性失败: {e}")
            return 0.0, 0, 0
        finally:
            if cursor:
                cursor.close()

    def get_data_date_range(
        self, stock_code: str
    ) -> Tuple[Optional[date], Optional[date]]:
        """
        获取指定股票在数据库中的日期范围

        Args:
            stock_code: 股票代码

        Returns:
            (最早日期, 最晚日期)，如果没有数据则返回(None, None)
        """
        try:
            cursor = self.connection.cursor()

            query = """
            SELECT MIN(trade_date), MAX(trade_date)
            FROM StockMarketData 
            WHERE stock_code = %s
            """
            cursor.execute(query, (stock_code,))
            result = cursor.fetchone()

            if not result or result[0] is None:
                return None, None

            return result[0], result[1]

        except Exception as e:
            self.logger.error(f"获取数据日期范围失败: {e}")
            return None, None
        finally:
            if cursor:
                cursor.close()

    def prepare_backtest_data(
        self, stock_codes: List[str], end_date: str = None, history_days: int = None
    ) -> Dict[str, Any]:
        """
        准备回测所需的历史数据

        Args:
            stock_codes: 股票代码列表
            end_date: 结束日期 (YYYY-MM-DD)，默认为当前日期
            history_days: 需要的历史数据天数，默认使用配置中的preferred_history_days

        Returns:
            准备结果的统计信息
        """
        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")

        if not history_days:
            history_days = self.config.get("backtest", {}).get(
                "preferred_history_days", 1095
            )

        start_date = (
            datetime.strptime(end_date, "%Y-%m-%d") - timedelta(days=history_days)
        ).strftime("%Y-%m-%d")

        # 转换为tushare格式
        start_date_ts = start_date.replace("-", "")
        end_date_ts = end_date.replace("-", "")

        self.logger.info(f"准备从{start_date}到{end_date}的回测数据")

        # 批处理股票数据获取
        batch_size = 5  # Tushare API有频率限制，每次获取少量股票
        api_interval = self.config.get("backtest", {}).get("batch_query_interval", 1)
        data_check_threshold = self.config.get("backtest", {}).get(
            "data_check_threshold", 0.9
        )

        result_stats = {
            "total_stocks": len(stock_codes),
            "processed_stocks": 0,
            "added_data_points": 0,
            "failed_stocks": [],
            "success_stocks": [],
            "start_date": start_date,
            "end_date": end_date,
            "history_days": history_days,
        }

        # 获取交易日历
        trade_dates = self.get_available_trade_dates(start_date_ts, end_date_ts)
        expected_days = len(trade_dates)
        result_stats["expected_trading_days"] = expected_days

        self.logger.info(f"该时间段内应有{expected_days}个交易日")

        for i in range(0, len(stock_codes), batch_size):
            batch_stocks = stock_codes[i : i + batch_size]
            self.logger.info(
                f"处理第{i//batch_size + 1}批，股票: {', '.join(batch_stocks)}"
            )

            for stock in batch_stocks:
                try:
                    # 检查现有数据完整性
                    completeness, actual_days, _ = self.check_stock_data_completeness(
                        stock, start_date, end_date
                    )

                    if completeness >= data_check_threshold:
                        self.logger.info(
                            f"股票{stock}数据完整性良好({completeness:.2%})，无需更新"
                        )
                        result_stats["success_stocks"].append(stock)
                        result_stats["processed_stocks"] += 1
                        continue

                    # 获取数据并处理
                    self.logger.info(
                        f"获取股票{stock}的历史数据，完整性: {completeness:.2%}，当前数据: {actual_days}天"
                    )
                    raw_data = self.get_stock_data(
                        ts_codes=[stock], start_date=start_date_ts, end_date=end_date_ts
                    )

                    if raw_data.empty:
                        self.logger.warning(
                            f"未获取到股票{stock}的数据，可能是新上市或已退市"
                        )
                        result_stats["failed_stocks"].append(stock)
                        continue

                    processed_data = self.process_stock_data(raw_data)
                    inserted_count = self.insert_stock_data(processed_data)

                    # 更新统计
                    result_stats["added_data_points"] += inserted_count
                    result_stats["processed_stocks"] += 1
                    result_stats["success_stocks"].append(stock)

                    # 检查更新后的完整性
                    new_completeness, new_actual_days, _ = (
                        self.check_stock_data_completeness(stock, start_date, end_date)
                    )
                    self.logger.info(
                        f"股票{stock}数据更新完成，新完整性: {new_completeness:.2%}，当前数据: {new_actual_days}天"
                    )

                except Exception as e:
                    self.logger.error(f"处理股票{stock}失败: {e}")
                    result_stats["failed_stocks"].append(stock)

                # 添加API调用间隔，避免超过频率限制
                time.sleep(api_interval)

            # 每批处理完显示进度
            progress = min(100, int((i + len(batch_stocks)) / len(stock_codes) * 100))
            self.logger.info(
                f"数据准备进度: {progress}% ({i + len(batch_stocks)}/{len(stock_codes)})"
            )

        # 计算最终统计数据
        result_stats["success_rate"] = (
            len(result_stats["success_stocks"]) / result_stats["total_stocks"]
            if result_stats["total_stocks"] > 0
            else 0
        )

        return result_stats

    def get_backtest_ready_stocks(
        self,
        min_completeness: float = 0.95,
        start_date: str = None,
        end_date: str = None,
    ) -> List[str]:
        """
        获取可用于回测的股票列表(数据完整性达标)

        Args:
            min_completeness: 最低数据完整性要求
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)

        Returns:
            可用于回测的股票代码列表
        """
        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")

        if not start_date:
            # 默认取配置中的最小历史天数
            min_days = self.config.get("backtest", {}).get("min_history_days", 365)
            start_date = (
                datetime.strptime(end_date, "%Y-%m-%d") - timedelta(days=min_days)
            ).strftime("%Y-%m-%d")

        try:
            cursor = self.connection.cursor()

            # 获取有数据的所有股票
            query = """
            SELECT DISTINCT stock_code
            FROM StockMarketData
            """
            cursor.execute(query)
            all_stocks = [row[0] for row in cursor.fetchall()]

            if not all_stocks:
                self.logger.warning("数据库中没有股票数据")
                return []

            ready_stocks = []
            total = len(all_stocks)

            self.logger.info(
                f"检查{total}只股票在{start_date}至{end_date}期间的数据完整性"
            )

            # 检查每只股票的数据完整性
            for i, stock in enumerate(all_stocks):
                completeness, actual, expected = self.check_stock_data_completeness(
                    stock, start_date, end_date
                )

                if completeness >= min_completeness:
                    ready_stocks.append(stock)

                # 每100只股票显示一次进度
                if (i + 1) % 100 == 0 or i + 1 == total:
                    self.logger.info(
                        f"进度: {i+1}/{total} ({(i+1)/total:.1%}), 可用: {len(ready_stocks)}"
                    )

            self.logger.info(f"检查完成，有{len(ready_stocks)}/{total}只股票可用于回测")
            return ready_stocks

        except Exception as e:
            self.logger.error(f"获取可回测股票列表失败: {e}")
            return []
        finally:
            if cursor:
                cursor.close()

    def get_index_data(
        self, index_code: str, start_date: str, end_date: str
    ) -> pd.DataFrame:
        """
        获取指数数据（对回测也很重要）

        Args:
            index_code: 指数代码，如000001.SH（上证指数）
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)

        Returns:
            指数数据DataFrame
        """
        try:
            self.logger.info(f"获取指数{index_code}从{start_date}到{end_date}的数据")
            df = self.pro.index_daily(
                ts_code=index_code, start_date=start_date, end_date=end_date
            )

            if df.empty:
                self.logger.warning(f"未获取到指数{index_code}的数据")
                return pd.DataFrame()

            self.logger.info(f"成功获取{len(df)}条指数数据")
            return df

        except Exception as e:
            self.logger.error(f"获取指数数据失败: {e}")
            return pd.DataFrame()


def main():
    """主函数"""
    print("🚀 量化交易系统 - 股票数据获取脚本")
    print("文件名: stock_data_fetcher.py")
    print("虚拟环境: quant_trading")
    print("推荐Python版本: 3.10.x")
    print("=" * 60)

    # 解析命令行参数
    parser = argparse.ArgumentParser(description="量化交易系统股票数据获取工具")
    parser.add_argument("--market", action="store_true", help="获取全市场数据")
    parser.add_argument("--backtest", action="store_true", help="准备回测数据")
    parser.add_argument("--stocks", type=str, help="指定股票代码，多个用逗号分隔")
    parser.add_argument("--days", type=int, help="历史数据天数")
    parser.add_argument("--end", type=str, help="结束日期 (YYYY-MM-DD)")
    parser.add_argument("--check", action="store_true", help="检查哪些股票可用于回测")
    parser.add_argument(
        "--completeness", type=float, default=0.95, help="数据完整性阈值"
    )
    args = parser.parse_args()

    try:
        # 1. 加载配置
        print("📄 加载配置文件...")
        config = ConfigManager.load_config("config.json")
        print("✅ 配置文件加载成功")

        # 2. 创建数据管理器
        stock_manager = StockDataManager(config)

        # 3. 连接数据库
        print("🔌 连接数据库...")
        stock_manager.connect_database()
        print("✅ 数据库连接成功")

        # 根据命令行参数执行相应功能
        if args.backtest:
            # 准备回测数据
            if args.stocks:
                stock_codes = args.stocks.split(",")
            else:
                # 使用配置中的默认股票
                stock_codes = config.get("trading", {}).get(
                    "default_stocks",
                    [
                        "000001.SZ",
                        "000002.SZ",
                        "600000.SH",
                        "600036.SH",
                        "600519.SH",
                        "000858.SZ",
                    ],
                )

            print(f"\n📊 准备回测数据:")
            print(f"  股票列表: {', '.join(stock_codes)}")

            # 准备数据
            results = stock_manager.prepare_backtest_data(
                stock_codes=stock_codes, end_date=args.end, history_days=args.days
            )

            # 显示结果
            print("\n📈 回测数据准备结果:")
            print(f"  数据范围: {results['start_date']} 至 {results['end_date']}")
            print(f"  交易日数: {results['expected_trading_days']}")
            print(
                f"  处理股票: {results['processed_stocks']}/{results['total_stocks']}"
            )
            print(f"  添加数据点: {results['added_data_points']}")
            print(f"  成功率: {results['success_rate']:.2%}")

            if results["failed_stocks"]:
                print(f"  失败股票: {', '.join(results['failed_stocks'])}")

        elif args.check:
            # 检查可用于回测的股票
            end_date = args.end or datetime.now().strftime("%Y-%m-%d")

            if args.days:
                start_date = (
                    datetime.strptime(end_date, "%Y-%m-%d") - timedelta(days=args.days)
                ).strftime("%Y-%m-%d")
            else:
                # 使用配置的最小天数
                min_days = config.get("backtest", {}).get("min_history_days", 365)
                start_date = (
                    datetime.strptime(end_date, "%Y-%m-%d") - timedelta(days=min_days)
                ).strftime("%Y-%m-%d")

            print(f"\n🔍 检查可用于回测的股票:")
            print(f"  时间范围: {start_date} 至 {end_date}")
            print(f"  完整性要求: {args.completeness:.2%}")

            # 获取可用股票
            ready_stocks = stock_manager.get_backtest_ready_stocks(
                min_completeness=args.completeness,
                start_date=start_date,
                end_date=end_date,
            )

            if ready_stocks:
                print(f"\n✅ 找到{len(ready_stocks)}只可用于回测的股票")

                # 如果少于10只，直接显示所有
                if len(ready_stocks) <= 10:
                    print(f"  可用股票: {', '.join(ready_stocks)}")
                else:
                    # 否则只显示前10只
                    print(f"  部分可用股票: {', '.join(ready_stocks[:10])}...")

                # 保存结果到文件
                result_file = (
                    f"backtest_ready_stocks_{datetime.now().strftime('%Y%m%d')}.txt"
                )
                with open(result_file, "w") as f:
                    f.write("\n".join(ready_stocks))
                print(f"  完整列表已保存至: {result_file}")
            else:
                print(f"❌ 未找到符合条件的股票")

        elif args.market:
            # 获取全市场数据
            get_today_market_data()

        else:
            # 默认流程
            # 4. 获取配置的股票和日期范围
            stock_codes = config.get("trading", {}).get(
                "default_stocks",
                [
                    "000001.SZ",
                    "000002.SZ",
                    "600000.SH",
                    "600036.SH",
                    "600519.SH",
                    "000858.SZ",
                ],
            )

            days_back = config.get("trading", {}).get("data_days_back", 30)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)

            start_date_str = start_date.strftime("%Y%m%d")
            end_date_str = end_date.strftime("%Y%m%d")

            print(f"📈 获取股票: {', '.join(stock_codes)}")
            print(f"📅 日期范围: {start_date_str} - {end_date_str}")

            # 5. 获取并处理数据
            print("🔄 获取股票数据...")
            raw_data = stock_manager.get_stock_data(
                ts_codes=stock_codes, start_date=start_date_str, end_date=end_date_str
            )

            if raw_data.empty:
                print("❌ 未获取到股票数据")
                return

            print("🔄 处理数据格式...")
            processed_data = stock_manager.process_stock_data(raw_data)

            print("💾 写入数据库...")
            inserted_count = stock_manager.insert_stock_data(processed_data)
            print(f"✅ 成功处理{inserted_count}条数据")

            # 6. 查询最新股价
            print("📊 查询最新股价...")
            latest_prices = stock_manager.get_latest_stock_prices(stock_codes)

            if not latest_prices.empty:
                print("\n" + "=" * 80)
                print("📈 最新股价信息（通过LatestStockPrice视图查询）")
                print("=" * 80)
                print(latest_prices.to_string(index=False))
                print("=" * 80)

                # 数据分析
                print(f"\n📊 数据统计:")
                print(f"   总计股票数量: {len(latest_prices)}")
                print(f"   平均涨跌幅: {latest_prices['涨跌幅(%)'].mean():.2f}%")
                print(f"   最大涨幅: {latest_prices['涨跌幅(%)'].max():.2f}%")
                print(f"   最大跌幅: {latest_prices['涨跌幅(%)'].min():.2f}%")

                up_stocks = len(latest_prices[latest_prices["涨跌幅(%)"] > 0])
                down_stocks = len(latest_prices[latest_prices["涨跌幅(%)"] < 0])
                flat_stocks = len(latest_prices[latest_prices["涨跌幅(%)"] == 0])

                print(f"   📈 上涨股票: {up_stocks} 只")
                print(f"   📉 下跌股票: {down_stocks} 只")
                print(f"   ➖ 平盘股票: {flat_stocks} 只")

                # 找出涨跌幅最大的股票
                if len(latest_prices) > 0:
                    top_gainer = latest_prices.loc[latest_prices["涨跌幅(%)"].idxmax()]
                    top_loser = latest_prices.loc[latest_prices["涨跌幅(%)"].idxmin()]

                    print(f"\n🏆 今日表现:")
                    print(
                        f"   最大涨幅: {top_gainer['股票代码']} ({top_gainer['涨跌幅(%)']}%)"
                    )
                    print(
                        f"   最大跌幅: {top_loser['股票代码']} ({top_loser['涨跌幅(%)']}%)"
                    )
            else:
                print("❌ 未查询到最新股价数据")

        print("\n🎉 股票数据获取和处理流程完成！")

    except FileNotFoundError as e:
        print(f"❌ 配置文件错误: {e}")
        print("💡 请运行 python test_database_connection.py 生成配置文件")
    except Exception as e:
        error_msg = f"处理过程中发生错误: {e}"
        print(f"❌ {error_msg}")
        logging.error(traceback.format_exc())

    finally:
        if "stock_manager" in locals():
            stock_manager.close_database()


def get_today_market_data():
    """获取今日市场数据的便捷函数"""
    try:
        config = ConfigManager.load_config("config.json")
        stock_manager = StockDataManager(config)

        # 获取昨日数据（今日数据可能未更新）
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")

        stock_manager.connect_database()

        print(f"📅 获取{yesterday}全市场数据...")
        raw_data = stock_manager.get_stock_data(trade_date=yesterday)

        if not raw_data.empty:
            processed_data = stock_manager.process_stock_data(raw_data)
            inserted_count = stock_manager.insert_stock_data(processed_data)

            print(f"✅ 成功获取并插入{inserted_count}条全市场数据")

            # 显示市场概况
            latest_all = stock_manager.get_latest_stock_prices()
            if not latest_all.empty:
                print(f"\n📊 市场概况:")
                print(f"   总股票数: {len(latest_all)}")
                print(f"   平均涨跌幅: {latest_all['涨跌幅(%)'].mean():.2f}%")

                # 涨跌分布
                up_count = len(latest_all[latest_all["涨跌幅(%)"] > 0])
                down_count = len(latest_all[latest_all["涨跌幅(%)"] < 0])

                print(f"   上涨家数: {up_count} ({up_count/len(latest_all)*100:.1f}%)")
                print(
                    f"   下跌家数: {down_count} ({down_count/len(latest_all)*100:.1f}%)"
                )
        else:
            print(f"❌ 未获取到{yesterday}的市场数据")

    except Exception as e:
        print(f"❌ 获取市场数据失败: {e}")
    finally:
        if "stock_manager" in locals():
            stock_manager.close_database()


def show_usage():
    """显示使用说明"""
    print(
        """
📖 使用说明:

1️⃣ 首次使用:
   python test_database_connection.py  # 测试连接并生成配置文件

2️⃣ 获取指定股票数据:
   python stock_data_fetcher.py  # 获取默认股票最近30天数据

3️⃣ 获取全市场数据:
   python stock_data_fetcher.py --market  # 获取昨日全市场数据

4️⃣ 准备回测数据:
   python stock_data_fetcher.py --backtest  # 准备默认股票的回测数据
   python stock_data_fetcher.py --backtest --stocks 000001.SZ,600000.SH --days 1095  # 准备指定股票3年数据
   python stock_data_fetcher.py --backtest --end 2024-08-31  # 指定结束日期

5️⃣ 检查回测可用股票:
   python stock_data_fetcher.py --check  # 检查哪些股票可用于回测
   python stock_data_fetcher.py --check --days 730 --completeness 0.98  # 检查2年内数据完整性>98%的股票

📋 参数说明:
   --market           : 获取全市场数据
   --backtest         : 准备回测数据
   --stocks [codes]   : 指定股票代码，多个用逗号分隔
   --days [number]    : 历史数据天数
   --end [date]       : 结束日期 (YYYY-MM-DD)
   --check            : 检查哪些股票可用于回测
   --completeness [n] : 数据完整性阈值(0-1)

⚠️ 注意事项:
   - 请确保config.json在.gitignore中，避免提交敏感信息
   - Tushare API有调用频率限制，请合理使用
   - 回测数据建议至少准备1年以上数据
   - 建议在非交易时间获取数据，避免影响实时分析
    """
    )


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and (sys.argv[1] == "--help" or sys.argv[1] == "-h"):
        show_usage()
    else:
        # 使用argparse处理参数
        main()
