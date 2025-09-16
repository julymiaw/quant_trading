#!/usr/bin/env python3
"""
测试回测API的脚本
"""

import requests
import json
import time

BASE_URL = "http://localhost:5000"


def test_login():
    """测试登录功能"""
    login_data = {"userName": "test_user", "password": "test_password"}

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


def test_start_backtest(token):
    """测试启动回测功能"""
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    backtest_data = {
        "strategy_creator": "system",
        "strategy_name": "MACD策略",
        "start_date": "2023-01-01",
        "end_date": "2023-12-31",
        "initial_capital": 100000,
        "commission_rate": 0.0003,
        "slippage_rate": 0.0001,
        "stock_code": "000001.SZ",
    }

    response = requests.post(
        f"{BASE_URL}/api/backtest/start", json=backtest_data, headers=headers
    )

    if response.status_code == 200:
        result = response.json()
        if result.get("success"):
            print("✓ 回测启动成功")
            print(f"  回测ID: {result.get('report_id', 'Unknown')}")
            return True
        else:
            print(f"✗ 回测启动失败: {result.get('message', '未知错误')}")
            return False
    else:
        print(f"✗ 回测请求失败: {response.status_code} - {response.text}")
        return False


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


def main():
    print("🚀 开始测试回测API流程...")

    # 1. 登录
    print("\n1. 测试登录...")
    token = test_login()
    if not token:
        print("❌ 登录失败，无法继续测试")
        return

    # 2. 启动回测
    print("\n2. 测试启动回测...")
    backtest_success = test_start_backtest(token)
    if not backtest_success:
        print("❌ 回测启动失败")
        return

    # 3. 等待一段时间让回测任务执行
    print("\n3. 等待回测任务执行（15秒）...")
    for i in range(15, 0, -1):
        print(f"  剩余 {i} 秒...", end="\r")
        time.sleep(1)
    print("                    ")  # 清除进度显示

    # 4. 检查消息
    print("\n4. 测试获取消息...")
    test_get_messages(token)

    # 5. 检查回测列表
    print("\n5. 测试获取回测列表...")
    test_get_backtests(token)

    print("\n🎉 测试完成！")


if __name__ == "__main__":
    main()
