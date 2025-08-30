#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据库连接测试脚本
文件名: test_database_connection.py
虚拟环境: quant_trading
Python版本: 3.10.x (推荐)
"""

import pymysql
import json
import os
import sys
from pathlib import Path
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class DatabaseTester:
    """数据库连接测试类"""

    def __init__(self, config_file: str = "config.json"):
        """
        初始化数据库测试器

        Args:
            config_file: 配置文件路径
        """
        self.config_file = config_file
        self.config = None
        self.connection = None

    def create_sample_config(self):
        """创建示例配置文件"""
        sample_config = {
            "database": {
                "host": "localhost",
                "port": 3306,
                "user": "root",
                "password": "your_mysql_password_here",
                "database": "quantitative_trading",
                "charset": "utf8mb4",
            },
            "tushare": {"token": "your_tushare_token_here"},
            "system": {"log_level": "INFO", "data_retention_days": 90},
        }

        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump(sample_config, f, indent=4, ensure_ascii=False)

        print(f"✅ 已创建示例配置文件: {self.config_file}")
        print("📝 请编辑此文件，填入正确的数据库密码和Tushare token")

    def load_config(self):
        """加载配置文件"""
        try:
            if not os.path.exists(self.config_file):
                print(f"❌ 配置文件不存在: {self.config_file}")
                print("正在创建示例配置文件...")
                self.create_sample_config()
                return False

            with open(self.config_file, "r", encoding="utf-8") as f:
                self.config = json.load(f)

            # 验证配置完整性
            required_keys = ["database", "tushare"]
            for key in required_keys:
                if key not in self.config:
                    raise ValueError(f"配置文件缺少必需的section: {key}")

            # 检查是否还是默认值
            if self.config["database"]["password"] == "your_mysql_password_here":
                print("⚠️  请在配置文件中设置正确的MySQL密码")
                return False

            if self.config["tushare"]["token"] == "your_tushare_token_here":
                print("⚠️  请在配置文件中设置正确的Tushare token")
                return False

            logger.info("配置文件加载成功")
            return True

        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            return False

    def test_database_connection(self):
        """测试数据库连接"""
        if not self.config:
            logger.error("配置未加载，无法测试数据库连接")
            return False

        db_config = self.config["database"]

        print("\n" + "=" * 60)
        print("🔍 数据库连接测试")
        print("=" * 60)
        print(f"主机: {db_config['host']}:{db_config.get('port', 3306)}")
        print(f"用户: {db_config['user']}")
        print(f"数据库: {db_config['database']}")
        print("-" * 60)

        try:
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
            ]

            for method in connection_methods:
                try:
                    print(f"🔄 尝试{method['name']}...")
                    self.connection = pymysql.connect(**method["params"])
                    print(f"✅ {method['name']}成功！")
                    self._test_database_operations()
                    return True

                except Exception as e:
                    print(f"❌ {method['name']}失败: {e}")
                    continue

            print("❌ 所有连接方式都失败了")
            return False

        except Exception as e:
            logger.error(f"数据库连接测试失败: {e}")
            return False

    def _test_database_operations(self):
        """测试数据库基本操作"""
        try:
            cursor = self.connection.cursor()

            # 测试基本查询
            cursor.execute("SELECT VERSION()")
            version = cursor.fetchone()
            print(f"📊 MySQL版本: {version[0]}")

            # 测试数据库是否存在
            cursor.execute("SHOW DATABASES LIKE 'quantitative_trading'")
            db_exists = cursor.fetchone()
            if db_exists:
                print("✅ quantitative_trading数据库存在")
            else:
                print("❌ quantitative_trading数据库不存在，请先运行初始化脚本")
                return

            # 切换到目标数据库
            cursor.execute("USE quantitative_trading")

            # 检查表是否存在
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()
            print(f"📋 数据库表数量: {len(tables)}")

            if tables:
                print("📋 现有表:")
                for table in tables:
                    cursor.execute(f"SELECT COUNT(*) FROM {table[0]}")
                    count = cursor.fetchone()[0]
                    print(f"   - {table[0]}: {count} 条记录")

            # 测试视图
            try:
                cursor.execute("SELECT COUNT(*) FROM LatestStockPrice")
                view_count = cursor.fetchone()[0]
                print(f"📈 LatestStockPrice视图: {view_count} 条记录")
            except Exception as e:
                print(f"⚠️  LatestStockPrice视图查询失败: {e}")

            print("✅ 数据库操作测试通过")

        except Exception as e:
            print(f"❌ 数据库操作测试失败: {e}")
        finally:
            if cursor:
                cursor.close()

    def test_tushare_connection(self):
        """测试Tushare连接"""
        if not self.config:
            logger.error("配置未加载，无法测试Tushare连接")
            return False

        print("\n" + "=" * 60)
        print("🔍 Tushare API连接测试")
        print("=" * 60)

        try:
            import tushare as ts

            token = self.config["tushare"]["token"]
            print(f"Token长度: {len(token)} 字符")

            # 设置token
            ts.set_token(token)
            pro = ts.pro_api()

            # 测试API调用 - 获取股票基本信息
            print("🔄 测试API调用...")
            df = pro.stock_basic(
                exchange="",
                list_status="L",
                fields="ts_code,symbol,name,area,industry,list_date",
            )

            if not df.empty:
                print(f"✅ Tushare API连接成功！")
                print(f"📊 获取到{len(df)}只股票信息")
                print("📋 部分股票信息:")
                print(
                    df.head(3)[["ts_code", "name", "industry"]].to_string(index=False)
                )
                return True
            else:
                print("❌ API返回空数据")
                return False

        except Exception as e:
            print(f"❌ Tushare API测试失败: {e}")
            return False

    def run_full_test(self):
        """运行完整测试"""
        print("🚀 量化交易系统 - 连接测试工具")
        print("=" * 60)

        # 1. 加载配置
        if not self.load_config():
            return False

        # 2. 测试数据库连接
        db_success = self.test_database_connection()

        # 3. 测试Tushare连接
        ts_success = self.test_tushare_connection()

        # 4. 总结
        print("\n" + "=" * 60)
        print("📋 测试结果总结")
        print("=" * 60)
        print(f"数据库连接: {'✅ 成功' if db_success else '❌ 失败'}")
        print(f"Tushare API: {'✅ 成功' if ts_success else '❌ 失败'}")

        if db_success and ts_success:
            print("\n🎉 所有连接测试通过！可以运行主要的数据获取脚本了。")
        else:
            print("\n⚠️  请解决上述连接问题后再运行主脚本。")

        return db_success and ts_success

    def close_connection(self):
        """关闭数据库连接"""
        if self.connection:
            self.connection.close()
            logger.info("数据库连接已关闭")


def main():
    """主函数"""
    # 检查当前目录
    current_dir = Path.cwd()
    print(f"📁 当前工作目录: {current_dir}")

    # 创建测试器
    tester = DatabaseTester("config.json")

    try:
        # 运行测试
        success = tester.run_full_test()

        if success:
            print("\n💡 提示: 现在可以运行主要的股票数据获取脚本了")
        else:
            print("\n🔧 故障排除建议:")
            print("1. 检查MySQL服务是否正在运行")
            print("2. 确认用户名和密码是否正确")
            print("3. 确认数据库'quantitative_trading'是否已创建")
            print("4. 检查Tushare token是否有效")
            print("5. 如果是MySQL 8.0+，确保已安装cryptography包")

    except KeyboardInterrupt:
        print("\n👋 用户中断了测试")
    except Exception as e:
        print(f"\n💥 测试过程中发生错误: {e}")
    finally:
        tester.close_connection()


if __name__ == "__main__":
    main()
