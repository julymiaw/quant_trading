#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
量化交易系统后端服务器
提供用户登录、注册等API接口
"""

import pymysql
import json
import os
import re
import logging
import hashlib
from datetime import datetime, timedelta, timezone
import uuid
from functools import wraps

from flask import Flask, request, jsonify
from flask_cors import CORS
import jwt

# 导入量化交易系统的数据准备和回测模块
from prepare_strategy_data import DataPreparer
from backtest_engine import BacktestEngine
import pandas as pd

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 创建Flask应用
app = Flask(__name__)
CORS(app)


# 加载配置文件
def load_config():
    """加载配置文件"""
    config_path = os.path.join(os.path.dirname(__file__), "config.json")
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"配置文件未找到: {config_path}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"配置文件格式错误: {e}")
        raise


# 加载配置
config = load_config()

# 配置项
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY") or "your-secret-key-here"
app.config["JWT_EXPIRATION_DELTA"] = timedelta(hours=24)


# 数据库连接工具函数
def get_db_connection():
    """获取数据库连接"""
    try:
        connection = pymysql.connect(
            host="localhost",
            port=3306,
            user="root",
            password=config["db_password"],
            database="quantitative_trading",
            charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor,
        )
        return connection
    except Exception as e:
        logger.error(f"数据库连接失败: {str(e)}")
        raise


# JWT工具函数
def generate_token(user_id, user_name, user_role):
    """生成JWT token"""
    payload = {
        "exp": datetime.now(timezone.utc) + app.config["JWT_EXPIRATION_DELTA"],
        "iat": datetime.now(timezone.utc),
        "sub": user_id,
        "user_name": user_name,
        "user_role": user_role,
    }
    return jwt.encode(payload, app.config["SECRET_KEY"], algorithm="HS256")


# 验证token的装饰器
def token_required(f):
    """验证JWT token的装饰器"""

    @wraps(f)
    def decorated(*args, **kwargs):
        token = None

        # 从请求头获取token
        if "Authorization" in request.headers:
            auth_header = request.headers["Authorization"]
            try:
                token = auth_header.split(" ")[1]
            except IndexError:
                return jsonify({"message": "无效的Token格式"}), 401

        if not token:
            return jsonify({"message": "Token缺失"}), 401

        try:
            # 解码token
            data = jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])
            current_user = {
                "user_id": data["sub"],
                "user_name": data["user_name"],
                "user_role": data["user_role"],
            }
        except jwt.ExpiredSignatureError:
            return jsonify({"message": "Token已过期"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"message": "无效的Token"}), 401

        return f(current_user, *args, **kwargs)

    return decorated


# 健康检查API
@app.route("/health", methods=["GET"])
def health_check():
    """服务健康检查接口"""
    try:
        connection = get_db_connection()
        connection.close()
        return jsonify({"status": "ok", "message": "服务正常运行"}), 200
    except Exception as e:
        logger.error(f"健康检查失败: {str(e)}")
        return jsonify({"status": "error", "message": f"数据库连接失败: {str(e)}"}), 500


# 登录API
@app.route("/auth/login", methods=["POST"])
def login():
    """用户登录接口"""
    try:
        data = request.get_json()
        # 兼容两种参数名格式
        user_name = data.get("userName") or data.get("user_name")
        password = data.get("password")

        if not user_name or not password:
            return jsonify({"message": "用户名和密码不能为空"}), 400

        # 查询数据库验证用户
        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                sql = (
                    "SELECT * FROM User WHERE user_name = %s AND user_status = 'active'"
                )
                cursor.execute(sql, (user_name,))
                user = cursor.fetchone()

                if not user:
                    return jsonify({"message": "用户名不存在或账户已禁用"}), 401

                # 使用MD5加密用户输入的密码后与数据库中的加密密码比对
                # 创建MD5哈希对象
                md5 = hashlib.md5()
                # 更新哈希对象，需要将字符串转换为字节
                md5.update(password.encode("utf-8"))
                # 获取加密后的密码（16进制格式）
                hashed_password = md5.hexdigest()

                if user["user_password"] != hashed_password:
                    return jsonify({"message": "密码错误"}), 401

                # 更新最后登录时间
                update_sql = (
                    "UPDATE User SET user_last_login_time = NOW() WHERE user_id = %s"
                )
                cursor.execute(update_sql, (user["user_id"],))
                connection.commit()

                # 生成token
                token = generate_token(
                    user["user_id"], user["user_name"], user["user_role"]
                )

                # 构建用户信息
                user_info = {
                    "user_id": user["user_id"],
                    "user_name": user["user_name"],
                    "user_role": user["user_role"],
                    "user_status": user["user_status"],
                    "user_email": user.get("user_email"),
                    "user_phone": user.get("user_phone"),
                    "user_create_time": (
                        user["user_create_time"].isoformat()
                        if user.get("user_create_time")
                        else None
                    ),
                    "user_last_login_time": datetime.now().isoformat(),  # 当前登录时间
                }

                return jsonify(
                    {
                        "code": 200,
                        "data": {"token": token, "userInfo": user_info},
                        "message": "登录成功",
                    }
                )
        finally:
            connection.close()
    except Exception as e:
        logger.error(f"登录过程中发生错误: {str(e)}")
        return jsonify({"message": f"登录失败: {str(e)}"}), 500


# 注册API
@app.route("/auth/register", methods=["POST"])
def register():
    """用户注册接口"""
    try:
        data = request.get_json()
        # 兼容两种参数名格式
        user_name = data.get("userName") or data.get("user_name")
        password = data.get("password")
        email = data.get("email")
        phone = data.get("phone")

        # 验证必填字段
        if not user_name or not password or not email:
            return jsonify({"message": "用户名、密码和邮箱为必填项"}), 400

        # 验证用户名格式（仅允许英文、数字、下划线）
        if not re.match(r"^[a-zA-Z0-9_]+$", user_name):
            return jsonify({"message": "用户名仅允许英文、数字、下划线"}), 400

        # 连接数据库
        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                # 检查用户名是否已存在
                check_sql = "SELECT * FROM User WHERE user_name = %s"
                cursor.execute(check_sql, (user_name,))
                if cursor.fetchone():
                    return jsonify({"message": "用户名已存在"}), 400

                # 检查邮箱是否已存在
                check_email_sql = "SELECT * FROM User WHERE user_email = %s"
                cursor.execute(check_email_sql, (email,))
                if cursor.fetchone():
                    return jsonify({"message": "该邮箱已被注册"}), 400

                # 生成用户ID
                user_id = str(uuid.uuid4())

                # 使用MD5加密密码
                md5 = hashlib.md5()
                md5.update(password.encode("utf-8"))
                hashed_password = md5.hexdigest()

                # 插入用户数据
                insert_sql = """
                INSERT INTO User (user_id, user_name, user_password, user_role, user_status, user_email, user_phone)
                VALUES (%s, %s, %s, 'analyst', 'active', %s, %s)
                """
                cursor.execute(
                    insert_sql, (user_id, user_name, hashed_password, email, phone)
                )
                connection.commit()

                return jsonify({"message": "注册成功，请登录"}), 201
        finally:
            connection.close()
    except Exception as e:
        logger.error(f"注册过程中发生错误: {str(e)}")
        return jsonify({"message": f"注册失败: {str(e)}"}), 500


# 获取用户信息API（需要验证token）
@app.route("/user/info", methods=["GET"])
@token_required
def get_user_info(current_user):
    """获取当前用户信息接口"""
    try:
        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                sql = "SELECT user_id, user_name, user_role, user_status, user_email, user_phone, user_create_time, user_last_login_time FROM User WHERE user_id = %s"
                cursor.execute(sql, (current_user["user_id"],))
                user = cursor.fetchone()

                if not user:
                    return jsonify({"code": 404, "message": "用户不存在"}), 404

                # 格式化日期字段
                user_data = {
                    "user_id": user["user_id"],
                    "user_name": user["user_name"],
                    "user_role": user["user_role"],
                    "user_status": user.get("user_status"),
                    "user_email": user.get("user_email"),
                    "user_phone": user.get("user_phone"),
                    "user_create_time": (
                        user["user_create_time"].isoformat()
                        if user.get("user_create_time")
                        else None
                    ),
                    "user_last_login_time": (
                        user["user_last_login_time"].isoformat()
                        if user.get("user_last_login_time")
                        else None
                    ),
                }

                return (
                    jsonify(
                        {"code": 200, "data": user_data, "message": "获取用户信息成功"}
                    ),
                    200,
                )
        finally:
            connection.close()
    except Exception as e:
        logger.error(f"获取用户信息过程中发生错误: {str(e)}")
        return jsonify({"message": f"获取用户信息失败: {str(e)}"}), 500


# =============================================
# 参数管理相关API
# =============================================


# 获取参数列表API
@app.route("/api/params", methods=["GET"])
@token_required
def get_params(current_user):
    """获取参数列表接口"""
    try:
        # 获取查询参数
        page = int(request.args.get("page", 1))
        page_size = int(request.args.get("page_size", 10))
        search_keyword = request.args.get("search", "").strip()
        param_type_filter = request.args.get("param_type", "my")  # my, system, all
        param_source_type = request.args.get(
            "param_source_type", "all"
        )  # all, table, indicator

        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                # 获取当前用户信息
                user_sql = "SELECT user_name FROM User WHERE user_id = %s"
                cursor.execute(user_sql, (current_user["user_id"],))
                current_user_info = cursor.fetchone()

                if not current_user_info:
                    return jsonify({"message": "用户不存在"}), 404

                current_user_name = current_user_info["user_name"]

                # 构建基础查询SQL
                base_sql = """
                SELECT 
                    CONCAT(creator_name, '.', param_name) as id,
                    creator_name,
                    param_name,
                    data_id,
                    param_type,
                    pre_period,
                    post_period,
                    agg_func,
                    DATE_FORMAT(creation_time, '%%Y-%%m-%%d %%H:%%i:%%s') as create_time
                FROM Param
                WHERE 1=1
                """

                # 构建WHERE条件
                where_conditions = []
                query_params = []

                # 根据参数类型筛选
                if param_type_filter == "my":
                    where_conditions.append("creator_name = %s")
                    query_params.append(current_user_name)
                elif param_type_filter == "system":
                    where_conditions.append("creator_name = 'system'")

                # 根据参数来源类型筛选
                if param_source_type != "all":
                    where_conditions.append("param_type = %s")
                    query_params.append(param_source_type)

                # 根据搜索关键词筛选
                if search_keyword:
                    where_conditions.append("(param_name LIKE %s OR data_id LIKE %s)")
                    query_params.extend([f"%{search_keyword}%", f"%{search_keyword}%"])

                # 组装完整的查询SQL
                if where_conditions:
                    count_sql = f"SELECT COUNT(*) as total FROM Param WHERE {' AND '.join(where_conditions)}"
                    data_sql = f"{base_sql} AND {' AND '.join(where_conditions)} ORDER BY creator_name, param_name"
                else:
                    count_sql = "SELECT COUNT(*) as total FROM Param"
                    data_sql = f"{base_sql} ORDER BY creator_name, param_name"

                # 获取总数
                cursor.execute(count_sql, query_params)
                total_result = cursor.fetchone()
                total = total_result["total"] if total_result else 0

                # 分页查询数据
                offset = (page - 1) * page_size
                data_sql += f" LIMIT %s OFFSET %s"
                query_params.extend([page_size, offset])

                cursor.execute(data_sql, query_params)
                params = cursor.fetchall()

                # 格式化返回数据
                formatted_params = []
                for param in params:
                    formatted_params.append(
                        {
                            "id": param["id"],
                            "creator_name": param["creator_name"],
                            "param_name": param["param_name"],
                            "data_id": param["data_id"],
                            "param_type": param["param_type"],
                            "pre_period": param["pre_period"],
                            "post_period": param["post_period"],
                            "agg_func": param["agg_func"],
                            "create_time": param["create_time"],
                        }
                    )

                return (
                    jsonify(
                        {
                            "data": {
                                "params": formatted_params,
                                "total": total,
                                "page": page,
                                "page_size": page_size,
                            },
                            "message": "获取参数列表成功",
                        }
                    ),
                    200,
                )

        finally:
            connection.close()

    except Exception as e:
        logger.error(f"获取参数列表过程中发生错误: {str(e)}")
        return jsonify({"message": f"获取参数列表失败: {str(e)}"}), 500


# 创建参数API
@app.route("/api/params", methods=["POST"])
@token_required
def create_param(current_user):
    """创建参数接口"""
    try:
        data = request.get_json()

        # 验证必填字段
        required_fields = [
            "param_name",
            "data_id",
            "param_type",
            "pre_period",
            "post_period",
        ]
        for field in required_fields:
            if field not in data or data[field] is None:
                return jsonify({"message": f"缺少必填字段: {field}"}), 400

        param_name = (
            str(data["param_name"]).strip() if data["param_name"] is not None else ""
        )
        data_id = str(data["data_id"]).strip() if data["data_id"] is not None else ""
        param_type = data["param_type"]
        pre_period = data["pre_period"]
        post_period = data["post_period"]

        # 处理agg_func字段（可选字段，可以为空）
        agg_func_raw = data.get("agg_func")
        if agg_func_raw is None or agg_func_raw == "":
            agg_func = None
        else:
            agg_func = str(agg_func_raw).strip() if str(agg_func_raw).strip() else None

        # 验证数据格式
        if not param_name or not data_id:
            return jsonify({"message": "参数ID和数据来源ID不能为空"}), 400

        if param_type not in ["table", "indicator"]:
            return jsonify({"message": "参数类型必须是table或indicator"}), 400

        try:
            pre_period = int(pre_period)
            post_period = int(post_period)
        except (ValueError, TypeError):
            return jsonify({"message": "历史天数和预测天数必须是整数"}), 400

        if pre_period < 0 or post_period < 0:
            return jsonify({"message": "历史天数和预测天数不能为负数"}), 400

        # 验证参数ID格式（仅允许字母、数字、下划线和点号）
        if not re.match(r"^[a-zA-Z0-9_.]+$", param_name):
            return jsonify({"message": "参数ID只能包含字母、数字、下划线和点号"}), 400

        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                # 获取当前用户信息
                user_sql = "SELECT user_name FROM User WHERE user_id = %s"
                cursor.execute(user_sql, (current_user["user_id"],))
                current_user_info = cursor.fetchone()

                if not current_user_info:
                    return jsonify({"message": "用户不存在"}), 404

                current_user_name = current_user_info["user_name"]

                # 检查参数ID是否已存在（同一创建者下）
                check_sql = (
                    "SELECT * FROM Param WHERE creator_name = %s AND param_name = %s"
                )
                cursor.execute(check_sql, (current_user_name, param_name))
                if cursor.fetchone():
                    return jsonify({"message": f'参数ID "{param_name}" 已存在'}), 400

                # 插入新参数
                insert_sql = """
                INSERT INTO Param (creator_name, param_name, data_id, param_type, pre_period, post_period, agg_func)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """
                cursor.execute(
                    insert_sql,
                    (
                        current_user_name,
                        param_name,
                        data_id,
                        param_type,
                        pre_period,
                        post_period,
                        agg_func,
                    ),
                )
                connection.commit()

                # 返回创建的参数信息
                new_param = {
                    "id": f"{current_user_name}_{param_name}",
                    "creator_name": current_user_name,
                    "param_name": param_name,
                    "data_id": data_id,
                    "param_type": param_type,
                    "pre_period": pre_period,
                    "post_period": post_period,
                    "agg_func": agg_func,
                    "create_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                }

                return jsonify({"data": new_param, "message": "参数创建成功"}), 201

        finally:
            connection.close()

    except Exception as e:
        logger.error(f"创建参数过程中发生错误: {str(e)}")
        return jsonify({"message": f"创建参数失败: {str(e)}"}), 500


# 更新参数API
@app.route("/api/params/<param_composite_id>", methods=["PUT"])
@token_required
def update_param(current_user, param_composite_id):
    """更新参数接口"""
    try:
        # 解析复合ID (格式: creator_name.param_name)
        try:
            parts = param_composite_id.split(".", 1)
            if len(parts) != 2:
                return jsonify({"message": "无效的参数ID格式"}), 400
            creator_name, param_name = parts
        except:
            return jsonify({"message": "无效的参数ID格式"}), 400

        data = request.get_json()

        # 验证必填字段
        required_fields = [
            "param_name",
            "data_id",
            "param_type",
            "pre_period",
            "post_period",
        ]
        for field in required_fields:
            if field not in data or data[field] is None:
                return jsonify({"message": f"缺少必填字段: {field}"}), 400

        new_param_name = (
            str(data["param_name"]).strip() if data["param_name"] is not None else ""
        )
        data_id = str(data["data_id"]).strip() if data["data_id"] is not None else ""
        param_type = data["param_type"]
        pre_period = data["pre_period"]
        post_period = data["post_period"]

        # 处理agg_func字段（可选字段，可以为空）
        agg_func_raw = data.get("agg_func")
        if agg_func_raw is None or agg_func_raw == "":
            agg_func = None
        else:
            agg_func = str(agg_func_raw).strip() if str(agg_func_raw).strip() else None

        # 验证数据格式
        if not new_param_name or not data_id:
            return jsonify({"message": "参数ID和数据来源ID不能为空"}), 400

        if param_type not in ["table", "indicator"]:
            return jsonify({"message": "参数类型必须是table或indicator"}), 400

        try:
            pre_period = int(pre_period)
            post_period = int(post_period)
        except (ValueError, TypeError):
            return jsonify({"message": "历史天数和预测天数必须是整数"}), 400

        if pre_period < 0 or post_period < 0:
            return jsonify({"message": "历史天数和预测天数不能为负数"}), 400

        # 验证参数ID格式
        if not re.match(r"^[a-zA-Z0-9_.]+$", new_param_name):
            return jsonify({"message": "参数ID只能包含字母、数字、下划线和点号"}), 400

        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                # 获取当前用户信息
                user_sql = "SELECT user_name FROM User WHERE user_id = %s"
                cursor.execute(user_sql, (current_user["user_id"],))
                current_user_info = cursor.fetchone()

                if not current_user_info:
                    return jsonify({"message": "用户不存在"}), 404

                current_user_name = current_user_info["user_name"]

                # 检查参数是否存在
                check_sql = (
                    "SELECT * FROM Param WHERE creator_name = %s AND param_name = %s"
                )
                cursor.execute(check_sql, (creator_name, param_name))
                existing_param = cursor.fetchone()

                if not existing_param:
                    return jsonify({"message": "参数不存在"}), 404

                # 检查权限（只能更新自己创建的参数）
                if creator_name != current_user_name:
                    return jsonify({"message": "无权限修改他人创建的参数"}), 403

                # 如果参数ID有变化，检查新ID是否已存在
                if new_param_name != param_name:
                    check_new_id_sql = "SELECT * FROM Param WHERE creator_name = %s AND param_name = %s"
                    cursor.execute(check_new_id_sql, (creator_name, new_param_name))
                    if cursor.fetchone():
                        return (
                            jsonify(
                                {"message": f'新的参数ID "{new_param_name}" 已存在'}
                            ),
                            400,
                        )

                # 更新参数
                if new_param_name != param_name:
                    # 如果参数ID变化了，需要先更新关联关系，然后更新参数本身
                    # 更新指标参数关系表中的参数ID引用
                    update_indicator_rel_sql = """
                    UPDATE IndicatorParamRel 
                    SET param_name = %s 
                    WHERE param_creator_name = %s AND param_name = %s
                    """
                    cursor.execute(
                        update_indicator_rel_sql,
                        (new_param_name, creator_name, param_name),
                    )

                    # 更新策略参数关系表中的参数ID引用
                    update_strategy_rel_sql = """
                    UPDATE StrategyParamRel 
                    SET param_name = %s 
                    WHERE param_creator_name = %s AND param_name = %s
                    """
                    cursor.execute(
                        update_strategy_rel_sql,
                        (new_param_name, creator_name, param_name),
                    )

                    # 更新参数表
                    update_sql = """
                    UPDATE Param 
                    SET param_name = %s, data_id = %s, param_type = %s, 
                        pre_period = %s, post_period = %s, agg_func = %s
                    WHERE creator_name = %s AND param_name = %s
                    """
                    cursor.execute(
                        update_sql,
                        (
                            new_param_name,
                            data_id,
                            param_type,
                            pre_period,
                            post_period,
                            agg_func,
                            creator_name,
                            param_name,
                        ),
                    )
                else:
                    # 只更新除param_name外的其他字段
                    update_sql = """
                    UPDATE Param 
                    SET data_id = %s, param_type = %s, pre_period = %s, post_period = %s, agg_func = %s
                    WHERE creator_name = %s AND param_name = %s
                    """
                    cursor.execute(
                        update_sql,
                        (
                            data_id,
                            param_type,
                            pre_period,
                            post_period,
                            agg_func,
                            creator_name,
                            param_name,
                        ),
                    )

                connection.commit()

                # 返回更新后的参数信息
                updated_param = {
                    "id": f"{creator_name}.{new_param_name}",
                    "creator_name": creator_name,
                    "param_name": new_param_name,
                    "data_id": data_id,
                    "param_type": param_type,
                    "pre_period": pre_period,
                    "post_period": post_period,
                    "agg_func": agg_func,
                    "create_time": existing_param.get(
                        "create_time", datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    ),
                }

                return jsonify({"data": updated_param, "message": "参数更新成功"}), 200

        finally:
            connection.close()

    except Exception as e:
        logger.error(f"更新参数过程中发生错误: {str(e)}")
        return jsonify({"message": f"更新参数失败: {str(e)}"}), 500


# 删除参数API
@app.route("/api/params/<param_composite_id>", methods=["DELETE"])
@token_required
def delete_param(current_user, param_composite_id):
    """删除参数接口"""
    try:
        # 解析复合ID (格式: creator_name.param_name)
        try:
            parts = param_composite_id.split(".", 1)
            if len(parts) != 2:
                return jsonify({"message": "无效的参数ID格式"}), 400
            creator_name, param_name = parts
        except:
            return jsonify({"message": "无效的参数ID格式"}), 400

        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                # 获取当前用户信息
                user_sql = "SELECT user_name FROM User WHERE user_id = %s"
                cursor.execute(user_sql, (current_user["user_id"],))
                current_user_info = cursor.fetchone()

                if not current_user_info:
                    return jsonify({"message": "用户不存在"}), 404

                current_user_name = current_user_info["user_name"]

                # 检查参数是否存在
                check_sql = (
                    "SELECT * FROM Param WHERE creator_name = %s AND param_name = %s"
                )
                cursor.execute(check_sql, (creator_name, param_name))
                existing_param = cursor.fetchone()

                if not existing_param:
                    return jsonify({"message": "参数不存在"}), 404

                # 检查权限（只能删除自己创建的参数）
                if creator_name != current_user_name:
                    return jsonify({"message": "无权限删除他人创建的参数"}), 403

                # 检查参数是否被指标引用
                check_indicator_rel_sql = """
                SELECT i.indicator_name 
                FROM IndicatorParamRel ipr
                JOIN Indicator i ON ipr.indicator_creator_name = i.creator_name 
                    AND ipr.indicator_name = i.indicator_name
                WHERE ipr.param_creator_name = %s AND ipr.param_name = %s
                """
                cursor.execute(check_indicator_rel_sql, (creator_name, param_name))
                indicator_relations = cursor.fetchall()

                # 检查参数是否被策略引用
                check_strategy_rel_sql = """
                SELECT s.strategy_name 
                FROM StrategyParamRel spr
                JOIN Strategy s ON spr.strategy_creator_name = s.creator_name 
                    AND spr.strategy_name = s.strategy_name
                WHERE spr.param_creator_name = %s AND spr.param_name = %s
                """
                cursor.execute(check_strategy_rel_sql, (creator_name, param_name))
                strategy_relations = cursor.fetchall()

                # 如果参数被引用，返回错误信息
                if indicator_relations or strategy_relations:
                    usage_info = []
                    if indicator_relations:
                        indicator_names = [
                            rel["indicator_name"] for rel in indicator_relations
                        ]
                        usage_info.append(f"指标: {', '.join(indicator_names)}")
                    if strategy_relations:
                        strategy_names = [
                            rel["strategy_name"] for rel in strategy_relations
                        ]
                        usage_info.append(f"策略: {', '.join(strategy_names)}")

                    return (
                        jsonify(
                            {
                                "message": f'参数正在被以下对象使用，无法删除: {"; ".join(usage_info)}'
                            }
                        ),
                        400,
                    )

                # 删除参数（由于设置了外键约束，相关的关系记录会自动删除）
                delete_sql = (
                    "DELETE FROM Param WHERE creator_name = %s AND param_name = %s"
                )
                cursor.execute(delete_sql, (creator_name, param_name))
                connection.commit()

                return jsonify({"message": "参数删除成功"}), 200

        finally:
            connection.close()

    except Exception as e:
        logger.error(f"删除参数过程中发生错误: {str(e)}")
        return jsonify({"message": f"删除参数失败: {str(e)}"}), 500


# 智能搜索建议API（替代原来的数据源列表API）
@app.route("/api/suggestions", methods=["POST"])
@token_required
def get_suggestions(current_user):
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
        elif node_type in ["股票", "指数", "基准"]:
            # 从 tushare_cache 数据库中查询 stock_basic 或 index_basic
            suggestions = handle_market_entity_suggestions(node_type, input_text)

        return jsonify({"success": True, "suggestions": suggestions})

    except Exception as e:
        logger.error(f"获取智能搜索建议过程中发生错误: {str(e)}")
        return jsonify({"success": False, "error": str(e)})


def handle_table_suggestions(input_text: str) -> list:
    """
    处理数据表类型的建议
    逻辑：
    1. 如果没有点号，搜索表名
    2. 如果有点号，点号前是表名，点号后搜索字段
    """
    # 只允许选择 daily/daily_basic 且排除 ts_code 和 trade_date 字段
    allowed_tables = ["daily", "daily_basic"]
    exclude_fields = ["ts_code", "trade_date"]
    if "." not in input_text:
        # 只返回允许的表
        if not input_text:
            return allowed_tables
        return [
            table for table in allowed_tables if table.startswith(input_text.lower())
        ]
    else:
        table_name, field_query = input_text.split(".", 1)
        if table_name in allowed_tables:
            fields_info = get_table_fields(table_name)
            # 过滤掉 ts_code 和 trade_date 字段
            filtered_fields = [
                f for f in fields_info if f["name"] not in exclude_fields
            ]
            if not field_query:
                result = []
                for field_info in filtered_fields:
                    field_name = field_info["name"]
                    field_comment = field_info["comment"]
                    if field_comment:
                        result.append(
                            {
                                "value": f"{table_name}.{field_name}",
                                "label": f"{field_name} - {field_comment}",
                            }
                        )
                    else:
                        result.append(
                            {"value": f"{table_name}.{field_name}", "label": field_name}
                        )
                return result
            else:
                matching_fields = []
                for field_info in filtered_fields:
                    field_name = field_info["name"]
                    field_comment = field_info["comment"]
                    if field_name.lower().startswith(field_query.lower()):
                        if field_comment:
                            matching_fields.append(
                                {
                                    "value": f"{table_name}.{field_name}",
                                    "label": f"{field_name} - {field_comment}",
                                }
                            )
                        else:
                            matching_fields.append(
                                {
                                    "value": f"{table_name}.{field_name}",
                                    "label": field_name,
                                }
                            )
                return matching_fields
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
        return search_users(input_text)
    else:
        # 搜索具体实体
        creator_name, entity_query = input_text.split(".", 1)

        entities = []
        if node_type == "策略":
            entities = search_strategies(creator_name, entity_query)
        elif node_type == "参数":
            entities = search_params(creator_name, entity_query)
        elif node_type == "指标":
            entities = search_indicators(creator_name, entity_query)

        # 返回完整的 creator.entity 格式
        return [f"{creator_name}.{entity}" for entity in entities]


def handle_market_entity_suggestions(node_type: str, input_text: str) -> list:
    """
    处理股票/指数/基准的智能补全，返回对象列表 {code, name}
    """
    try:
        conn = pymysql.connect(
            host="localhost",
            port=3306,
            user="root",
            password=config["db_password"],
            database="tushare_cache",
            charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor,
        )
        cur = conn.cursor()
        q = input_text.strip()
        if node_type == "股票":
            if not q:
                cur.execute("SELECT ts_code, name FROM stock_basic LIMIT 50")
            else:
                like = f"{q}%"
                cur.execute(
                    "SELECT ts_code, name FROM stock_basic WHERE ts_code LIKE %s OR name LIKE %s LIMIT 50",
                    (like, like),
                )
        else:
            # 指数或基准使用 index_basic
            if not q:
                cur.execute("SELECT ts_code, name FROM index_basic LIMIT 50")
            else:
                like = f"{q}%"
                cur.execute(
                    "SELECT ts_code, name FROM index_basic WHERE ts_code LIKE %s OR name LIKE %s LIMIT 50",
                    (like, like),
                )
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return [{"ts_code": r["ts_code"], "name": r.get("name") or ""} for r in rows]
    except Exception as e:
        logger.exception("查询市场实体建议失败")
        try:
            conn.close()
        except:
            pass
        return []


def get_table_fields(table_name: str) -> list:
    """获取指定表的所有字段名和注释信息"""
    try:
        # 根据表名判断使用哪个数据库
        if table_name in [
            "daily",
            "daily_basic",
            "stock_basic",
            "index_basic",
            "index_daily",
        ]:
            # 这些表在tushare_cache数据库中
            connection = pymysql.connect(
                host="localhost",
                port=3306,
                user="root",
                password=config["db_password"],
                database="tushare_cache",
                charset="utf8mb4",
                cursorclass=pymysql.cursors.DictCursor,
            )
            database_name = "tushare_cache"
        else:
            # 其他表在quantitative_trading数据库中
            connection = get_db_connection()
            database_name = "quantitative_trading"

        if connection is None:
            return []

        cursor = connection.cursor()

        # 查询表的字段信息和注释
        cursor.execute(
            """
            SELECT COLUMN_NAME, COLUMN_COMMENT 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
            ORDER BY ORDINAL_POSITION
        """,
            (database_name, table_name),
        )

        fields = []
        for row in cursor.fetchall():
            field_name = row["COLUMN_NAME"]
            field_comment = row["COLUMN_COMMENT"]
            if field_comment:
                # 返回格式: {"name": "字段名", "comment": "注释"}
                fields.append({"name": field_name, "comment": field_comment})
            else:
                fields.append({"name": field_name, "comment": ""})

        cursor.close()
        return fields
    except Exception as e:
        logger.exception("获取表字段失败")
        return []
    finally:
        connection.close()


def search_users(query: str = "") -> list:
    """搜索用户名"""
    try:
        connection = get_db_connection()
        if connection is None:
            return []

        cursor = connection.cursor()
        if query:
            cursor.execute(
                "SELECT DISTINCT user_name FROM User WHERE user_name LIKE %s ORDER BY user_name",
                (f"{query}%",),
            )
        else:
            cursor.execute("SELECT DISTINCT user_name FROM User ORDER BY user_name")

        users = [row["user_name"] for row in cursor.fetchall()]
        cursor.close()
        return users
    except Exception as e:
        logger.exception("搜索用户失败")
        return []


def search_strategies(creator_name: str, query: str = "") -> list:
    """搜索指定用户的策略"""
    try:
        connection = get_db_connection()
        if connection is None:
            return []

        cursor = connection.cursor()
        if query:
            cursor.execute(
                "SELECT strategy_name FROM Strategy WHERE creator_name = %s AND strategy_name LIKE %s ORDER BY strategy_name",
                (creator_name, f"{query}%"),
            )
        else:
            cursor.execute(
                "SELECT strategy_name FROM Strategy WHERE creator_name = %s ORDER BY strategy_name",
                (creator_name,),
            )

        strategies = [row["strategy_name"] for row in cursor.fetchall()]
        cursor.close()
        return strategies
    except Exception as e:
        logger.exception("搜索策略失败")
        return []


def search_params(creator_name: str, query: str = "") -> list:
    """搜索指定用户的参数"""
    try:
        connection = get_db_connection()
        if connection is None:
            return []

        cursor = connection.cursor()
        if query:
            cursor.execute(
                "SELECT param_name FROM Param WHERE creator_name = %s AND param_name LIKE %s ORDER BY param_name",
                (creator_name, f"{query}%"),
            )
        else:
            cursor.execute(
                "SELECT param_name FROM Param WHERE creator_name = %s ORDER BY param_name",
                (creator_name,),
            )

        params = [row["param_name"] for row in cursor.fetchall()]
        cursor.close()
        return params
    except Exception as e:
        logger.exception("搜索参数失败")
        return []


def search_indicators(creator_name: str, query: str = "") -> list:
    """搜索指定用户的指标"""
    try:
        connection = get_db_connection()
        if connection is None:
            return []

        cursor = connection.cursor()
        if query:
            cursor.execute(
                "SELECT indicator_name FROM Indicator WHERE creator_name = %s AND indicator_name LIKE %s ORDER BY indicator_name",
                (creator_name, f"{query}%"),
            )
        else:
            cursor.execute(
                "SELECT indicator_name FROM Indicator WHERE creator_name = %s ORDER BY indicator_name",
                (creator_name,),
            )

        indicators = [row["indicator_name"] for row in cursor.fetchall()]
        cursor.close()
        return indicators
    except Exception as e:
        logger.exception("搜索指标失败")
        return []


# 保留原来的数据源API作为兼容性支持
@app.route("/api/data-sources", methods=["GET"])
@token_required
def get_data_sources(current_user):
    """获取数据源列表接口（兼容性支持）"""
    try:
        # 获取查询参数
        query = request.args.get("q", "").strip()

        # 使用新的智能搜索逻辑
        suggestions = handle_table_suggestions(query)

        return jsonify(
            {
                "data": suggestions[:50],  # 限制返回数量
                "message": "获取数据源列表成功",
            }
        )

    except Exception as e:
        logger.error(f"获取数据源列表过程中发生错误: {str(e)}")
        return jsonify({"message": f"获取数据源列表失败: {str(e)}"}), 500


# =============================================
# 策略管理相关API
# =============================================


# 获取策略列表API
@app.route("/api/strategies", methods=["GET"])
@token_required
def get_strategies(current_user):
    """获取策略列表接口"""
    try:
        # 获取查询参数
        page = int(request.args.get("page", 1))
        page_size = int(request.args.get("page_size", 10))
        search_keyword = request.args.get("search", "").strip()
        strategy_type_filter = request.args.get(
            "strategy_type", "all"
        )  # my, system, public, all
        scope_type_filter = request.args.get(
            "scope_type", "all"
        )  # all, single_stock, index

        connection = get_db_connection()
        try:
            cursor = connection.cursor()

            # 构建基础查询SQL
            base_sql = """
            SELECT s.creator_name, s.strategy_name, s.public, s.scope_type, s.scope_id,
                   s.benchmark_index,
                   s.select_func, s.risk_control_func, s.position_count, s.rebalance_interval,
                   s.buy_fee_rate, s.sell_fee_rate, s.strategy_desc, 
                   s.create_time, s.update_time
            FROM Strategy s
            WHERE 1=1
            """

            # 构建查询条件和参数
            conditions = []
            params = []

            # 根据策略类型筛选
            if strategy_type_filter == "my":
                conditions.append("s.creator_name = %s")
                params.append(current_user["user_name"])
            elif strategy_type_filter == "system":
                conditions.append("s.creator_name = 'system'")
            elif strategy_type_filter == "public":
                # 公开策略：只显示其他普通用户的公开策略（不包括系统策略和自己的策略）
                conditions.append(
                    "s.public = TRUE AND s.creator_name != 'system' AND s.creator_name != %s"
                )
                params.append(current_user["user_name"])

            # 根据搜索关键词筛选
            if search_keyword:
                conditions.append(
                    "(s.strategy_name LIKE %s OR s.strategy_desc LIKE %s)"
                )
                keyword_pattern = f"%{search_keyword}%"
                params.extend([keyword_pattern, keyword_pattern])

            # 根据生效范围筛选
            if scope_type_filter != "all":
                conditions.append("s.scope_type = %s")
                params.append(scope_type_filter)

            # 拼接条件
            if conditions:
                base_sql += " AND " + " AND ".join(conditions)

            # 添加排序
            base_sql += " ORDER BY s.update_time DESC"

            # 执行查询获取总数
            count_sql = (
                f"SELECT COUNT(*) as total FROM ({base_sql}) as counted_strategies"
            )
            cursor.execute(count_sql, params)
            total = cursor.fetchone()["total"]

            # 添加分页
            base_sql += " LIMIT %s OFFSET %s"
            offset = (page - 1) * page_size
            params.extend([page_size, offset])

            # 执行分页查询
            cursor.execute(base_sql, params)
            strategies = cursor.fetchall()

            # 格式化时间字段
            for strategy in strategies:
                if strategy["create_time"]:
                    strategy["create_time"] = strategy["create_time"].strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )
                if strategy["update_time"]:
                    strategy["update_time"] = strategy["update_time"].strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )

            return jsonify(
                {
                    "code": 200,
                    "message": "获取策略列表成功",
                    "data": {
                        "strategies": strategies,
                        "total": total,
                        "page": page,
                        "page_size": page_size,
                    },
                }
            )

        finally:
            connection.close()

    except Exception as e:
        logger.error(f"获取策略列表过程中发生错误: {str(e)}")
        return jsonify({"code": 500, "message": "获取策略列表失败，请重试"})


# 创建策略API
@app.route("/api/strategies", methods=["POST"])
@token_required
def create_strategy(current_user):
    """创建策略接口"""
    try:
        data = request.get_json()

        # 验证必填字段
        required_fields = ["strategy_name", "scope_type", "select_func"]
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({"code": 400, "message": f"缺少必填字段: {field}"})

        strategy_name = str(data["strategy_name"]).strip()
        public = bool(data.get("public", True))
        scope_type = data["scope_type"]
        scope_id = (
            str(data.get("scope_id", "")).strip() if data.get("scope_id") else None
        )
        select_func = str(data["select_func"]).strip()
        benchmark_index = (
            str(data.get("benchmark_index", "")).strip()
            if data.get("benchmark_index")
            else None
        )
        risk_control_func = (
            str(data.get("risk_control_func", "")).strip()
            if data.get("risk_control_func")
            else None
        )
        position_count = data.get("position_count")
        rebalance_interval = data.get("rebalance_interval")
        buy_fee_rate = float(data.get("buy_fee_rate", 0.001))
        sell_fee_rate = float(data.get("sell_fee_rate", 0.001))
        strategy_desc = (
            str(data.get("strategy_desc", "")).strip()
            if data.get("strategy_desc")
            else None
        )

        # 验证数据格式
        if not strategy_name:
            return jsonify({"code": 400, "message": "策略名称不能为空"})

        if scope_type not in ["all", "single_stock", "index"]:
            return jsonify({"code": 400, "message": "生效范围类型无效"})

        if scope_type != "all" and not scope_id:
            return jsonify(
                {"code": 400, "message": "当生效范围不是全部时，必须指定股票/指数ID"}
            )

        if scope_type != "single_stock":
            if not position_count or position_count <= 0:
                return jsonify({"code": 400, "message": "持仓数量必须大于0"})
            if not rebalance_interval or rebalance_interval <= 0:
                return jsonify({"code": 400, "message": "调仓间隔必须大于0"})

        # 验证 benchmark_index 长度（可选）
        if benchmark_index and len(benchmark_index) > 20:
            return jsonify({"code": 400, "message": "基准指数代码长度不能超过20"})

        # 验证策略名格式（仅允许中文、英文、数字、下划线）
        if not re.match(r"^[\u4e00-\u9fa5a-zA-Z0-9_]+$", strategy_name):
            return jsonify(
                {"code": 400, "message": "策略名称只能包含中文、英文、数字和下划线"}
            )

        connection = get_db_connection()
        try:
            cursor = connection.cursor()

            # 检查策略名是否已存在（同一创建者）
            check_sql = "SELECT COUNT(*) as count FROM Strategy WHERE creator_name = %s AND strategy_name = %s"
            cursor.execute(check_sql, (current_user["user_name"], strategy_name))
            if cursor.fetchone()["count"] > 0:
                return jsonify({"code": 400, "message": "策略名称已存在"})

            # 插入策略记录
            insert_sql = """
            INSERT INTO Strategy 
            (creator_name, strategy_name, public, scope_type, scope_id, benchmark_index, select_func, 
             risk_control_func, position_count, rebalance_interval, buy_fee_rate, 
             sell_fee_rate, strategy_desc, create_time, update_time)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
            """

            cursor.execute(
                insert_sql,
                (
                    current_user["user_name"],
                    strategy_name,
                    public,
                    scope_type,
                    scope_id,
                    benchmark_index,
                    select_func,
                    risk_control_func,
                    position_count,
                    rebalance_interval,
                    buy_fee_rate,
                    sell_fee_rate,
                    strategy_desc,
                ),
            )

            connection.commit()

            return jsonify(
                {
                    "code": 200,
                    "message": "策略创建成功",
                    "data": {
                        "creator_name": current_user["user_name"],
                        "strategy_name": strategy_name,
                    },
                }
            )

        finally:
            connection.close()

    except Exception as e:
        logger.error(f"创建策略过程中发生错误: {str(e)}")
        return jsonify({"code": 500, "message": "创建策略失败，请重试"})


# 获取策略详情API
@app.route("/api/strategies/<creator_name>/<strategy_name>", methods=["GET"])
@token_required
def get_strategy_detail(current_user, creator_name, strategy_name):
    """获取策略详情接口"""
    try:
        connection = get_db_connection()
        try:
            cursor = connection.cursor()

            # 查询策略详情
            select_sql = """
            SELECT s.creator_name, s.strategy_name, s.public, s.scope_type, s.scope_id,
                   s.benchmark_index,
                   s.select_func, s.risk_control_func, s.position_count, s.rebalance_interval,
                   s.buy_fee_rate, s.sell_fee_rate, s.strategy_desc, 
                   s.create_time, s.update_time
            FROM Strategy s
            WHERE s.creator_name = %s AND s.strategy_name = %s
            """

            cursor.execute(select_sql, (creator_name, strategy_name))
            strategy = cursor.fetchone()

            if not strategy:
                return jsonify({"code": 404, "message": "策略不存在"})

            # 检查访问权限（如果不是公开策略且不是创建者，则不能访问）
            if (
                not strategy["public"]
                and strategy["creator_name"] != current_user["user_name"]
            ):
                return jsonify({"code": 403, "message": "无权限访问此策略"})

            # 格式化时间字段
            if strategy["create_time"]:
                strategy["create_time"] = strategy["create_time"].strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
            if strategy["update_time"]:
                strategy["update_time"] = strategy["update_time"].strftime(
                    "%Y-%m-%d %H:%M:%S"
                )

            return jsonify(
                {"code": 200, "message": "获取策略详情成功", "data": strategy}
            )

        finally:
            connection.close()

    except Exception as e:
        logger.error(f"获取策略详情过程中发生错误: {str(e)}")
        return jsonify({"code": 500, "message": "获取策略详情失败，请重试"})


# 更新策略API
@app.route("/api/strategies/<creator_name>/<strategy_name>", methods=["PUT"])
@token_required
def update_strategy(current_user, creator_name, strategy_name):
    """更新策略接口"""
    try:
        # 权限检查：只能更新自己创建的策略
        if creator_name != current_user["user_name"]:
            return jsonify({"code": 403, "message": "无权限修改此策略"})

        data = request.get_json()

        # 验证必填字段
        required_fields = ["strategy_name", "scope_type", "select_func"]
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({"code": 400, "message": f"缺少必填字段: {field}"})

        new_strategy_name = str(data["strategy_name"]).strip()
        public = bool(data.get("public", True))
        scope_type = data["scope_type"]
        scope_id = (
            str(data.get("scope_id", "")).strip() if data.get("scope_id") else None
        )
        select_func = str(data["select_func"]).strip()
        benchmark_index = (
            str(data.get("benchmark_index", "")).strip()
            if data.get("benchmark_index")
            else None
        )
        risk_control_func = (
            str(data.get("risk_control_func", "")).strip()
            if data.get("risk_control_func")
            else None
        )
        position_count = data.get("position_count")
        rebalance_interval = data.get("rebalance_interval")
        buy_fee_rate = float(data.get("buy_fee_rate", 0.001))
        sell_fee_rate = float(data.get("sell_fee_rate", 0.001))
        strategy_desc = (
            str(data.get("strategy_desc", "")).strip()
            if data.get("strategy_desc")
            else None
        )

        # 验证数据格式
        if not new_strategy_name:
            return jsonify({"code": 400, "message": "策略名称不能为空"})

        if scope_type not in ["all", "single_stock", "index"]:
            return jsonify({"code": 400, "message": "生效范围类型无效"})

        if scope_type != "all" and not scope_id:
            return jsonify(
                {"code": 400, "message": "当生效范围不是全部时，必须指定股票/指数ID"}
            )

        if scope_type != "single_stock":
            if not position_count or position_count <= 0:
                return jsonify({"code": 400, "message": "持仓数量必须大于0"})
            if not rebalance_interval or rebalance_interval <= 0:
                return jsonify({"code": 400, "message": "调仓间隔必须大于0"})

        # 验证策略名格式
        if not re.match(r"^[\u4e00-\u9fa5a-zA-Z0-9_]+$", new_strategy_name):
            return jsonify(
                {"code": 400, "message": "策略名称只能包含中文、英文、数字和下划线"}
            )

        # 验证 benchmark_index 长度（可选）
        if benchmark_index and len(benchmark_index) > 20:
            return jsonify({"code": 400, "message": "基准指数代码长度不能超过20"})

        connection = get_db_connection()
        try:
            cursor = connection.cursor()

            # 检查策略是否存在
            check_sql = "SELECT COUNT(*) as count FROM Strategy WHERE creator_name = %s AND strategy_name = %s"
            cursor.execute(check_sql, (creator_name, strategy_name))
            if cursor.fetchone()["count"] == 0:
                return jsonify({"code": 404, "message": "策略不存在"})

            # 如果策略名发生变化，检查新名称是否已存在
            if new_strategy_name != strategy_name:
                check_new_name_sql = "SELECT COUNT(*) as count FROM Strategy WHERE creator_name = %s AND strategy_name = %s"
                cursor.execute(check_new_name_sql, (creator_name, new_strategy_name))
                if cursor.fetchone()["count"] > 0:
                    return jsonify({"code": 400, "message": "新策略名称已存在"})

            # 更新策略记录
            update_sql = """
            UPDATE Strategy 
            SET strategy_name = %s, public = %s, scope_type = %s, scope_id = %s, 
                benchmark_index = %s,
                select_func = %s, risk_control_func = %s, position_count = %s, 
                rebalance_interval = %s, buy_fee_rate = %s, sell_fee_rate = %s, 
                strategy_desc = %s, update_time = NOW()
            WHERE creator_name = %s AND strategy_name = %s
            """

            cursor.execute(
                update_sql,
                (
                    new_strategy_name,
                    public,
                    scope_type,
                    scope_id,
                    benchmark_index,
                    select_func,
                    risk_control_func,
                    position_count,
                    rebalance_interval,
                    buy_fee_rate,
                    sell_fee_rate,
                    strategy_desc,
                    creator_name,
                    strategy_name,
                ),
            )

            # 如果策略名发生变化，需要更新相关的关联表
            if new_strategy_name != strategy_name:
                # 更新策略参数关系表
                update_strategy_rel_sql = """
                UPDATE StrategyParamRel 
                SET strategy_name = %s 
                WHERE strategy_creator_name = %s AND strategy_name = %s
                """
                cursor.execute(
                    update_strategy_rel_sql,
                    (new_strategy_name, creator_name, strategy_name),
                )

                # 更新交易信号表
                update_signal_sql = """
                UPDATE TradingSignal 
                SET strategy_name = %s 
                WHERE creator_name = %s AND strategy_name = %s
                """
                cursor.execute(
                    update_signal_sql, (new_strategy_name, creator_name, strategy_name)
                )

                # 更新回测报告表
                update_backtest_sql = """
                UPDATE BacktestReport 
                SET strategy_name = %s 
                WHERE creator_name = %s AND strategy_name = %s
                """
                cursor.execute(
                    update_backtest_sql,
                    (new_strategy_name, creator_name, strategy_name),
                )

            connection.commit()

            return jsonify(
                {
                    "code": 200,
                    "message": "策略更新成功",
                    "data": {
                        "creator_name": creator_name,
                        "strategy_name": new_strategy_name,
                        "benchmark_index": benchmark_index,
                    },
                }
            )

        finally:
            connection.close()

    except Exception as e:
        logger.error(f"更新策略过程中发生错误: {str(e)}")
        return jsonify({"code": 500, "message": "更新策略失败，请重试"})


# 删除策略API
@app.route("/api/strategies/<creator_name>/<strategy_name>", methods=["DELETE"])
@token_required
def delete_strategy(current_user, creator_name, strategy_name):
    """删除策略接口"""
    try:
        # 权限检查：只能删除自己创建的策略
        if creator_name != current_user["user_name"]:
            return jsonify({"code": 403, "message": "无权限删除此策略"})

        connection = get_db_connection()
        try:
            cursor = connection.cursor()

            # 检查策略是否存在
            check_sql = "SELECT COUNT(*) as count FROM Strategy WHERE creator_name = %s AND strategy_name = %s"
            cursor.execute(check_sql, (creator_name, strategy_name))
            if cursor.fetchone()["count"] == 0:
                return jsonify({"code": 404, "message": "策略不存在"})

            # 检查是否有关联的回测报告
            check_backtest_sql = "SELECT COUNT(*) as count FROM BacktestReport WHERE creator_name = %s AND strategy_name = %s"
            cursor.execute(check_backtest_sql, (creator_name, strategy_name))
            backtest_count = cursor.fetchone()["count"]

            if backtest_count > 0:
                return jsonify(
                    {
                        "code": 400,
                        "message": f"策略已有 {backtest_count} 个回测报告，不能删除",
                    }
                )

            # 删除相关记录（先删除外键约束的表）
            # 1. 删除策略参数关系
            cursor.execute(
                "DELETE FROM StrategyParamRel WHERE strategy_creator_name = %s AND strategy_name = %s",
                (creator_name, strategy_name),
            )

            # 2. 删除交易信号
            cursor.execute(
                "DELETE FROM TradingSignal WHERE creator_name = %s AND strategy_name = %s",
                (creator_name, strategy_name),
            )

            # 3. 删除策略主记录
            cursor.execute(
                "DELETE FROM Strategy WHERE creator_name = %s AND strategy_name = %s",
                (creator_name, strategy_name),
            )

            connection.commit()

            return jsonify({"code": 200, "message": "策略删除成功"})

        finally:
            connection.close()

    except Exception as e:
        logger.error(f"删除策略过程中发生错误: {str(e)}")
        return jsonify({"code": 500, "message": "删除策略失败，请重试"})


# 复制策略API
@app.route("/api/strategies/<creator_name>/<strategy_name>/copy", methods=["POST"])
@token_required
def copy_strategy(current_user, creator_name, strategy_name):
    """复制策略接口（包含深度复制参数关系）"""
    try:
        data = request.get_json()
        new_strategy_name = data.get("strategy_name", "").strip()
        new_description = data.get("description", "").strip()

        if not new_strategy_name:
            return jsonify({"code": 400, "message": "新策略名称不能为空"})

        # 验证策略名格式（仅允许中文、英文、数字、下划线）
        if not re.match(r"^[\u4e00-\u9fa5a-zA-Z0-9_]+$", new_strategy_name):
            return jsonify(
                {"code": 400, "message": "策略名称只能包含中文、英文、数字和下划线"}
            )

        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                current_user_name = current_user["user_name"]

                # 检查源策略是否存在
                check_strategy_sql = """
                SELECT * FROM Strategy 
                WHERE creator_name = %s AND strategy_name = %s
                """
                cursor.execute(check_strategy_sql, (creator_name, strategy_name))
                source_strategy = cursor.fetchone()

                if not source_strategy:
                    return jsonify({"code": 404, "message": "源策略不存在"})

                # 检查访问权限（如果不是公开策略且不是创建者，则不能复制）
                if (
                    not source_strategy["public"]
                    and source_strategy["creator_name"] != current_user_name
                ):
                    return jsonify({"code": 403, "message": "无权限复制此策略"})

                # 检查新策略名是否已存在
                check_name_sql = """
                SELECT COUNT(*) as count FROM Strategy 
                WHERE creator_name = %s AND strategy_name = %s
                """
                cursor.execute(check_name_sql, (current_user_name, new_strategy_name))
                if cursor.fetchone()["count"] > 0:
                    return jsonify({"code": 400, "message": "策略名称已存在"})

                # 获取策略的所有参数关系
                get_params_sql = """
                SELECT param_creator_name, param_name 
                FROM StrategyParamRel 
                WHERE strategy_creator_name = %s AND strategy_name = %s
                """
                cursor.execute(get_params_sql, (creator_name, strategy_name))
                param_relations = cursor.fetchall()

                # 收集需要复制的参数和指标（递归处理依赖）
                params_to_copy = set()  # (creator_name, param_name)
                indicators_to_copy = set()  # (creator_name, indicator_name)
                copied_params = {}  # 原参数 -> 新参数映射
                copied_indicators = {}  # 原指标 -> 新指标映射

                def collect_dependencies(param_creator, param_name):
                    """递归收集参数和指标的依赖关系"""
                    param_key = (param_creator, param_name)

                    # 如果已经处理过，跳过
                    if param_key in params_to_copy:
                        return

                    # 获取参数详情
                    param_sql = """
                    SELECT * FROM Param 
                    WHERE creator_name = %s AND param_name = %s
                    """
                    cursor.execute(param_sql, (param_creator, param_name))
                    param_info = cursor.fetchone()

                    if not param_info:
                        return

                    # 如果参数不是当前用户的且不是系统的，需要复制
                    if param_creator != current_user_name and param_creator != "system":
                        params_to_copy.add(param_key)

                        # 如果参数类型是指标，处理指标依赖
                        if param_info["param_type"] == "indicator":
                            indicator_id = param_info["data_id"]
                            try:
                                indicator_creator, indicator_name = indicator_id.split(
                                    ".", 1
                                )
                                indicator_key = (indicator_creator, indicator_name)

                                # 如果指标不是当前用户的且不是系统的，需要复制
                                if (
                                    indicator_creator != current_user_name
                                    and indicator_creator != "system"
                                ):
                                    indicators_to_copy.add(indicator_key)

                                    # 递归处理指标的参数依赖
                                    indicator_params_sql = """
                                    SELECT param_creator_name, param_name 
                                    FROM IndicatorParamRel 
                                    WHERE indicator_creator_name = %s AND indicator_name = %s
                                    """
                                    cursor.execute(
                                        indicator_params_sql,
                                        (indicator_creator, indicator_name),
                                    )
                                    for rel in cursor.fetchall():
                                        collect_dependencies(
                                            rel["param_creator_name"], rel["param_name"]
                                        )
                            except ValueError:
                                pass  # 忽略格式错误的指标ID

                # 收集所有需要复制的依赖
                for rel in param_relations:
                    collect_dependencies(rel["param_creator_name"], rel["param_name"])

                # 复制指标
                for indicator_creator, indicator_name in indicators_to_copy:
                    # 生成新指标名
                    new_indicator_name = f"{current_user_name}_{indicator_name}"
                    counter = 1
                    while True:
                        check_indicator_sql = """
                        SELECT COUNT(*) as count FROM Indicator 
                        WHERE creator_name = %s AND indicator_name = %s
                        """
                        cursor.execute(
                            check_indicator_sql, (current_user_name, new_indicator_name)
                        )
                        if cursor.fetchone()["count"] == 0:
                            break
                        new_indicator_name = (
                            f"{current_user_name}_{indicator_name}_{counter}"
                        )
                        counter += 1

                    # 复制指标
                    copy_indicator_sql = """
                    INSERT INTO Indicator 
                    (creator_name, indicator_name, calculation_method, description, is_active, create_time, update_time)
                    SELECT %s, %s, calculation_method, 
                           CONCAT('复制自: ', creator_name, '.', indicator_name, 
                                  CASE WHEN description IS NOT NULL THEN CONCAT(' - ', description) ELSE '' END),
                           is_active, NOW(), NOW()
                    FROM Indicator 
                    WHERE creator_name = %s AND indicator_name = %s
                    """
                    cursor.execute(
                        copy_indicator_sql,
                        (
                            current_user_name,
                            new_indicator_name,
                            indicator_creator,
                            indicator_name,
                        ),
                    )

                    copied_indicators[(indicator_creator, indicator_name)] = (
                        current_user_name,
                        new_indicator_name,
                    )

                # 复制参数
                for param_creator, param_name in params_to_copy:
                    # 生成新参数名
                    new_param_name = f"{current_user_name}_{param_name}"
                    counter = 1
                    while True:
                        check_param_sql = """
                        SELECT COUNT(*) as count FROM Param 
                        WHERE creator_name = %s AND param_name = %s
                        """
                        cursor.execute(
                            check_param_sql, (current_user_name, new_param_name)
                        )
                        if cursor.fetchone()["count"] == 0:
                            break
                        new_param_name = f"{current_user_name}_{param_name}_{counter}"
                        counter += 1

                    # 获取原参数信息
                    param_sql = """
                    SELECT * FROM Param 
                    WHERE creator_name = %s AND param_name = %s
                    """
                    cursor.execute(param_sql, (param_creator, param_name))
                    param_info = cursor.fetchone()

                    # 处理data_id（如果是指标类型）
                    new_data_id = param_info["data_id"]
                    if param_info["param_type"] == "indicator":
                        try:
                            orig_indicator_creator, orig_indicator_name = param_info[
                                "data_id"
                            ].split(".", 1)
                            if (
                                orig_indicator_creator,
                                orig_indicator_name,
                            ) in copied_indicators:
                                new_indicator_creator, new_indicator_name = (
                                    copied_indicators[
                                        (orig_indicator_creator, orig_indicator_name)
                                    ]
                                )
                                new_data_id = (
                                    f"{new_indicator_creator}.{new_indicator_name}"
                                )
                        except ValueError:
                            pass

                    # 复制参数
                    copy_param_sql = """
                    INSERT INTO Param 
                    (creator_name, param_name, param_type, data_id, pre_period, post_period, agg_func, creation_time, update_time)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                    """
                    cursor.execute(
                        copy_param_sql,
                        (
                            current_user_name,
                            new_param_name,
                            param_info["param_type"],
                            new_data_id,
                            param_info.get("pre_period", 0),
                            param_info.get("post_period", 0),
                            param_info.get("agg_func"),
                        ),
                    )

                    copied_params[(param_creator, param_name)] = (
                        current_user_name,
                        new_param_name,
                    )

                # 复制指标参数关系
                for (indicator_creator, indicator_name), (
                    new_indicator_creator,
                    new_indicator_name,
                ) in copied_indicators.items():
                    # 获取原指标的参数关系
                    orig_relations_sql = """
                    SELECT param_creator_name, param_name 
                    FROM IndicatorParamRel 
                    WHERE indicator_creator_name = %s AND indicator_name = %s
                    """
                    cursor.execute(
                        orig_relations_sql, (indicator_creator, indicator_name)
                    )

                    for rel in cursor.fetchall():
                        # 确定使用的参数（复制的或原有的）
                        rel_key = (rel["param_creator_name"], rel["param_name"])
                        if rel_key in copied_params:
                            final_param_creator, final_param_name = copied_params[
                                rel_key
                            ]
                        else:
                            final_param_creator, final_param_name = (
                                rel["param_creator_name"],
                                rel["param_name"],
                            )

                        # 创建新的指标参数关系
                        copy_relation_sql = """
                        INSERT INTO IndicatorParamRel 
                        (indicator_creator_name, indicator_name, param_creator_name, param_name)
                        VALUES (%s, %s, %s, %s)
                        """
                        cursor.execute(
                            copy_relation_sql,
                            (
                                new_indicator_creator,
                                new_indicator_name,
                                final_param_creator,
                                final_param_name,
                            ),
                        )

                # 复制策略
                copy_strategy_sql = """
                INSERT INTO Strategy 
                (creator_name, strategy_name, public, scope_type, scope_id, benchmark_index,
                 select_func, risk_control_func, position_count, rebalance_interval,
                 buy_fee_rate, sell_fee_rate, strategy_desc, create_time, update_time)
                SELECT %s, %s, %s, scope_type, scope_id, benchmark_index,
                       select_func, risk_control_func, position_count, rebalance_interval,
                       buy_fee_rate, sell_fee_rate, 
                       CONCAT('复制自: ', creator_name, '.', strategy_name,
                              CASE WHEN %s != '' THEN CONCAT(' - ', %s) 
                                   WHEN strategy_desc IS NOT NULL THEN CONCAT(' - ', strategy_desc)
                                   ELSE '' END),
                       NOW(), NOW()
                FROM Strategy 
                WHERE creator_name = %s AND strategy_name = %s
                """
                cursor.execute(
                    copy_strategy_sql,
                    (
                        current_user_name,
                        new_strategy_name,
                        False,  # 复制的策略默认为私有
                        new_description,
                        new_description,
                        creator_name,
                        strategy_name,
                    ),
                )

                # 复制策略参数关系
                for rel in param_relations:
                    rel_key = (rel["param_creator_name"], rel["param_name"])
                    if rel_key in copied_params:
                        final_param_creator, final_param_name = copied_params[rel_key]
                    else:
                        final_param_creator, final_param_name = (
                            rel["param_creator_name"],
                            rel["param_name"],
                        )

                    copy_strategy_rel_sql = """
                    INSERT INTO StrategyParamRel 
                    (strategy_creator_name, strategy_name, param_creator_name, param_name)
                    VALUES (%s, %s, %s, %s)
                    """
                    cursor.execute(
                        copy_strategy_rel_sql,
                        (
                            current_user_name,
                            new_strategy_name,
                            final_param_creator,
                            final_param_name,
                        ),
                    )

                connection.commit()

                return jsonify(
                    {
                        "code": 200,
                        "message": "策略复制成功，已自动复制相关参数和指标",
                        "data": {
                            "creator_name": current_user_name,
                            "strategy_name": new_strategy_name,
                            "copied_indicators": len(copied_indicators),
                            "copied_params": len(copied_params),
                        },
                    }
                )

        finally:
            connection.close()

    except Exception as e:
        logger.error(f"复制策略过程中发生错误: {str(e)}")
        return jsonify({"code": 500, "message": f"复制策略失败: {str(e)}"})


# 获取策略参数列表API
@app.route("/api/strategies/<creator_name>/<strategy_name>/params", methods=["GET"])
@token_required
def get_strategy_params(current_user, creator_name, strategy_name):
    """获取策略参数列表接口"""
    try:
        connection = get_db_connection()
        try:
            cursor = connection.cursor()

            # 首先检查策略是否存在和权限
            strategy_check_sql = """
            SELECT public FROM Strategy 
            WHERE creator_name = %s AND strategy_name = %s
            """
            cursor.execute(strategy_check_sql, (creator_name, strategy_name))
            strategy_info = cursor.fetchone()

            if not strategy_info:
                return jsonify({"code": 404, "message": "策略不存在"})

            # 检查访问权限
            if (
                not strategy_info["public"]
                and creator_name != current_user["user_name"]
            ):
                return jsonify({"code": 403, "message": "无权限访问此策略的参数"})

            # 查询策略关联的参数
            select_sql = """
            SELECT p.creator_name, p.param_name, p.data_id, p.param_type, 
                   p.pre_period, p.post_period, p.agg_func, 
                   p.creation_time, p.update_time
            FROM StrategyParamRel spr
            JOIN Param p ON spr.param_creator_name = p.creator_name 
                         AND spr.param_name = p.param_name
            WHERE spr.strategy_creator_name = %s AND spr.strategy_name = %s
            ORDER BY p.creation_time ASC
            """

            cursor.execute(select_sql, (creator_name, strategy_name))
            params = cursor.fetchall()

            # 格式化时间字段
            for param in params:
                if param["creation_time"]:
                    param["creation_time"] = param["creation_time"].strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )
                if param["update_time"]:
                    param["update_time"] = param["update_time"].strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )

            return jsonify({"code": 200, "message": "获取策略参数成功", "data": params})

        finally:
            connection.close()

    except Exception as e:
        logger.error(f"获取策略参数过程中发生错误: {str(e)}")
        return jsonify({"code": 500, "message": "获取策略参数失败，请重试"})


# 添加策略参数关系API
@app.route("/api/strategies/<creator_name>/<strategy_name>/params", methods=["POST"])
@token_required
def add_strategy_param(current_user, creator_name, strategy_name):
    """添加策略参数关系接口"""
    try:
        # 权限检查：只能修改自己创建的策略
        if creator_name != current_user["user_name"]:
            return jsonify({"code": 403, "message": "无权限修改此策略"})

        data = request.get_json()
        param_creator_name = data.get("param_creator_name", "").strip()
        param_name = data.get("param_name", "").strip()

        if not param_creator_name or not param_name:
            return jsonify({"code": 400, "message": "参数创建者和参数名不能为空"})

        connection = get_db_connection()
        try:
            cursor = connection.cursor()

            # 检查策略是否存在
            strategy_check_sql = "SELECT COUNT(*) as count FROM Strategy WHERE creator_name = %s AND strategy_name = %s"
            cursor.execute(strategy_check_sql, (creator_name, strategy_name))
            if cursor.fetchone()["count"] == 0:
                return jsonify({"code": 404, "message": "策略不存在"})

            # 检查参数是否存在
            param_check_sql = "SELECT COUNT(*) as count FROM Param WHERE creator_name = %s AND param_name = %s"
            cursor.execute(param_check_sql, (param_creator_name, param_name))
            if cursor.fetchone()["count"] == 0:
                return jsonify({"code": 404, "message": "参数不存在"})

            # 检查关系是否已存在
            rel_check_sql = """
            SELECT COUNT(*) as count FROM StrategyParamRel 
            WHERE strategy_creator_name = %s AND strategy_name = %s 
              AND param_creator_name = %s AND param_name = %s
            """
            cursor.execute(
                rel_check_sql,
                (creator_name, strategy_name, param_creator_name, param_name),
            )
            if cursor.fetchone()["count"] > 0:
                return jsonify({"code": 400, "message": "参数关系已存在"})

            # 插入关系记录
            insert_sql = """
            INSERT INTO StrategyParamRel 
            (strategy_creator_name, strategy_name, param_creator_name, param_name)
            VALUES (%s, %s, %s, %s)
            """
            cursor.execute(
                insert_sql,
                (creator_name, strategy_name, param_creator_name, param_name),
            )

            connection.commit()

            return jsonify({"code": 200, "message": "添加策略参数关系成功"})

        finally:
            connection.close()

    except Exception as e:
        logger.error(f"添加策略参数关系过程中发生错误: {str(e)}")
        return jsonify({"code": 500, "message": "添加策略参数关系失败，请重试"})


# 删除策略参数关系API
@app.route(
    "/api/strategies/<creator_name>/<strategy_name>/params/<param_creator_name>/<param_name>",
    methods=["DELETE"],
)
@token_required
def remove_strategy_param(
    current_user, creator_name, strategy_name, param_creator_name, param_name
):
    """删除策略参数关系接口"""
    try:
        # 权限检查：只能修改自己创建的策略
        if creator_name != current_user["user_name"]:
            return jsonify({"code": 403, "message": "无权限修改此策略"})

        connection = get_db_connection()
        try:
            cursor = connection.cursor()

            # 检查关系是否存在
            check_sql = """
            SELECT COUNT(*) as count FROM StrategyParamRel 
            WHERE strategy_creator_name = %s AND strategy_name = %s 
              AND param_creator_name = %s AND param_name = %s
            """
            cursor.execute(
                check_sql, (creator_name, strategy_name, param_creator_name, param_name)
            )
            if cursor.fetchone()["count"] == 0:
                return jsonify({"code": 404, "message": "参数关系不存在"})

            # 删除关系记录
            delete_sql = """
            DELETE FROM StrategyParamRel 
            WHERE strategy_creator_name = %s AND strategy_name = %s 
              AND param_creator_name = %s AND param_name = %s
            """
            cursor.execute(
                delete_sql,
                (creator_name, strategy_name, param_creator_name, param_name),
            )

            connection.commit()

            return jsonify({"code": 200, "message": "删除策略参数关系成功"})

        finally:
            connection.close()

    except Exception as e:
        logger.error(f"删除策略参数关系过程中发生错误: {str(e)}")
        return jsonify({"code": 500, "message": "删除策略参数关系失败，请重试"})


# =============================================
# 指标管理相关API
# =============================================


# 获取指标列表API
@app.route("/api/indicators", methods=["GET"])
@token_required
def get_indicators(current_user):
    """获取指标列表接口"""
    try:
        # 获取查询参数
        page = int(request.args.get("page", 1))
        page_size = int(request.args.get("limit", 10))  # 前端发送的是 limit
        search_keyword = request.args.get("search", "").strip()
        creator_name_filter = request.args.get(
            "creator_name", ""
        ).strip()  # 前端直接发送creator_name
        is_enabled = request.args.get("is_enabled", "all")  # 前端发送的是 is_enabled

        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                # 获取当前用户信息
                user_sql = "SELECT user_name FROM User WHERE user_id = %s"
                cursor.execute(user_sql, (current_user["user_id"],))
                current_user_info = cursor.fetchone()

                if not current_user_info:
                    return jsonify({"message": "用户不存在"}), 404

                current_user_name = current_user_info["user_name"]

                # 构建基础查询SQL
                base_sql = """
                SELECT 
                    CONCAT(creator_name, '.', indicator_name) as id,
                    creator_name,
                    indicator_name,
                    calculation_method,
                    description,
                    is_active,
                    DATE_FORMAT(creation_time, '%%Y-%%m-%%d %%H:%%i:%%s') as create_time
                FROM Indicator
                WHERE 1=1
                """

                # 构建WHERE条件
                where_conditions = []
                query_params = []

                # 根据创建者筛选（前端直接发送creator_name）
                if creator_name_filter:
                    where_conditions.append("creator_name = %s")
                    query_params.append(creator_name_filter)

                # 根据状态筛选
                if is_enabled != "all":
                    where_conditions.append("is_active = %s")
                    query_params.append(int(is_enabled) == 1)

                # 根据搜索关键词筛选
                if search_keyword:
                    where_conditions.append(
                        "(indicator_name LIKE %s OR description LIKE %s)"
                    )
                    query_params.extend([f"%{search_keyword}%", f"%{search_keyword}%"])

                # 组装完整的查询SQL
                if where_conditions:
                    count_sql = f"SELECT COUNT(*) as total FROM Indicator WHERE {' AND '.join(where_conditions)}"
                    data_sql = f"{base_sql} AND {' AND '.join(where_conditions)} ORDER BY creator_name, indicator_name"
                else:
                    count_sql = "SELECT COUNT(*) as total FROM Indicator"
                    data_sql = f"{base_sql} ORDER BY creator_name, indicator_name"

                # 获取总数
                cursor.execute(count_sql, query_params)
                total_result = cursor.fetchone()
                total = total_result["total"] if total_result else 0

                # 分页查询数据
                offset = (page - 1) * page_size
                data_sql += f" LIMIT %s OFFSET %s"
                query_params.extend([page_size, offset])

                cursor.execute(data_sql, query_params)
                indicators = cursor.fetchall()

                # 格式化返回数据
                formatted_indicators = []
                for indicator in indicators:
                    formatted_indicators.append(
                        {
                            "id": indicator["id"],
                            "creator_name": indicator["creator_name"],
                            "indicator_name": indicator["indicator_name"],
                            "calculation_method": indicator["calculation_method"],
                            "description": indicator["description"],
                            "is_active": bool(indicator["is_active"]),
                            "create_time": indicator["create_time"],
                        }
                    )

                return (
                    jsonify(
                        {
                            "data": formatted_indicators,
                            "pagination": {
                                "total": total,
                                "page": page,
                                "page_size": page_size,
                                "pages": (total + page_size - 1) // page_size,
                            },
                            "message": "获取指标列表成功",
                        }
                    ),
                    200,
                )

        finally:
            connection.close()

    except Exception as e:
        logger.error(f"获取指标列表过程中发生错误: {str(e)}")
        return jsonify({"message": f"获取指标列表失败: {str(e)}"}), 500


# 复制指标API
@app.route("/api/indicators/<indicator_composite_id>/copy", methods=["POST"])
@token_required
def copy_indicator(current_user, indicator_composite_id):
    """复制指标接口，同时复制指标参数关系"""
    try:
        # 解析复合ID
        parts = indicator_composite_id.split(".")
        if len(parts) != 2:
            return jsonify({"message": "无效的指标ID格式"}), 400

        original_creator_name, original_indicator_name = parts

        # 获取请求数据
        data = request.get_json()
        new_indicator_name = data.get(
            "indicator_name", f"复制_{original_indicator_name}"
        )
        new_description = data.get("description", "")

        # 获取当前用户信息
        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                # 获取当前用户名
                cursor.execute(
                    "SELECT user_name FROM User WHERE user_id = %s",
                    (current_user["user_id"],),
                )
                user_info = cursor.fetchone()
                if not user_info:
                    return jsonify({"message": "用户不存在"}), 404

                current_user_name = user_info["user_name"]

                # 检查新指标名称是否已存在
                cursor.execute(
                    "SELECT 1 FROM Indicator WHERE creator_name = %s AND indicator_name = %s",
                    (current_user_name, new_indicator_name),
                )
                if cursor.fetchone():
                    return jsonify({"message": "指标名称已存在"}), 400

                # 获取原始指标信息
                cursor.execute(
                    "SELECT * FROM Indicator WHERE creator_name = %s AND indicator_name = %s",
                    (original_creator_name, original_indicator_name),
                )
                original_indicator = cursor.fetchone()
                if not original_indicator:
                    return jsonify({"message": "原始指标不存在"}), 404

                # 创建新指标
                cursor.execute(
                    """
                    INSERT INTO Indicator (creator_name, indicator_name, calculation_method, description, is_active)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (
                        current_user_name,
                        new_indicator_name,
                        original_indicator["calculation_method"],
                        new_description or original_indicator["description"],
                        True,
                    ),
                )

                # 复制指标参数关系
                cursor.execute(
                    """
                    SELECT param_creator_name, param_name 
                    FROM IndicatorParamRel 
                    WHERE indicator_creator_name = %s AND indicator_name = %s
                    """,
                    (original_creator_name, original_indicator_name),
                )
                param_relations = cursor.fetchall()

                for relation in param_relations:
                    cursor.execute(
                        """
                        INSERT INTO IndicatorParamRel (indicator_creator_name, indicator_name, param_creator_name, param_name)
                        VALUES (%s, %s, %s, %s)
                        """,
                        (
                            current_user_name,
                            new_indicator_name,
                            relation["param_creator_name"],
                            relation["param_name"],
                        ),
                    )

                connection.commit()

                return (
                    jsonify(
                        {
                            "message": "指标复制成功",
                            "data": {
                                "creator_name": current_user_name,
                                "indicator_name": new_indicator_name,
                            },
                        }
                    ),
                    200,
                )

        finally:
            connection.close()

    except Exception as e:
        logger.error(f"复制指标过程中发生错误: {str(e)}")
        return jsonify({"message": "复制指标失败，请重试"}), 500


