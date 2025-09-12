#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Flask Demo - 智能搜索Demo应用
展示如何实现带下拉框联想的搜索功能
"""

from flask import Flask, render_template, request, jsonify
from database import DatabaseManager

app = Flask(__name__)
db_manager = DatabaseManager()


@app.route("/")
def index():
    """主页"""
    return render_template("index.html")


@app.route("/api/suggestions", methods=["POST"])
def get_suggestions():
    """
    获取智能搜索建议
    请求格式：
    {
        "node_type": "策略|参数|指标|数据表",
        "input_text": "用户输入的文本"
    }
    """
    try:
        data = request.get_json()
        node_type = data.get("node_type", "")
        input_text = data.get("input_text", "")

        suggestions = []

        if node_type == "数据表":
            suggestions = handle_table_suggestions(input_text)
        elif node_type in ["策略", "参数", "指标"]:
            suggestions = handle_entity_suggestions(node_type, input_text)

        return jsonify({"success": True, "suggestions": suggestions})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


def handle_table_suggestions(input_text: str) -> list:
    """
    处理数据表类型的建议
    逻辑：
    1. 如果没有点号，搜索表名（daily, daily_basic）
    2. 如果有点号，点号前是表名，点号后搜索字段
    """
    if "." not in input_text:
        # 搜索表名
        return db_manager.search_table_suggestions(input_text)
    else:
        # 搜索字段
        table_name, field_query = input_text.split(".", 1)
        if table_name in ["daily", "daily_basic"]:
            fields = db_manager.search_field_suggestions(table_name, field_query)
            # 返回完整的 table.field 格式
            return [f"{table_name}.{field}" for field in fields]
        else:
            return []


def handle_entity_suggestions(node_type: str, input_text: str) -> list:
    """
    处理策略、参数、指标类型的建议
    逻辑：
    1. 如果没有点号，搜索用户名
    2. 如果有点号，点号前是用户名，点号后搜索对应的实体
    """
    if "." not in input_text:
        # 搜索用户名
        return db_manager.search_users(input_text)
    else:
        # 搜索具体实体
        creator_name, entity_query = input_text.split(".", 1)

        entities = []
        if node_type == "策略":
            entities = db_manager.search_strategies(creator_name, entity_query)
        elif node_type == "参数":
            entities = db_manager.search_params(creator_name, entity_query)
        elif node_type == "指标":
            entities = db_manager.search_indicators(creator_name, entity_query)

        # 返回完整的 creator.entity 格式
        return [f"{creator_name}.{entity}" for entity in entities]


@app.teardown_appcontext
def close_db(error):
    """在应用上下文结束时关闭数据库连接"""
    db_manager.close()


if __name__ == "__main__":
    print("Flask智能搜索Demo启动中...")
    print("访问 http://localhost:5000 查看Demo")
    print("Ctrl+C 停止服务")
    app.run(debug=True, host="0.0.0.0", port=5000)
