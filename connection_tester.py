#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据库和Tushare API连接测试工具
文件名: connection_tester.py
虚拟环境: quant_trading
Python版本: 3.10.x (推荐)

该脚本用于测试MySQL数据库连接和Tushare API token是否有效，
并生成详细的API可用性报告，帮助开发者了解当前可以访问哪些功能。
"""

import pymysql
import json
import os
import logging
from datetime import datetime
import time
import argparse

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 数据库默认设置 - 这些通常不需要修改
DB_DEFAULTS = {
    "host": "localhost",
    "port": 3306,
    "user": "root",
    "database": "quantitative_trading",
    "charset": "utf8mb4"
}

# Tushare API分类及对应的功能
TUSHARE_API_CATEGORIES = {
    "股票数据": [
        {"api": "stock_basic", "name": "股票列表", "points": 120},
        {"api": "daily", "name": "日线行情", "points": 120},
        {"api": "weekly", "name": "周线行情", "points": 2000},
        {"api": "monthly", "name": "月线行情", "points": 2000},
        {"api": "daily_basic", "name": "每日指标数据", "points": 2000},
        {"api": "new_share", "name": "IPO新股列表", "points": 120},
        {"api": "top_list", "name": "龙虎榜每日明细", "points": 2000},
        {"api": "top_inst", "name": "龙虎榜机构交易明细", "points": 2000},
        {"api": "pledge_detail", "name": "股权质押明细", "points": 2000},
        {"api": "pledge_stat", "name": "股权质押统计", "points": 2000},
        {"api": "margin", "name": "融资融券交易汇总", "points": 2000},
        {"api": "margin_detail", "name": "融资融券交易明细", "points": 2000},
        {"api": "repurchase", "name": "股票回购", "points": 2000},
        {"api": "concept", "name": "概念股行情", "points": 5000},
        {"api": "concept_detail", "name": "概念股列表", "points": 5000},
        {"api": "share_float", "name": "限售股解禁", "points": 3000},
        {"api": "block_trade", "name": "大宗交易", "points": 2000},
        {"api": "stk_holdernumber", "name": "股东人数", "points": 2000},
        {"api": "moneyflow", "name": "个股资金流向", "points": 2000},
        {"api": "stk_holdertrade", "name": "股东增减持", "points": 2000},
        {"api": "stk_limit", "name": "每日涨跌停价格", "points": 2000},
        {"api": "hk_hold", "name": "沪深股通持股明细", "points": 2000}
    ],
    "财务数据": [
        {"api": "income", "name": "利润表", "points": 2000},
        {"api": "balancesheet", "name": "资产负债表", "points": 2000},
        {"api": "cashflow", "name": "现金流量表", "points": 2000},
        {"api": "forecast", "name": "业绩预告", "points": 2000},
        {"api": "express", "name": "业绩快报", "points": 2000},
        {"api": "dividend", "name": "分红送股", "points": 2000},
        {"api": "fina_indicator", "name": "财务指标数据", "points": 2000},
        {"api": "fina_audit", "name": "财务审计意见", "points": 2000},
        {"api": "fina_mainbz", "name": "主营业务构成", "points": 2000},
        {"api": "disclosure_date", "name": "财报披露计划", "points": 2000}
    ],
    "基金数据": [
        {"api": "fund_basic", "name": "公募基金列表", "points": 2000},
        {"api": "fund_company", "name": "公募基金公司", "points": 2000},
        {"api": "fund_nav", "name": "公募基金净值", "points": 2000},
        {"api": "fund_daily", "name": "场内基金日线行情", "points": 2000},
        {"api": "fund_div", "name": "公募基金分红", "points": 2000},
        {"api": "fund_portfolio", "name": "公募基金持仓数据", "points": 2000},
        {"api": "fund_adj", "name": "基金复权因子", "points": 5000}
    ],
    "期货数据": [
        {"api": "fut_basic", "name": "期货合约列表", "points": 2000},
        {"api": "trade_cal", "name": "期货交易日历", "points": 2000},
        {"api": "fut_daily", "name": "期货日线行情", "points": 2000},
        {"api": "fut_holding", "name": "每日成交持仓排名", "points": 2000},
        {"api": "fut_wsr", "name": "仓单日报", "points": 2000},
        {"api": "fut_settle", "name": "结算参数", "points": 2000},
        {"api": "index_daily", "name": "南华期货指数行情", "points": 2000}
    ],
    "期权数据": [
        {"api": "opt_basic", "name": "期权合约列表", "points": 2000},
        {"api": "opt_daily", "name": "期权日线行情", "points": 5000}
    ],
    "债券数据": [
        {"api": "cb_basic", "name": "可转债基础信息", "points": 2000},
        {"api": "cb_issue", "name": "可转债发行数据", "points": 2000},
        {"api": "cb_daily", "name": "可转债日线数据", "points": 2000}
    ],
    "外汇数据": [
        {"api": "fx_obasic", "name": "外汇基础信息（海外）", "points": 2000},
        {"api": "fx_daily", "name": "外汇日线行情", "points": 2000}
    ],
    "指数数据": [
        {"api": "index_basic", "name": "指数基本信息", "points": 2000},
        {"api": "index_daily", "name": "指数日线行情", "points": 2000},
        {"api": "index_weekly", "name": "指数周线行情", "points": 2000},
        {"api": "index_monthly", "name": "指数月线行情", "points": 2000},
        {"api": "index_weight", "name": "指数成分和权重", "points": 2000},
        {"api": "index_dailybasic", "name": "大盘指数每日指标", "points": 4000},
        {"api": "index_classify", "name": "申万行业分类", "points": 2000},
        {"api": "index_member_all", "name": "申万行业成分", "points": 2000}
    ],
    "港股数据": [
        {"api": "hk_basic", "name": "港股列表", "points": 2000},
        {"api": "hk_daily", "name": "港股日线行情", "points": 1000},
        {"api": "hk_mins", "name": "港股分钟行情", "points": 2000}
    ],
    "宏观经济": [
        {"api": "shibor", "name": "SHIBOR利率数据", "points": 2000},
        {"api": "shibor_quote", "name": "SHIBOR报价数据", "points": 2000},
        {"api": "shibor_lpr", "name": "LPR贷款基础利率", "points": 120},
        {"api": "libor", "name": "LIBOR拆借利率", "points": 120},
        {"api": "hibor", "name": "HIBOR拆借利率", "points": 120},
        {"api": "wz_index", "name": "温州民间借贷利率", "points": 2000},
        {"api": "gz_index", "name": "广州民间借贷利率", "points": 2000}
    ],
    "行业特色": [
        {"api": "tmt_twincome", "name": "台湾电子产业月营收", "points": 0},
        {"api": "tmt_twincomedetail", "name": "台湾电子产业月营收明细", "points": 0},
        {"api": "bo_monthly", "name": "电影月度票房", "points": 500},
        {"api": "bo_weekly", "name": "电影周度票房", "points": 500},
        {"api": "bo_daily", "name": "电影日度票房", "points": 500},
        {"api": "bo_cinema", "name": "影院每日票房", "points": 500},
        {"api": "film_record", "name": "全国电影剧本备案数据", "points": 120},
        {"api": "teleplay_record", "name": "全国电视剧本备案数据", "points": 600}
    ]
}


class ConnectionTester:
    """数据库和API连接测试类"""

    def __init__(self, config_file: str = "config.json"):
        """初始化连接测试器"""
        self.config_file = config_file
        self.config = None
        self.connection = None
        self.api_test_results = {}
        self.api_success = False
        self.db_success = False

    def create_sample_config(self):
        """创建示例配置文件"""
        sample_config = {
            "db_password": "your_mysql_password_here",
            "tushare_token": "your_tushare_token_here"
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
            required_keys = ["db_password", "tushare_token"]
            for key in required_keys:
                if key not in self.config:
                    raise ValueError(f"配置文件缺少必需的字段: {key}")

            # 检查是否还是默认值
            if self.config["db_password"] == "your_mysql_password_here":
                print("⚠️  请在配置文件中设置正确的MySQL密码")
                return False

            if self.config["tushare_token"] == "your_tushare_token_here":
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
    
        logger.info("连接数据库...")
                
        try:
            self.connection = pymysql.connect(
                host=DB_DEFAULTS["host"],
                port=DB_DEFAULTS["port"],
                user=DB_DEFAULTS["user"],
                password=self.config["db_password"],
                database=DB_DEFAULTS["database"],
                charset=DB_DEFAULTS["charset"],
                autocommit=False
            )
            
            logger.info("数据库连接成功")
            self.db_success = True
            return True
            
        except Exception as e:
            self.db_success = False
            logger.error(f"数据库连接失败: {e}")
            return False

    def test_tushare_api(self):
        """测试Tushare API及可用功能"""
        if not self.config:
            logger.error("配置未加载，无法测试Tushare API")
            return False

        logger.info("开始测试Tushare API连接")

        try:
            import tushare as ts
            ts.set_token(self.config["tushare_token"])
            pro = ts.pro_api()

            logger.info("开始测试API功能可用性...")
            self._test_api_categories(pro)
                
            self.api_success = True
            return True

        except Exception as e:
            logger.error(f"Tushare API测试失败: {e}")
            self.api_success = False
            return False
            
    def _test_api_categories(self, pro):
        """测试不同类别的API功能"""
        total_apis = 0
        available_apis = 0
        
        for category, apis in TUSHARE_API_CATEGORIES.items():
            category_results = []
            
            logger.info(f"测试 {category} 类别下的API...")
                
            for api_info in apis:
                api_func = api_info["api"]
                api_name = api_info["name"]
                api_points = api_info["points"]
                total_apis += 1
                
                # 通过实际调用测试API可用性
                try:
                    # 通用参数：仅获取一条记录
                    kwargs = {"limit": 1}
                    
                    # 特殊API的处理
                    if api_func == "trade_cal":
                        kwargs = {"start_date": "20200101", "end_date": "20200110"}
                    elif api_func == "daily":
                        kwargs = {"ts_code": "000001.SZ", "start_date": "20200101", "end_date": "20200105"}
                    elif api_func == "weekly" or api_func == "monthly":
                        kwargs = {"ts_code": "000001.SZ", "start_date": "20200101", "end_date": "20200630"}
                    elif api_func == "income" or api_func == "balancesheet" or api_func == "cashflow":
                        kwargs = {"ts_code": "000001.SZ", "period": "20191231"}
                        
                    # 调用API
                    result = getattr(pro, api_func)(**kwargs)
                    
                    if result is not None and not result.empty:
                        status = "可用"
                        call_status = True
                        available_apis += 1
                    else:
                        status = "返回空数据"
                        call_status = False
                except Exception as e:
                    status = f"错误: {str(e)[:50]}..."
                    call_status = False
                
                # 添加到结果
                category_results.append({
                    "api": api_func,
                    "name": api_name,
                    "points_required": api_points,
                    "status": status,
                    "call_status": call_status
                })
                
                # 限制API调用频率，避免超过限制
                time.sleep(0.3)
            
            # 保存类别结果
            self.api_test_results[category] = category_results
            
        logger.info(f"API测试完成，共测试 {total_apis} 个API，其中 {available_apis} 个可用")

    def generate_api_report(self, output_dir="api_reports", report_format="json"):
        """生成API可用性报告并保存到指定文件夹"""
        # 确保输出目录存在
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        # 生成报告文件名
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        report_file = f"{output_dir}/tushare_api_report_{timestamp}.{report_format}"
        
        # 生成报告
        report = {
            "report_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "token_status": "有效" if self.api_success else "无效",
            "database_status": "连接成功" if self.db_success else "连接失败",
            "api_summary": {
                "total_categories": len(self.api_test_results),
                "total_apis": sum(len(apis) for apis in self.api_test_results.values()),
                "available_apis": sum(
                    sum(1 for api in apis if api["call_status"]) 
                    for apis in self.api_test_results.values()
                )
            },
            "api_categories": {}
        }
        
        # 填充API测试结果
        for category, apis in self.api_test_results.items():
            available_count = sum(1 for api in apis if api["call_status"])
            
            report["api_categories"][category] = {
                "name": category,
                "total_apis": len(apis),
                "available_apis": available_count,
                "apis": apis
            }
        
        # 保存报告
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
            
        print(f"\n✅ API可用性报告已保存至: {report_file}")
        return report_file
        
    def generate_text_summary(self):
        """生成简明的文本摘要"""
        if not self.api_test_results:
            return "未执行API测试"
            
        total_apis = sum(len(apis) for apis in self.api_test_results.values())
        available_apis = sum(
            sum(1 for api in apis if api["call_status"]) 
            for apis in self.api_test_results.values()
        )
        
        summary = [
            "=" * 60,
            "Tushare API 可用性摘要",
            "=" * 60,
            f"API总数: {total_apis}",
            f"可用API: {available_apis} ({available_apis/total_apis*100:.1f}%)",
            "-" * 60,
            "API类别摘要:",
        ]
        
        for category, apis in self.api_test_results.items():
            available_count = sum(1 for api in apis if api["call_status"])
            summary.append(f"  {category}: {available_count}/{len(apis)} 可用")
            
        summary.append("=" * 60)
        return "\n".join(summary)

    def run_full_test(self, generate_report=True, report_dir="api_reports"):
        """运行完整测试"""
        logger.info("开始运行连接测试工具")

        # 1. 加载配置
        if not self.load_config():
            return False

        # 2. 测试数据库连接
        db_success = self.test_database_connection()

        # 3. 测试Tushare API
        api_success = self.test_tushare_api()

        # 4. 总结
        logger.info(f"测试结果总结 - 数据库连接: {'成功' if db_success else '失败'}, Tushare API: {'成功' if api_success else '失败'}")

        # 5. 生成API报告
        if generate_report and self.api_test_results:
            report_file = self.generate_api_report(report_dir)
            print(self.generate_text_summary())

        return db_success and api_success

    def close_connection(self):
        """关闭数据库连接"""
        if self.connection:
            self.connection.close()
            logger.info("数据库连接已关闭")


def main():
    """主函数"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="数据库和Tushare API连接测试工具")
    parser.add_argument("--config", "-c", type=str, default="config.json", help="配置文件路径")
    parser.add_argument("--report-dir", "-d", type=str, default="api_reports", help="报告输出目录")
    parser.add_argument("--no-report", action="store_true", help="不生成报告文件")
    args = parser.parse_args()
    
    # 创建测试器
    tester = ConnectionTester(args.config)

    try:
        # 运行测试
        tester.run_full_test(
            generate_report=not args.no_report,
            report_dir=args.report_dir
        )

    except KeyboardInterrupt:
        print("\n👋 用户中断了测试")
    except Exception as e:
        print(f"\n💥 测试过程中发生错误: {e}")
    finally:
        tester.close_connection()


if __name__ == "__main__":
    main()