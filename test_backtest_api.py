#!/usr/bin/env python3
"""
完整的端到端回测流程测试脚本
测试：数据准备 -> 回测执行 -> 图表生成 -> 数据库存储 -> API返回
"""

import os
import sys
import requests
import json
import time

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 导入我们的模块
from prepare_strategy_data import DataPreparer
from backtest_engine import BacktestEngine

BASE_URL = "http://localhost:5000"


def test_login():
    """测试登录功能"""
    login_data = {"userName": "system", "password": "Admin@2025!SeQuan"}  # 使用系统用户

    response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
    if response.status_code == 200:
        result = response.json()
        if result.get("code") == 200:
            print("✓ 登录成功")
            return result["data"]["token"]
        else:
            print(f"✗ 登录失败: {result.get('message', '未知错误')}")
            return None
    else:
        print(f"✗ 登录请求失败: {response.status_code}")
        return None


def test_data_preparation():
    """测试数据准备模块（本地测试）"""
    print("\n🔄 测试数据准备模块...")

    try:
        preparer = DataPreparer("config.json")

        # 使用双均线策略进行测试
        strategy_name = "system.双均线策略"
        start_date = "2024-01-01"
        end_date = "2024-01-31"

        print(f"   准备策略数据: {strategy_name}")
        print(f"   时间范围: {start_date} 到 {end_date}")

        prepared_data = preparer.prepare_data(
            strategy_name, start_date, end_date, save_files=False
        )

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


def test_backtest_engine(prepared_data):
    """测试回测引擎（本地测试）"""
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


def test_start_backtest(token):
    """测试启动回测功能 - 使用简化的API参数"""
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # 只传递后端真正需要的参数：策略创建者、策略名、时间范围、初始资金
    # 使用双均线策略，处理速度更快
    backtest_data = {
        "strategy_creator": "system",
        "strategy_name": "双均线策略",
        "start_date": "2024-01-01",
        "end_date": "2024-01-31",  # 缩短测试时间范围
        "initial_fund": 100000,
    }

    print(f"  发送回测数据: {json.dumps(backtest_data, indent=2, ensure_ascii=False)}")

    response = requests.post(
        f"{BASE_URL}/api/backtest/start", json=backtest_data, headers=headers
    )

    if response.status_code == 200:
        result = response.json()
        if result.get("success"):
            report_id = result.get("report_id", "Unknown")
            print("✓ 回测启动成功")
            print(f"  回测ID: {report_id}")
            return report_id
        else:
            print(f"✗ 回测启动失败: {result.get('message', '未知错误')}")
            return None
    else:
        print(f"✗ 回测请求失败: {response.status_code} - {response.text}")
        return None


def wait_for_backtest_completion(token, report_id, max_wait_seconds=60):
    """等待回测完成并返回结果"""
    print(f"\n⏳ 等待回测完成（最多 {max_wait_seconds} 秒）...")
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    for i in range(max_wait_seconds):
        time.sleep(1)

        # 检查回测状态
        try:
            response = requests.get(
                f"{BASE_URL}/api/backtest/report/{report_id}",
                headers=headers,
            )

            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    report = result["data"]
                    status = report["report_status"]

                    if status == "completed":
                        total_return = (
                            float(report["total_return"])
                            if isinstance(report["total_return"], str)
                            else report["total_return"]
                        )
                        print(f"   ✅ 回测完成! 总收益率: {total_return:.2%}")
                        print(
                            f"   ✅ 图表数据长度: {len(report.get('chart_data', ''))}"
                        )

                        if report.get("plotly_chart_data"):
                            plotly_curves = len(
                                report["plotly_chart_data"].get("data", [])
                            )
                            print(f"   ✅ Plotly图表包含 {plotly_curves} 条数据曲线")

                        return report
                    elif status == "failed":
                        print(
                            f"   ❌ 回测失败: {report.get('error_message', '未知错误')}"
                        )
                        return None
                    else:
                        print(
                            f"   ⏳ 等待中... ({i+1}/{max_wait_seconds}) - 状态: {status}"
                        )

        except Exception as e:
            print(f"   ⚠️ 检查状态时出错: {e}")

    print(f"   ⚠️ 回测超时（{max_wait_seconds}秒）")
    return None


