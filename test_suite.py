#!/usr/bin/env python3
"""
集成测试套件
统一的测试入口，运行所有API测试脚本
"""

import os
import sys
import subprocess
import time
from datetime import datetime


class TestSuite:
    def __init__(self):
        self.test_scripts = [
            {
                "name": "用户认证API测试",
                "file": "test_auth_api.py",
                "description": "测试登录、注册、用户信息获取等认证功能",
            },
            {
                "name": "参数管理API测试",
                "file": "test_param_api.py",
                "description": "测试参数的增删改查、智能搜索建议等功能",
            },
            {
                "name": "策略管理API测试",
                "file": "test_strategy_api.py",
                "description": "测试策略的增删改查、复制、参数关系管理等功能",
            },
            {
                "name": "指标管理API测试",
                "file": "test_indicator_api.py",
                "description": "测试指标的增删改查、复制、参数关系管理等功能",
            },
            {
                "name": "消息系统API测试",
                "file": "test_message_api.py",
                "description": "测试消息的获取、标记已读、删除等功能",
            },
            {
                "name": "回测系统API测试",
                "file": "test_backtest_api.py",
                "description": "测试完整的回测工作流程",
            },
            {
                "name": "权限安全测试",
                "file": "test_security.py",
                "description": "测试跨用户访问权限控制，确保数据隔离",
            },
            {
                "name": "性能和压力测试",
                "file": "test_performance.py",
                "description": "测试API在高并发情况下的性能表现",
            },
        ]

        self.results = {}

    def check_server_status(self):
        """检查服务器是否运行"""
        print("🔍 检查服务器状态...")
        try:
            import requests

            response = requests.get("http://localhost:5000/health", timeout=5)
            if response.status_code == 200:
                print("✓ 服务器运行正常")
                return True
            else:
                print(f"❌ 服务器响应异常: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ 无法连接到服务器: {e}")
            print("   请确保 app.py 已启动并运行在 http://localhost:5000")
            return False

    def run_single_test(self, test_info):
        """运行单个测试脚本"""
        test_name = test_info["name"]
        test_file = test_info["file"]

        print(f"\n{'='*60}")
        print(f"🧪 开始测试: {test_name}")
        print(f"📝 描述: {test_info['description']}")
        print(f"📄 脚本: {test_file}")
        print("=" * 60)

        if not os.path.exists(test_file):
            print(f"❌ 测试脚本不存在: {test_file}")
            return False

        try:
            # 运行测试脚本
            start_time = time.time()
            result = subprocess.run(
                [sys.executable, test_file], capture_output=True, text=True, timeout=300
            )  # 5分钟超时
            end_time = time.time()

            duration = end_time - start_time

            # 打印输出
            if result.stdout:
                print(result.stdout)
            if result.stderr:
                print("错误输出:", result.stderr)

            success = result.returncode == 0

            self.results[test_name] = {
                "success": success,
                "duration": duration,
                "return_code": result.returncode,
            }

            if success:
                print(f"✅ {test_name} 完成 (耗时: {duration:.2f}秒)")
            else:
                print(f"❌ {test_name} 失败 (返回码: {result.returncode})")

            return success

        except subprocess.TimeoutExpired:
            print(f"⏰ {test_name} 超时 (超过5分钟)")
            self.results[test_name] = {
                "success": False,
                "duration": 300,
                "return_code": -1,
            }
            return False
        except Exception as e:
            print(f"❌ {test_name} 执行异常: {e}")
            self.results[test_name] = {
                "success": False,
                "duration": 0,
                "return_code": -2,
            }
            return False

    def print_summary(self):
        """打印测试总结"""
        print(f"\n{'='*80}")
        print("📊 测试总结报告")
        print("=" * 80)

        total_tests = len(self.results)
        passed_tests = sum(1 for result in self.results.values() if result["success"])
        failed_tests = total_tests - passed_tests
        total_time = sum(result["duration"] for result in self.results.values())

        print(f"📈 整体统计:")
        print(f"   总测试数: {total_tests}")
        print(f"   通过数: {passed_tests}")
        print(f"   失败数: {failed_tests}")
        print(f"   通过率: {passed_tests/total_tests*100:.1f}%")
        print(f"   总耗时: {total_time:.2f}秒")

        print(f"\n📋 详细结果:")
        for test_name, result in self.results.items():
            status = "✅ 通过" if result["success"] else "❌ 失败"
            print(f"   {status} - {test_name} ({result['duration']:.2f}秒)")

        if failed_tests > 0:
            print(f"\n⚠️  发现 {failed_tests} 个测试失败:")
            for test_name, result in self.results.items():
                if not result["success"]:
                    print(f"   - {test_name} (返回码: {result['return_code']})")

        if passed_tests == total_tests:
            print(f"\n🎉 恭喜！所有测试都通过了！")
            print(f"   系统功能完整，性能良好，安全可靠。")
        else:
            print(f"\n💡 建议:")
            print(f"   - 检查失败的测试脚本")
            print(f"   - 确认API服务器运行正常")
            print(f"   - 验证数据库连接和数据完整性")

    def run_interactive_mode(self):
        """交互式运行模式"""
        print("🚀 量化交易系统API测试套件")
        print("=" * 50)

        while True:
            print("\n请选择测试模式:")
            print("1. 运行所有测试")
            print("2. 选择性运行测试")
            print("3. 仅运行快速测试(跳过性能测试)")
            print("4. 退出")

            choice = input("\n请输入选择 (1-4): ").strip()

            if choice == "1":
                return self.run_all_tests()
            elif choice == "2":
                return self.run_selective_tests()
            elif choice == "3":
                return self.run_quick_tests()
            elif choice == "4":
                print("👋 退出测试套件")
                return True
            else:
                print("❌ 无效选择，请重新输入")

    def run_selective_tests(self):
        """选择性运行测试"""
        print("\n📋 可用的测试脚本:")
        for i, test_info in enumerate(self.test_scripts, 1):
            print(f"{i}. {test_info['name']}")
            print(f"   {test_info['description']}")

        print("\n请选择要运行的测试 (输入数字，用逗号分隔多个选择):")
        choices = input("选择: ").strip()

        try:
            indices = [int(x.strip()) - 1 for x in choices.split(",")]
            selected_tests = [
                self.test_scripts[i] for i in indices if 0 <= i < len(self.test_scripts)
            ]

            if not selected_tests:
                print("❌ 没有选择有效的测试")
                return False

            return self.run_tests(selected_tests)

        except ValueError:
            print("❌ 输入格式错误")
            return False

    def run_quick_tests(self):
        """运行快速测试（跳过性能测试）"""
        quick_tests = [
            test
            for test in self.test_scripts
            if test["file"] not in ["test_performance.py", "test_security.py"]
        ]
        return self.run_tests(quick_tests)

    def run_tests(self, test_list):
        """运行指定的测试列表"""
        if not self.check_server_status():
            return False

        print(f"\n🏁 开始运行 {len(test_list)} 个测试...")
        print(f"⏰ 开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        success_count = 0
        for test_info in test_list:
            if self.run_single_test(test_info):
                success_count += 1
            time.sleep(1)  # 测试间隔

        print(f"\n⏰ 结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        self.print_summary()
        return success_count == len(test_list)

    def run_all_tests(self):
        """运行所有测试"""
        return self.run_tests(self.test_scripts)


def main():
    """主函数"""
    print("🎯 量化交易系统 - 集成测试套件")
    print(f"📅 {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}")

    suite = TestSuite()

    # 检查命令行参数
    if len(sys.argv) > 1:
        if sys.argv[1] == "--all":
            success = suite.run_all_tests()
        elif sys.argv[1] == "--quick":
            success = suite.run_quick_tests()
        elif sys.argv[1] == "--help":
            print("\n使用方法:")
            print("  python test_suite.py         # 交互式模式")
            print("  python test_suite.py --all   # 运行所有测试")
            print("  python test_suite.py --quick # 运行快速测试")
            print("  python test_suite.py --help  # 显示帮助")
            return
        else:
            print(f"❌ 未知参数: {sys.argv[1]}")
            print("使用 --help 查看用法")
            return
    else:
        # 交互式模式
        success = suite.run_interactive_mode()

    # 设置退出码
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
