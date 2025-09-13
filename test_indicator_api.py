#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
指标管理API测试脚本
"""

import requests
import json

BASE_URL = 'http://localhost:5000'

def test_indicator_apis():
    """测试指标管理相关API"""
    
    # 1. 先登录获取token
    login_data = {
        'userName': 'testuser',
        'password': 'test123'
    }
    
    try:
        print("1. 尝试登录...")
        response = requests.post(f'{BASE_URL}/auth/login', json=login_data)
        print(f"登录响应状态: {response.status_code}")
        print(f"登录响应内容: {response.text}")
        
        if response.status_code != 200:
            print("登录失败，请检查用户是否存在")
            return
            
        token = response.json().get('data', {}).get('token')
        if not token:
            print("未能获取到token")
            return
            
        print(f"登录成功，token: {token[:50]}...")
        
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        # 2. 测试创建指标
        print("\n2. 测试创建指标...")
        indicator_data = {
            'indicator_name': 'TestRSI',
            'calculation_method': 'def calculation_method(params):\n    return 50',
            'description': '测试RSI指标',
            'is_active': True
        }
        
        response = requests.post(f'{BASE_URL}/api/indicators', 
                               json=indicator_data, 
                               headers=headers)
        print(f"创建指标响应状态: {response.status_code}")
        print(f"创建指标响应内容: {response.text}")
        
        # 3. 测试获取指标列表
        print("\n3. 测试获取指标列表...")
        params = {
            'page': 1,
            'limit': 10,
            'creator_name': 'testuser'
        }
        
        response = requests.get(f'{BASE_URL}/api/indicators',
                               params=params,
                               headers=headers)
        print(f"获取指标列表响应状态: {response.status_code}")
        print(f"获取指标列表响应内容: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            indicators = data.get('data', [])
            print(f"找到 {len(indicators)} 个指标")
            for indicator in indicators:
                print(f"  - {indicator.get('indicator_name')} (创建者: {indicator.get('creator_name')})")
        
        # 4. 测试获取系统指标
        print("\n4. 测试获取系统指标...")
        params = {
            'page': 1,
            'limit': 10,
            'creator_name': 'system'
        }
        
        response = requests.get(f'{BASE_URL}/api/indicators',
                               params=params,
                               headers=headers)
        print(f"获取系统指标响应状态: {response.status_code}")
        print(f"获取系统指标响应内容: {response.text}")
        
    except Exception as e:
        print(f"测试过程中发生错误: {str(e)}")

if __name__ == '__main__':
    test_indicator_apis()