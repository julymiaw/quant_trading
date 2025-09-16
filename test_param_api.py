#!/usr/bin/env python3
"""
参数管理API测试脚本
测试参数的增删改查、智能搜索建议等功能
"""

import requests
import json
import uuid
from datetime import datetime

# API基础URL
BASE_URL = "http://localhost:5000"


class ParamManagementTester:
    def __init__(self):
        self.session = requests.Session()
        self.token = None
        self.test_param_name = f"test_param_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

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

    def test_get_params_list(self):
        """测试获取参数列表"""
        print("1. 测试获取参数列表...")
        try:
            response = self.session.get(
                f"{BASE_URL}/api/params", headers=self.get_headers()
            )

            if response.status_code == 200:
                result = response.json()
                params = result.get("params", [])
                print(f"✓ 获取参数列表成功，共 {len(params)} 个参数")

                # 显示前3个参数信息
                for i, param in enumerate(params[:3]):
                    print(
                        f"   参数 {i+1}: {param.get('creator_name')}.{param.get('param_name')} - {param.get('data_id')}"
                    )

                return True
            else:
                result = response.json()
                print(f"❌ 获取参数列表失败: {result.get('message')}")
                return False

        except Exception as e:
            print(f"❌ 获取参数列表异常: {e}")
            return False

    def test_create_param(self):
        """测试创建参数"""
        print("2. 测试创建参数...")
        try:
            param_data = {
                "param_name": self.test_param_name,
                "data_id": "daily.close",
                "param_type": "table",
                "pre_period": 10,
                "post_period": 0,
                "agg_func": "SMA",
            }

            response = self.session.post(
                f"{BASE_URL}/api/params", json=param_data, headers=self.get_headers()
            )

            if response.status_code == 201:
                result = response.json()
                print(f"✓ 参数创建成功: {result.get('message')}")
                return True
            else:
                result = response.json()
                print(f"❌ 参数创建失败: {result.get('message')}")
                return False

        except Exception as e:
            print(f"❌ 参数创建异常: {e}")
            return False

    def test_update_param(self):
        """测试更新参数"""
        print("3. 测试更新参数...")
        try:
            param_composite_id = f"system.{self.test_param_name}"
            update_data = {
                "param_name": self.test_param_name,
                "data_id": "daily.high",
                "param_type": "table",
                "pre_period": 15,
                "post_period": 0,
                "agg_func": "MAX",
            }

            response = self.session.put(
                f"{BASE_URL}/api/params/{param_composite_id}",
                json=update_data,
                headers=self.get_headers(),
            )

            if response.status_code == 200:
                result = response.json()
                print(f"✓ 参数更新成功: {result.get('message')}")
                return True
            else:
                result = response.json()
                print(f"❌ 参数更新失败: {result.get('message')}")
                return False

        except Exception as e:
            print(f"❌ 参数更新异常: {e}")
            return False

    def test_get_suggestions(self):
        """测试智能搜索建议"""
        print("4. 测试智能搜索建议...")
        try:
            # 测试表建议
            suggestion_data = {"node_type": "数据表", "input_text": "daily"}

            response = self.session.post(
                f"{BASE_URL}/api/suggestions",
                json=suggestion_data,
                headers=self.get_headers(),
            )

            if response.status_code == 200:
                result = response.json()
                suggestions = result.get("suggestions", [])
                print(f"✓ 表建议获取成功，共 {len(suggestions)} 个建议: {suggestions}")
            else:
                print(f"❌ 表建议获取失败")
                return False

            # 测试字段建议
            suggestion_data = {"node_type": "数据表", "input_text": "daily."}

            response = self.session.post(
                f"{BASE_URL}/api/suggestions",
                json=suggestion_data,
                headers=self.get_headers(),
            )

            if response.status_code == 200:
                result = response.json()
                suggestions = result.get("suggestions", [])
                print(f"✓ 字段建议获取成功，共 {len(suggestions)} 个建议")

                # 显示前5个字段
                for i, suggestion in enumerate(suggestions[:5]):
                    print(f"   字段 {i+1}: {suggestion}")
            else:
                print(f"❌ 字段建议获取失败")
                return False

            # 测试参数建议
            suggestion_data = {"node_type": "参数", "input_text": "system"}

            response = self.session.post(
                f"{BASE_URL}/api/suggestions",
                json=suggestion_data,
                headers=self.get_headers(),
            )

            if response.status_code == 200:
                result = response.json()
                suggestions = result.get("suggestions", [])
                print(f"✓ 参数建议获取成功，共 {len(suggestions)} 个建议")
                return True
            else:
                print(f"❌ 参数建议获取失败")
                return False

        except Exception as e:
            print(f"❌ 智能搜索建议异常: {e}")
            return False

    def test_create_duplicate_param(self):
        """测试创建重复参数"""
        print("5. 测试创建重复参数...")
        try:
            # 尝试创建已存在的参数
            param_data = {
                "param_name": "close",  # system用户已有的参数
                "data_id": "daily.close",
                "param_type": "table",
                "pre_period": 0,
                "post_period": 0,
                "agg_func": None,
            }

            response = self.session.post(
                f"{BASE_URL}/api/params", json=param_data, headers=self.get_headers()
            )

            if response.status_code == 400:
                result = response.json()
                print(f"✓ 重复参数创建正确被拒绝: {result.get('message')}")
                return True
            else:
                print(f"❌ 重复参数创建未被拒绝，状态码: {response.status_code}")
                return False

        except Exception as e:
            print(f"❌ 重复参数创建测试异常: {e}")
            return False

    def test_update_nonexistent_param(self):
        """测试更新不存在的参数"""
        print("6. 测试更新不存在的参数...")
        try:
            param_composite_id = "system.nonexistent_param"
            update_data = {
                "param_name": "nonexistent_param",
                "data_id": "daily.close",
                "param_type": "table",
                "pre_period": 0,
                "post_period": 0,
                "agg_func": None,
            }

            response = self.session.put(
                f"{BASE_URL}/api/params/{param_composite_id}",
                json=update_data,
                headers=self.get_headers(),
            )

            if response.status_code == 404:
                result = response.json()
                print(f"✓ 不存在参数更新正确被拒绝: {result.get('message')}")
                return True
            else:
                print(f"❌ 不存在参数更新未被拒绝，状态码: {response.status_code}")
                return False

        except Exception as e:
            print(f"❌ 更新不存在参数测试异常: {e}")
            return False

    def test_delete_param(self):
        """测试删除参数"""
        print("7. 测试删除参数...")
        try:
            param_composite_id = f"system.{self.test_param_name}"

            response = self.session.delete(
                f"{BASE_URL}/api/params/{param_composite_id}",
                headers=self.get_headers(),
            )

            if response.status_code == 200:
                result = response.json()
                print(f"✓ 参数删除成功: {result.get('message')}")
                return True
            else:
                result = response.json()
                print(f"❌ 参数删除失败: {result.get('message')}")
                return False

        except Exception as e:
            print(f"❌ 参数删除异常: {e}")
            return False

    def test_delete_nonexistent_param(self):
        """测试删除不存在的参数"""
        print("8. 测试删除不存在的参数...")
        try:
            param_composite_id = "system.nonexistent_param"

            response = self.session.delete(
                f"{BASE_URL}/api/params/{param_composite_id}",
                headers=self.get_headers(),
            )

            if response.status_code == 404:
                result = response.json()
                print(f"✓ 不存在参数删除正确被拒绝: {result.get('message')}")
                return True
            else:
                print(f"❌ 不存在参数删除未被拒绝，状态码: {response.status_code}")
                return False

        except Exception as e:
            print(f"❌ 删除不存在参数测试异常: {e}")
            return False

    def run_all_tests(self):
        """运行所有测试"""
        print("🚀 开始参数管理API测试...\n")

        # 首先设置认证
        if not self.setup_auth():
            print("❌ 认证失败，无法继续测试")
            return False

        test_results = []

        # 执行所有测试
        test_methods = [
            self.test_get_params_list,
            self.test_create_param,
            self.test_update_param,
            self.test_get_suggestions,
            self.test_create_duplicate_param,
            self.test_update_nonexistent_param,
            self.test_delete_param,
            self.test_delete_nonexistent_param,
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
            print("🎉 所有参数管理测试通过！")
        else:
            print("⚠️  部分测试失败，请检查API实现")

        return passed == total


if __name__ == "__main__":
    tester = ParamManagementTester()
    tester.run_all_tests()