# 创建指标API
@app.route("/api/indicators", methods=["POST"])
@token_required
def create_indicator(current_user):
    """创建指标接口"""
    try:
        data = request.get_json()

        # 验证必填字段
        required_fields = ["indicator_name", "calculation_method"]
        for field in required_fields:
            if field not in data or data[field] is None:
                return jsonify({"message": f"缺少必填字段: {field}"}), 400

        indicator_name = (
            str(data["indicator_name"]).strip()
            if data["indicator_name"] is not None
            else ""
        )
        calculation_method = (
            str(data["calculation_method"]).strip()
            if data["calculation_method"] is not None
            else ""
        )
        description = (
            str(data.get("description", "")).strip()
            if data.get("description")
            else None
        )
        is_active = bool(data.get("is_active", True))

        # 验证数据格式
        if not indicator_name or not calculation_method:
            return jsonify({"message": "指标名称和计算函数不能为空"}), 400

        # 验证指标名称格式（仅允许中英文、数字、下划线）
        if not re.match(r"^[a-zA-Z0-9_\u4e00-\u9fa5]+$", indicator_name):
            return jsonify({"message": "指标名称只能包含中英文、数字、下划线"}), 400

        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                # 获取当前用户信息
                user_sql = "SELECT user_name FROM User WHERE user_id = %s"
                cursor.execute(user_sql, (current_user["user_id"],))
                current_user_info = cursor.fetchone()

                if not current_user_info:
                    return jsonify({"message": "用户不存在"}), 404

                current_user_name = current_user_info["user_name"]

                # 检查指标名称是否已存在（同一创建者下）
                check_sql = "SELECT * FROM Indicator WHERE creator_name = %s AND indicator_name = %s"
                cursor.execute(check_sql, (current_user_name, indicator_name))
                if cursor.fetchone():
                    return (
                        jsonify({"message": f'指标名称 "{indicator_name}" 已存在'}),
                        400,
                    )

                # 插入新指标
                insert_sql = """
                INSERT INTO Indicator (creator_name, indicator_name, calculation_method, description, is_active)
                VALUES (%s, %s, %s, %s, %s)
                """
                cursor.execute(
                    insert_sql,
                    (
                        current_user_name,
                        indicator_name,
                        calculation_method,
                        description,
                        is_active,
                    ),
                )
                connection.commit()

                # 返回创建的指标信息
                new_indicator = {
                    "id": f"{current_user_name}_{indicator_name}",
                    "creator_name": current_user_name,
                    "indicator_name": indicator_name,
                    "calculation_method": calculation_method,
                    "description": description,
                    "is_active": is_active,
                    "create_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                }

                return jsonify({"data": new_indicator, "message": "指标创建成功"}), 201

        finally:
            connection.close()

    except Exception as e:
        logger.error(f"创建指标过程中发生错误: {str(e)}")
        return jsonify({"message": f"创建指标失败: {str(e)}"}), 500


# 更新指标API
@app.route("/api/indicators/<indicator_composite_id>", methods=["PUT"])
@token_required
def update_indicator(current_user, indicator_composite_id):
    """更新指标接口"""
    try:
        # 解析复合ID (格式: creator_name.indicator_name)
        try:
            parts = indicator_composite_id.split(".", 1)
            if len(parts) != 2:
                return jsonify({"message": "无效的指标ID格式"}), 400
            creator_name, indicator_name = parts
        except:
            return jsonify({"message": "无效的指标ID格式"}), 400

        data = request.get_json()

        # 验证必填字段
        required_fields = ["indicator_name", "calculation_method"]
        for field in required_fields:
            if field not in data or data[field] is None:
                return jsonify({"message": f"缺少必填字段: {field}"}), 400

        new_indicator_name = (
            str(data["indicator_name"]).strip()
            if data["indicator_name"] is not None
            else ""
        )
        calculation_method = (
            str(data["calculation_method"]).strip()
            if data["calculation_method"] is not None
            else ""
        )
        description = (
            str(data.get("description", "")).strip()
            if data.get("description")
            else None
        )
        is_active = bool(data.get("is_active", True))

        # 验证数据格式
        if not new_indicator_name or not calculation_method:
            return jsonify({"message": "指标名称和计算函数不能为空"}), 400

        # 验证指标名称格式
        if not re.match(r"^[a-zA-Z0-9_\u4e00-\u9fa5]+$", new_indicator_name):
            return jsonify({"message": "指标名称只能包含中英文、数字、下划线"}), 400

        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                # 获取当前用户信息
                user_sql = "SELECT user_name FROM User WHERE user_id = %s"
                cursor.execute(user_sql, (current_user["user_id"],))
                current_user_info = cursor.fetchone()

                if not current_user_info:
                    return jsonify({"message": "用户不存在"}), 404

                current_user_name = current_user_info["user_name"]

                # 检查指标是否存在
                check_sql = "SELECT * FROM Indicator WHERE creator_name = %s AND indicator_name = %s"
                cursor.execute(check_sql, (creator_name, indicator_name))
                existing_indicator = cursor.fetchone()

                if not existing_indicator:
                    return jsonify({"message": "指标不存在"}), 404

                # 检查权限（只能更新自己创建的指标）
                if creator_name != current_user_name:
                    return jsonify({"message": "无权限修改他人创建的指标"}), 403

                # 如果指标名称有变化，检查新名称是否已存在
                if new_indicator_name != indicator_name:
                    check_new_name_sql = "SELECT * FROM Indicator WHERE creator_name = %s AND indicator_name = %s"
                    cursor.execute(
                        check_new_name_sql, (creator_name, new_indicator_name)
                    )
                    if cursor.fetchone():
                        return (
                            jsonify(
                                {
                                    "message": f'新的指标名称 "{new_indicator_name}" 已存在'
                                }
                            ),
                            400,
                        )

                # 更新指标
                if new_indicator_name != indicator_name:
                    # 如果指标名称变化了，需要先更新关联关系，然后更新指标本身
                    # 更新指标参数关系表中的指标名称引用
                    update_indicator_rel_sql = """
                    UPDATE IndicatorParamRel 
                    SET indicator_name = %s 
                    WHERE indicator_creator_name = %s AND indicator_name = %s
                    """
                    cursor.execute(
                        update_indicator_rel_sql,
                        (new_indicator_name, creator_name, indicator_name),
                    )

                    # 更新指标表
                    update_sql = """
                    UPDATE Indicator 
                    SET indicator_name = %s, calculation_method = %s, description = %s, is_active = %s
                    WHERE creator_name = %s AND indicator_name = %s
                    """
                    cursor.execute(
                        update_sql,
                        (
                            new_indicator_name,
                            calculation_method,
                            description,
                            is_active,
                            creator_name,
                            indicator_name,
                        ),
                    )
                else:
                    # 只更新除indicator_name外的其他字段
                    update_sql = """
                    UPDATE Indicator 
                    SET calculation_method = %s, description = %s, is_active = %s
                    WHERE creator_name = %s AND indicator_name = %s
                    """
                    cursor.execute(
                        update_sql,
                        (
                            calculation_method,
                            description,
                            is_active,
                            creator_name,
                            indicator_name,
                        ),
                    )

                connection.commit()

                # 返回更新后的指标信息
                updated_indicator = {
                    "id": f"{creator_name}_{new_indicator_name}",
                    "creator_name": creator_name,
                    "indicator_name": new_indicator_name,
                    "calculation_method": calculation_method,
                    "description": description,
                    "is_active": is_active,
                    "create_time": existing_indicator.get(
                        "create_time", datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    ),
                }

                return (
                    jsonify({"data": updated_indicator, "message": "指标更新成功"}),
                    200,
                )

        finally:
            connection.close()

    except Exception as e:
        logger.error(f"更新指标过程中发生错误: {str(e)}")
        return jsonify({"message": f"更新指标失败: {str(e)}"}), 500


# 删除指标API
@app.route("/api/indicators/<indicator_composite_id>", methods=["DELETE"])
@token_required
def delete_indicator(current_user, indicator_composite_id):
    """删除指标接口"""
    try:
        # 解析复合ID (格式: creator_name.indicator_name)
        try:
            parts = indicator_composite_id.split(".", 1)
            if len(parts) != 2:
                return jsonify({"message": "无效的指标ID格式"}), 400
            creator_name, indicator_name = parts
        except:
            return jsonify({"message": "无效的指标ID格式"}), 400

        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                # 获取当前用户信息
                user_sql = "SELECT user_name FROM User WHERE user_id = %s"
                cursor.execute(user_sql, (current_user["user_id"],))
                current_user_info = cursor.fetchone()

                if not current_user_info:
                    return jsonify({"message": "用户不存在"}), 404

                current_user_name = current_user_info["user_name"]

                # 检查指标是否存在
                check_sql = "SELECT * FROM Indicator WHERE creator_name = %s AND indicator_name = %s"
                cursor.execute(check_sql, (creator_name, indicator_name))
                existing_indicator = cursor.fetchone()

                if not existing_indicator:
                    return jsonify({"message": "指标不存在"}), 404

                # 检查权限（只能删除自己创建的指标）
                if creator_name != current_user_name:
                    return jsonify({"message": "无权限删除他人创建的指标"}), 403

                # 检查指标是否被参数引用
                check_param_rel_sql = """
                SELECT COUNT(*) as count
                FROM Param p
                WHERE p.param_type = 'indicator' AND p.data_id LIKE %s
                """
                cursor.execute(
                    check_param_rel_sql, (f"{creator_name}.{indicator_name}%",)
                )
                param_usage = cursor.fetchone()

                if param_usage and param_usage["count"] > 0:
                    return (
                        jsonify(
                            {
                                "message": f'指标正在被 {param_usage["count"]} 个参数使用，无法删除。请先删除相关参数。'
                            }
                        ),
                        400,
                    )

                # 检查指标是否有参数关系
                check_indicator_rel_sql = """
                SELECT COUNT(*) as count
                FROM IndicatorParamRel ipr
                WHERE ipr.indicator_creator_name = %s AND ipr.indicator_name = %s
                """
                cursor.execute(check_indicator_rel_sql, (creator_name, indicator_name))
                rel_count = cursor.fetchone()

                # 删除指标参数关系（如果有）
                if rel_count and rel_count["count"] > 0:
                    delete_rel_sql = """
                    DELETE FROM IndicatorParamRel 
                    WHERE indicator_creator_name = %s AND indicator_name = %s
                    """
                    cursor.execute(delete_rel_sql, (creator_name, indicator_name))

                # 删除指标
                delete_sql = "DELETE FROM Indicator WHERE creator_name = %s AND indicator_name = %s"
                cursor.execute(delete_sql, (creator_name, indicator_name))
                connection.commit()

                return jsonify({"message": "指标删除成功"}), 200

        finally:
            connection.close()

    except Exception as e:
        logger.error(f"删除指标过程中发生错误: {str(e)}")
        return jsonify({"message": f"删除指标失败: {str(e)}"}), 500


# 获取指标参数关系列表API
@app.route("/api/indicator-param-relations", methods=["GET"])
@token_required
def get_indicator_param_relations(current_user):
    """获取指标参数关系列表"""
    try:
        # 获取查询参数
        indicator_creator = request.args.get("indicator_creator", "").strip()
        indicator_name = request.args.get("indicator_name", "").strip()
        param_creator = request.args.get("param_creator", "").strip()
        param_name = request.args.get("param_name", "").strip()
        page = int(request.args.get("page", 1))
        limit = int(request.args.get("limit", 10))

        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                # 构建查询条件
                conditions = []
                params = []

                if indicator_creator:
                    conditions.append("ipr.indicator_creator_name LIKE %s")
                    params.append(f"%{indicator_creator}%")

                if indicator_name:
                    conditions.append("ipr.indicator_name LIKE %s")
                    params.append(f"%{indicator_name}%")

                if param_creator:
                    conditions.append("ipr.param_creator_name LIKE %s")
                    params.append(f"%{param_creator}%")

                if param_name:
                    conditions.append("ipr.param_name LIKE %s")
                    params.append(f"%{param_name}%")

                where_clause = ""
                if conditions:
                    where_clause = "WHERE " + " AND ".join(conditions)

                # 查询总数
                count_sql = f"""
                SELECT COUNT(*) as total
                FROM IndicatorParamRel ipr
                {where_clause}
                """
                cursor.execute(count_sql, params)
                total_count = cursor.fetchone()["total"]

                # 查询数据
                offset = (page - 1) * limit
                sql = f"""
                SELECT 
                    ipr.*,
                    i.description AS indicator_description,
                    i.is_active AS indicator_active,
                    p.data_id,
                    p.param_type,
                    p.pre_period,
                    p.post_period,
                    p.agg_func
                FROM IndicatorParamRel ipr
                LEFT JOIN Indicator i ON ipr.indicator_creator_name = i.creator_name 
                    AND ipr.indicator_name = i.indicator_name
                LEFT JOIN Param p ON ipr.param_creator_name = p.creator_name 
                    AND ipr.param_name = p.param_name
                {where_clause}
                ORDER BY ipr.indicator_creator_name, ipr.indicator_name, ipr.param_creator_name, ipr.param_name
                LIMIT %s OFFSET %s
                """

                cursor.execute(sql, params + [limit, offset])
                relations = cursor.fetchall()

                return (
                    jsonify(
                        {
                            "data": relations,
                            "pagination": {
                                "page": page,
                                "limit": limit,
                                "total": total_count,
                                "pages": (total_count + limit - 1) // limit,
                            },
                        }
                    ),
                    200,
                )

        finally:
            connection.close()

    except Exception as e:
        logger.error(f"获取指标参数关系列表过程中发生错误: {str(e)}")
        return jsonify({"message": f"获取关系列表失败: {str(e)}"}), 500


# 创建指标参数关系API
@app.route("/api/indicator-param-relations", methods=["POST"])
@token_required
def create_indicator_param_relation(current_user):
    """创建指标参数关系"""
    try:
        data = request.get_json()

        # 验证必需字段
        required_fields = [
            "indicator_creator_name",
            "indicator_name",
            "param_creator_name",
            "param_name",
        ]
        for field in required_fields:
            if not data.get(field):
                return jsonify({"message": f"缺少必需字段: {field}"}), 400

        indicator_creator_name = data["indicator_creator_name"].strip()
        indicator_name = data["indicator_name"].strip()
        param_creator_name = data["param_creator_name"].strip()
        param_name = data["param_name"].strip()

        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                # 验证指标是否存在
                indicator_check_sql = "SELECT * FROM Indicator WHERE creator_name = %s AND indicator_name = %s"
                cursor.execute(
                    indicator_check_sql, (indicator_creator_name, indicator_name)
                )
                if not cursor.fetchone():
                    return jsonify({"message": "指定的指标不存在"}), 404

                # 验证参数是否存在
                param_check_sql = (
                    "SELECT * FROM Param WHERE creator_name = %s AND param_name = %s"
                )
                cursor.execute(param_check_sql, (param_creator_name, param_name))
                if not cursor.fetchone():
                    return jsonify({"message": "指定的参数不存在"}), 404

                # 检查关系是否已存在
                check_sql = """
                SELECT * FROM IndicatorParamRel 
                WHERE indicator_creator_name = %s AND indicator_name = %s 
                AND param_creator_name = %s AND param_name = %s
                """
                cursor.execute(
                    check_sql,
                    (
                        indicator_creator_name,
                        indicator_name,
                        param_creator_name,
                        param_name,
                    ),
                )
                if cursor.fetchone():
                    return jsonify({"message": "指标参数关系已存在"}), 400

                # 创建关系
                insert_sql = """
                INSERT INTO IndicatorParamRel 
                (indicator_creator_name, indicator_name, param_creator_name, param_name)
                VALUES (%s, %s, %s, %s)
                """
                cursor.execute(
                    insert_sql,
                    (
                        indicator_creator_name,
                        indicator_name,
                        param_creator_name,
                        param_name,
                    ),
                )
                connection.commit()

                # 返回创建的关系信息
                new_relation = {
                    "indicator_creator_name": indicator_creator_name,
                    "indicator_name": indicator_name,
                    "param_creator_name": param_creator_name,
                    "param_name": param_name,
                }

                return (
                    jsonify({"data": new_relation, "message": "指标参数关系创建成功"}),
                    201,
                )

        finally:
            connection.close()

    except Exception as e:
        logger.error(f"创建指标参数关系过程中发生错误: {str(e)}")
        return jsonify({"message": f"创建关系失败: {str(e)}"}), 500


# 删除指标参数关系API
@app.route("/api/indicator-param-relations/<path:relation_id>", methods=["DELETE"])
@token_required
def delete_indicator_param_relation(current_user, relation_id):
    """删除指标参数关系"""
    try:
        # 解析关系ID (格式: indicator_creator.indicator_name.param_creator.param_name)
        try:
            parts = relation_id.split(".")
            if len(parts) != 4:
                return (
                    jsonify(
                        {
                            "message": "无效的关系ID格式，应为indicator_creator.indicator_name.param_creator.param_name"
                        }
                    ),
                    400,
                )

            indicator_creator_name, indicator_name, param_creator_name, param_name = (
                parts
            )

        except Exception as parse_error:
            logger.error(f"解析关系ID失败: {str(parse_error)}")
            return jsonify({"message": "无效的关系ID格式"}), 400

        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                # 检查关系是否存在
                check_sql = """
                SELECT * FROM IndicatorParamRel 
                WHERE indicator_creator_name = %s AND indicator_name = %s 
                AND param_creator_name = %s AND param_name = %s
                """
                cursor.execute(
                    check_sql,
                    (
                        indicator_creator_name,
                        indicator_name,
                        param_creator_name,
                        param_name,
                    ),
                )
                if not cursor.fetchone():
                    return jsonify({"message": "指标参数关系不存在"}), 404

                # 删除关系
                delete_sql = """
                DELETE FROM IndicatorParamRel 
                WHERE indicator_creator_name = %s AND indicator_name = %s 
                AND param_creator_name = %s AND param_name = %s
                """
                cursor.execute(
                    delete_sql,
                    (
                        indicator_creator_name,
                        indicator_name,
                        param_creator_name,
                        param_name,
                    ),
                )
                connection.commit()

                return jsonify({"message": "指标参数关系删除成功"}), 200

        finally:
            connection.close()

    except Exception as e:
        logger.error(f"删除指标参数关系过程中发生错误: {str(e)}")
        return jsonify({"message": f"删除关系失败: {str(e)}"}), 500


# 切换指标状态API
@app.route("/api/indicators/<indicator_composite_id>/toggle-status", methods=["PUT"])
@token_required
def toggle_indicator_status(current_user, indicator_composite_id):
    """切换指标启用/禁用状态"""
    try:
        # 解析复合ID (格式: creator_name.indicator_name)
        try:
            parts = indicator_composite_id.split(".", 1)
            if len(parts) != 2:
                return jsonify({"message": "无效的指标ID格式"}), 400
            creator_name, indicator_name = parts
        except:
            return jsonify({"message": "无效的指标ID格式"}), 400

        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                # 获取当前用户信息
                user_sql = "SELECT user_name FROM User WHERE user_id = %s"
                cursor.execute(user_sql, (current_user["user_id"],))
                current_user_info = cursor.fetchone()

                if not current_user_info:
                    return jsonify({"message": "用户不存在"}), 404

                current_user_name = current_user_info["user_name"]

                # 检查指标是否存在
                check_sql = "SELECT * FROM Indicator WHERE creator_name = %s AND indicator_name = %s"
                cursor.execute(check_sql, (creator_name, indicator_name))
                existing_indicator = cursor.fetchone()

                if not existing_indicator:
                    return jsonify({"message": "指标不存在"}), 404

                # 检查权限（只能修改自己创建的指标状态）
                if creator_name != current_user_name:
                    return jsonify({"message": "无权限修改他人创建的指标状态"}), 403

                # 切换状态
                current_status = existing_indicator["is_active"]
                new_status = 0 if current_status == 1 else 1

                # 更新状态
                update_sql = """
                UPDATE Indicator 
                SET is_active = %s, update_time = %s 
                WHERE creator_name = %s AND indicator_name = %s
                """
                cursor.execute(
                    update_sql,
                    (new_status, datetime.now(), creator_name, indicator_name),
                )
                connection.commit()

                # 获取更新后的指标信息
                cursor.execute(check_sql, (creator_name, indicator_name))
                updated_indicator = cursor.fetchone()

                status_text = "启用" if new_status == 1 else "禁用"

                return (
                    jsonify(
                        {"data": updated_indicator, "message": f"指标已{status_text}"}
                    ),
                    200,
                )

        finally:
            connection.close()

    except Exception as e:
        logger.error(f"切换指标状态过程中发生错误: {str(e)}")
        return jsonify({"message": f"状态切换失败: {str(e)}"}), 500


# =============================================
# 消息管理相关API
# =============================================


# 获取消息列表API
@app.route("/api/messages", methods=["GET"])
@token_required
def get_messages(current_user):
    """获取用户消息列表接口"""
    try:
        page = int(request.args.get("page", 1))
        page_size = int(request.args.get("page_size", 10))
        status_filter = request.args.get("status", "all")  # all, unread, read
        message_type = request.args.get(
            "message_type", "all"
        )  # all, backtest_data_ready, etc.

        connection = get_db_connection()
        if connection is None:
            return jsonify({"message": "数据库连接失败"}), 500

        try:
            cursor = connection.cursor()
            current_user_name = current_user["user_name"]

            # 构建查询条件
            where_conditions = ["user_name = %s"]
            params = [current_user_name]

            if status_filter != "all":
                where_conditions.append("status = %s")
                params.append(status_filter)

            if message_type != "all":
                where_conditions.append("message_type = %s")
                params.append(message_type)

            where_clause = " AND ".join(where_conditions)

            # 获取总数
            count_sql = f"SELECT COUNT(*) as total FROM Messages WHERE {where_clause}"
            cursor.execute(count_sql, params)
            total = cursor.fetchone()["total"]

            # 获取分页数据
            offset = (page - 1) * page_size
            data_sql = f"""
            SELECT message_id, user_name, message_type, title, content, link_url, link_params, 
                   status, created_at, read_at
            FROM Messages 
            WHERE {where_clause}
            ORDER BY created_at DESC 
            LIMIT %s OFFSET %s
            """
            cursor.execute(data_sql, params + [page_size, offset])
            messages = cursor.fetchall()

            # 格式化日期字段和JSON字段
            for message in messages:
                if message.get("created_at"):
                    message["created_at"] = message["created_at"].strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )
                if message.get("read_at"):
                    message["read_at"] = message["read_at"].strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )
                # 处理JSON字段
                if message.get("link_params"):
                    try:
                        message["link_params"] = json.loads(message["link_params"])
                    except (json.JSONDecodeError, TypeError):
                        message["link_params"] = None

            return (
                jsonify(
                    {
                        "success": True,
                        "data": {
                            "messages": messages,
                            "total": total,
                            "page": page,
                            "page_size": page_size,
                        },
                    }
                ),
                200,
            )

        finally:
            connection.close()

    except Exception as e:
        logger.error(f"获取消息列表过程中发生错误: {str(e)}")
        return jsonify({"message": f"获取消息列表失败: {str(e)}"}), 500


