#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
量化交易系统后端服务器
提供用户登录、注册等API接口
"""

import pymysql
import json
import os
import logging
import hashlib
from datetime import datetime, timedelta
import uuid
from functools import wraps

from flask import Flask, request, jsonify
from flask_cors import CORS
import jwt
from werkzeug.security import generate_password_hash, check_password_hash

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

# 数据库配置
DB_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "user": "root",
    "password": config["db_password"],  # 从配置文件读取密码
    "database": "quantitative_trading",
    "charset": "utf8mb4",
}


# 数据库连接工具函数
def get_db_connection():
    """获取数据库连接"""
    try:
        connection = pymysql.connect(
            host=DB_CONFIG["host"],
            port=DB_CONFIG["port"],
            user=DB_CONFIG["user"],
            password=DB_CONFIG["password"],
            database=DB_CONFIG["database"],
            charset=DB_CONFIG["charset"],
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
        "exp": datetime.utcnow() + app.config["JWT_EXPIRATION_DELTA"],
        "iat": datetime.utcnow(),
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
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            current_user = {
                'user_id': data['sub'],
                'user_name': data['user_name'],
                'user_role': data['user_role']
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
        user_name = data.get("userName")
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
                    "user_email": user.get("user_email"),
                    "user_phone": user.get("user_phone"),
                }
                
                return jsonify({
                    'code': 200,
                    'data': {
                        'token': token,
                        'userInfo': user_info
                    },
                    'message': '登录成功'
                })
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
        user_name = data.get("userName")
        password = data.get("password")
        email = data.get("email")
        phone = data.get("phone")

        # 验证必填字段
        if not user_name or not password or not email:
            return jsonify({"message": "用户名、密码和邮箱为必填项"}), 400

        # 验证用户名格式（仅允许英文、数字、下划线）
        import re

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
                sql = "SELECT user_id, user_name, user_role, user_email, user_phone, user_create_time, user_last_login_time FROM User WHERE user_id = %s"
                cursor.execute(sql, (current_user['user_id'],))
                user = cursor.fetchone()

                if not user:
                    return jsonify({"message": "用户不存在"}), 404

                return jsonify({"data": user, "message": "获取用户信息成功"}), 200
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
        param_type_filter = request.args.get(
            "param_type", "my"
        )  # my, system, public, all
        param_source_type = request.args.get(
            "param_source_type", "all"
        )  # all, table, indicator

        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                # 获取当前用户信息
                user_sql = "SELECT user_name FROM User WHERE user_id = %s"
                cursor.execute(user_sql, (current_user['user_id'],))
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
                elif param_type_filter == "public":
                    where_conditions.append("creator_name != %s")
                    query_params.append(current_user_name)
                # param_type_filter == 'all' 时不添加条件

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
        import re

        if not re.match(r"^[a-zA-Z0-9_.]+$", param_name):
            return jsonify({"message": "参数ID只能包含字母、数字、下划线和点号"}), 400

        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                # 获取当前用户信息
                user_sql = "SELECT user_name FROM User WHERE user_id = %s"
                cursor.execute(user_sql, (current_user['user_id'],))
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
            parts = param_composite_id.split('.', 1)
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
        import re

        if not re.match(r"^[a-zA-Z0-9_.]+$", new_param_name):
            return jsonify({"message": "参数ID只能包含字母、数字、下划线和点号"}), 400

        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                # 获取当前用户信息
                user_sql = "SELECT user_name FROM User WHERE user_id = %s"
                cursor.execute(user_sql, (current_user['user_id'],))
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
                    'id': f"{creator_name}.{new_param_name}",
                    'creator_name': creator_name,
                    'param_name': new_param_name,
                    'data_id': data_id,
                    'param_type': param_type,
                    'pre_period': pre_period,
                    'post_period': post_period,
                    'agg_func': agg_func,
                    'create_time': existing_param.get('create_time', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                }
                
                return jsonify({
                    'data': updated_param,
                    'message': '参数更新成功'
                }), 200
                
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
            parts = param_composite_id.split('.', 1)
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
                cursor.execute(user_sql, (current_user['user_id'],))
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


# 获取数据源列表API（用于前端自动完成）
@app.route("/api/data-sources", methods=["GET"])
@token_required
def get_data_sources(current_user):
    """获取数据源列表接口"""
    try:
        # 模拟数据源列表，实际项目中可以从配置文件或数据库获取
        data_sources = [
            # 基础数据表
            "daily.open",
            "daily.close",
            "daily.high",
            "daily.low",
            "daily.volume",
            "daily.amount",
            "daily.pct_change",
            "daily_basic.total_mv",
            "daily_basic.circ_mv",
            "daily_basic.pe",
            "daily_basic.pb",
            "daily_basic.ps",
            "daily_basic.pcf",
            # 估值数据
            "valuation.market_cap",
            "valuation.pe_ratio",
            "valuation.pb_ratio",
            "valuation.ps_ratio",
            "valuation.pcf_ratio",
            # 技术指标
            "indicator.MACD",
            "indicator.KDJ",
            "indicator.RSI",
            "indicator.BOLL",
            "indicator.MA",
            "indicator.EMA",
            "indicator.VOLMA",
            "indicator.ATR",
            "indicator.CCI",
            # 系统指标（来自Indicator表）
            "system.MACD",
            "system.KDJ",
            "system.RSI",
        ]

        # 获取查询参数
        query = request.args.get("q", "").strip().lower()

        # 过滤数据源
        if query:
            filtered_sources = [
                source for source in data_sources if query in source.lower()
            ]
        else:
            filtered_sources = data_sources

        return (
            jsonify(
                {
                    "data": filtered_sources[:50],  # 限制返回数量
                    "message": "获取数据源列表成功",
                }
            ),
            200,
        )

    except Exception as e:
        logger.error(f"获取数据源列表过程中发生错误: {str(e)}")
        return jsonify({'message': f'获取数据源列表失败: {str(e)}'}), 500

# =============================================
# 策略管理相关API
# =============================================

# 获取策略列表API
@app.route('/api/strategies', methods=['GET'])
@token_required
def get_strategies(current_user):
    """获取策略列表接口"""
    try:
        # 获取查询参数
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', 10))
        search_keyword = request.args.get('search', '').strip()
        strategy_type_filter = request.args.get('strategy_type', 'all')  # my, system, public, all
        scope_type_filter = request.args.get('scope_type', 'all')  # all, single_stock, index
        
        connection = get_db_connection()
        try:
            cursor = connection.cursor()
            
            # 构建基础查询SQL
            base_sql = """
            SELECT s.creator_name, s.strategy_name, s.public, s.scope_type, s.scope_id,
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
            if strategy_type_filter == 'my':
                conditions.append("s.creator_name = %s")
                params.append(current_user['user_name'])
            elif strategy_type_filter == 'system':
                conditions.append("s.creator_name = 'system'")
            elif strategy_type_filter == 'public':
                conditions.append("s.public = TRUE")
            
            # 根据搜索关键词筛选
            if search_keyword:
                conditions.append("(s.strategy_name LIKE %s OR s.strategy_desc LIKE %s)")
                keyword_pattern = f'%{search_keyword}%'
                params.extend([keyword_pattern, keyword_pattern])
            
            # 根据生效范围筛选
            if scope_type_filter != 'all':
                conditions.append("s.scope_type = %s")
                params.append(scope_type_filter)
            
            # 拼接条件
            if conditions:
                base_sql += " AND " + " AND ".join(conditions)
            
            # 添加排序
            base_sql += " ORDER BY s.update_time DESC"
            
            # 执行查询获取总数
            count_sql = f"SELECT COUNT(*) as total FROM ({base_sql}) as counted_strategies"
            cursor.execute(count_sql, params)
            total = cursor.fetchone()['total']
            
            # 添加分页
            base_sql += " LIMIT %s OFFSET %s"
            offset = (page - 1) * page_size
            params.extend([page_size, offset])
            
            # 执行分页查询
            cursor.execute(base_sql, params)
            strategies = cursor.fetchall()
            
            # 格式化时间字段
            for strategy in strategies:
                if strategy['create_time']:
                    strategy['create_time'] = strategy['create_time'].strftime('%Y-%m-%d %H:%M:%S')
                if strategy['update_time']:
                    strategy['update_time'] = strategy['update_time'].strftime('%Y-%m-%d %H:%M:%S')
            
            return jsonify({
                'code': 200,
                'message': '获取策略列表成功',
                'data': {
                    'strategies': strategies,
                    'total': total,
                    'page': page,
                    'page_size': page_size
                }
            })
                
        finally:
            connection.close()
            
    except Exception as e:
        logger.error(f"获取策略列表过程中发生错误: {str(e)}")
        return jsonify({'code': 500, 'message': '获取策略列表失败，请重试'})

