#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Flask Demo - 数据库连接模块
提供数据库连接和查询功能，支持智能搜索提示
"""

import pymysql
import json
from typing import List, Tuple


class DatabaseManager:
    def __init__(self, config_path: str = "config.json"):
        """
        初始化数据库连接管理器
        """
        self.config = self._load_config(config_path)
        self.connection = None

    def _load_config(self, config_path: str) -> dict:
        """加载配置文件"""
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def connect(self):
        """建立数据库连接"""
        if self.connection is None or not self._is_connection_alive():
            self.connection = pymysql.connect(
                host="localhost",
                user="root",
                password=self.config["db_password"],
                database="quantitative_trading",
                charset="utf8mb4",
                autocommit=True,
            )

    def _is_connection_alive(self) -> bool:
        """检查连接是否有效"""
        try:
            self.connection.ping(reconnect=False)
            return True
        except:
            return False

    def close(self):
        """关闭数据库连接"""
        if self.connection:
            self.connection.close()
            self.connection = None

    def get_table_fields(self, table_name: str) -> List[str]:
        """获取指定表的所有字段名"""
        self.connect()
        cursor = self.connection.cursor()
        try:
            # 查询表的字段信息
            cursor.execute(f"DESCRIBE {table_name}")
            fields = [row[0] for row in cursor.fetchall()]
            return fields
        except Exception as e:
            print(f"获取表字段失败: {e}")
            return []
        finally:
            cursor.close()

    def search_table_suggestions(self, query: str) -> List[str]:
        """搜索表名建议（支持daily和daily_basic）"""
        tables = ["daily", "daily_basic"]
        if not query:
            return tables
        return [table for table in tables if table.startswith(query.lower())]

    def search_field_suggestions(self, table_name: str, query: str = "") -> List[str]:
        """搜索字段建议"""
        fields = self.get_table_fields(table_name)
        if not query:
            return fields[:5]  # 默认返回前5个
        matching_fields = [
            field for field in fields if field.lower().startswith(query.lower())
        ]
        return matching_fields[:5]  # 最多返回5个匹配的字段

    def search_users(self, query: str = "") -> List[str]:
        """搜索用户名"""
        self.connect()
        cursor = self.connection.cursor()
        try:
            if query:
                cursor.execute(
                    "SELECT user_name FROM User WHERE user_name LIKE %s LIMIT 5",
                    (f"{query}%",),
                )
            else:
                cursor.execute("SELECT user_name FROM User LIMIT 5")
            return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            print(f"搜索用户失败: {e}")
            return []
        finally:
            cursor.close()

    def search_strategies(self, creator_name: str, query: str = "") -> List[str]:
        """搜索指定用户的策略"""
        self.connect()
        cursor = self.connection.cursor()
        try:
            if query:
                cursor.execute(
                    "SELECT strategy_name FROM Strategy WHERE creator_name = %s AND strategy_name LIKE %s LIMIT 5",
                    (creator_name, f"{query}%"),
                )
            else:
                cursor.execute(
                    "SELECT strategy_name FROM Strategy WHERE creator_name = %s LIMIT 5",
                    (creator_name,),
                )
            return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            print(f"搜索策略失败: {e}")
            return []
        finally:
            cursor.close()

    def search_params(self, creator_name: str, query: str = "") -> List[str]:
        """搜索指定用户的参数"""
        self.connect()
        cursor = self.connection.cursor()
        try:
            if query:
                cursor.execute(
                    "SELECT param_id FROM Param WHERE creator_name = %s AND param_id LIKE %s LIMIT 5",
                    (creator_name, f"{query}%"),
                )
            else:
                cursor.execute(
                    "SELECT param_id FROM Param WHERE creator_name = %s LIMIT 5",
                    (creator_name,),
                )
            return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            print(f"搜索参数失败: {e}")
            return []
        finally:
            cursor.close()

    def search_indicators(self, creator_name: str, query: str = "") -> List[str]:
        """搜索指定用户的指标"""
        self.connect()
        cursor = self.connection.cursor()
        try:
            if query:
                cursor.execute(
                    "SELECT indicator_name FROM Indicator WHERE creator_name = %s AND indicator_name LIKE %s LIMIT 5",
                    (creator_name, f"{query}%"),
                )
            else:
                cursor.execute(
                    "SELECT indicator_name FROM Indicator WHERE creator_name = %s LIMIT 5",
                    (creator_name,),
                )
            return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            print(f"搜索指标失败: {e}")
            return []
        finally:
            cursor.close()