# 标记消息为已读API
@app.route("/api/messages/<message_id>/read", methods=["PUT"])
@token_required
def mark_message_read(current_user, message_id):
    """标记消息为已读"""
    try:
        connection = get_db_connection()
        if connection is None:
            return jsonify({"message": "数据库连接失败"}), 500

        try:
            cursor = connection.cursor()
            current_user_name = current_user["user_name"]

            # 检查消息是否存在且属于当前用户
            check_sql = (
                "SELECT status FROM Messages WHERE message_id = %s AND user_name = %s"
            )
            cursor.execute(check_sql, (message_id, current_user_name))
            message = cursor.fetchone()

            if not message:
                return jsonify({"message": "消息不存在"}), 404

            # 如果已经是已读状态，直接返回
            if message["status"] == "read":
                return jsonify({"message": "消息已经是已读状态"}), 200

            # 更新为已读
            update_sql = "UPDATE Messages SET status = 'read', read_at = %s WHERE message_id = %s AND user_name = %s"
            cursor.execute(update_sql, (datetime.now(), message_id, current_user_name))
            connection.commit()

            return jsonify({"message": "消息已标记为已读"}), 200

        finally:
            connection.close()

    except Exception as e:
        logger.error(f"标记消息已读过程中发生错误: {str(e)}")
        return jsonify({"message": f"标记消息已读失败: {str(e)}"}), 500


