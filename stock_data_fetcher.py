#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
量化交易系统 - 股票数据获取脚本
文件名: stock_data_fetcher.py
虚拟环境: quant_trading
Python版本: 3.10.x (推荐)

使用配置文件管理敏感信息，支持安全的股票数据获取和数据库操作
"""

import tushare as ts
import pymysql
import pandas as pd
import numpy as np
import json
import os
from datetime import datetime, timedelta
import logging
import uuid
import traceback
from typing import List, Dict, Any, Optional
from pathlib import Path


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

            # 格式化数据
            df["涨跌幅(%)"] = (df["涨跌幅(%)"] * 100).round(2)
            df["最新价格"] = df["最新价格"].round(3)
            df["成交量"] = df["成交量"].astype(int)

            self.logger.info(f"查询到{len(df)}只股票的最新价格")
            return df

        except Exception as e:
            self.logger.error(f"查询最新股价失败: {e}")
            raise
        finally:
            if cursor:
                cursor.close()


def main():
    """主函数"""
    print("🚀 量化交易系统 - 股票数据获取脚本")
    print("文件名: stock_data_fetcher.py")
    print("虚拟环境: quant_trading")
    print("推荐Python版本: 3.10.x")
    print("=" * 60)

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
   python stock_data_fetcher.py  # 运行主脚本

3️⃣ 获取全市场数据:
   在Python中调用: get_today_market_data()

📋 文件说明:
   - stock_data_fetcher.py: 主要的股票数据获取脚本
   - test_database_connection.py: 数据库连接测试脚本  
   - config.json: 配置文件（包含敏感信息）

⚠️ 注意事项:
   - 请确保config.json在.gitignore中，避免提交敏感信息
   - Tushare API有调用频率限制，请合理使用
   - 建议在非交易时间获取数据，避免影响实时分析
    """
    )


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        if sys.argv[1] == "--help" or sys.argv[1] == "-h":
            show_usage()
        elif sys.argv[1] == "--market":
            get_today_market_data()
        else:
            print("❌ 未知参数，使用 --help 查看使用说明")
    else:
        # 默认运行主流程
        main()
