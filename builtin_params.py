#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
内置参数定义模块
定义系统内置的技术指标参数，包括波动率等
"""

import numpy as np
import pandas as pd


def historical_volatility_param(prices, window=30):
    """
    计算滚动历史波动率参数 - 基于volatility_calculator.py的historical_volatility函数

    :param prices: 价格序列（Pandas Series或numpy array）
    :param window: 计算波动率的滚动窗口大小（默认30天）
    :return: 年化历史波动率数组（百分比），与输入prices长度相同
    """
    # 确保输入是NumPy数组
    prices_arr = np.asarray(prices)

    # 计算日简单收益率
    returns = np.diff(prices_arr) / prices_arr[:-1]

    # 创建一个数组来存储结果，第一天初始值为0
    volatility_series = np.full_like(prices_arr, 0.0, dtype=float)

    # 从第二天开始计算滚动波动率
    for i in range(1, len(returns) + 1):
        # 获取当前窗口内的收益率
        current_window = min(i, window)
        window_returns = returns[i - current_window : i]

        # 计算窗口内收益率的标准差（日波动率）
        daily_vol = np.std(window_returns, ddof=1) if len(window_returns) > 1 else 0

        # 年化波动率并转换为百分比（与原始实现一致）
        annual_vol = daily_vol * np.sqrt(252) * 100

        # 将结果存储在对应位置
        volatility_series[i] = annual_vol

    return volatility_series


def parkinson_volatility_param(highs, lows, window=30):
    """
    计算Parkinson波动率参数

    :param highs: 最高价序列
    :param lows: 最低价序列
    :param window: 计算窗口大小
    :return: Parkinson波动率序列（百分比）
    """
    if len(highs) != len(lows):
        raise ValueError("Highs and lows must have the same length.")

    highs_arr = np.asarray(highs)
    lows_arr = np.asarray(lows)

    # 计算对数范围
    log_range = np.log(highs_arr / lows_arr)

    # 创建结果数组
    volatility_series = np.full_like(highs_arr, 0.0, dtype=float)

    # 滚动计算Parkinson波动率
    for i in range(window, len(log_range) + 1):
        window_log_range = log_range[i - window : i]

        # 使用Parkinson公式计算方差
        variance = (1 / (4 * np.log(2))) * np.mean(window_log_range**2)

        # 年化波动率并转换为百分比
        annualized_volatility = np.sqrt(variance) * np.sqrt(252) * 100

        volatility_series[i - 1] = annualized_volatility

    return volatility_series


def garman_klass_volatility_param(opens, highs, lows, closes, window=30):
    """
    计算Garman-Klass波动率参数

    :param opens: 开盘价序列
    :param highs: 最高价序列
    :param lows: 最低价序列
    :param closes: 收盘价序列
    :param window: 计算窗口大小
    :return: Garman-Klass波动率序列（百分比）
    """
    if not (len(opens) == len(highs) == len(lows) == len(closes)):
        raise ValueError("All price lists must have the same length.")

    opens_arr = np.asarray(opens)
    highs_arr = np.asarray(highs)
    lows_arr = np.asarray(lows)
    closes_arr = np.asarray(closes)

    # 计算对数范围
    log_hl = np.log(highs_arr / lows_arr)
    log_co = np.log(closes_arr / opens_arr)

    # 创建结果数组
    volatility_series = np.full_like(opens_arr, 0.0, dtype=float)

    # 滚动计算Garman-Klass波动率
    for i in range(window, len(log_hl) + 1):
        window_log_hl = log_hl[i - window : i]
        window_log_co = log_co[i - window : i]

        # 使用Garman-Klass公式计算方差
        variance = (0.5 * np.mean(window_log_hl**2)) - (2 * np.log(2) - 1) * np.mean(
            window_log_co**2
        )

        # 年化波动率并转换为百分比
        annualized_volatility = np.sqrt(variance) * np.sqrt(252) * 100

        volatility_series[i - 1] = annualized_volatility

    return volatility_series


# 定义参数配置信息，用于数据库初始化
BUILTIN_PARAMS = {
    "historical_volatility": {
        "param_name": "historical_volatility",
        "data_id": "daily.close",
        "param_type": "table",
        "pre_period": 30,
        "post_period": 0,
        "agg_func": "VOLATILITY",
        "description": "基于收盘价的30天滚动历史波动率",
    },
    "parkinson_volatility": {
        "param_name": "parkinson_volatility",
        "data_id": "daily.high,daily.low",
        "param_type": "table",
        "pre_period": 30,
        "post_period": 0,
        "agg_func": "PARKINSON_VOL",
        "description": "基于最高价和最低价的30天Parkinson波动率",
    },
    "garman_klass_volatility": {
        "param_name": "garman_klass_volatility",
        "data_id": "daily.open,daily.high,daily.low,daily.close",
        "param_type": "table",
        "pre_period": 30,
        "post_period": 0,
        "agg_func": "GARMAN_KLASS_VOL",
        "description": "基于OHLC价格的30天Garman-Klass波动率",
    },
}

# 注意：波动率预测功能已通过PREDICT聚合函数和预测参数实现，无需单独的指标