# 删除消息API
@app.route("/api/messages/<message_id>", methods=["DELETE"])
@token_required
def delete_message(current_user, message_id):
    """删除消息"""
    try:
        connection = get_db_connection()
        if connection is None:
            return jsonify({"message": "数据库连接失败"}), 500

        try:
            cursor = connection.cursor()
            current_user_name = current_user["user_name"]

            # 检查消息是否存在且属于当前用户
            check_sql = "SELECT message_id FROM Messages WHERE message_id = %s AND user_name = %s"
            cursor.execute(check_sql, (message_id, current_user_name))
            message = cursor.fetchone()

            if not message:
                return jsonify({"message": "消息不存在"}), 404

            # 删除消息
            delete_sql = "DELETE FROM Messages WHERE message_id = %s AND user_name = %s"
            cursor.execute(delete_sql, (message_id, current_user_name))
            connection.commit()

            return jsonify({"message": "消息已删除"}), 200

        finally:
            connection.close()

    except Exception as e:
        logger.error(f"删除消息过程中发生错误: {str(e)}")
        return jsonify({"message": f"删除消息失败: {str(e)}"}), 500


# 创建消息的内部函数
def create_message(
    user_name, message_type, title, content, link_url=None, link_params=None
):
    """创建新消息（内部函数）"""
    try:
        import uuid

        message_id = str(uuid.uuid4())

        connection = get_db_connection()
        if connection is None:
            return False

        try:
            cursor = connection.cursor()

            insert_sql = """
            INSERT INTO Messages (message_id, user_name, message_type, title, content, 
                                link_url, link_params, status, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, 'unread', %s)
            """

            cursor.execute(
                insert_sql,
                (
                    message_id,
                    user_name,
                    message_type,
                    title,
                    content,
                    link_url,
                    json.dumps(link_params) if link_params else None,
                    datetime.now(),
                ),
            )
            connection.commit()

            return True

        finally:
            connection.close()

    except Exception as e:
        logger.error(f"创建消息失败: {str(e)}")
        return False


