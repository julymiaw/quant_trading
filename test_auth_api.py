#!/usr/bin/env python3
"""
用户认证API测试脚本
测试登录、注册、用户信息获取等认证相关功能
"""

import requests
import json
import uuid
from datetime import datetime

# API基础URL
BASE_URL = "http://localhost:5000"


class UserAuthTester:
    def __init__(self):
        self.session = requests.Session()
        self.test_user_name = f"test_user_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.test_password = "test123456"
        self.test_email = f"{self.test_user_name}@test.com"
        self.token = None

    def test_health_check(self):
        """测试健康检查"""
        print("1. 测试健康检查...")
        try:
            response = self.session.get(f"{BASE_URL}/health")
            if response.status_code == 200:
                print("✓ 健康检查通过")
                return True
            else:
                print(f"❌ 健康检查失败: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ 健康检查异常: {e}")
            return False

    def test_register(self):
        """测试用户注册"""
        print("2. 测试用户注册...")
        try:
            register_data = {
                "user_name": self.test_user_name,
                "password": self.test_password,
                "email": self.test_email,
                "phone": "13800138000",
            }

            response = self.session.post(
                f"{BASE_URL}/auth/register",
                json=register_data,
                headers={"Content-Type": "application/json"},
            )

            if response.status_code == 201:
                result = response.json()
                print(f"✓ 用户注册成功: {result.get('message')}")
                return True
            else:
                result = response.json()
                print(f"❌ 用户注册失败: {result.get('message')}")
                return False

        except Exception as e:
            print(f"❌ 用户注册异常: {e}")
            return False

    def test_login(self):
        """测试用户登录"""
        print("3. 测试用户登录...")
        try:
            login_data = {
                "user_name": self.test_user_name,
                "password": self.test_password,
            }

            response = self.session.post(
                f"{BASE_URL}/auth/login",
                json=login_data,
                headers={"Content-Type": "application/json"},
            )

            if response.status_code == 200:
                result = response.json()
                # API返回格式: {"code": 200, "data": {"token": "...", "userInfo": {...}}}
                data = result.get("data", {})
                self.token = data.get("token")
                print(f"✓ 登录成功，获得token: {self.token[:20]}...")
                return True
            else:
                result = response.json()
                print(f"❌ 登录失败: {result.get('message')}")
                return False

        except Exception as e:
            print(f"❌ 登录异常: {e}")
            return False

    def test_get_user_info(self):
        """测试获取用户信息"""
        print("4. 测试获取用户信息...")
        try:
            if not self.token:
                print("❌ 没有有效token，跳过测试")
                return False

            headers = {"Authorization": f"Bearer {self.token}"}
            response = self.session.get(f"{BASE_URL}/user/info", headers=headers)

            if response.status_code == 200:
                result = response.json()
                # API返回格式: {"code": 200, "data": {...}, "message": "..."}
                user_info = result.get("data", {})
                print(f"✓ 获取用户信息成功:")
                print(f"   用户名: {user_info.get('user_name')}")
                print(f"   邮箱: {user_info.get('user_email')}")
                print(f"   角色: {user_info.get('user_role')}")
                print(f"   状态: {user_info.get('user_status')}")
                return True
            else:
                result = response.json()
                print(f"❌ 获取用户信息失败: {result.get('message')}")
                return False

        except Exception as e:
            print(f"❌ 获取用户信息异常: {e}")
            return False

    def test_invalid_login(self):
        """测试无效登录"""
        print("5. 测试无效登录...")
        try:
            # 测试错误密码
            login_data = {
                "user_name": self.test_user_name,
                "password": "wrong_password",
            }

            response = self.session.post(
                f"{BASE_URL}/auth/login",
                json=login_data,
                headers={"Content-Type": "application/json"},
            )

            if response.status_code == 401:
                result = response.json()
                print(f"✓ 错误密码正确被拒绝: {result.get('message')}")
            else:
                print(f"❌ 错误密码未被拒绝，状态码: {response.status_code}")
                return False

            # 测试不存在的用户
            login_data = {
                "user_name": "nonexistent_user",
                "password": self.test_password,
            }

            response = self.session.post(
                f"{BASE_URL}/auth/login",
                json=login_data,
                headers={"Content-Type": "application/json"},
            )

            if response.status_code == 401:
                result = response.json()
                print(f"✓ 不存在用户正确被拒绝: {result.get('message')}")
                return True
            else:
                print(f"❌ 不存在用户未被拒绝，状态码: {response.status_code}")
                return False

        except Exception as e:
            print(f"❌ 无效登录测试异常: {e}")
            return False

    def test_duplicate_registration(self):
        """测试重复注册"""
        print("6. 测试重复注册...")
        try:
            register_data = {
                "user_name": self.test_user_name,
                "password": self.test_password,
                "email": self.test_email,
                "phone": "13800138001",
            }

            response = self.session.post(
                f"{BASE_URL}/auth/register",
                json=register_data,
                headers={"Content-Type": "application/json"},
            )

            if response.status_code == 400:
                result = response.json()
                print(f"✓ 重复注册正确被拒绝: {result.get('message')}")
                return True
            else:
                print(f"❌ 重复注册未被拒绝，状态码: {response.status_code}")
                return False

        except Exception as e:
            print(f"❌ 重复注册测试异常: {e}")
            return False

    def test_unauthorized_access(self):
        """测试未授权访问"""
        print("7. 测试未授权访问...")
        try:
            # 不提供token访问需要认证的接口
            response = self.session.get(f"{BASE_URL}/user/info")

            if response.status_code == 401:
                print("✓ 未授权访问正确被拒绝")
            else:
                print(f"❌ 未授权访问未被拒绝，状态码: {response.status_code}")
                return False

            # 提供无效token
            headers = {"Authorization": "Bearer invalid_token"}
            response = self.session.get(f"{BASE_URL}/user/info", headers=headers)

            if response.status_code == 401:
                print("✓ 无效token正确被拒绝")
                return True
            else:
                print(f"❌ 无效token未被拒绝，状态码: {response.status_code}")
                return False

        except Exception as e:
            print(f"❌ 未授权访问测试异常: {e}")
            return False

    def run_all_tests(self):
        """运行所有测试"""
        print("🚀 开始用户认证API测试...\n")

        test_results = []

        # 执行所有测试
        test_methods = [
            self.test_health_check,
            self.test_register,
            self.test_login,
            self.test_get_user_info,
            self.test_invalid_login,
            self.test_duplicate_registration,
            self.test_unauthorized_access,
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
            print("🎉 所有用户认证测试通过！")
        else:
            print("⚠️  部分测试失败，请检查API实现")

        return passed == total


if __name__ == "__main__":
    tester = UserAuthTester()
    tester.run_all_tests()
