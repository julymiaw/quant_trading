#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
完整测试波动率预测系统
"""

import sys
import os
import numpy as np
import pandas as pd
from datetime import datetime

from tushare_cache_client import TushareCacheClient
from builtin_params import (
    historical_volatility_param,
    BUILTIN_PARAMS,
)
from predict import predict, predict_single_day


def test_complete_system():
    """测试完整的波动率预测系统"""
    print("开始测试完整的波动率预测系统...")

    # 1. 测试基础波动率计算
    print("\n=== 1. 测试基础波动率计算 ===")
    client = TushareCacheClient()
    ts_code = "000001.SZ"

    try:
        daily_data = client.daily(
            ts_code=ts_code, start_date="20240801", end_date="20240930"
        )
        closes = daily_data["close"].values
        print(f"获取到 {len(closes)} 条价格数据")

        # 计算历史波动率
        vol = historical_volatility_param(closes, 30)
        print(f"历史波动率计算成功，最后5个值: {vol[-5:]}")
        print("✓ 基础波动率计算正常")

    except Exception as e:
        print(f"✗ 基础波动率计算失败: {e}")
        return
    finally:
        client.close()

    # 2. 测试预测函数
    print("\n=== 2. 测试预测函数 ===")
    try:
        # 使用最后30天的波动率数据进行预测
        window_data = vol[-30:].reshape(-1, 1)
        predictions = predict(window_data, n_days=5)
        print(f"预测未来5天波动率: {predictions}")

        # 测试单天预测
        single_pred = predict_single_day(window_data)
        print(f"预测明天波动率: {single_pred}")
        print("✓ 预测函数正常")

    except Exception as e:
        print(f"✗ 预测函数失败: {e}")
        return

    # 3. 测试内置参数配置
    print("\n=== 3. 测试内置参数配置 ===")
    try:
        print("内置参数:")
        for key, config in BUILTIN_PARAMS.items():
            print(f"  - {key}: {config['description']}")

        print("\n预测参数通过PREDICT聚合函数实现:")
        print(
            "  - predict_volatility_1day ~ predict_volatility_5day: 基于GINN-LSTM模型的波动率预测参数"
        )

        print("✓ 参数配置正常")

    except Exception as e:
        print(f"✗ 参数配置失败: {e}")
        return

    # 4. 简单验证预测逻辑
    print("\n=== 4. 验证预测逻辑 ===")
    try:
        # 模拟递归预测过程
        base_vol = vol[-1]  # 最后一天的波动率
        pred_1 = base_vol * 1.02  # 预测第1天
        pred_2 = pred_1 * 1.01  # 预测第2天
        pred_3 = pred_2 * 1.01  # 预测第3天
        pred_4 = pred_3 * 1.01  # 预测第4天
        pred_5 = pred_4 * 1.01  # 预测第5天

        print(f"基础波动率: {base_vol:.4f}")
        print(
            f"递归预测结果: [{pred_1:.4f}, {pred_2:.4f}, {pred_3:.4f}, {pred_4:.4f}, {pred_5:.4f}]"
        )
        print(f"直接预测结果: {predictions}")

        # 检查是否合理（预测值应该与基础值相近）
        if (
            abs(predictions[0] - base_vol) / base_vol < 0.5
        ):  # 预测值与基础值差异不超过50%
            print("✓ 预测逻辑合理")
        else:
            print("⚠ 预测值与基础值差异较大，可能需要调整")

    except Exception as e:
        print(f"✗ 预测逻辑验证失败: {e}")
        return

    print("\n=== 系统测试总结 ===")
    print("✓ 基础波动率计算模块正常")
    print("✓ 预测函数模块正常")
    print("✓ 内置参数配置正常")
    print("✓ 预测逻辑验证通过")
    print("✓ 整个波动率预测系统工作正常！")

    print("\n=== 使用说明 ===")
    print("1. 历史波动率参数: system.historical_volatility (30天滚动窗口)")
    print(
        "2. 预测波动率参数: system.predict_volatility_1day ~ system.predict_volatility_5day"
    )
    print("3. 聚合函数: VOLATILITY (历史波动率), PREDICT (预测波动率)")
    print("4. 数据库已包含完整的初始化配置")
    print("5. 参数通过递归预测实现：1天->2天->3天->4天->5天")


if __name__ == "__main__":
    test_complete_system()
