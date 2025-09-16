#!/usr/bin/env python3
"""
指标管理API测试脚本
测试指标的增删改查、复制、参数关系管理等功能
"""

import requests
import json
import uuid
from datetime import datetime

# API基础URL
BASE_URL = "http://localhost:5000"


class IndicatorManagementTester:
    def __init__(self):
        self.session = requests.Session()
        self.token = None
        self.test_indicator_name = (
            f"test_indicator_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
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

    def test_get_indicators_list(self):
        """测试获取指标列表"""
        print("1. 测试获取指标列表...")
        try:
            response = self.session.get(
                f"{BASE_URL}/api/indicators", headers=self.get_headers()
            )

            if response.status_code == 200:
                result = response.json()
                indicators = result.get("indicators", [])
                print(f"✓ 获取指标列表成功，共 {len(indicators)} 个指标")

                # 显示前3个指标信息
                for i, indicator in enumerate(indicators[:3]):
                    print(
                        f"   指标 {i+1}: {indicator.get('creator_name')}.{indicator.get('indicator_name')} - {'启用' if indicator.get('is_active') else '禁用'}"
                    )

                return True
            else:
                result = response.json()
                print(f"❌ 获取指标列表失败: {result.get('message')}")
                return False

        except Exception as e:
            print(f"❌ 获取指标列表异常: {e}")
            return False

    def test_create_indicator(self):
        """测试创建指标"""
        print("2. 测试创建指标...")
        try:
            indicator_data = {
                "indicator_name": self.test_indicator_name,
                "calculation_method": "def calculation_method(params):\n    # 测试指标计算方法\n    return params['system.close'] * 1.1",
                "description": "这是一个测试指标，计算收盘价的1.1倍",
                "is_active": True,
            }

            response = self.session.post(
                f"{BASE_URL}/api/indicators",
                json=indicator_data,
                headers=self.get_headers(),
            )

            if response.status_code == 201:
                result = response.json()
                print(f"✓ 指标创建成功: {result.get('message')}")
                return True
            else:
                result = response.json()
                print(f"❌ 指标创建失败: {result.get('message')}")
                return False

        except Exception as e:
            print(f"❌ 指标创建异常: {e}")
            return False

    def test_update_indicator(self):
        """测试更新指标"""
        print("3. 测试更新指标...")
        try:
            indicator_composite_id = f"system.{self.test_indicator_name}"
            update_data = {
                "indicator_name": self.test_indicator_name,
                "calculation_method": "def calculation_method(params):\n    # 更新后的指标计算方法\n    return params['system.close'] * 1.2",
                "description": "这是更新后的测试指标，计算收盘价的1.2倍",
                "is_active": False,  # 改为禁用状态
            }

            response = self.session.put(
                f"{BASE_URL}/api/indicators/{indicator_composite_id}",
                json=update_data,
                headers=self.get_headers(),
            )

            if response.status_code == 200:
                result = response.json()
                print(f"✓ 指标更新成功: {result.get('message')}")
                return True
            else:
                result = response.json()
                print(f"❌ 指标更新失败: {result.get('message')}")
                return False

        except Exception as e:
            print(f"❌ 指标更新异常: {e}")
            return False

    def test_toggle_indicator_status(self):
        """测试切换指标状态"""
        print("4. 测试切换指标状态...")
        try:
            indicator_composite_id = f"system.{self.test_indicator_name}"

            response = self.session.put(
                f"{BASE_URL}/api/indicators/{indicator_composite_id}/toggle-status",
                headers=self.get_headers(),
            )

            if response.status_code == 200:
                result = response.json()
                print(f"✓ 指标状态切换成功: {result.get('message')}")
                return True
            else:
                result = response.json()
                print(f"❌ 指标状态切换失败: {result.get('message')}")
                return False

        except Exception as e:
            print(f"❌ 指标状态切换异常: {e}")
            return False

    def test_copy_indicator(self):
        """测试复制指标"""
        print("5. 测试复制指标...")
        try:
            indicator_composite_id = f"system.{self.test_indicator_name}"
            copy_data = {"new_indicator_name": f"{self.test_indicator_name}_copy"}

            response = self.session.post(
                f"{BASE_URL}/api/indicators/{indicator_composite_id}/copy",
                json=copy_data,
                headers=self.get_headers(),
            )

            if response.status_code == 201:
                result = response.json()
                print(f"✓ 指标复制成功: {result.get('message')}")
                return True
            else:
                result = response.json()
                print(f"❌ 指标复制失败: {result.get('message')}")
                return False

        except Exception as e:
            print(f"❌ 指标复制异常: {e}")
            return False

    def test_get_indicator_param_relations(self):
        """测试获取指标参数关系列表"""
        print("6. 测试获取指标参数关系列表...")
        try:
            response = self.session.get(
                f"{BASE_URL}/api/indicator-param-relations", headers=self.get_headers()
            )

            if response.status_code == 200:
                result = response.json()
                relations = result.get("relations", [])
                print(f"✓ 获取指标参数关系列表成功，共 {len(relations)} 个关系")

                # 显示前3个关系信息
                for i, relation in enumerate(relations[:3]):
                    print(
                        f"   关系 {i+1}: {relation.get('indicator_creator_name')}.{relation.get('indicator_name')} -> {relation.get('param_creator_name')}.{relation.get('param_name')}"
                    )

                return True
            else:
                result = response.json()
                print(f"❌ 获取指标参数关系列表失败: {result.get('message')}")
                return False

        except Exception as e:
            print(f"❌ 获取指标参数关系列表异常: {e}")
            return False

    def test_create_indicator_param_relation(self):
        """测试创建指标参数关系"""
        print("7. 测试创建指标参数关系...")
        try:
            relation_data = {
                "indicator_creator_name": "system",
                "indicator_name": self.test_indicator_name,
                "param_creator_name": "system",
                "param_name": "close",
            }

            response = self.session.post(
                f"{BASE_URL}/api/indicator-param-relations",
                json=relation_data,
                headers=self.get_headers(),
            )

            if response.status_code == 201:
                result = response.json()
                print(f"✓ 创建指标参数关系成功: {result.get('message')}")
                return True
            else:
                result = response.json()
                print(f"❌ 创建指标参数关系失败: {result.get('message')}")
                return False

        except Exception as e:
            print(f"❌ 创建指标参数关系异常: {e}")
            return False

    def test_delete_indicator_param_relation(self):
        """测试删除指标参数关系"""
        print("8. 测试删除指标参数关系...")
        try:
            relation_id = f"system.{self.test_indicator_name}.system.close"

            response = self.session.delete(
                f"{BASE_URL}/api/indicator-param-relations/{relation_id}",
                headers=self.get_headers(),
            )

            if response.status_code == 200:
                result = response.json()
                print(f"✓ 删除指标参数关系成功: {result.get('message')}")
                return True
            else:
                result = response.json()
                print(f"❌ 删除指标参数关系失败: {result.get('message')}")
                return False

        except Exception as e:
            print(f"❌ 删除指标参数关系异常: {e}")
            return False

    def test_create_duplicate_indicator(self):
        """测试创建重复指标"""
        print("9. 测试创建重复指标...")
        try:
            # 尝试创建已存在的指标
            indicator_data = {
                "indicator_name": "MACD",  # system用户已有的指标
                "calculation_method": "def calculation_method(params): return 0",
                "description": "重复指标测试",
                "is_active": True,
            }

            response = self.session.post(
                f"{BASE_URL}/api/indicators",
                json=indicator_data,
                headers=self.get_headers(),
            )

            if response.status_code == 400:
                result = response.json()
                print(f"✓ 重复指标创建正确被拒绝: {result.get('message')}")
                return True
            else:
                print(f"❌ 重复指标创建未被拒绝，状态码: {response.status_code}")
                return False

        except Exception as e:
            print(f"❌ 重复指标创建测试异常: {e}")
            return False

    def test_delete_indicator(self):
        """测试删除指标"""
        print("10. 测试删除指标...")
        try:
            # 先删除复制的指标
            indicator_composite_id = f"system.{self.test_indicator_name}_copy"
            response = self.session.delete(
                f"{BASE_URL}/api/indicators/{indicator_composite_id}",
                headers=self.get_headers(),
            )

            if response.status_code == 200:
                result = response.json()
                print(f"✓ 删除复制指标成功: {result.get('message')}")

            # 再删除原指标
            indicator_composite_id = f"system.{self.test_indicator_name}"
            response = self.session.delete(
                f"{BASE_URL}/api/indicators/{indicator_composite_id}",
                headers=self.get_headers(),
            )

            if response.status_code == 200:
                result = response.json()
                print(f"✓ 删除测试指标成功: {result.get('message')}")
                return True
            else:
                result = response.json()
                print(f"❌ 删除测试指标失败: {result.get('message')}")
                return False

        except Exception as e:
            print(f"❌ 删除指标异常: {e}")
            return False

    def run_all_tests(self):
        """运行所有测试"""
        print("🚀 开始指标管理API测试...\n")

        # 首先设置认证
        if not self.setup_auth():
            print("❌ 认证失败，无法继续测试")
            return False

        test_results = []

        # 执行所有测试
        test_methods = [
            self.test_get_indicators_list,
            self.test_create_indicator,
            self.test_update_indicator,
            self.test_toggle_indicator_status,
            self.test_copy_indicator,
            self.test_get_indicator_param_relations,
            self.test_create_indicator_param_relation,
            self.test_delete_indicator_param_relation,
            self.test_create_duplicate_indicator,
            self.test_delete_indicator,
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
            print("🎉 所有指标管理测试通过！")
        else:
            print("⚠️  部分测试失败，请检查API实现")

        return passed == total


if __name__ == "__main__":
    tester = IndicatorManagementTester()
    tester.run_all_tests()
