#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
量化交易系统 - 回测数据准备脚本
文件名: stock_data_fetcher.py
虚拟环境: quant_trading
Python版本: 3.10.x

专注于为回测准备必要的历史股票数据，支持基本面分析和策略回测
"""

import sys
import tushare as ts
import pymysql
import pandas as pd
import json
import os
import time
from datetime import datetime, timedelta, date
import logging
import traceback
from typing import List, Dict, Any, Optional, Tuple
import argparse


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


class StockDataManager:
    """股票数据管理类"""

    def __init__(
        self,
        db_password: str,
        tushare_token: str,
        start_date: str,
        end_date: str,
    ):
        """
        初始化股票数据管理器

        Args:
            db_password: 数据库密码
            tushare_token: Tushare API令牌
            start_date: 回测开始日期 (YYYY-MM-DD)
            end_date: 回测结束日期 (YYYY-MM-DD)
        """
        self.db_password = db_password
        self.connection = None
        self.start_date = start_date
        self.end_date = end_date

        # 转换为tushare格式的日期 (YYYYMMDD)
        self.start_date_ts = (
            self.start_date.replace("-", "") if self.start_date else None
        )
        self.end_date_ts = self.end_date.replace("-", "") if self.end_date else None

        # 初始化Tushare
        ts.set_token(tushare_token)
        self.pro = ts.pro_api()
        self.logger = logger

    def connect_database(self):
        """连接数据库"""
        try:
            self.logger.info("连接数据库...")

            # 获取默认转换器并进行自定义
            conv = pymysql.converters.conversions.copy()
            conv[datetime.date] = pymysql.converters.escape_date
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

    def initialize_trade_dates(self):
        """初始化交易日历"""
        try:
            self.logger.info(f"初始化从{self.start_date}到{self.end_date}的交易日历...")
            df = self.pro.trade_cal(
                exchange="SSE",
                start_date=self.start_date_ts,
                end_date=self.end_date_ts,
                is_open=1,
            )
            if df.empty:
                self.logger.warning(f"未获取到交易日信息")
                self.trade_dates = []
            else:
                self.trade_dates = df["cal_date"].tolist()
                self.logger.info(f"成功初始化{len(self.trade_dates)}个交易日")
        except Exception as e:
            self.logger.error(f"初始化交易日历失败: {e}")
            self.trade_dates = []

    def get_stock_data(
        self,
        ts_codes: List[str],
    ) -> pd.DataFrame:
        """获取股票行情数据"""
        try:
            ts_code_str = ",".join(ts_codes)
            self.logger.info(
                f"获取股票{ts_code_str}从{self.start_date}到{self.end_date}的数据"
            )
            df = self.pro.daily(
                ts_code=ts_code_str,
                start_date=self.start_date_ts,
                end_date=self.end_date_ts,
            )

            if df.empty:
                self.logger.warning("未获取到股票数据")
                return pd.DataFrame()

            self.logger.info(f"成功获取{len(df)}条股票数据")
            return df
        except Exception as e:
            self.logger.error(f"获取股票数据失败: {e}")
            return pd.DataFrame()

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
            batch_size = 1000
            total_inserted = 0

            for i in range(0, len(df), batch_size):
                batch_df = df.iloc[i : i + batch_size]
                data_list = [tuple(row) for _, row in batch_df.iterrows()]

                cursor.executemany(insert_sql, data_list)
                batch_inserted = cursor.rowcount
                total_inserted += batch_inserted

            self.connection.commit()
            self.logger.info(f"成功插入/更新{total_inserted}条股票数据")
            return total_inserted

        except Exception as e:
            if self.connection:
                self.connection.rollback()
            self.logger.error(f"插入股票数据失败: {e}")
            return 0
        finally:
            if cursor:
                cursor.close()

    def check_stock_data_completeness(self, stock_code: str) -> Tuple[float, int, int]:
        """检查指定股票在回测期间的数据完整性"""
        try:
            cursor = self.connection.cursor()

            # 获取该时间段内应有的交易日
            trade_dates = self.get_available_trade_dates()
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
            cursor.execute(query, (stock_code, self.start_date, self.end_date))
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

    def prepare_backtest_data(
        self,
        stock_codes: List[str],
        data_check_threshold: float = 0.9,  # 数据完整性阈值
        batch_query_interval: int = 1,  # API调用间隔
    ) -> Dict[str, Any]:
        """准备回测所需的历史数据"""

        self.logger.info(f"准备从{self.start_date}到{self.end_date}的回测数据")

        # 批处理股票数据获取
        batch_size = 5  # Tushare API有频率限制，每次获取少量股票

        result_stats = {
            "total_stocks": len(stock_codes),
            "processed_stocks": 0,
            "added_data_points": 0,
            "failed_stocks": [],
            "success_stocks": [],
            "start_date": self.start_date,
            "end_date": self.end_date,
        }

        # 获取交易日历
        trade_dates = self.get_available_trade_dates()
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
                        stock
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
                        f"获取股票{stock}的历史数据，完整性: {completeness:.2%}"
                    )
                    raw_data = self.get_stock_data(ts_codes=[stock])

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

                except Exception as e:
                    self.logger.error(f"处理股票{stock}失败: {e}")
                    result_stats["failed_stocks"].append(stock)

                # 添加API调用间隔，避免超过频率限制
                time.sleep(batch_query_interval)

        # 计算最终统计数据
        result_stats["success_rate"] = (
            len(result_stats["success_stocks"]) / result_stats["total_stocks"]
            if result_stats["total_stocks"] > 0
            else 0
        )

        return result_stats

    def get_stock_basic(self) -> int:
        """获取股票基本信息"""
        try:
            self.logger.info("获取股票基本信息...")
            df = self.pro.stock_basic(
                exchange="",
                list_status="L",
                fields="ts_code,name,area,industry,market,list_status,list_date,is_hs",
            )

            if df.empty:
                self.logger.warning("未获取到股票基本信息")
                return 0

            # 重命名列
            df = df.rename(columns={"ts_code": "stock_code", "name": "stock_name"})

            # 处理日期格式
            if "list_date" in df.columns:
                df["list_date"] = pd.to_datetime(df["list_date"]).dt.date

            # 添加数据源和采集时间
            df["data_source"] = "tushare"
            df["collect_time"] = datetime.now()

            # 插入数据库
            return self.insert_data(df, "StockBasic")
        except Exception as e:
            self.logger.error(f"获取股票基本信息失败: {e}")
            return 0

    def get_historical_stock_valuation(self) -> int:
        """
        获取回测期间每个交易日的股票估值数据

        Returns:
            插入/更新的记录数
        """

        # 获取回测期间的所有交易日
        self.logger.info(
            f"获取从 {self.start_date} 到 {self.end_date} 的历史股票估值数据..."
        )
        trade_dates = self.get_available_trade_dates()

        if not trade_dates:
            self.logger.warning(
                f"在 {self.start_date} 至 {self.end_date} 期间未找到交易日"
            )
            return 0

        total_records = 0
        # 为每个交易日获取估值数据
        for trade_date in trade_dates:
            self.logger.info(f"获取 {trade_date} 的估值数据...")
            records = self.get_stock_valuation(trade_date)
            total_records += records

            # 添加API调用延迟，避免超过频率限制
            time.sleep(1)

        self.logger.info(f"成功获取并存储了 {total_records} 条历史估值数据")
        return total_records

    def get_stock_valuation(self, trade_date) -> int:
        """
        获取特定日期的股票估值数据

        Args:
            trade_date: 交易日期，格式YYYYMMDD

        Returns:
            插入/更新的记录数
        """
        try:
            self.logger.info(f"获取{trade_date}的股票估值数据...")
            df = self.pro.daily_basic(
                trade_date=trade_date,
                fields="ts_code,trade_date,pe,pb,ps,total_mv,circ_mv,turnover_rate",
            )

            if df.empty:
                self.logger.warning(f"未获取到{trade_date}的股票估值数据")
                return 0

            # 重命名列
            df = df.rename(
                columns={
                    "ts_code": "stock_code",
                    "pe": "pe_ratio",
                    "pb": "pb_ratio",
                    "ps": "ps_ratio",
                    "total_mv": "market_cap",
                    "circ_mv": "circulating_market_cap",
                    "turnover_rate": "turnover_ratio",
                }
            )

            # 转换日期格式
            df["trade_date"] = pd.to_datetime(df["trade_date"]).dt.date

            # 添加数据源和采集时间
            df["data_source"] = "tushare"
            df["collect_time"] = datetime.now()

            # 插入数据库
            return self.insert_data(df, "StockValuation")
        except Exception as e:
            self.logger.error(f"获取股票估值数据失败: {e}")
            return 0

    def get_index_component(self, index_code="000300.SH") -> int:
        """获取指数成分股数据"""
        try:
            self.logger.info(f"获取{index_code}的成分股数据...")

            # 使用一个已知存在数据的历史月份（固定为2023年最后一个完整月份）
            # 这样保证数据稳定可用
            start_date = "20231201"
            end_date = "20231231"

            self.logger.info(f"使用日期范围：{start_date}至{end_date}")

            # 按文档建议传入月度开始和结束日期
            df = self.pro.index_weight(
                index_code=index_code, start_date=start_date, end_date=end_date
            )

            if df.empty:
                self.logger.warning(f"未获取到{index_code}的成分股数据")

                # 尝试另一种指数代码格式（沪深300可能有两种代码表示）
                alt_code = "399300.SZ" if index_code == "000300.SH" else index_code
                if alt_code != index_code:
                    self.logger.info(f"尝试使用替代指数代码: {alt_code}")
                    df = self.pro.index_weight(
                        index_code=alt_code, start_date=start_date, end_date=end_date
                    )

                if df.empty:
                    self.logger.warning(
                        f"仍未获取到指数成分股数据，请检查指数代码或API权限"
                    )
                    return 0

            # 获取最新交易日的数据（通常是当月最后一个交易日）
            latest_date = df["trade_date"].max()
            df = df[df["trade_date"] == latest_date]

            self.logger.info(
                f"成功获取{len(df)}只{index_code}的成分股（{latest_date}）"
            )

            # 重命名列
            df = df.rename(columns={"con_code": "stock_code"})

            # 添加指数代码
            df["index_code"] = index_code
            df["is_current"] = True

            # 确保 weight 列存在
            if "weight" not in df.columns:
                df["weight"] = 0

            # 添加数据源和采集时间
            df["data_source"] = "tushare"
            df["collect_time"] = datetime.now()

            # 在插入数据库前显式选择需要的列
            needed_columns = [
                "index_code",
                "stock_code",
                "weight",
                "is_current",
                "data_source",
                "collect_time",
            ]
            df = df[needed_columns]

            # 清理旧数据
            self.delete_old_index_components(index_code)

            # 插入数据库
            return self.insert_data(df, "IndexComponent")
        except Exception as e:
            self.logger.error(f"获取指数成分股数据失败: {e}")
            traceback.print_exc()  # 打印完整错误堆栈，方便调试
            return 0

    def delete_old_index_components(self, index_code):
        """删除旧的指数成分股数据"""
        try:
            cursor = self.connection.cursor()
            query = "UPDATE IndexComponent SET is_current = FALSE WHERE index_code = %s"
            cursor.execute(query, (index_code,))
            self.connection.commit()
            self.logger.info(f"已将{index_code}的旧成分股标记为非当前")
        except Exception as e:
            if self.connection:
                self.connection.rollback()
            self.logger.error(f"更新旧指数成分股状态失败: {e}")
        finally:
            if cursor:
                cursor.close()

    def get_trading_calendar(
        self, exchange="SSE", start_date=None, end_date=None
    ) -> int:
        """获取交易日历"""
        if not start_date:
            # 默认获取当年和下一年的日历
            today = datetime.now()
            start_date = f"{today.year}0101"

        if not end_date:
            today = datetime.now()
            end_date = f"{today.year + 1}1231"

        try:
            self.logger.info(f"获取{exchange}从{start_date}到{end_date}的交易日历...")

            df = self.pro.trade_cal(
                exchange=exchange, start_date=start_date, end_date=end_date
            )

            if df.empty:
                self.logger.warning(f"未获取到交易日历数据")
                return 0

            # 转换日期格式
            df["cal_date"] = pd.to_datetime(df["cal_date"]).dt.date
            if "pretrade_date" in df.columns:
                df["pretrade_date"] = pd.to_datetime(df["pretrade_date"]).dt.date
            else:
                df["pretrade_date"] = None

            # 添加数据源和采集时间
            df["data_source"] = "tushare"
            df["collect_time"] = datetime.now()

            # 插入数据库
            return self.insert_data(df, "TradingCalendar")
        except Exception as e:
            self.logger.error(f"获取交易日历失败: {e}")
            return 0

    def insert_data(
        self, df: pd.DataFrame, table_name: str, on_duplicate="update"
    ) -> int:
        """通用数据插入方法"""
        if df.empty:
            return 0

        try:
            # 在插入前处理 NaN 值，将其替换为 None（对应MySQL中的 NULL）
            df = df.replace({float("nan"): None, pd.NA: None})

            cursor = self.connection.cursor()

            # 构建SQL
            columns = df.columns.tolist()
            placeholders = ", ".join(["%s"] * len(columns))

            sql = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"

            if on_duplicate == "update":
                updates = [
                    f"{col}=VALUES({col})"
                    for col in columns
                    if col not in ["collect_time"]
                ]
                if updates:
                    sql += f" ON DUPLICATE KEY UPDATE {', '.join(updates)}"

            # 执行批量插入
            data = [tuple(x) for x in df.values]
            cursor.executemany(sql, data)
            self.connection.commit()

            inserted = cursor.rowcount
            self.logger.info(f"成功插入/更新{inserted}条记录到{table_name}表")
            return inserted
        except Exception as e:
            if self.connection:
                self.connection.rollback()
            self.logger.error(f"插入数据到{table_name}表失败: {e}")
            traceback.print_exc()
            return 0
        finally:
            if cursor:
                cursor.close()

    def get_index_stocks(self, index_code="000300.SH") -> List[str]:
        """获取指定指数的成分股列表"""
        try:
            cursor = self.connection.cursor()

            query = """
            SELECT stock_code FROM IndexComponent 
            WHERE index_code = %s AND is_current = TRUE
            """

            cursor.execute(query, (index_code,))
            result = cursor.fetchall()

            if not result:
                # 如果数据库中没有，就从API获取
                self.get_index_component(index_code)

                # 再次查询
                cursor.execute(query, (index_code,))
                result = cursor.fetchall()

            stock_list = [row[0] for row in result]
            self.logger.info(f"获取到{index_code}的{len(stock_list)}只成分股")
            return stock_list
        except Exception as e:
            self.logger.error(f"获取指数成分股失败: {e}")
            return []
        finally:
            if cursor:
                cursor.close()


def load_config(config_file="config.json"):
    """加载配置文件"""
    try:
        if not os.path.exists(config_file):
            raise FileNotFoundError(f"配置文件不存在: {config_file}")

        with open(config_file, "r", encoding="utf-8") as f:
            config = json.load(f)

        # 验证必需字段
        if "db_password" not in config:
            raise ValueError("配置文件缺少数据库密码")
        if "tushare_token" not in config:
            raise ValueError("配置文件缺少Tushare token")

        return config
    except Exception as e:
        logger.error(f"加载配置文件失败: {e}")
        raise


def main():
    """主函数"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="量化交易系统回测数据准备工具")
    parser.add_argument(
        "--start", type=str, required=True, help="开始日期 (YYYY-MM-DD)"
    )
    parser.add_argument("--end", type=str, required=True, help="结束日期 (YYYY-MM-DD)")
    parser.add_argument("--stock", type=str, help="准备单只股票的回测数据")
    parser.add_argument(
        "--index", type=str, help="使用指定指数的成分股，例如：000300.SH (沪深300)"
    )
    parser.add_argument(
        "--config", type=str, default="config.json", help="配置文件路径"
    )

    args = parser.parse_args()

    # 验证必须提供 --stock 或 --index 参数
    if not args.stock and not args.index:
        logger.error("必须提供 --stock 或 --index 参数")
        print("错误: 必须提供 --stock 或 --index 参数")
        show_usage()
        return

    try:
        # 加载配置
        config = load_config(args.config)

        # 创建数据管理器，传入日期范围
        stock_manager = StockDataManager(
            db_password=config["db_password"],
            tushare_token=config["tushare_token"],
            start_date=args.start,
            end_date=args.end,
        )

        # 连接数据库
        stock_manager.connect_database()

        # 准备回测数据
        stock_codes = []

        if args.index:
            # 使用指定指数成分股
            logger.info(f"准备指数 {args.index} 成分股的数据...")
            stock_manager.get_index_component(args.index)  # 确保指数成分股数据最新
            stock_codes = stock_manager.get_index_stocks(args.index)

            if stock_codes:
                logger.info(
                    f"将为指数 {args.index} 的 {len(stock_codes)} 只成分股准备数据"
                )
            else:
                logger.warning(
                    f"未找到指数 {args.index} 的成分股，请检查指数代码是否正确"
                )
                return
        elif args.stock:
            # 单只股票模式
            stock_codes = [args.stock]
            logger.info(f"将为单只股票 {args.stock} 准备数据")

        # 准备所有必要的数据
        logger.info("准备回测所需的完整数据...")

        # 1. 获取基础数据表
        stock_manager.get_stock_basic()
        stock_manager.get_trading_calendar()

        # 2. 获取回测期间的估值数据（为每个交易日获取）
        stock_manager.get_historical_stock_valuation()

        # 3. 获取最近季度的财务数据
        stock_manager.get_balance_sheet()
        stock_manager.get_income_statement()

        # 4. 准备股票市场数据
        results = stock_manager.prepare_backtest_data(stock_codes=stock_codes)

        logger.info(
            f"回测数据准备完成 - 成功处理{results['processed_stocks']}/{results['total_stocks']}只股票"
        )

        # 根据模式显示不同的完成信息
        if args.index:
            logger.info(f"指数 {args.index} 的成分股数据准备完成，可以进行回测了")
        elif args.stock:
            logger.info(f"股票 {args.stock} 的数据准备完成，可以进行回测了")

    except Exception as e:
        logger.error(f"处理过程中发生错误: {e}")
        logger.error(traceback.format_exc())
    finally:
        if "stock_manager" in locals():
            stock_manager.close_database()


def show_usage():
    """显示使用说明"""
    print(
        """
📖 回测数据准备工具使用说明:

1️⃣ 准备单只股票数据:
   python stock_data_fetcher.py --start 2024-01-01 --end 2024-08-31 --stock 600519.SH

2️⃣ 准备指数成分股数据:
   python stock_data_fetcher.py --start 2024-01-01 --end 2024-08-31 --index 000300.SH

📋 参数说明:
   --start        : 开始日期 (YYYY-MM-DD)，必须提供
   --end          : 结束日期 (YYYY-MM-DD)，必须提供
   --stock        : 准备单只股票的回测数据（必须提供--stock或--index）
   --index        : 使用指定指数的成分股，例如：000300.SH (沪深300)
   --config       : 配置文件路径，默认为config.json
   --help         : 显示帮助信息

⚠️ 注意事项:
   - 必须提供开始日期和结束日期
   - 必须指定股票代码(--stock)或指数代码(--index)
   - 数据将保存到数据库相应的表中
   - 确保config.json中包含正确的数据库密码和Tushare令牌
    """
    )


if __name__ == "__main__":
    main()