# 创建策略API
@app.route('/api/strategies', methods=['POST'])
@token_required
def create_strategy(current_user):
    """创建策略接口"""
    try:
        data = request.get_json()
        
        # 验证必填字段
        required_fields = ['strategy_name', 'scope_type', 'select_func']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({'code': 400, 'message': f'缺少必填字段: {field}'})
        
        strategy_name = str(data['strategy_name']).strip()
        public = bool(data.get('public', True))
        scope_type = data['scope_type']
        scope_id = str(data.get('scope_id', '')).strip() if data.get('scope_id') else None
        select_func = str(data['select_func']).strip()
        risk_control_func = str(data.get('risk_control_func', '')).strip() if data.get('risk_control_func') else None
        position_count = data.get('position_count')
        rebalance_interval = data.get('rebalance_interval')
        buy_fee_rate = float(data.get('buy_fee_rate', 0.001))
        sell_fee_rate = float(data.get('sell_fee_rate', 0.001))
        strategy_desc = str(data.get('strategy_desc', '')).strip() if data.get('strategy_desc') else None
        
        # 验证数据格式
        if not strategy_name:
            return jsonify({'code': 400, 'message': '策略名称不能为空'})
        
        if scope_type not in ['all', 'single_stock', 'index']:
            return jsonify({'code': 400, 'message': '生效范围类型无效'})
        
        if scope_type != 'all' and not scope_id:
            return jsonify({'code': 400, 'message': '当生效范围不是全部时，必须指定股票/指数ID'})
        
        if scope_type != 'single_stock':
            if not position_count or position_count <= 0:
                return jsonify({'code': 400, 'message': '持仓数量必须大于0'})
            if not rebalance_interval or rebalance_interval <= 0:
                return jsonify({'code': 400, 'message': '调仓间隔必须大于0'})
        
        # 验证策略名格式（仅允许中文、英文、数字、下划线）
        import re
        if not re.match(r'^[\u4e00-\u9fa5a-zA-Z0-9_]+$', strategy_name):
            return jsonify({'code': 400, 'message': '策略名称只能包含中文、英文、数字和下划线'})
        
        connection = get_db_connection()
        try:
            cursor = connection.cursor()
            
            # 检查策略名是否已存在（同一创建者）
            check_sql = "SELECT COUNT(*) as count FROM Strategy WHERE creator_name = %s AND strategy_name = %s"
            cursor.execute(check_sql, (current_user['user_name'], strategy_name))
            if cursor.fetchone()['count'] > 0:
                return jsonify({'code': 400, 'message': '策略名称已存在'})
            
            # 插入策略记录
            insert_sql = """
            INSERT INTO Strategy 
            (creator_name, strategy_name, public, scope_type, scope_id, select_func, 
             risk_control_func, position_count, rebalance_interval, buy_fee_rate, 
             sell_fee_rate, strategy_desc, create_time, update_time)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
            """
            
            cursor.execute(insert_sql, (
                current_user['user_name'], strategy_name, public, scope_type, scope_id,
                select_func, risk_control_func, position_count, rebalance_interval,
                buy_fee_rate, sell_fee_rate, strategy_desc
            ))
            
            connection.commit()
            
            return jsonify({
                'code': 200,
                'message': '策略创建成功',
                'data': {
                    'creator_name': current_user['user_name'],
                    'strategy_name': strategy_name
                }
            })
                
        finally:
            connection.close()
            
    except Exception as e:
        logger.error(f"创建策略过程中发生错误: {str(e)}")
        return jsonify({'code': 500, 'message': '创建策略失败，请重试'})

