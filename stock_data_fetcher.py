#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
量化交易系统 - 回测数据准备脚本
文件名: stock_data_fetcher.py
虚拟环境: quant_trading
Python版本: 3.10.x

专注于为回测准备必要的历史股票数据
"""

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
    "charset": "utf8mb4"
}


class StockDataManager:
    """股票数据管理类"""

    def __init__(self, db_password: str, tushare_token: str):
        """
        初始化股票数据管理器

        Args:
            db_password: 数据库密码
            tushare_token: Tushare API令牌
        """
        self.db_password = db_password
        self.connection = None

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
                conv=conv
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

    def get_stock_data(
        self,
        ts_codes: List[str],
        start_date: str,
        end_date: str,
    ) -> pd.DataFrame:
        """获取股票行情数据"""
        try:
            ts_code_str = ",".join(ts_codes)
            self.logger.info(
                f"获取股票{ts_code_str}从{start_date}到{end_date}的数据"
            )
            df = self.pro.daily(
                ts_code=ts_code_str, start_date=start_date, end_date=end_date
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

    def get_stock_list(self, list_status="L") -> List[str]:
        """获取股票列表"""
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
        """获取指定日期范围内的交易日"""
        try:
            df = self.pro.trade_cal(
                exchange="SSE", start_date=start_date, end_date=end_date, is_open=1
            )
            if df.empty:
                self.logger.warning(f"未获取到交易日信息")
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
        """检查指定股票在指定日期范围内的数据完整性"""
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
            completeness_ratio = actual_days / expected_days if expected_days > 0 else 0.0

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
        end_date: str = None, 
        history_days: int = 1095,  # 默认3年数据
        batch_query_interval: int = 1,  # API调用间隔
        data_check_threshold: float = 0.9  # 数据完整性阈值
    ) -> Dict[str, Any]:
        """准备回测所需的历史数据"""
        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")
            
        start_date = (datetime.strptime(end_date, "%Y-%m-%d") - timedelta(days=history_days)).strftime("%Y-%m-%d")
        
        # 转换为tushare格式
        start_date_ts = start_date.replace("-", "")
        end_date_ts = end_date.replace("-", "")
        
        self.logger.info(f"准备从{start_date}到{end_date}的回测数据")
        
        # 批处理股票数据获取
        batch_size = 5  # Tushare API有频率限制，每次获取少量股票
        
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
            self.logger.info(f"处理第{i//batch_size + 1}批，股票: {', '.join(batch_stocks)}")

            for stock in batch_stocks:
                try:
                    # 检查现有数据完整性
                    completeness, actual_days, _ = self.check_stock_data_completeness(
                        stock, start_date, end_date
                    )

                    if completeness >= data_check_threshold:
                        self.logger.info(f"股票{stock}数据完整性良好({completeness:.2%})，无需更新")
                        result_stats["success_stocks"].append(stock)
                        result_stats["processed_stocks"] += 1
                        continue

                    # 获取数据并处理
                    self.logger.info(f"获取股票{stock}的历史数据，完整性: {completeness:.2%}")
                    raw_data = self.get_stock_data(
                        ts_codes=[stock], start_date=start_date_ts, end_date=end_date_ts
                    )

                    if raw_data.empty:
                        self.logger.warning(f"未获取到股票{stock}的数据，可能是新上市或已退市")
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

    def get_backtest_ready_stocks(
        self,
        min_completeness: float = 0.95,
        start_date: str = None,
        end_date: str = None,
        min_days: int = 365
    ) -> List[str]:
        """获取可用于回测的股票列表(数据完整性达标)"""
        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")

        if not start_date:
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

            self.logger.info(f"检查{total}只股票在{start_date}至{end_date}期间的数据完整性")

            # 检查每只股票的数据完整性
            for i, stock in enumerate(all_stocks):
                completeness, actual, expected = self.check_stock_data_completeness(
                    stock, start_date, end_date
                )

                if completeness >= min_completeness:
                    ready_stocks.append(stock)

                # 每100只股票显示一次进度
                if (i + 1) % 100 == 0 or i + 1 == total:
                    self.logger.info(f"进度: {i+1}/{total}, 可用: {len(ready_stocks)}")

            self.logger.info(f"检查完成，有{len(ready_stocks)}/{total}只股票可用于回测")
            return ready_stocks

        except Exception as e:
            self.logger.error(f"获取可回测股票列表失败: {e}")
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
    parser.add_argument("--backtest", action="store_true", help="准备回测数据")
    parser.add_argument("--stocks", type=str, help="指定股票代码，多个用逗号分隔")
    parser.add_argument("--days", type=int, default=1095, help="历史数据天数")
    parser.add_argument("--end", type=str, help="结束日期 (YYYY-MM-DD)")
    parser.add_argument("--check", action="store_true", help="检查哪些股票可用于回测")
    parser.add_argument("--completeness", type=float, default=0.95, help="数据完整性阈值")
    parser.add_argument("--config", type=str, default="config.json", help="配置文件路径")
    args = parser.parse_args()

    try:
        # 加载配置
        config = load_config(args.config)
        
        # 创建数据管理器
        stock_manager = StockDataManager(
            db_password=config["db_password"],
            tushare_token=config["tushare_token"]
        )
        
        # 连接数据库
        stock_manager.connect_database()
        
        # 默认股票列表
        default_stocks = [
            "000001.SZ", "000002.SZ", "600000.SH", 
            "600036.SH", "600519.SH", "000858.SZ"
        ]

        if args.check:
            # 检查可用于回测的股票
            end_date = args.end or datetime.now().strftime("%Y-%m-%d")
            
            ready_stocks = stock_manager.get_backtest_ready_stocks(
                min_completeness=args.completeness,
                end_date=end_date,
                min_days=args.days
            )

            if ready_stocks:
                # 保存结果到文件
                result_file = f"backtest_ready_stocks_{datetime.now().strftime('%Y%m%d')}.txt"
                with open(result_file, "w") as f:
                    f.write("\n".join(ready_stocks))
                logger.info(f"找到{len(ready_stocks)}只可用于回测的股票，已保存至{result_file}")
            else:
                logger.warning("未找到符合条件的股票")

        else:  # 默认准备回测数据
            # 准备回测数据
            if args.stocks:
                stock_codes = args.stocks.split(",")
            else:
                stock_codes = default_stocks

            # 准备数据
            results = stock_manager.prepare_backtest_data(
                stock_codes=stock_codes, 
                end_date=args.end, 
                history_days=args.days
            )
            
            logger.info(f"回测数据准备完成 - 成功处理{results['processed_stocks']}/{results['total_stocks']}只股票")

    except Exception as e:
        logger.error(f"处理过程中发生错误: {e}")
        logger.debug(traceback.format_exc())
    finally:
        if 'stock_manager' in locals():
            stock_manager.close_database()


if __name__ == "__main__":
    main()