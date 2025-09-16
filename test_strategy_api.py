#!/usr/bin/env python3
"""
策略管理API测试脚本
测试策略的增删改查、复制、参数关系管理等功能
"""

import requests
import json
import uuid
from datetime import datetime

# API基础URL
BASE_URL = "http://localhost:5000"


class StrategyManagementTester:
    def __init__(self):
        self.session = requests.Session()
        self.token = None
        self.test_strategy_name = (
            f"test_strategy_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )

    def setup_auth(self):
        """设置认证，登录获取token"""
        print("🔑 设置认证...")
        try:
            # 使用现有的system用户登录
            login_data = {"user_name": "system", "password": "******"}

            response = self.session.post(
                f"{BASE_URL}/auth/login",
                json=login_data,
                headers={"Content-Type": "application/json"},
            )

            if response.status_code == 200:
                result = response.json()
                self.token = result.get("token")
                print(f"✓ 认证成功，获得token")
                return True
            else:
                print(f"❌ 认证失败: {response.status_code}")
                return False

        except Exception as e:
            print(f"❌ 认证异常: {e}")
            return False

    def get_headers(self):
        """获取请求头"""
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    def test_get_strategies_list(self):
        """测试获取策略列表"""
        print("1. 测试获取策略列表...")
        try:
            response = self.session.get(
                f"{BASE_URL}/api/strategies", headers=self.get_headers()
            )

            if response.status_code == 200:
                result = response.json()
                strategies = result.get("strategies", [])
                print(f"✓ 获取策略列表成功，共 {len(strategies)} 个策略")

                # 显示前3个策略信息
                for i, strategy in enumerate(strategies[:3]):
                    print(
                        f"   策略 {i+1}: {strategy.get('creator_name')}.{strategy.get('strategy_name')} - {strategy.get('scope_type')}"
                    )

                return True
            else:
                result = response.json()
                print(f"❌ 获取策略列表失败: {result.get('message')}")
                return False

        except Exception as e:
            print(f"❌ 获取策略列表异常: {e}")
            return False

    def test_create_strategy(self):
        """测试创建策略"""
        print("2. 测试创建策略...")
        try:
            strategy_data = {
                "strategy_name": self.test_strategy_name,
                "public": True,
                "scope_type": "single_stock",
                "scope_id": "000002.SZ",
                "benchmark_index": "000300.SH",
                "select_func": "def select_func(candidates, params, position_count, current_holdings, date, context=None):\n    # 测试选股函数\n    return candidates[:1]",
                "risk_control_func": "def risk_control_func(current_holdings, params, date, context=None):\n    # 测试风控函数\n    return current_holdings",
                "position_count": 1,
                "rebalance_interval": 1,
                "buy_fee_rate": 0.0003,
                "sell_fee_rate": 0.0013,
                "strategy_desc": "这是一个测试策略",
            }

            response = self.session.post(
                f"{BASE_URL}/api/strategies",
                json=strategy_data,
                headers=self.get_headers(),
            )

            if response.status_code == 201:
                result = response.json()
                print(f"✓ 策略创建成功: {result.get('message')}")
                return True
            else:
                result = response.json()
                print(f"❌ 策略创建失败: {result.get('message')}")
                return False

        except Exception as e:
            print(f"❌ 策略创建异常: {e}")
            return False

    def test_get_strategy_detail(self):
        """测试获取策略详情"""
        print("3. 测试获取策略详情...")
        try:
            response = self.session.get(
                f"{BASE_URL}/api/strategies/system/{self.test_strategy_name}",
                headers=self.get_headers(),
            )

            if response.status_code == 200:
                result = response.json()
                strategy = result.get("strategy")
                print(f"✓ 获取策略详情成功:")
                print(f"   策略名称: {strategy.get('strategy_name')}")
                print(f"   作用范围: {strategy.get('scope_type')}")
                print(f"   基准指数: {strategy.get('benchmark_index')}")
                print(f"   是否公开: {strategy.get('public')}")
                return True
            else:
                result = response.json()
                print(f"❌ 获取策略详情失败: {result.get('message')}")
                return False

        except Exception as e:
            print(f"❌ 获取策略详情异常: {e}")
            return False

    def test_update_strategy(self):
        """测试更新策略"""
        print("4. 测试更新策略...")
        try:
            update_data = {
                "strategy_name": self.test_strategy_name,
                "public": False,  # 改为私有
                "scope_type": "single_stock",
                "scope_id": "000003.SZ",  # 换个股票
                "benchmark_index": "000001.SH",  # 换个基准
                "select_func": "def select_func(candidates, params, position_count, current_holdings, date, context=None):\n    # 更新后的选股函数\n    return candidates[:1]",
                "risk_control_func": "def risk_control_func(current_holdings, params, date, context=None):\n    # 更新后的风控函数\n    return current_holdings",
                "position_count": 1,
                "rebalance_interval": 5,  # 改变调仓间隔
                "buy_fee_rate": 0.0005,  # 改变费率
                "sell_fee_rate": 0.0015,
                "strategy_desc": "这是更新后的测试策略",
            }

            response = self.session.put(
                f"{BASE_URL}/api/strategies/system/{self.test_strategy_name}",
                json=update_data,
                headers=self.get_headers(),
            )

            if response.status_code == 200:
                result = response.json()
                print(f"✓ 策略更新成功: {result.get('message')}")
                return True
            else:
                result = response.json()
                print(f"❌ 策略更新失败: {result.get('message')}")
                return False

        except Exception as e:
            print(f"❌ 策略更新异常: {e}")
            return False

    def test_copy_strategy(self):
        """测试复制策略"""
        print("5. 测试复制策略...")
        try:
            copy_data = {"new_strategy_name": f"{self.test_strategy_name}_copy"}

            response = self.session.post(
                f"{BASE_URL}/api/strategies/system/{self.test_strategy_name}/copy",
                json=copy_data,
                headers=self.get_headers(),
            )

            if response.status_code == 201:
                result = response.json()
                print(f"✓ 策略复制成功: {result.get('message')}")
                return True
            else:
                result = response.json()
                print(f"❌ 策略复制失败: {result.get('message')}")
                return False

        except Exception as e:
            print(f"❌ 策略复制异常: {e}")
            return False

    def test_get_strategy_params(self):
        """测试获取策略参数列表"""
        print("6. 测试获取策略参数列表...")
        try:
            response = self.session.get(
                f"{BASE_URL}/api/strategies/system/{self.test_strategy_name}/params",
                headers=self.get_headers(),
            )

            if response.status_code == 200:
                result = response.json()
                params = result.get("params", [])
                print(f"✓ 获取策略参数列表成功，共 {len(params)} 个参数")

                # 显示参数信息
                for i, param in enumerate(params[:3]):
                    print(
                        f"   参数 {i+1}: {param.get('param_creator_name')}.{param.get('param_name')}"
                    )

                return True
            else:
                result = response.json()
                print(f"❌ 获取策略参数列表失败: {result.get('message')}")
                return False

        except Exception as e:
            print(f"❌ 获取策略参数列表异常: {e}")
            return False

    def test_add_strategy_param(self):
        """测试添加策略参数关系"""
        print("7. 测试添加策略参数关系...")
        try:
            param_data = {"param_creator_name": "system", "param_name": "close"}

            response = self.session.post(
                f"{BASE_URL}/api/strategies/system/{self.test_strategy_name}/params",
                json=param_data,
                headers=self.get_headers(),
            )

            if response.status_code == 201:
                result = response.json()
                print(f"✓ 添加策略参数关系成功: {result.get('message')}")
                return True
            else:
                result = response.json()
                print(f"❌ 添加策略参数关系失败: {result.get('message')}")
                return False

        except Exception as e:
            print(f"❌ 添加策略参数关系异常: {e}")
            return False

    def test_remove_strategy_param(self):
        """测试删除策略参数关系"""
        print("8. 测试删除策略参数关系...")
        try:
            response = self.session.delete(
                f"{BASE_URL}/api/strategies/system/{self.test_strategy_name}/params/system/close",
                headers=self.get_headers(),
            )

            if response.status_code == 200:
                result = response.json()
                print(f"✓ 删除策略参数关系成功: {result.get('message')}")
                return True
            else:
                result = response.json()
                print(f"❌ 删除策略参数关系失败: {result.get('message')}")
                return False

        except Exception as e:
            print(f"❌ 删除策略参数关系异常: {e}")
            return False

    def test_create_duplicate_strategy(self):
        """测试创建重复策略"""
        print("9. 测试创建重复策略...")
        try:
            # 尝试创建已存在的策略
            strategy_data = {
                "strategy_name": "小市值策略",  # system用户已有的策略
                "public": True,
                "scope_type": "all",
                "benchmark_index": "000300.SH",
                "select_func": "def select_func(): pass",
                "position_count": 3,
                "rebalance_interval": 5,
                "buy_fee_rate": 0.0003,
                "sell_fee_rate": 0.0013,
                "strategy_desc": "重复策略测试",
            }

            response = self.session.post(
                f"{BASE_URL}/api/strategies",
                json=strategy_data,
                headers=self.get_headers(),
            )

            if response.status_code == 400:
                result = response.json()
                print(f"✓ 重复策略创建正确被拒绝: {result.get('message')}")
                return True
            else:
                print(f"❌ 重复策略创建未被拒绝，状态码: {response.status_code}")
                return False

        except Exception as e:
            print(f"❌ 重复策略创建测试异常: {e}")
            return False

    def test_delete_strategy(self):
        """测试删除策略"""
        print("10. 测试删除策略...")
        try:
            # 先删除复制的策略
            response = self.session.delete(
                f"{BASE_URL}/api/strategies/system/{self.test_strategy_name}_copy",
                headers=self.get_headers(),
            )

            if response.status_code == 200:
                result = response.json()
                print(f"✓ 删除复制策略成功: {result.get('message')}")

            # 再删除原策略
            response = self.session.delete(
                f"{BASE_URL}/api/strategies/system/{self.test_strategy_name}",
                headers=self.get_headers(),
            )

            if response.status_code == 200:
                result = response.json()
                print(f"✓ 删除测试策略成功: {result.get('message')}")
                return True
            else:
                result = response.json()
                print(f"❌ 删除测试策略失败: {result.get('message')}")
                return False

        except Exception as e:
            print(f"❌ 删除策略异常: {e}")
            return False

    def run_all_tests(self):
        """运行所有测试"""
        print("🚀 开始策略管理API测试...\n")

        # 首先设置认证
        if not self.setup_auth():
            print("❌ 认证失败，无法继续测试")
            return False

        test_results = []

        # 执行所有测试
        test_methods = [
            self.test_get_strategies_list,
            self.test_create_strategy,
            self.test_get_strategy_detail,
            self.test_update_strategy,
            self.test_copy_strategy,
            self.test_get_strategy_params,
            self.test_add_strategy_param,
            self.test_remove_strategy_param,
            self.test_create_duplicate_strategy,
            self.test_delete_strategy,
        ]

        for test_method in test_methods:
            try:
                result = test_method()
                test_results.append(result)
                print()  # 添加空行分隔
            except Exception as e:
                print(f"❌ 测试方法 {test_method.__name__} 执行失败: {e}")
                test_results.append(False)
                print()

        # 统计结果
        passed = sum(test_results)
        total = len(test_results)

        print("=" * 50)
        print(f"📊 测试结果统计:")
        print(f"   总测试数: {total}")
        print(f"   通过数: {passed}")
        print(f"   失败数: {total - passed}")
        print(f"   通过率: {passed/total*100:.1f}%")

        if passed == total:
            print("🎉 所有策略管理测试通过！")
        else:
            print("⚠️  部分测试失败，请检查API实现")

        return passed == total


if __name__ == "__main__":
    tester = StrategyManagementTester()
    tester.run_all_tests()