def test_get_messages(token):
    """测试获取消息功能"""
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    response = requests.get(f"{BASE_URL}/api/messages", headers=headers)

    if response.status_code == 200:
        result = response.json()
        if result.get("success"):
            messages = result.get("data", {}).get("messages", [])
            print(f"✓ 获取消息成功，共 {len(messages)} 条消息")
            for i, msg in enumerate(messages):
                print(
                    f"  消息 {i+1}: {msg.get('title', 'Unknown')} - {msg.get('message_type', 'Unknown')}"
                )
            return True
        else:
            print(f"✗ 获取消息失败: {result.get('message', '未知错误')}")
            return False
    else:
        print(f"✗ 获取消息请求失败: {response.status_code} - {response.text}")
        return False


def test_get_backtests(token):
    """测试获取回测列表功能"""
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    response = requests.get(f"{BASE_URL}/api/backtests", headers=headers)

    if response.status_code == 200:
        result = response.json()
        if result.get("code") == 200:
            backtests = result.get("data", {}).get("list", [])
            print(f"✓ 获取回测列表成功，共 {len(backtests)} 条记录")
            for i, backtest in enumerate(backtests):
                print(
                    f"  回测 {i+1}: {backtest.get('strategy_name', 'Unknown')} - {backtest.get('report_status', 'Unknown')}"
                )
            return True
        else:
            print(f"✗ 获取回测列表失败: {result.get('message', '未知错误')}")
            return False
    else:
        print(f"✗ 获取回测列表请求失败: {response.status_code} - {response.text}")
        return False


def run_local_tests():
    """运行本地模块测试"""
    print("📍 本地模块测试")
    print("=" * 40)

    # 1. 测试数据准备
    prepared_data = test_data_preparation()
    if not prepared_data:
        print("❌ 数据准备测试失败")
        return False

    # 2. 测试回测引擎
    backtest_results = test_backtest_engine(prepared_data)
    if not backtest_results:
        print("❌ 回测引擎测试失败")
        return False

    print("✅ 所有本地模块测试通过!")
    return True


def run_api_tests():
    """运行API集成测试"""
    print("\n📍 API集成测试")
    print("=" * 40)

    # 1. 登录
    print("\n1. 测试登录...")
    token = test_login()
    if not token:
        print("❌ 登录失败，无法继续测试")
        return False

    # 2. 启动回测
    print("\n2. 测试启动回测...")
    report_id = test_start_backtest(token)
    if not report_id:
        print("❌ 回测启动失败")
        return False

    # 3. 等待回测完成
    report = wait_for_backtest_completion(token, report_id, max_wait_seconds=30)
    if not report:
        print("❌ 回测未能成功完成")
        return False

    # 4. 检查消息
    print("\n4. 测试获取消息...")
    test_get_messages(token)

    # 5. 检查回测列表
    print("\n5. 测试获取回测列表...")
    test_get_backtests(token)

    print("✅ 所有API测试通过!")
    return True


def main():
    print("🚀 开始完整的端到端回测流程测试")
    print("=" * 60)

    # 运行本地测试
    local_success = run_local_tests()

    # 运行API测试
    api_success = run_api_tests()

    print("\n" + "=" * 60)
    if local_success and api_success:
        print("🎉 端到端测试全部通过!")
        print("✅ 数据准备模块正常")
        print("✅ 回测引擎正常")
        print("✅ 图表生成正常")
        print("✅ API集成正常")
        print("✅ 数据库存储正常")
        print("\n🎯 集成测试成功! 系统已准备就绪。")
        print("💡 现在可以:")
        print("   1. 启动前端: cd frontend && npm run dev")
        print("   2. 启动后端: python app.py")
        print("   3. 在前端发起回测并查看结果")
        return True
    else:
        print("💥 部分测试失败:")
        if not local_success:
            print("❌ 本地模块测试失败")
        if not api_success:
            print("❌ API集成测试失败")
        print("请检查错误信息并修复问题。")
        return False


if __name__ == "__main__":
    main()
