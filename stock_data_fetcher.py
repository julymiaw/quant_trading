#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
量化交易系统 - 股票数据获取与数据库操作脚本
使用Tushare API获取股票数据并写入MySQL数据库
通过视图查询最新股价信息
"""

import tushare as ts
import pymysql
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
import uuid
import traceback
from typing import List, Dict, Any, Optional

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class StockDataManager:
    """股票数据管理类"""

    def __init__(self, tushare_token: str, db_config: Dict[str, Any]):
        """
        初始化股票数据管理器

        Args:
            tushare_token: Tushare API token
            db_config: 数据库配置字典
        """
        self.tushare_token = tushare_token
        self.db_config = db_config
        self.connection = None

        # 初始化Tushare
        ts.set_token(tushare_token)
        self.pro = ts.pro_api()

    def connect_database(self):
        """连接数据库"""
        try:
            self.connection = pymysql.connect(
                host=self.db_config["host"],
                user=self.db_config["user"],
                password=self.db_config["password"],
                database=self.db_config["database"],
                charset="utf8mb4",
                autocommit=False,
            )
            logger.info("数据库连接成功")
        except Exception as e:
            logger.error(f"数据库连接失败: {e}")
            raise

    def close_database(self):
        """关闭数据库连接"""
        if self.connection:
            self.connection.close()
            logger.info("数据库连接已关闭")

    def get_stock_data(
        self,
        ts_codes: List[str] = None,
        start_date: str = None,
        end_date: str = None,
        trade_date: str = None,
    ) -> pd.DataFrame:
        """
        获取股票行情数据

        Args:
            ts_codes: 股票代码列表，如['000001.SZ', '600000.SH']
            start_date: 开始日期，格式YYYYMMDD
            end_date: 结束日期，格式YYYYMMDD
            trade_date: 特定交易日期，格式YYYYMMDD

        Returns:
            股票数据DataFrame
        """
        try:
            if trade_date:
                # 获取特定日期的所有股票数据
                logger.info(f"获取{trade_date}的全部股票数据")
                df = self.pro.daily(trade_date=trade_date)
            elif ts_codes:
                # 获取指定股票的历史数据
                ts_code_str = ",".join(ts_codes)
                logger.info(f"获取股票{ts_code_str}从{start_date}到{end_date}的数据")
                df = self.pro.daily(
                    ts_code=ts_code_str, start_date=start_date, end_date=end_date
                )
            else:
                raise ValueError("必须指定ts_codes或trade_date参数")

            if df.empty:
                logger.warning("未获取到股票数据")
                return pd.DataFrame()

            logger.info(f"成功获取{len(df)}条股票数据")
            return df

        except Exception as e:
            logger.error(f"获取股票数据失败: {e}")
            raise

    def process_stock_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        处理股票数据，转换为数据库格式

        Args:
            df: 原始股票数据DataFrame

        Returns:
            处理后的DataFrame
        """
        if df.empty:
            return df

        # 重命名列以匹配数据库字段
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

        # 转换数据类型
        processed_df["trade_date"] = pd.to_datetime(processed_df["trade_date"]).dt.date
        processed_df["change_percent"] = (
            processed_df["change_percent"] / 100
        )  # 转换为小数
        processed_df["volume"] = processed_df["volume"] * 100  # 手转换为股
        processed_df["amount"] = processed_df["amount"] * 1000  # 千元转换为元

        # 添加数据源和采集时间
        processed_df["data_source"] = "tushare"
        processed_df["collect_time"] = datetime.now()

        # 处理缺失值
        processed_df = processed_df.fillna(0)

        # 只保留需要的列
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

        logger.info(f"数据处理完成，处理了{len(processed_df)}条记录")
        return processed_df

    def insert_stock_data(self, df: pd.DataFrame) -> int:
        """
        将股票数据插入数据库

        Args:
            df: 处理后的股票数据DataFrame

        Returns:
            成功插入的记录数
        """
        if df.empty:
            logger.warning("没有数据需要插入")
            return 0

        try:
            cursor = self.connection.cursor()

            # 准备插入SQL
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

            # 准备数据
            data_list = []
            for _, row in df.iterrows():
                data_list.append(tuple(row))

            # 批量插入
            cursor.executemany(insert_sql, data_list)
            affected_rows = cursor.rowcount

            self.connection.commit()
            logger.info(f"成功插入/更新{affected_rows}条股票数据")

            return affected_rows

        except Exception as e:
            if self.connection:
                self.connection.rollback()
            logger.error(f"插入股票数据失败: {e}")
            raise
        finally:
            if cursor:
                cursor.close()

    def get_latest_stock_prices(self, stock_codes: List[str] = None) -> pd.DataFrame:
        """
        通过视图获取最新股价信息

        Args:
            stock_codes: 可选的股票代码列表，用于过滤

        Returns:
            最新股价DataFrame
        """
        try:
            cursor = self.connection.cursor()

            if stock_codes:
                # 构建IN查询条件
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
                # 获取所有股票的最新价格
                query_sql = """
                SELECT stock_code, latest_date, latest_price, 
                       change_percent, volume
                FROM LatestStockPrice 
                ORDER BY stock_code
                """
                cursor.execute(query_sql)

            # 获取查询结果
            results = cursor.fetchall()

            if not results:
                logger.warning("未查询到最新股价数据")
                return pd.DataFrame()

            # 转换为DataFrame
            columns = ["股票代码", "最新日期", "最新价格", "涨跌幅(%)", "成交量"]
            df = pd.DataFrame(results, columns=columns)

            # 格式化显示
            df["涨跌幅(%)"] = (df["涨跌幅(%)"] * 100).round(2)
            df["最新价格"] = df["最新价格"].round(3)
            df["成交量"] = df["成交量"].astype(int)

            logger.info(f"查询到{len(df)}只股票的最新价格")
            return df

        except Exception as e:
            logger.error(f"查询最新股价失败: {e}")
            raise
        finally:
            if cursor:
                cursor.close()

    def log_operation(
        self,
        operation_type: str,
        content: str,
        result: str = "success",
        error_info: str = None,
    ):
        """
        记录系统操作日志

        Args:
            operation_type: 操作类型
            content: 操作内容
            result: 操作结果
            error_info: 错误信息
        """
        try:
            cursor = self.connection.cursor()

            log_sql = """
            INSERT INTO SystemLog (
                log_id, operator_id, operator_role, operation_type, 
                operation_content, operation_result, error_info
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """

            log_data = (
                str(uuid.uuid4()),
                "admin_001",  # 系统管理员
                "system",
                operation_type,
                content,
                result,
                error_info,
            )

            cursor.execute(log_sql, log_data)
            self.connection.commit()

        except Exception as e:
            logger.error(f"记录操作日志失败: {e}")
        finally:
            if cursor:
                cursor.close()


