#!/usr/bin/env python3
"""
性能和压力测试脚本
测试API在高并发情况下的性能表现
"""

import requests
import json
import time
import threading
import statistics
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# API基础URL
BASE_URL = "http://localhost:5000"


class PerformanceTester:
    def __init__(self):
        self.token = None
        self.results = {
            "response_times": [],
            "success_count": 0,
            "error_count": 0,
            "errors": [],
        }

    def setup_auth(self):
        """设置认证，登录获取token"""
        print("🔑 设置认证...")
        try:
            # 使用现有的system用户登录
            login_data = {"user_name": "system", "password": "******"}

            response = requests.post(
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

    def single_api_request(self, url, method="GET", data=None):
        """发送单个API请求并记录性能"""
        start_time = time.time()

        try:
            if method == "GET":
                response = requests.get(url, headers=self.get_headers())
            elif method == "POST":
                response = requests.post(url, json=data, headers=self.get_headers())

            end_time = time.time()
            response_time = (end_time - start_time) * 1000  # 转换为毫秒

            self.results["response_times"].append(response_time)

            if response.status_code == 200:
                self.results["success_count"] += 1
                return True, response_time
            else:
                self.results["error_count"] += 1
                self.results["errors"].append(f"Status: {response.status_code}")
                return False, response_time

        except Exception as e:
            end_time = time.time()
            response_time = (end_time - start_time) * 1000
            self.results["response_times"].append(response_time)
            self.results["error_count"] += 1
            self.results["errors"].append(str(e))
            return False, response_time

    def test_concurrent_requests(
        self, url, num_requests, num_threads, method="GET", data=None
    ):
        """测试并发请求性能"""
        print(f"🏃‍♂️ 发起 {num_requests} 个并发请求 (使用 {num_threads} 个线程)...")

        # 重置结果
        self.results = {
            "response_times": [],
            "success_count": 0,
            "error_count": 0,
            "errors": [],
        }

        start_time = time.time()

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = []

            for i in range(num_requests):
                future = executor.submit(self.single_api_request, url, method, data)
                futures.append(future)

            # 等待所有请求完成
            for future in as_completed(futures):
                future.result()

        end_time = time.time()
        total_time = end_time - start_time

        return total_time

    def test_health_check_performance(self):
        """测试健康检查API性能"""
        print("1. 测试健康检查API性能...")

        try:
            total_time = self.test_concurrent_requests(
                f"{BASE_URL}/health", num_requests=100, num_threads=10
            )

            self.print_performance_stats("健康检查API", total_time)
            return True

        except Exception as e:
            print(f"❌ 健康检查性能测试异常: {e}")
            return False

    def test_params_list_performance(self):
        """测试参数列表API性能"""
        print("2. 测试参数列表API性能...")

        try:
            total_time = self.test_concurrent_requests(
                f"{BASE_URL}/api/params", num_requests=50, num_threads=10
            )

            self.print_performance_stats("参数列表API", total_time)
            return True

        except Exception as e:
            print(f"❌ 参数列表性能测试异常: {e}")
            return False

    def test_strategies_list_performance(self):
        """测试策略列表API性能"""
        print("3. 测试策略列表API性能...")

        try:
            total_time = self.test_concurrent_requests(
                f"{BASE_URL}/api/strategies", num_requests=50, num_threads=10
            )

            self.print_performance_stats("策略列表API", total_time)
            return True

        except Exception as e:
            print(f"❌ 策略列表性能测试异常: {e}")
            return False

    def test_indicators_list_performance(self):
        """测试指标列表API性能"""
        print("4. 测试指标列表API性能...")

        try:
            total_time = self.test_concurrent_requests(
                f"{BASE_URL}/api/indicators", num_requests=50, num_threads=10
            )

            self.print_performance_stats("指标列表API", total_time)
            return True

        except Exception as e:
            print(f"❌ 指标列表性能测试异常: {e}")
            return False

    def test_messages_list_performance(self):
        """测试消息列表API性能"""
        print("5. 测试消息列表API性能...")

        try:
            total_time = self.test_concurrent_requests(
                f"{BASE_URL}/api/messages", num_requests=30, num_threads=5
            )

            self.print_performance_stats("消息列表API", total_time)
            return True

        except Exception as e:
            print(f"❌ 消息列表性能测试异常: {e}")
            return False

    def test_login_performance(self):
        """测试登录API性能"""
        print("6. 测试登录API性能...")

        try:
            login_data = {"user_name": "system", "password": "******"}

            total_time = self.test_concurrent_requests(
                f"{BASE_URL}/auth/login",
                num_requests=20,
                num_threads=5,
                method="POST",
                data=login_data,
            )

            self.print_performance_stats("登录API", total_time)
            return True

        except Exception as e:
            print(f"❌ 登录性能测试异常: {e}")
            return False

    def test_suggestions_performance(self):
        """测试智能搜索建议API性能"""
        print("7. 测试智能搜索建议API性能...")

        try:
            suggestion_data = {"node_type": "数据表", "input_text": "daily"}

            total_time = self.test_concurrent_requests(
                f"{BASE_URL}/api/suggestions",
                num_requests=30,
                num_threads=5,
                method="POST",
                data=suggestion_data,
            )

            self.print_performance_stats("智能搜索建议API", total_time)
            return True

        except Exception as e:
            print(f"❌ 智能搜索建议性能测试异常: {e}")
            return False

    def print_performance_stats(self, api_name, total_time):
        """打印性能统计信息"""
        if not self.results["response_times"]:
            print(f"❌ {api_name} - 没有收集到响应时间数据")
            return

        avg_response_time = statistics.mean(self.results["response_times"])
        min_response_time = min(self.results["response_times"])
        max_response_time = max(self.results["response_times"])
        median_response_time = statistics.median(self.results["response_times"])

        success_rate = (
            self.results["success_count"]
            / (self.results["success_count"] + self.results["error_count"])
        ) * 100

        requests_per_second = (
            self.results["success_count"] + self.results["error_count"]
        ) / total_time

        print(f"✓ {api_name} 性能统计:")
        print(
            f"   总请求数: {self.results['success_count'] + self.results['error_count']}"
        )
        print(f"   成功请求: {self.results['success_count']}")
        print(f"   失败请求: {self.results['error_count']}")
        print(f"   成功率: {success_rate:.1f}%")
        print(f"   总耗时: {total_time:.2f}秒")
        print(f"   请求/秒: {requests_per_second:.2f}")
        print(f"   平均响应时间: {avg_response_time:.2f}ms")
        print(f"   最小响应时间: {min_response_time:.2f}ms")
        print(f"   最大响应时间: {max_response_time:.2f}ms")
        print(f"   中位响应时间: {median_response_time:.2f}ms")

        if self.results["errors"]:
            print(f"   错误样例: {self.results['errors'][:3]}")

    def test_memory_leak(self):
        """测试内存泄漏（长时间连续请求）"""
        print("8. 测试内存泄漏（长时间连续请求）...")

        try:
            print("   发起1000个连续请求，监测性能变化...")

            first_batch_times = []
            last_batch_times = []

            # 第一批100个请求
            for i in range(100):
                success, response_time = self.single_api_request(f"{BASE_URL}/health")
                first_batch_times.append(response_time)
                if i % 20 == 0:
                    print(f"     进度: {i}/1000")

            # 中间800个请求
            for i in range(100, 900):
                self.single_api_request(f"{BASE_URL}/health")
                if i % 100 == 0:
                    print(f"     进度: {i}/1000")

            # 最后100个请求
            for i in range(900, 1000):
                success, response_time = self.single_api_request(f"{BASE_URL}/health")
                last_batch_times.append(response_time)
                if i % 20 == 0:
                    print(f"     进度: {i}/1000")

            # 比较性能变化
            first_avg = statistics.mean(first_batch_times)
            last_avg = statistics.mean(last_batch_times)

            performance_change = ((last_avg - first_avg) / first_avg) * 100

            print(f"✓ 内存泄漏测试完成:")
            print(f"   前100个请求平均响应时间: {first_avg:.2f}ms")
            print(f"   后100个请求平均响应时间: {last_avg:.2f}ms")
            print(f"   性能变化: {performance_change:+.1f}%")

            if abs(performance_change) < 50:  # 性能变化小于50%认为正常
                print(f"   ✓ 性能变化在可接受范围内")
                return True
            else:
                print(f"   ⚠️ 性能变化较大，可能存在内存泄漏")
                return False

        except Exception as e:
            print(f"❌ 内存泄漏测试异常: {e}")
            return False

    def run_all_tests(self):
        """运行所有性能测试"""
        print("🚀 开始性能和压力测试...\n")

        # 首先设置认证
        if not self.setup_auth():
            print("❌ 认证失败，无法继续测试")
            return False

        test_results = []

        # 执行所有测试
        test_methods = [
            self.test_health_check_performance,
            self.test_params_list_performance,
            self.test_strategies_list_performance,
            self.test_indicators_list_performance,
            self.test_messages_list_performance,
            self.test_login_performance,
            self.test_suggestions_performance,
            self.test_memory_leak,
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

        print("=" * 60)
        print(f"⚡ 性能测试结果统计:")
        print(f"   总测试数: {total}")
        print(f"   通过数: {passed}")
        print(f"   失败数: {total - passed}")
        print(f"   通过率: {passed/total*100:.1f}%")

        if passed == total:
            print("🎉 所有性能测试通过！系统性能表现良好。")
        else:
            print("⚠️  部分性能测试失败，建议优化系统性能。")

        # 性能建议
        print("\n📋 性能优化建议:")
        print("   - 如果响应时间>1000ms，考虑添加数据库索引")
        print("   - 如果并发处理能力不足，考虑增加连接池大小")
        print("   - 如果内存使用持续增长，检查是否存在内存泄漏")
        print("   - 考虑添加Redis缓存来优化查询性能")

        return passed == total


if __name__ == "__main__":
    tester = PerformanceTester()
    tester.run_all_tests()
