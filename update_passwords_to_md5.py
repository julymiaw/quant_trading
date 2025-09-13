#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
密码更新脚本：将数据库中所有用户的明文密码转换为MD5加密格式
使用说明：运行前请确保已配置好config.json文件或直接修改下面的数据库配置
"""

import pymysql
import hashlib
import json
import os

# 数据库配置
def get_db_config():
    """获取数据库配置信息"""
    # 尝试从配置文件中读取数据库配置
    if os.path.exists('config.json'):
        try:
            with open('config.json', 'r', encoding='utf-8') as f:
                config = json.load(f)
                return {
                    "host": config.get("db_host", "localhost"),
                    "port": config.get("db_port", 3306),
                    "user": config.get("db_user", "root"),
                    "password": config.get("db_password", ""),
                    "database": "quantitative_trading",
                    "charset": "utf8mb4"
                }
        except Exception as e:
            print(f"读取配置文件失败: {e}")
    
    # 如果配置文件不存在或读取失败，使用默认配置
    print("使用默认数据库配置")
    return {
        "host": "localhost",
        "port": 3306,
        "user": "root",
        "password": "12345678abc",  # 请手动修改为您的MySQL密码
        "database": "quantitative_trading",
        "charset": "utf8mb4"
    }


def get_db_connection():
    """获取数据库连接"""
    db_config = get_db_config()
    try:
        connection = pymysql.connect(
            host=db_config['host'],
            port=db_config['port'],
            user=db_config['user'],
            password=db_config['password'],
            database=db_config['database'],
            charset=db_config['charset'],
            cursorclass=pymysql.cursors.DictCursor
        )
        return connection
    except Exception as e:
        print(f"数据库连接失败: {str(e)}")
        raise


def update_passwords_to_md5():
    """将数据库中所有用户的明文密码更新为MD5加密格式"""
    try:
        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                # 查询所有用户的密码
                sql = "SELECT user_id, user_password FROM User"
                cursor.execute(sql)
                users = cursor.fetchall()
                
                if not users:
                    print("数据库中没有用户记录")
                    return
                
                updated_count = 0
                
                # 遍历所有用户，将密码转换为MD5格式
                for user in users:
                    user_id = user['user_id']
                    plain_password = user['user_password']
                    
                    # 检查密码是否已经是MD5格式（32位16进制字符串）
                    if len(plain_password) == 32 and all(c in "0123456789abcdefABCDEF" for c in plain_password):
                        print(f"用户 {user_id} 的密码可能已经是MD5格式，跳过更新")
                        continue
                    
                    # 使用MD5加密密码
                    md5 = hashlib.md5()
                    md5.update(plain_password.encode('utf-8'))
                    hashed_password = md5.hexdigest()
                    
                    # 更新密码
                    update_sql = "UPDATE User SET user_password = %s WHERE user_id = %s"
                    cursor.execute(update_sql, (hashed_password, user_id))
                    updated_count += 1
                    print(f"已更新用户 {user_id} 的密码为MD5格式")
                
                # 提交事务
                connection.commit()
                print(f"\n密码更新完成！共更新了 {updated_count} 个用户的密码")
        finally:
            connection.close()
    except Exception as e:
        print(f"更新密码过程中发生错误: {str(e)}")


if __name__ == '__main__':
    print("===== 密码更新工具 - 将明文密码转换为MD5加密格式 =====")
    print("注意：此脚本会更新数据库中所有用户的密码")
    confirm = input("请确认是否继续？(y/n): ")
    
    if confirm.lower() == 'y':
        update_passwords_to_md5()
    else:
        print("操作已取消")