def main():
    """主函数"""

    # 配置参数
    TUSHARE_TOKEN = "YOUR_TUSHARE_TOKEN_HERE"  # 请替换为您的Tushare token

    DB_CONFIG = {
        "host": "localhost",
        "user": "root",
        "password": "your_password",  # 请替换为您的数据库密码
        "database": "quantitative_trading",
    }

    # 示例股票代码（A股主要股票）
    STOCK_CODES = [
        "000001.SZ",  # 平安银行
        "000002.SZ",  # 万科A
        "600000.SH",  # 浦发银行
        "600036.SH",  # 招商银行
        "600519.SH",  # 贵州茅台
        "000858.SZ",  # 五粮液
    ]

    # 数据获取日期范围（最近30天）
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)

    start_date_str = start_date.strftime("%Y%m%d")
    end_date_str = end_date.strftime("%Y%m%d")

    # 创建数据管理器实例
    stock_manager = StockDataManager(TUSHARE_TOKEN, DB_CONFIG)

    try:
        # 连接数据库
        stock_manager.connect_database()
        logger.info("开始股票数据获取和处理流程")

        # 1. 获取股票数据
        logger.info(f"获取股票数据，日期范围: {start_date_str} - {end_date_str}")
        raw_data = stock_manager.get_stock_data(
            ts_codes=STOCK_CODES, start_date=start_date_str, end_date=end_date_str
        )

        if raw_data.empty:
            logger.warning("未获取到股票数据")
            return

        # 2. 处理数据
        logger.info("处理股票数据格式")
        processed_data = stock_manager.process_stock_data(raw_data)

        # 3. 插入数据库
        logger.info("将数据写入数据库")
        inserted_count = stock_manager.insert_stock_data(processed_data)

        # 记录操作日志
        stock_manager.log_operation(
            "data_sync",
            f'成功同步{inserted_count}条股票数据，股票代码: {", ".join(STOCK_CODES)}',
            "success",
        )

        # 4. 查询最新股价
        logger.info("查询最新股价信息")
        latest_prices = stock_manager.get_latest_stock_prices(STOCK_CODES)

        if not latest_prices.empty:
            print("\n" + "=" * 80)
            print("最新股价信息（通过LatestStockPrice视图查询）")
            print("=" * 80)
            print(latest_prices.to_string(index=False))
            print("=" * 80)

            # 显示统计信息
            print(f"\n数据统计:")
            print(f"- 总计股票数量: {len(latest_prices)}")
            print(f"- 平均涨跌幅: {latest_prices['涨跌幅(%)'].mean():.2f}%")
            print(f"- 上涨股票数: {len(latest_prices[latest_prices['涨跌幅(%)'] > 0])}")
            print(f"- 下跌股票数: {len(latest_prices[latest_prices['涨跌幅(%)'] < 0])}")
            print(
                f"- 平盘股票数: {len(latest_prices[latest_prices['涨跌幅(%)'] == 0])}"
            )
        else:
            logger.warning("未查询到最新股价数据")

        logger.info("股票数据获取和处理流程完成")

    except Exception as e:
        error_msg = f"处理过程中发生错误: {e}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())

        # 记录错误日志
        try:
            stock_manager.log_operation(
                "data_sync", "股票数据同步失败", "failed", error_msg
            )
        except:
            pass

    finally:
        # 关闭数据库连接
        stock_manager.close_database()