# =============================================
# 回测相关API
# =============================================


# 启动回测任务API
@app.route("/api/backtest/start", methods=["POST"])
@token_required
def start_backtest(current_user):
    """启动真实回测任务，集成数据准备和回测引擎"""
    try:
        data = request.get_json()
        strategy_creator = data.get("strategy_creator")
        strategy_name = data.get("strategy_name")
        start_date = data.get("start_date")
        end_date = data.get("end_date")
        initial_fund = data.get("initial_fund", 100000)

        if not all([strategy_creator, strategy_name, start_date, end_date]):
            return jsonify({"message": "缺少必要参数"}), 400

        current_user_name = current_user["user_name"]
        report_id = str(uuid.uuid4())

        # 启动异步回测任务
        import threading

        def backtest_task():
            connection = None
            try:
                # 初始化回测报告记录
                connection = get_db_connection()
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO BacktestReport (
                            report_id, creator_name, strategy_name, user_name,
                            start_date, end_date, initial_fund, final_fund, 
                            total_return, annual_return, max_drawdown, sharpe_ratio, 
                            win_rate, profit_loss_ratio, trade_count, report_status
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, 0, 0, 0, 0, 0, 0, 0, 0, 'generating')
                    """,
                        (
                            report_id,
                            strategy_creator,
                            strategy_name,
                            current_user_name,
                            start_date,
                            end_date,
                            initial_fund,
                        ),
                    )
                    connection.commit()

                # 第一阶段：数据准备
                logger.info(f"开始数据准备，策略: {strategy_creator}.{strategy_name}")

                preparer = DataPreparer("config.json")
                strategy_fullname = f"{strategy_creator}.{strategy_name}"

                # 调用数据准备模块（作为模块使用，不生成CSV文件）
                prepared_data = preparer.prepare_data(
                    strategy_fullname, start_date, end_date, save_files=False
                )

                # 发送数据准备完成消息
                create_message(
                    user_name=current_user_name,
                    message_type="backtest_data_ready",
                    title=f"回测数据准备完成 - {strategy_name}",
                    content=f"策略 '{strategy_name}' 的回测数据准备已完成，正在进行回测计算...",
                )

                # 第二阶段：回测执行
                logger.info(f"开始执行回测，策略: {strategy_creator}.{strategy_name}")

                # 从数据准备结果中获取策略手续费信息
                strategy_info = prepared_data.get("strategy_info", {})
                buy_fee_rate = strategy_info.get("buy_fee_rate", 0.0003)
                sell_fee_rate = strategy_info.get("sell_fee_rate", 0.0013)

                backtest_engine = BacktestEngine(
                    initial_fund=float(initial_fund),
                    buy_fee_rate=float(buy_fee_rate),
                    sell_fee_rate=float(sell_fee_rate),
                )

                # 使用数据准备模块的输出运行回测
                config = backtest_engine.load_data_direct(prepared_data)
                results = backtest_engine.run_backtest(config, print_log=False)

                # 第三阶段：生成图表数据
                logger.info(f"生成图表数据，策略: {strategy_creator}.{strategy_name}")

                # 生成matplotlib图表的base64数据
                chart_base64 = backtest_engine.generate_matplotlib_plot()

                # 生成plotly图表的JSON数据
                plotly_data = None
                try:
                    plotly_data = backtest_engine.generate_plotly_json(
                        f"{strategy_name}回测结果"
                    )
                    plotly_json_str = json.dumps(plotly_data)
                except Exception as e:
                    logger.warning(f"Plotly图表生成失败: {e}")
                    plotly_json_str = None

                # 第四阶段：更新回测报告
                logger.info(f"更新回测报告，策略: {strategy_creator}.{strategy_name}")

                final_fund = results["final_value"]
                total_return = results["total_return"]
                annual_return = (
                    total_return
                    * 365
                    / (
                        (pd.to_datetime(end_date) - pd.to_datetime(start_date)).days
                        or 1
                    )
                )

                analysis = results.get("analysis", {})
                max_drawdown = analysis.get("max_drawdown", 0)
                sharpe_ratio = analysis.get("sharpe_ratio", 0)
                win_rate = analysis.get("win_rate", 0)
                total_trades = analysis.get("total_trades", 0)

                # 计算盈亏比（简化计算）
                profit_loss_ratio = 1.0
                if analysis.get("lost_total", 0) > 0:
                    won_avg = total_return / max(analysis.get("won_total", 1), 1)
                    lost_avg = abs(total_return) / max(analysis.get("lost_total", 1), 1)
                    if lost_avg > 0:
                        profit_loss_ratio = won_avg / lost_avg

                # 更新数据库记录
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        UPDATE BacktestReport SET
                            final_fund = %s, total_return = %s, annual_return = %s,
                            max_drawdown = %s, sharpe_ratio = %s, win_rate = %s,
                            profit_loss_ratio = %s, trade_count = %s,
                            chart_data = %s, plotly_chart_data = %s,
                            report_status = 'completed'
                        WHERE report_id = %s
                    """,
                        (
                            final_fund,
                            total_return,
                            annual_return,
                            max_drawdown,
                            sharpe_ratio,
                            win_rate,
                            profit_loss_ratio,
                            total_trades,
                            chart_base64,
                            plotly_json_str,
                            report_id,
                        ),
                    )
                    connection.commit()

                # 发送回测完成消息
                create_message(
                    user_name=current_user_name,
                    message_type="backtest_complete",
                    title=f"回测完成 - {strategy_name}",
                    content=f"策略 '{strategy_name}' 回测已完成。总收益率: {total_return:.2%}，夏普比率: {sharpe_ratio:.4f}",
                    link_url="/backtests",
                    link_params={"report_id": report_id},
                )

                logger.info(f"回测任务完成，报告ID: {report_id}")

            except Exception as e:
                logger.error(f"回测任务执行失败: {str(e)}")

                # 更新失败状态
                if connection:
                    try:
                        with connection.cursor() as cursor:
                            cursor.execute(
                                """
                                UPDATE BacktestReport SET
                                    report_status = 'failed',
                                    error_message = %s
                                WHERE report_id = %s
                            """,
                                (str(e), report_id),
                            )
                            connection.commit()
                    except Exception as db_e:
                        logger.error(f"更新失败状态时出错: {str(db_e)}")

                # 发送失败消息
                create_message(
                    user_name=current_user_name,
                    message_type="error_alert",
                    title=f"回测失败 - {strategy_name}",
                    content=f"策略 '{strategy_name}' 回测执行失败: {str(e)}",
                )

            finally:
                if connection:
                    connection.close()

        # 启动后台线程
        thread = threading.Thread(target=backtest_task)
        thread.daemon = True
        thread.start()

        return (
            jsonify(
                {
                    "success": True,
                    "message": "回测任务已启动，请稍后查看消息通知",
                    "report_id": report_id,
                }
            ),
            200,
        )

    except Exception as e:
        logger.error(f"启动回测任务过程中发生错误: {str(e)}")
        return jsonify({"message": f"启动回测任务失败: {str(e)}"}), 500


