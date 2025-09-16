#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
端到端回测流程测试脚本
测试：数据准备 -> 回测执行 -> 图表生成 -> 数据库存储 -> API返回
"""

import os
import sys
import json
import uuid
import time
import requests
import pandas as pd
from datetime import datetime, timedelta

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 导入我们的模块
from prepare_strategy_data import DataPreparer
from backtest_engine import BacktestEngine


class BacktestFlowTester:
    def __init__(self):
        self.base_url = "http://localhost:5000"
        self.token = None
        self.user_info = None

    def login(self, username="system", password="123456"):
        """登录获取token"""
        try:
            response = requests.post(
                f"{self.base_url}/auth/login",
                json={"username": username, "password": password},
            )

            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    self.token = data["data"]["token"]
                    self.user_info = data["data"]["user"]
                    print(f"✅ 登录成功，用户: {self.user_info['user_name']}")
                    return True
                else:
                    print(f"❌ 登录失败: {data.get('message')}")
                    return False
            else:
                print(f"❌ 登录请求失败，状态码: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ 登录过程中出错: {e}")
            return False

    def test_data_preparation(self):
        """测试数据准备模块"""
        print("\n🔄 测试数据准备模块...")

        try:
            preparer = DataPreparer("config.json")

            # 使用双均线策略进行测试
            strategy_name = "system.双均线策略"
            start_date = "2024-01-01"
            end_date = "2024-01-31"

            print(f"   准备策略数据: {strategy_name}")
            print(f"   时间范围: {start_date} 到 {end_date}")

            prepared_data = preparer.prepare_data(strategy_name, start_date, end_date)

            # 验证准备的数据
            required_keys = [
                "dataframe",
                "select_func",
                "risk_control_func",
                "param_columns",
            ]
            for key in required_keys:
                if key not in prepared_data:
                    print(f"❌ 缺少必要字段: {key}")
                    return False

            df = prepared_data["dataframe"]
            print(f"   ✅ 数据准备完成，数据形状: {df.shape}")
            print(f"   ✅ 参数列: {prepared_data['param_columns']}")

            return prepared_data

        except Exception as e:
            print(f"❌ 数据准备失败: {e}")
            return None

    def test_backtest_engine(self, prepared_data):
        """测试回测引擎"""
        print("\n🔄 测试回测引擎...")

        try:
            engine = BacktestEngine(
                initial_fund=100000.0, buy_fee_rate=0.0003, sell_fee_rate=0.0013
            )

            # 运行回测
            config = engine.load_data_direct(prepared_data)
            results = engine.run_backtest(config, print_log=False)

            print(f"   ✅ 回测完成")
            print(f"   初始资金: {results['initial_value']:,.2f}")
            print(f"   最终资金: {results['final_value']:,.2f}")
            print(f"   总收益率: {results['total_return']:.2%}")
            print(f"   夏普比率: {results['analysis']['sharpe_ratio']:.4f}")
            print(f"   最大回撤: {results['analysis']['max_drawdown']:.2%}")

            # 生成图表
            print("   🔄 生成图表...")
            chart_base64 = engine.generate_matplotlib_plot()
            print(f"   ✅ Matplotlib图表生成完成 (长度: {len(chart_base64)})")

            # 尝试生成plotly图表
            try:
                plotly_data = engine.generate_plotly_json("测试策略回测结果")
                print(
                    f"   ✅ Plotly图表生成完成 (数据曲线: {len(plotly_data.get('data', []))})"
                )
            except Exception as plotly_e:
                print(f"   ⚠️ Plotly图表生成失败: {plotly_e}")
                plotly_data = None

            return {
                "results": results,
                "chart_base64": chart_base64,
                "plotly_data": plotly_data,
                "engine": engine,
            }

        except Exception as e:
            print(f"❌ 回测引擎测试失败: {e}")
            return None

    def test_api_integration(self):
        """测试API集成"""
        print("\n🔄 测试后端API集成...")

        if not self.token:
            print("❌ 需要先登录")
            return False

        try:
            # 发起回测请求
            headers = {"Authorization": f"Bearer {self.token}"}
            backtest_request = {
                "strategy_creator": "system",
                "strategy_name": "双均线策略",
                "start_date": "2024-01-01",
                "end_date": "2024-01-31",
                "initial_fund": 100000,
            }

            print("   发起回测请求...")
            response = requests.post(
                f"{self.base_url}/api/backtest/start",
                json=backtest_request,
                headers=headers,
            )

            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    report_id = data["report_id"]
                    print(f"   ✅ 回测任务已启动，报告ID: {report_id}")

                    # 等待回测完成
                    print("   ⏳ 等待回测完成...")
                    for i in range(30):  # 最多等待30秒
                        time.sleep(1)

                        # 检查回测状态
                        report_response = requests.get(
                            f"{self.base_url}/api/backtest/report/{report_id}",
                            headers=headers,
                        )

                        if report_response.status_code == 200:
                            report_data = report_response.json()
                            if report_data.get("success"):
                                report = report_data["data"]
                                if report["report_status"] == "completed":
                                    print(
                                        f"   ✅ 回测完成! 总收益率: {report['total_return']:.2%}"
                                    )
                                    print(
                                        f"   ✅ 图表数据长度: {len(report.get('chart_data', ''))}"
                                    )

                                    if report.get("plotly_chart_data"):
                                        plotly_curves = len(
                                            report["plotly_chart_data"].get("data", [])
                                        )
                                        print(
                                            f"   ✅ Plotly图表包含 {plotly_curves} 条数据曲线"
                                        )

                                    return True
                                elif report["report_status"] == "failed":
                                    print(
                                        f"   ❌ 回测失败: {report.get('error_message', '未知错误')}"
                                    )
                                    return False

                        print(f"   ⏳ 等待中... ({i+1}/30)")

                    print("   ⚠️ 回测超时")
                    return False
                else:
                    print(f"   ❌ 启动回测失败: {data.get('message')}")
                    return False
            else:
                print(f"   ❌ API请求失败，状态码: {response.status_code}")
                return False

        except Exception as e:
            print(f"❌ API集成测试失败: {e}")
            return False

    def run_full_test(self):
        """运行完整的端到端测试"""
        print("🚀 开始端到端回测流程测试")
        print("=" * 60)

        # 1. 登录
        if not self.login():
            return False

        # 2. 测试数据准备
        prepared_data = self.test_data_preparation()
        if not prepared_data:
            return False

        # 3. 测试回测引擎
        backtest_results = self.test_backtest_engine(prepared_data)
        if not backtest_results:
            return False

        # 4. 测试API集成
        api_success = self.test_api_integration()
        if not api_success:
            return False

        print("\n" + "=" * 60)
        print("🎉 端到端测试全部通过!")
        print("✅ 数据准备模块正常")
        print("✅ 回测引擎正常")
        print("✅ 图表生成正常")
        print("✅ API集成正常")
        print("✅ 数据库存储正常")

        return True


def main():
    """主函数"""
    tester = BacktestFlowTester()
    success = tester.run_full_test()

    if success:
        print("\n🎯 集成测试成功! 系统已准备就绪。")
        print("💡 现在可以:")
        print("   1. 启动前端: cd frontend && npm run dev")
        print("   2. 启动后端: python app.py")
        print("   3. 在前端发起回测并查看结果")
    else:
        print("\n💥 集成测试失败，请检查错误信息并修复问题。")

    return success


if __name__ == "__main__":
    main()