# 获取策略详情API
@app.route('/api/strategies/<creator_name>/<strategy_name>', methods=['GET'])
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
                   s.select_func, s.risk_control_func, s.position_count, s.rebalance_interval,
                   s.buy_fee_rate, s.sell_fee_rate, s.strategy_desc, 
                   s.create_time, s.update_time
            FROM Strategy s
            WHERE s.creator_name = %s AND s.strategy_name = %s
            """
            
            cursor.execute(select_sql, (creator_name, strategy_name))
            strategy = cursor.fetchone()
            
            if not strategy:
                return jsonify({'code': 404, 'message': '策略不存在'})
            
            # 检查访问权限（如果不是公开策略且不是创建者，则不能访问）
            if not strategy['public'] and strategy['creator_name'] != current_user['user_name']:
                return jsonify({'code': 403, 'message': '无权限访问此策略'})
            
            # 格式化时间字段
            if strategy['create_time']:
                strategy['create_time'] = strategy['create_time'].strftime('%Y-%m-%d %H:%M:%S')
            if strategy['update_time']:
                strategy['update_time'] = strategy['update_time'].strftime('%Y-%m-%d %H:%M:%S')
            
            return jsonify({
                'code': 200,
                'message': '获取策略详情成功',
                'data': strategy
            })
                
        finally:
            connection.close()
            
    except Exception as e:
        logger.error(f"获取策略详情过程中发生错误: {str(e)}")
        return jsonify({'code': 500, 'message': '获取策略详情失败，请重试'})

# 更新策略API
@app.route('/api/strategies/<creator_name>/<strategy_name>', methods=['PUT'])
@token_required
def update_strategy(current_user, creator_name, strategy_name):
    """更新策略接口"""
    try:
        # 权限检查：只能更新自己创建的策略
        if creator_name != current_user['user_name']:
            return jsonify({'code': 403, 'message': '无权限修改此策略'})
        
        data = request.get_json()
        
        # 验证必填字段
        required_fields = ['strategy_name', 'scope_type', 'select_func']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({'code': 400, 'message': f'缺少必填字段: {field}'})
        
        new_strategy_name = str(data['strategy_name']).strip()
        public = bool(data.get('public', True))
        scope_type = data['scope_type']
        scope_id = str(data.get('scope_id', '')).strip() if data.get('scope_id') else None
        select_func = str(data['select_func']).strip()
        risk_control_func = str(data.get('risk_control_func', '')).strip() if data.get('risk_control_func') else None
        position_count = data.get('position_count')
        rebalance_interval = data.get('rebalance_interval')
        buy_fee_rate = float(data.get('buy_fee_rate', 0.001))
        sell_fee_rate = float(data.get('sell_fee_rate', 0.001))
        strategy_desc = str(data.get('strategy_desc', '')).strip() if data.get('strategy_desc') else None
        
        # 验证数据格式
        if not new_strategy_name:
            return jsonify({'code': 400, 'message': '策略名称不能为空'})
        
        if scope_type not in ['all', 'single_stock', 'index']:
            return jsonify({'code': 400, 'message': '生效范围类型无效'})
        
        if scope_type != 'all' and not scope_id:
            return jsonify({'code': 400, 'message': '当生效范围不是全部时，必须指定股票/指数ID'})
        
        if scope_type != 'single_stock':
            if not position_count or position_count <= 0:
                return jsonify({'code': 400, 'message': '持仓数量必须大于0'})
            if not rebalance_interval or rebalance_interval <= 0:
                return jsonify({'code': 400, 'message': '调仓间隔必须大于0'})
        
        # 验证策略名格式
        import re
        if not re.match(r'^[\u4e00-\u9fa5a-zA-Z0-9_]+$', new_strategy_name):
            return jsonify({'code': 400, 'message': '策略名称只能包含中文、英文、数字和下划线'})
        
        connection = get_db_connection()
        try:
            cursor = connection.cursor()
            
            # 检查策略是否存在
            check_sql = "SELECT COUNT(*) as count FROM Strategy WHERE creator_name = %s AND strategy_name = %s"
            cursor.execute(check_sql, (creator_name, strategy_name))
            if cursor.fetchone()['count'] == 0:
                return jsonify({'code': 404, 'message': '策略不存在'})
            
            # 如果策略名发生变化，检查新名称是否已存在
            if new_strategy_name != strategy_name:
                check_new_name_sql = "SELECT COUNT(*) as count FROM Strategy WHERE creator_name = %s AND strategy_name = %s"
                cursor.execute(check_new_name_sql, (creator_name, new_strategy_name))
                if cursor.fetchone()['count'] > 0:
                    return jsonify({'code': 400, 'message': '新策略名称已存在'})
            
            # 更新策略记录
            update_sql = """
            UPDATE Strategy 
            SET strategy_name = %s, public = %s, scope_type = %s, scope_id = %s, 
                select_func = %s, risk_control_func = %s, position_count = %s, 
                rebalance_interval = %s, buy_fee_rate = %s, sell_fee_rate = %s, 
                strategy_desc = %s, update_time = NOW()
            WHERE creator_name = %s AND strategy_name = %s
            """
            
            cursor.execute(update_sql, (
                new_strategy_name, public, scope_type, scope_id, select_func, 
                risk_control_func, position_count, rebalance_interval, buy_fee_rate, 
                sell_fee_rate, strategy_desc, creator_name, strategy_name
            ))
            
            # 如果策略名发生变化，需要更新相关的关联表
            if new_strategy_name != strategy_name:
                # 更新策略参数关系表
                update_strategy_rel_sql = """
                UPDATE StrategyParamRel 
                SET strategy_name = %s 
                WHERE strategy_creator_name = %s AND strategy_name = %s
                """
                cursor.execute(update_strategy_rel_sql, (new_strategy_name, creator_name, strategy_name))
                
                # 更新交易信号表
                update_signal_sql = """
                UPDATE TradingSignal 
                SET strategy_name = %s 
                WHERE creator_name = %s AND strategy_name = %s
                """
                cursor.execute(update_signal_sql, (new_strategy_name, creator_name, strategy_name))
                
                # 更新回测报告表
                update_backtest_sql = """
                UPDATE BacktestReport 
                SET strategy_name = %s 
                WHERE creator_name = %s AND strategy_name = %s
                """
                cursor.execute(update_backtest_sql, (new_strategy_name, creator_name, strategy_name))
            
            connection.commit()
            
            return jsonify({
                'code': 200,
                'message': '策略更新成功',
                'data': {
                    'creator_name': creator_name,
                    'strategy_name': new_strategy_name
                }
            })
                
        finally:
            connection.close()
            
    except Exception as e:
        logger.error(f"更新策略过程中发生错误: {str(e)}")
        return jsonify({'code': 500, 'message': '更新策略失败，请重试'})

# 删除策略API
@app.route('/api/strategies/<creator_name>/<strategy_name>', methods=['DELETE'])
@token_required
def delete_strategy(current_user, creator_name, strategy_name):
    """删除策略接口"""
    try:
        # 权限检查：只能删除自己创建的策略
        if creator_name != current_user['user_name']:
            return jsonify({'code': 403, 'message': '无权限删除此策略'})
        
        connection = get_db_connection()
        try:
            cursor = connection.cursor()
            
            # 检查策略是否存在
            check_sql = "SELECT COUNT(*) as count FROM Strategy WHERE creator_name = %s AND strategy_name = %s"
            cursor.execute(check_sql, (creator_name, strategy_name))
            if cursor.fetchone()['count'] == 0:
                return jsonify({'code': 404, 'message': '策略不存在'})
            
            # 检查是否有关联的回测报告
            check_backtest_sql = "SELECT COUNT(*) as count FROM BacktestReport WHERE creator_name = %s AND strategy_name = %s"
            cursor.execute(check_backtest_sql, (creator_name, strategy_name))
            backtest_count = cursor.fetchone()['count']
            
            if backtest_count > 0:
                return jsonify({'code': 400, 'message': f'策略已有 {backtest_count} 个回测报告，不能删除'})
            
            # 删除相关记录（先删除外键约束的表）
            # 1. 删除策略参数关系
            cursor.execute("DELETE FROM StrategyParamRel WHERE strategy_creator_name = %s AND strategy_name = %s", 
                         (creator_name, strategy_name))
            
            # 2. 删除交易信号
            cursor.execute("DELETE FROM TradingSignal WHERE creator_name = %s AND strategy_name = %s", 
                         (creator_name, strategy_name))
            
            # 3. 删除策略主记录
            cursor.execute("DELETE FROM Strategy WHERE creator_name = %s AND strategy_name = %s", 
                         (creator_name, strategy_name))
            
            connection.commit()
            
            return jsonify({
                'code': 200,
                'message': '策略删除成功'
            })
                
        finally:
            connection.close()
            
    except Exception as e:
        logger.error(f"删除策略过程中发生错误: {str(e)}")
        return jsonify({'code': 500, 'message': '删除策略失败，请重试'})

# 获取策略参数列表API
@app.route('/api/strategies/<creator_name>/<strategy_name>/params', methods=['GET'])
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
                return jsonify({'code': 404, 'message': '策略不存在'})
            
            # 检查访问权限
            if not strategy_info['public'] and creator_name != current_user['user_name']:
                return jsonify({'code': 403, 'message': '无权限访问此策略的参数'})
            
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
                if param['creation_time']:
                    param['creation_time'] = param['creation_time'].strftime('%Y-%m-%d %H:%M:%S')
                if param['update_time']:
                    param['update_time'] = param['update_time'].strftime('%Y-%m-%d %H:%M:%S')
            
            return jsonify({
                'code': 200,
                'message': '获取策略参数成功',
                'data': params
            })
                
        finally:
            connection.close()
            
    except Exception as e:
        logger.error(f"获取策略参数过程中发生错误: {str(e)}")
        return jsonify({'code': 500, 'message': '获取策略参数失败，请重试'})

# 添加策略参数关系API
@app.route('/api/strategies/<creator_name>/<strategy_name>/params', methods=['POST'])
@token_required
def add_strategy_param(current_user, creator_name, strategy_name):
    """添加策略参数关系接口"""
    try:
        # 权限检查：只能修改自己创建的策略
        if creator_name != current_user['user_name']:
            return jsonify({'code': 403, 'message': '无权限修改此策略'})
        
        data = request.get_json()
        param_creator_name = data.get('param_creator_name', '').strip()
        param_name = data.get('param_name', '').strip()
        
        if not param_creator_name or not param_name:
            return jsonify({'code': 400, 'message': '参数创建者和参数名不能为空'})
        
        connection = get_db_connection()
        try:
            cursor = connection.cursor()
            
            # 检查策略是否存在
            strategy_check_sql = "SELECT COUNT(*) as count FROM Strategy WHERE creator_name = %s AND strategy_name = %s"
            cursor.execute(strategy_check_sql, (creator_name, strategy_name))
            if cursor.fetchone()['count'] == 0:
                return jsonify({'code': 404, 'message': '策略不存在'})
            
            # 检查参数是否存在
            param_check_sql = "SELECT COUNT(*) as count FROM Param WHERE creator_name = %s AND param_name = %s"
            cursor.execute(param_check_sql, (param_creator_name, param_name))
            if cursor.fetchone()['count'] == 0:
                return jsonify({'code': 404, 'message': '参数不存在'})
            
            # 检查关系是否已存在
            rel_check_sql = """
            SELECT COUNT(*) as count FROM StrategyParamRel 
            WHERE strategy_creator_name = %s AND strategy_name = %s 
              AND param_creator_name = %s AND param_name = %s
            """
            cursor.execute(rel_check_sql, (creator_name, strategy_name, param_creator_name, param_name))
            if cursor.fetchone()['count'] > 0:
                return jsonify({'code': 400, 'message': '参数关系已存在'})
            
            # 插入关系记录
            insert_sql = """
            INSERT INTO StrategyParamRel 
            (strategy_creator_name, strategy_name, param_creator_name, param_name)
            VALUES (%s, %s, %s, %s)
            """
            cursor.execute(insert_sql, (creator_name, strategy_name, param_creator_name, param_name))
            
            connection.commit()
            
            return jsonify({
                'code': 200,
                'message': '添加策略参数关系成功'
            })
                
        finally:
            connection.close()
            
    except Exception as e:
        logger.error(f"添加策略参数关系过程中发生错误: {str(e)}")
        return jsonify({'code': 500, 'message': '添加策略参数关系失败，请重试'})

# 删除策略参数关系API
@app.route('/api/strategies/<creator_name>/<strategy_name>/params/<param_creator_name>/<param_name>', methods=['DELETE'])
@token_required
def remove_strategy_param(current_user, creator_name, strategy_name, param_creator_name, param_name):
    """删除策略参数关系接口"""
    try:
        # 权限检查：只能修改自己创建的策略
        if creator_name != current_user['user_name']:
            return jsonify({'code': 403, 'message': '无权限修改此策略'})
        
        connection = get_db_connection()
        try:
            cursor = connection.cursor()
            
            # 检查关系是否存在
            check_sql = """
            SELECT COUNT(*) as count FROM StrategyParamRel 
            WHERE strategy_creator_name = %s AND strategy_name = %s 
              AND param_creator_name = %s AND param_name = %s
            """
            cursor.execute(check_sql, (creator_name, strategy_name, param_creator_name, param_name))
            if cursor.fetchone()['count'] == 0:
                return jsonify({'code': 404, 'message': '参数关系不存在'})
            
            # 删除关系记录
            delete_sql = """
            DELETE FROM StrategyParamRel 
            WHERE strategy_creator_name = %s AND strategy_name = %s 
              AND param_creator_name = %s AND param_name = %s
            """
            cursor.execute(delete_sql, (creator_name, strategy_name, param_creator_name, param_name))
            
            connection.commit()
            
            return jsonify({
                'code': 200,
                'message': '删除策略参数关系成功'
            })
                
        finally:
            connection.close()
            
    except Exception as e:
        logger.error(f"删除策略参数关系过程中发生错误: {str(e)}")
        return jsonify({'code': 500, 'message': '删除策略参数关系失败，请重试'})

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
                cursor.execute(user_sql, (current_user['user_id'],))
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
        import re

        if not re.match(r"^[a-zA-Z0-9_\u4e00-\u9fa5]+$", indicator_name):
            return jsonify({"message": "指标名称只能包含中英文、数字、下划线"}), 400

        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                # 获取当前用户信息
                user_sql = "SELECT user_name FROM User WHERE user_id = %s"
                cursor.execute(user_sql, (current_user['user_id'],))
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
            parts = indicator_composite_id.split('.', 1)
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
        import re

        if not re.match(r"^[a-zA-Z0-9_\u4e00-\u9fa5]+$", new_indicator_name):
            return jsonify({"message": "指标名称只能包含中英文、数字、下划线"}), 400

        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                # 获取当前用户信息
                user_sql = "SELECT user_name FROM User WHERE user_id = %s"
                cursor.execute(user_sql, (current_user['user_id'],))
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
            parts = indicator_composite_id.split('.', 1)
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
                cursor.execute(user_sql, (current_user['user_id'],))
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
                    i.indicator_desc,
                    i.indicator_category,
                    i.is_enabled as indicator_enabled,
                    p.param_desc,
                    p.param_type,
                    p.data_type as param_data_type,
                    p.default_value,
                    p.is_required,
                    p.is_enabled as param_enabled
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
            parts = relation_id.split('.')
            if len(parts) != 4:
                return jsonify({'message': '无效的关系ID格式，应为indicator_creator.indicator_name.param_creator.param_name'}), 400
            
            indicator_creator_name, indicator_name, param_creator_name, param_name = parts
            
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
            parts = indicator_composite_id.split('.', 1)
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
                cursor.execute(user_sql, (current_user['user_id'],))
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
                current_status = existing_indicator['is_active']
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


if __name__ == "__main__":
    # 注意：在生产环境中，请使用适当的WSGI服务器（如Gunicorn）运行，而不是使用Flask的开发服务器
    # 同时，应将debug设置为False
    app.run(host="0.0.0.0", port=5000, debug=True)