# 获取回测报告详情API
@app.route("/api/backtests", methods=["GET"])
@token_required
def get_backtest_list(current_user):
    """获取当前用户的回测报告列表"""
    try:
        page = int(request.args.get("page", 1))
        page_size = int(request.args.get("page_size", 10))
        offset = (page - 1) * page_size

        connection = get_db_connection()
        if connection is None:
            return jsonify({"code": 500, "message": "数据库连接失败"}), 500

        try:
            cursor = connection.cursor()

            # 查询当前用户的回测报告总数
            count_sql = """
            SELECT COUNT(*) FROM BacktestReport 
            WHERE user_name = %s
            """
            cursor.execute(count_sql, (current_user["user_name"],))
            total_result = cursor.fetchone()
            total = total_result["COUNT(*)"] if total_result else 0

            # 查询回测报告列表，按时间倒序
            list_sql = """
            SELECT report_id, creator_name, strategy_name, 
                   start_date, end_date, initial_fund, final_fund,
                   total_return, annual_return, max_drawdown, sharpe_ratio,
                   win_rate, profit_loss_ratio, trade_count,
                   report_generate_time, report_status
            FROM BacktestReport 
            WHERE user_name = %s
            ORDER BY report_generate_time DESC
            LIMIT %s OFFSET %s
            """
            cursor.execute(list_sql, (current_user["user_name"], page_size, offset))
            raw_reports = cursor.fetchall()

            # 简化处理：只格式化日期和时间字段
            reports = []
            for report in raw_reports:
                try:
                    # 直接使用数据库字段，只处理日期格式化
                    processed_report = dict(report)

                    # 格式化日期字段
                    if processed_report.get("start_date"):
                        processed_report["start_date"] = processed_report[
                            "start_date"
                        ].strftime("%Y-%m-%d")
                    if processed_report.get("end_date"):
                        processed_report["end_date"] = processed_report[
                            "end_date"
                        ].strftime("%Y-%m-%d")
                    if processed_report.get("report_generate_time"):
                        processed_report["report_generate_time"] = processed_report[
                            "report_generate_time"
                        ].strftime("%Y-%m-%d %H:%M:%S")

                    reports.append(processed_report)
                except Exception as map_error:
                    logger.error(f"映射回测记录失败: {str(map_error)}")
                    continue

            return (
                jsonify(
                    {
                        "code": 200,
                        "message": "获取成功",
                        "data": {
                            "list": reports,
                            "total": total,
                            "page": page,
                            "page_size": page_size,
                        },
                    }
                ),
                200,
            )

        finally:
            connection.close()

    except Exception as e:
        logger.error(f"获取回测列表过程中发生错误: {str(e)}")
        return jsonify({"code": 500, "message": f"获取回测列表失败: {str(e)}"}), 500


