#!/usr/bin/env python3
"""
权限安全测试脚本
测试跨用户访问权限控制，确保数据隔离
"""

import requests
import json
import uuid
from datetime import datetime

# API基础URL
BASE_URL = "http://localhost:5000"


class SecurityTester:
    def __init__(self):
        self.session_user1 = requests.Session()
        self.session_user2 = requests.Session()
        self.token_user1 = None
        self.token_user2 = None
        self.user1_name = (
            f"security_test_user1_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )
        self.user2_name = (
            f"security_test_user2_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )
        self.test_password = "test123456"

    def setup_test_users(self):
        """创建测试用户"""
        print("🔧 设置测试用户...")

        try:
            # 创建用户1
            user1_data = {
                "user_name": self.user1_name,
                "password": self.test_password,
                "email": f"{self.user1_name}@test.com",
            }

            response = self.session_user1.post(
                f"{BASE_URL}/auth/register",
                json=user1_data,
                headers={"Content-Type": "application/json"},
            )

            if response.status_code == 201:
                print(f"✓ 用户1创建成功: {self.user1_name}")
            else:
                print(f"❌ 用户1创建失败")
                return False

            # 创建用户2
            user2_data = {
                "user_name": self.user2_name,
                "password": self.test_password,
                "email": f"{self.user2_name}@test.com",
            }

            response = self.session_user2.post(
                f"{BASE_URL}/auth/register",
                json=user2_data,
                headers={"Content-Type": "application/json"},
            )

            if response.status_code == 201:
                print(f"✓ 用户2创建成功: {self.user2_name}")
                return True
            else:
                print(f"❌ 用户2创建失败")
                return False

        except Exception as e:
            print(f"❌ 创建测试用户异常: {e}")
            return False

    def setup_auth(self):
        """为两个用户设置认证"""
        print("🔑 设置用户认证...")

        try:
            # 用户1登录
            login_data = {"user_name": self.user1_name, "password": self.test_password}

            response = self.session_user1.post(
                f"{BASE_URL}/auth/login",
                json=login_data,
                headers={"Content-Type": "application/json"},
            )

            if response.status_code == 200:
                result = response.json()
                self.token_user1 = result.get("token")
                print(f"✓ 用户1认证成功")
            else:
                print(f"❌ 用户1认证失败")
                return False

            # 用户2登录
            login_data = {"user_name": self.user2_name, "password": self.test_password}

            response = self.session_user2.post(
                f"{BASE_URL}/auth/login",
                json=login_data,
                headers={"Content-Type": "application/json"},
            )

            if response.status_code == 200:
                result = response.json()
                self.token_user2 = result.get("token")
                print(f"✓ 用户2认证成功")
                return True
            else:
                print(f"❌ 用户2认证失败")
                return False

        except Exception as e:
            print(f"❌ 用户认证异常: {e}")
            return False

    def get_headers_user1(self):
        """获取用户1请求头"""
        return {
            "Authorization": f"Bearer {self.token_user1}",
            "Content-Type": "application/json",
        }

    def get_headers_user2(self):
        """获取用户2请求头"""
        return {
            "Authorization": f"Bearer {self.token_user2}",
            "Content-Type": "application/json",
        }

    def test_cross_user_param_access(self):
        """测试跨用户参数访问"""
        print("1. 测试跨用户参数访问...")

        try:
            # 用户1创建一个参数
            param_name = "test_security_param"
            param_data = {
                "param_name": param_name,
                "data_id": "daily.close",
                "param_type": "table",
                "pre_period": 5,
                "post_period": 0,
                "agg_func": "SMA",
            }

            response = self.session_user1.post(
                f"{BASE_URL}/api/params",
                json=param_data,
                headers=self.get_headers_user1(),
            )

            if response.status_code != 201:
                print(f"❌ 用户1创建参数失败")
                return False

            print(f"✓ 用户1成功创建参数: {param_name}")

            # 用户2尝试访问用户1的参数
            param_composite_id = f"{self.user1_name}.{param_name}"

            response = self.session_user2.put(
                f"{BASE_URL}/api/params/{param_composite_id}",
                json=param_data,
                headers=self.get_headers_user2(),
            )

            if response.status_code == 403 or response.status_code == 404:
                print(f"✓ 用户2无法访问用户1的参数（权限控制正确）")
                return True
            else:
                print(
                    f"❌ 用户2可以访问用户1的参数（权限控制失败），状态码: {response.status_code}"
                )
                return False

        except Exception as e:
            print(f"❌ 跨用户参数访问测试异常: {e}")
            return False

    def test_cross_user_strategy_access(self):
        """测试跨用户策略访问"""
        print("2. 测试跨用户策略访问...")

        try:
            # 用户1创建一个策略
            strategy_name = "test_security_strategy"
            strategy_data = {
                "strategy_name": strategy_name,
                "public": False,  # 私有策略
                "scope_type": "single_stock",
                "scope_id": "000001.SZ",
                "benchmark_index": "000300.SH",
                "select_func": "def select_func(): pass",
                "position_count": 1,
                "rebalance_interval": 1,
                "buy_fee_rate": 0.0003,
                "sell_fee_rate": 0.0013,
                "strategy_desc": "安全测试策略",
            }

            response = self.session_user1.post(
                f"{BASE_URL}/api/strategies",
                json=strategy_data,
                headers=self.get_headers_user1(),
            )

            if response.status_code != 201:
                print(f"❌ 用户1创建策略失败")
                return False

            print(f"✓ 用户1成功创建私有策略: {strategy_name}")

            # 用户2尝试访问用户1的私有策略
            response = self.session_user2.get(
                f"{BASE_URL}/api/strategies/{self.user1_name}/{strategy_name}",
                headers=self.get_headers_user2(),
            )

            if response.status_code == 403 or response.status_code == 404:
                print(f"✓ 用户2无法访问用户1的私有策略（权限控制正确）")
                return True
            else:
                print(
                    f"❌ 用户2可以访问用户1的私有策略（权限控制失败），状态码: {response.status_code}"
                )
                return False

        except Exception as e:
            print(f"❌ 跨用户策略访问测试异常: {e}")
            return False

    def test_cross_user_indicator_access(self):
        """测试跨用户指标访问"""
        print("3. 测试跨用户指标访问...")

        try:
            # 用户1创建一个指标
            indicator_name = "test_security_indicator"
            indicator_data = {
                "indicator_name": indicator_name,
                "calculation_method": "def calculation_method(params): return 1",
                "description": "安全测试指标",
                "is_active": True,
            }

            response = self.session_user1.post(
                f"{BASE_URL}/api/indicators",
                json=indicator_data,
                headers=self.get_headers_user1(),
            )

            if response.status_code != 201:
                print(f"❌ 用户1创建指标失败")
                return False

            print(f"✓ 用户1成功创建指标: {indicator_name}")

            # 用户2尝试修改用户1的指标
            indicator_composite_id = f"{self.user1_name}.{indicator_name}"

            response = self.session_user2.put(
                f"{BASE_URL}/api/indicators/{indicator_composite_id}",
                json=indicator_data,
                headers=self.get_headers_user2(),
            )

            if response.status_code == 403 or response.status_code == 404:
                print(f"✓ 用户2无法修改用户1的指标（权限控制正确）")
                return True
            else:
                print(
                    f"❌ 用户2可以修改用户1的指标（权限控制失败），状态码: {response.status_code}"
                )
                return False

        except Exception as e:
            print(f"❌ 跨用户指标访问测试异常: {e}")
            return False

    def test_cross_user_message_access(self):
        """测试跨用户消息访问"""
        print("4. 测试跨用户消息访问...")

        try:
            # 获取用户1的消息列表
            response = self.session_user1.get(
                f"{BASE_URL}/api/messages", headers=self.get_headers_user1()
            )

            user1_messages = []
            if response.status_code == 200:
                result = response.json()
                user1_messages = result.get("messages", [])
                print(f"✓ 用户1有 {len(user1_messages)} 条消息")

            # 获取用户2的消息列表
            response = self.session_user2.get(
                f"{BASE_URL}/api/messages", headers=self.get_headers_user2()
            )

            user2_messages = []
            if response.status_code == 200:
                result = response.json()
                user2_messages = result.get("messages", [])
                print(f"✓ 用户2有 {len(user2_messages)} 条消息")

            # 检查是否有重叠的消息ID
            user1_message_ids = {msg.get("message_id") for msg in user1_messages}
            user2_message_ids = {msg.get("message_id") for msg in user2_messages}

            overlap = user1_message_ids.intersection(user2_message_ids)

            if len(overlap) == 0:
                print(f"✓ 用户消息完全隔离（权限控制正确）")
                return True
            else:
                print(f"❌ 发现重叠的消息ID: {overlap}（权限控制失败）")
                return False

        except Exception as e:
            print(f"❌ 跨用户消息访问测试异常: {e}")
            return False

    def test_cross_user_backtest_access(self):
        """测试跨用户回测报告访问"""
        print("5. 测试跨用户回测报告访问...")

        try:
            # 获取用户1的回测列表
            response = self.session_user1.get(
                f"{BASE_URL}/api/backtests", headers=self.get_headers_user1()
            )

            user1_backtests = []
            if response.status_code == 200:
                result = response.json()
                user1_backtests = result.get("backtests", [])
                print(f"✓ 用户1有 {len(user1_backtests)} 个回测报告")

            # 获取用户2的回测列表
            response = self.session_user2.get(
                f"{BASE_URL}/api/backtests", headers=self.get_headers_user2()
            )

            user2_backtests = []
            if response.status_code == 200:
                result = response.json()
                user2_backtests = result.get("backtests", [])
                print(f"✓ 用户2有 {len(user2_backtests)} 个回测报告")

            # 检查是否有重叠的报告ID
            user1_report_ids = {bt.get("report_id") for bt in user1_backtests}
            user2_report_ids = {bt.get("report_id") for bt in user2_backtests}

            overlap = user1_report_ids.intersection(user2_report_ids)

            if len(overlap) == 0:
                print(f"✓ 用户回测报告完全隔离（权限控制正确）")

                # 如果用户1有回测报告，测试用户2是否能直接访问
                if user1_backtests:
                    report_id = user1_backtests[0].get("report_id")
                    response = self.session_user2.get(
                        f"{BASE_URL}/api/backtest/report/{report_id}",
                        headers=self.get_headers_user2(),
                    )

                    if response.status_code == 403 or response.status_code == 404:
                        print(f"✓ 用户2无法直接访问用户1的回测报告（权限控制正确）")
                        return True
                    else:
                        print(f"❌ 用户2可以直接访问用户1的回测报告（权限控制失败）")
                        return False

                return True
            else:
                print(f"❌ 发现重叠的回测报告ID: {overlap}（权限控制失败）")
                return False

        except Exception as e:
            print(f"❌ 跨用户回测访问测试异常: {e}")
            return False

    def test_invalid_token_access(self):
        """测试无效token访问"""
        print("6. 测试无效token访问...")

        try:
            # 使用无效token访问API
            invalid_headers = {
                "Authorization": "Bearer invalid_token_12345",
                "Content-Type": "application/json",
            }

            response = requests.get(f"{BASE_URL}/api/params", headers=invalid_headers)

            if response.status_code == 401:
                print(f"✓ 无效token正确被拒绝")
                return True
            else:
                print(f"❌ 无效token未被拒绝，状态码: {response.status_code}")
                return False

        except Exception as e:
            print(f"❌ 无效token访问测试异常: {e}")
            return False

    def cleanup_test_data(self):
        """清理测试数据"""
        print("🧹 清理测试数据...")

        try:
            # 清理用户1创建的数据
            self.session_user1.delete(
                f"{BASE_URL}/api/params/{self.user1_name}.test_security_param",
                headers=self.get_headers_user1(),
            )

            self.session_user1.delete(
                f"{BASE_URL}/api/strategies/{self.user1_name}/test_security_strategy",
                headers=self.get_headers_user1(),
            )

            self.session_user1.delete(
                f"{BASE_URL}/api/indicators/{self.user1_name}.test_security_indicator",
                headers=self.get_headers_user1(),
            )

            print("✓ 测试数据清理完成")

        except Exception as e:
            print(f"⚠️ 清理测试数据时出现异常: {e}")

    def run_all_tests(self):
        """运行所有安全测试"""
        print("🚀 开始权限安全测试...\n")

        # 设置测试环境
        if not self.setup_test_users():
            print("❌ 无法创建测试用户，终止测试")
            return False

        if not self.setup_auth():
            print("❌ 无法设置用户认证，终止测试")
            return False

        test_results = []

        # 执行所有测试
        test_methods = [
            self.test_cross_user_param_access,
            self.test_cross_user_strategy_access,
            self.test_cross_user_indicator_access,
            self.test_cross_user_message_access,
            self.test_cross_user_backtest_access,
            self.test_invalid_token_access,
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

        # 清理测试数据
        self.cleanup_test_data()

        # 统计结果
        passed = sum(test_results)
        total = len(test_results)

        print("=" * 50)
        print(f"🛡️ 安全测试结果统计:")
        print(f"   总测试数: {total}")
        print(f"   通过数: {passed}")
        print(f"   失败数: {total - passed}")
        print(f"   通过率: {passed/total*100:.1f}%")

        if passed == total:
            print("🎉 所有安全测试通过！系统权限控制完善。")
        else:
            print("⚠️  发现安全漏洞，请立即检查权限控制实现！")

        return passed == total


if __name__ == "__main__":
    tester = SecurityTester()
    tester.run_all_tests()
