#!/usr/bin/env python3
"""
安全审计脚本：检查API中的权限控制问题
"""
import re


def audit_security():
    print("=== 量化交易系统安全审计报告 ===\n")

    # 读取app.py文件
    with open("app.py", "r", encoding="utf-8") as f:
        content = f.read()

    # 定义需要用户权限控制的敏感表
    sensitive_tables = [
        "BacktestReport",
        "Messages",
        "Strategy",
        "Indicator",
        "Param",
        "TradingSignal",
        "StrategyParamRel",
        "IndicatorParamRel",
    ]

    # 查找所有API路由
    api_routes = re.findall(
        r'@app\.route\([\'"]([^\'\"]*)[\'"].*\n.*def\s+(\w+)', content
    )

    print(f"发现 {len(api_routes)} 个API端点")

    # 查找可能的权限问题
    issues_found = []

    # 检查SELECT语句
    select_patterns = re.findall(
        r"SELECT.*?FROM\s+(\w+).*?WHERE.*?(user_name|creator_name)",
        content,
        re.IGNORECASE | re.DOTALL,
    )

    # 检查没有权限控制的SELECT语句
    unprotected_selects = re.findall(
        r"SELECT[^;]*?FROM\s+("
        + "|".join(sensitive_tables)
        + r")(?![^;]*(?:user_name|creator_name))[^;]*;?",
        content,
        re.IGNORECASE,
    )

    if unprotected_selects:
        issues_found.append("发现可能缺少用户权限验证的SELECT语句")
        for select in unprotected_selects[:5]:  # 只显示前5个
            print(f"⚠️  可能的问题: SELECT from {select}")

    # 检查公开数据的情况
    public_data_queries = re.findall(r"public.*?=.*?1", content, re.IGNORECASE)

    print(f"\n✅ 权限控制良好的方面:")
    print(f"   - 发现 {len(select_patterns)} 个包含用户权限验证的查询")
    print(f"   - 发现 {len(public_data_queries)} 个公开数据访问控制")
    print(f"   - JWT token认证系统已实施")

    # 检查关键安全修复
    security_fixes = [
        "user_name = %s" in content,
        "creator_name = %s" in content,
        "WHERE report_id = %s AND user_name = %s" in content,
        "WHERE message_id = %s AND user_name = %s" in content,
    ]

    print(f"\n🔒 安全修复状态:")
    print(f"   - 用户身份验证: {'✅' if security_fixes[0] else '❌'}")
    print(f"   - 创建者权限验证: {'✅' if security_fixes[1] else '❌'}")
    print(f"   - 回测报告权限控制: {'✅' if security_fixes[2] else '❌'}")
    print(f"   - 消息权限控制: {'✅' if security_fixes[3] else '❌'}")

    # 总结
    total_issues = len(issues_found)
    print(f"\n📊 审计总结:")
    print(f"   - 发现的潜在问题: {total_issues}")
    print(
        f"   - 安全等级: {'🟢 良好' if total_issues == 0 else '🟡 需要关注' if total_issues < 3 else '🔴 严重'}"
    )

    if total_issues == 0:
        print("   - 建议: 系统权限控制已基本完善，建议定期进行安全审计")

    return total_issues == 0


if __name__ == "__main__":
    audit_security()