@app.route("/api/backtests/simple", methods=["GET"])
@token_required
def get_backtest_list_simple(current_user):
    """获取当前用户的回测报告列表 - 简化版本用于调试"""
    try:
        connection = get_db_connection()
        if connection is None:
            return jsonify({"code": 500, "message": "数据库连接失败"}), 500

        try:
            cursor = connection.cursor()

            # 简单查询，只获取基本字段
            simple_sql = """
            SELECT report_id, creator_name, strategy_name, user_name, 
                   start_date, end_date, initial_fund, report_status, report_generate_time
            FROM BacktestReport 
            WHERE user_name = %s
            ORDER BY report_generate_time DESC
            LIMIT 10
            """
            cursor.execute(simple_sql, (current_user["user_name"],))
            reports = cursor.fetchall()

            # 简单映射 - 使用字典键名而不是索引
            simple_reports = []
            for report in reports:
                simple_report = {
                    "report_id": str(report["report_id"]),
                    "creator_name": str(report["creator_name"]),
                    "strategy_name": str(report["strategy_name"]),
                    "user_name": str(report["user_name"]),
                    "start_date": str(report["start_date"]),
                    "end_date": str(report["end_date"]),
                    "initial_fund": float(report["initial_fund"]),
                    "report_status": str(report["report_status"]),
                    "report_generate_time": str(report["report_generate_time"]),
                }
                simple_reports.append(simple_report)

            return (
                jsonify(
                    {
                        "code": 200,
                        "message": "获取成功",
                        "data": {
                            "list": simple_reports,
                            "total": len(simple_reports),
                            "page": 1,
                            "page_size": 10,
                        },
                    }
                ),
                200,
            )

        finally:
            connection.close()

    except Exception as e:
        import traceback

        error_msg = f"错误详情: {str(e)} | 用户: {current_user.get('user_name', 'Unknown')} | 堆栈: {traceback.format_exc()}"
        logger.error(error_msg)
        print(f"DEBUG: {error_msg}")  # 临时调试输出
        return jsonify({"code": 500, "message": f"获取回测列表失败: {str(e)}"}), 500


