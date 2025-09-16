#!/usr/bin/env python3
"""
消息系统API测试脚本
测试消息的获取、标记已读、删除等功能
"""

import requests
import json
import uuid
from datetime import datetime
import time

# API基础URL
BASE_URL = "http://localhost:5000"


class MessageSystemTester:
    def __init__(self):
        self.session = requests.Session()
        self.token = None

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

    def test_get_messages_list(self):
        """测试获取消息列表"""
        print("1. 测试获取消息列表...")
        try:
            response = self.session.get(
                f"{BASE_URL}/api/messages", headers=self.get_headers()
            )

            if response.status_code == 200:
                result = response.json()
                messages = result.get("messages", [])
                pagination = result.get("pagination", {})

                print(f"✓ 获取消息列表成功，共 {pagination.get('total', 0)} 条消息")
                print(
                    f"   当前页: {pagination.get('page', 1)}/{pagination.get('total_pages', 1)}"
                )

                # 显示前3条消息信息
                for i, message in enumerate(messages[:3]):
                    status_text = "已读" if message.get("status") == "read" else "未读"
                    print(
                        f"   消息 {i+1}: {message.get('title')} - {message.get('message_type')} [{status_text}]"
                    )

                return True
            else:
                result = response.json()
                print(f"❌ 获取消息列表失败: {result.get('message')}")
                return False

        except Exception as e:
            print(f"❌ 获取消息列表异常: {e}")
            return False

    def test_get_messages_with_pagination(self):
        """测试分页获取消息"""
        print("2. 测试分页获取消息...")
        try:
            # 测试第一页
            response = self.session.get(
                f"{BASE_URL}/api/messages?page=1&page_size=3",
                headers=self.get_headers(),
            )

            if response.status_code == 200:
                result = response.json()
                messages = result.get("messages", [])
                pagination = result.get("pagination", {})

                print(f"✓ 获取分页消息成功，第1页显示 {len(messages)} 条消息")
                print(
                    f"   总计: {pagination.get('total', 0)} 条，共 {pagination.get('total_pages', 1)} 页"
                )
                return True
            else:
                result = response.json()
                print(f"❌ 获取分页消息失败: {result.get('message')}")
                return False

        except Exception as e:
            print(f"❌ 获取分页消息异常: {e}")
            return False

    def test_get_messages_by_type(self):
        """测试按类型过滤消息"""
        print("3. 测试按类型过滤消息...")
        try:
            # 测试获取回测完成消息
            response = self.session.get(
                f"{BASE_URL}/api/messages?message_type=backtest_complete",
                headers=self.get_headers(),
            )

            if response.status_code == 200:
                result = response.json()
                messages = result.get("messages", [])

                print(f"✓ 获取回测完成消息成功，共 {len(messages)} 条")

                # 验证所有消息都是指定类型
                all_correct_type = all(
                    msg.get("message_type") == "backtest_complete" for msg in messages
                )
                if all_correct_type:
                    print("   所有消息类型正确")
                else:
                    print("   ⚠️ 存在错误类型的消息")

                return True
            else:
                result = response.json()
                print(f"❌ 按类型获取消息失败: {result.get('message')}")
                return False

        except Exception as e:
            print(f"❌ 按类型获取消息异常: {e}")
            return False

    def test_get_messages_by_status(self):
        """测试按状态过滤消息"""
        print("4. 测试按状态过滤消息...")
        try:
            # 测试获取未读消息
            response = self.session.get(
                f"{BASE_URL}/api/messages?status=unread", headers=self.get_headers()
            )

            if response.status_code == 200:
                result = response.json()
                messages = result.get("messages", [])

                print(f"✓ 获取未读消息成功，共 {len(messages)} 条")

                # 验证所有消息都是未读状态
                all_unread = all(msg.get("status") == "unread" for msg in messages)
                if all_unread:
                    print("   所有消息状态正确")
                else:
                    print("   ⚠️ 存在错误状态的消息")

                return True
            else:
                result = response.json()
                print(f"❌ 按状态获取消息失败: {result.get('message')}")
                return False

        except Exception as e:
            print(f"❌ 按状态获取消息异常: {e}")
            return False

    def test_mark_message_read(self):
        """测试标记消息为已读"""
        print("5. 测试标记消息为已读...")
        try:
            # 先获取一个未读消息
            response = self.session.get(
                f"{BASE_URL}/api/messages?status=unread&page_size=1",
                headers=self.get_headers(),
            )

            if response.status_code != 200:
                print("❌ 无法获取未读消息进行测试")
                return False

            result = response.json()
            messages = result.get("messages", [])

            if not messages:
                print("⚠️ 没有未读消息可供测试")
                return True  # 没有消息不算失败

            message_id = messages[0].get("message_id")

            # 标记为已读
            response = self.session.put(
                f"{BASE_URL}/api/messages/{message_id}/read", headers=self.get_headers()
            )

            if response.status_code == 200:
                result = response.json()
                print(f"✓ 标记消息为已读成功: {result.get('message')}")
                return True
            else:
                result = response.json()
                print(f"❌ 标记消息为已读失败: {result.get('message')}")
                return False

        except Exception as e:
            print(f"❌ 标记消息为已读异常: {e}")
            return False

    def test_mark_already_read_message(self):
        """测试标记已读消息为已读"""
        print("6. 测试标记已读消息为已读...")
        try:
            # 先获取一个已读消息
            response = self.session.get(
                f"{BASE_URL}/api/messages?status=read&page_size=1",
                headers=self.get_headers(),
            )

            if response.status_code != 200:
                print("❌ 无法获取已读消息进行测试")
                return False

            result = response.json()
            messages = result.get("messages", [])

            if not messages:
                print("⚠️ 没有已读消息可供测试")
                return True

            message_id = messages[0].get("message_id")

            # 再次标记为已读
            response = self.session.put(
                f"{BASE_URL}/api/messages/{message_id}/read", headers=self.get_headers()
            )

            if response.status_code == 200:
                result = response.json()
                print(f"✓ 重复标记已读消息处理正确: {result.get('message')}")
                return True
            else:
                result = response.json()
                print(f"❌ 重复标记已读消息失败: {result.get('message')}")
                return False

        except Exception as e:
            print(f"❌ 重复标记已读消息异常: {e}")
            return False

    def test_delete_message(self):
        """测试删除消息"""
        print("7. 测试删除消息...")
        try:
            # 先获取最新的消息
            response = self.session.get(
                f"{BASE_URL}/api/messages?page_size=1&page=1",
                headers=self.get_headers(),
            )

            if response.status_code != 200:
                print("❌ 无法获取消息进行删除测试")
                return False

            result = response.json()
            messages = result.get("messages", [])

            if not messages:
                print("⚠️ 没有消息可供删除测试")
                return True

            message_id = messages[0].get("message_id")
            message_title = messages[0].get("title")

            # 删除消息
            response = self.session.delete(
                f"{BASE_URL}/api/messages/{message_id}", headers=self.get_headers()
            )

            if response.status_code == 200:
                result = response.json()
                print(f"✓ 删除消息成功: {message_title}")
                return True
            else:
                result = response.json()
                print(f"❌ 删除消息失败: {result.get('message')}")
                return False

        except Exception as e:
            print(f"❌ 删除消息异常: {e}")
            return False

    def test_delete_nonexistent_message(self):
        """测试删除不存在的消息"""
        print("8. 测试删除不存在的消息...")
        try:
            fake_message_id = str(uuid.uuid4())

            response = self.session.delete(
                f"{BASE_URL}/api/messages/{fake_message_id}", headers=self.get_headers()
            )

            if response.status_code == 404:
                result = response.json()
                print(f"✓ 删除不存在消息正确被拒绝: {result.get('message')}")
                return True
            else:
                print(f"❌ 删除不存在消息未被拒绝，状态码: {response.status_code}")
                return False

        except Exception as e:
            print(f"❌ 删除不存在消息测试异常: {e}")
            return False

    def test_mark_nonexistent_message_read(self):
        """测试标记不存在的消息为已读"""
        print("9. 测试标记不存在的消息为已读...")
        try:
            fake_message_id = str(uuid.uuid4())

            response = self.session.put(
                f"{BASE_URL}/api/messages/{fake_message_id}/read",
                headers=self.get_headers(),
            )

            if response.status_code == 404:
                result = response.json()
                print(f"✓ 标记不存在消息正确被拒绝: {result.get('message')}")
                return True
            else:
                print(f"❌ 标记不存在消息未被拒绝，状态码: {response.status_code}")
                return False

        except Exception as e:
            print(f"❌ 标记不存在消息测试异常: {e}")
            return False

    def run_all_tests(self):
        """运行所有测试"""
        print("🚀 开始消息系统API测试...\n")

        # 首先设置认证
        if not self.setup_auth():
            print("❌ 认证失败，无法继续测试")
            return False

        test_results = []

        # 执行所有测试
        test_methods = [
            self.test_get_messages_list,
            self.test_get_messages_with_pagination,
            self.test_get_messages_by_type,
            self.test_get_messages_by_status,
            self.test_mark_message_read,
            self.test_mark_already_read_message,
            self.test_delete_message,
            self.test_delete_nonexistent_message,
            self.test_mark_nonexistent_message_read,
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
            print("🎉 所有消息系统测试通过！")
        else:
            print("⚠️  部分测试失败，请检查API实现")

        return passed == total


if __name__ == "__main__":
    tester = MessageSystemTester()
    tester.run_all_tests()