def get_single_day_all_stocks(
    tushare_token: str, db_config: Dict[str, Any], trade_date: str = None
):
    """
    获取单日全部股票数据的便捷函数

    Args:
        tushare_token: Tushare token
        db_config: 数据库配置
        trade_date: 交易日期，格式YYYYMMDD，默认为昨天
    """
    if not trade_date:
        # 默认获取昨天的数据（因为当日数据可能未更新）
        yesterday = datetime.now() - timedelta(days=1)
        trade_date = yesterday.strftime("%Y%m%d")

    stock_manager = StockDataManager(tushare_token, db_config)

    try:
        stock_manager.connect_database()

        # 获取单日全部股票数据
        logger.info(f"获取{trade_date}全部股票数据")
        raw_data = stock_manager.get_stock_data(trade_date=trade_date)

        if not raw_data.empty:
            # 处理并插入数据
            processed_data = stock_manager.process_stock_data(raw_data)
            inserted_count = stock_manager.insert_stock_data(processed_data)

            print(f"成功获取并插入{inserted_count}条股票数据（{trade_date}）")

            # 显示部分数据预览
            if len(processed_data) > 0:
                print("\n数据预览（前10条）:")
                preview_cols = [
                    "stock_code",
                    "trade_date",
                    "close_price",
                    "change_percent",
                    "volume",
                ]
                print(processed_data[preview_cols].head(10).to_string(index=False))
        else:
            print(f"未获取到{trade_date}的股票数据，可能是非交易日")

    except Exception as e:
        logger.error(f"获取单日全部股票数据失败: {e}")
    finally:
        stock_manager.close_database()


def demo_latest_prices(tushare_token: str, db_config: Dict[str, Any]):
    """
    演示最新股价查询功能

    Args:
        tushare_token: Tushare token
        db_config: 数据库配置
    """
    stock_manager = StockDataManager(tushare_token, db_config)

    try:
        stock_manager.connect_database()

        # 查询所有股票的最新价格
        all_latest = stock_manager.get_latest_stock_prices()

        if not all_latest.empty:
            print("\n" + "=" * 60)
            print("数据库中所有股票的最新价格")
            print("=" * 60)
            print(all_latest.head(20).to_string(index=False))  # 只显示前20条
            print(f"... 共{len(all_latest)}只股票")
            print("=" * 60)
        else:
            print("数据库中暂无股票数据")

    except Exception as e:
        logger.error(f"查询最新股价失败: {e}")
    finally:
        stock_manager.close_database()


if __name__ == "__main__":
    # 使用示例
    print("量化交易系统 - 股票数据获取脚本")
    print("请确保已安装以下依赖包: tushare, pymysql, pandas, numpy")
    print("请在脚本中配置正确的Tushare token和数据库连接信息\n")

    # 注意：运行前请替换以下配置
    TUSHARE_TOKEN = "YOUR_TUSHARE_TOKEN_HERE"
    DB_CONFIG = {
        "host": "localhost",
        "user": "root",
        "password": "your_password",
        "database": "quantitative_trading",
    }

    # 检查配置
    if TUSHARE_TOKEN == "YOUR_TUSHARE_TOKEN_HERE":
        print("⚠️  请先配置Tushare token！")
        print("   1. 访问 https://tushare.pro/ 注册并获取token")
        print("   2. 将token替换到脚本中的TUSHARE_TOKEN变量")
        exit(1)

    if DB_CONFIG["password"] == "your_password":
        print("⚠️  请先配置数据库连接信息！")
        print("   请在DB_CONFIG中填入正确的数据库配置")
        exit(1)

    try:
        # 运行主流程
        print("正在执行股票数据获取和处理...")
        main()

        print("\n正在演示最新股价查询...")
        demo_latest_prices(TUSHARE_TOKEN, DB_CONFIG)

    except KeyboardInterrupt:
        print("\n用户中断了程序执行")
    except Exception as e:
        print(f"\n程序执行失败: {e}")
        logger.error(traceback.format_exc())