@app.route("/api/backtest/report/<report_id>", methods=["GET"])
@token_required
def get_backtest_report(current_user, report_id):
    """获取回测报告详情"""
    try:
        connection = get_db_connection()
        if connection is None:
            return jsonify({"message": "数据库连接失败"}), 500

        try:
            cursor = connection.cursor()

            # 获取回测报告 - 添加用户权限验证，包含图表数据
            report_sql = """
            SELECT report_id, creator_name, strategy_name, user_name,
                   start_date, end_date, initial_fund, final_fund, 
                   total_return, annual_return, max_drawdown, sharpe_ratio,
                   win_rate, profit_loss_ratio, trade_count, chart_data, 
                   plotly_chart_data, report_generate_time, report_status
            FROM BacktestReport 
            WHERE report_id = %s AND user_name = %s
            """
            cursor.execute(report_sql, (report_id, current_user["user_name"]))
            report = cursor.fetchone()

            if not report:
                return jsonify({"message": "回测报告不存在或无权限访问"}), 404

            # 格式化日期字段
            if report.get("start_date"):
                report["start_date"] = report["start_date"].strftime("%Y-%m-%d")
            if report.get("end_date"):
                report["end_date"] = report["end_date"].strftime("%Y-%m-%d")
            if report.get("report_generate_time"):
                report["report_generate_time"] = report[
                    "report_generate_time"
                ].strftime("%Y-%m-%d %H:%M:%S")

            # 处理plotly数据
            if report.get("plotly_chart_data"):
                try:
                    report["plotly_chart_data"] = json.loads(
                        report["plotly_chart_data"]
                    )
                except json.JSONDecodeError:
                    logger.warning(f"无法解析报告 {report_id} 的plotly数据")
                    report["plotly_chart_data"] = None

            return jsonify({"success": True, "data": report}), 200

        finally:
            connection.close()

    except Exception as e:
        logger.error(f"获取回测报告过程中发生错误: {str(e)}")
        return jsonify({"message": f"获取回测报告失败: {str(e)}"}), 500


if __name__ == "__main__":
    # 注意：在生产环境中，请使用适当的WSGI服务器（如Gunicorn）运行，而不是使用Flask的开发服务器
    # 同时，应将debug设置为False
    app.run(host="0.0.0.0", port=5000, debug=True)
