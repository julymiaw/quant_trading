#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试predict聚合函数是否正常工作
"""

import sys
import os
import numpy as np
import pandas as pd
from datetime import datetime

from tushare_cache_client import TushareCacheClient
from prepare_strategy_data import DataPreparer


def test_predict_aggregation():
    """测试predict聚合函数"""
    print("开始测试predict聚合函数...")

    try:
        # 创建数据准备器
        preparer = DataPreparer("config.json")

        # 获取测试数据
        ts_code = "000001.SZ"  # 平安银行
        end_date = "2024-09-30"
        start_date = "2024-08-01"

        print(f"获取 {ts_code} 从 {start_date} 到 {end_date} 的数据...")

        # 获取股票列表（单只股票）
        stock_list = [ts_code]

        # 获取表数据来测试聚合函数
        table_data = preparer.get_table_data(
            "daily.close", stock_list, start_date, end_date
        )
        print(f"获取到 {len(table_data)} 条价格数据")
        print("价格数据样例:")
        print(table_data.head())

        # 测试历史波动率聚合函数
        print("\n=== 测试VOLATILITY聚合函数 ===")
        param_info_vol = {"agg_func": "VOLATILITY", "pre_period": 30, "post_period": 0}
        param_range = (start_date, end_date)
        vol_result = preparer.calc_param(
            param_info_vol, table_data.reset_index(), param_range
        )
        print(f"历史波动率计算结果:")
        print(vol_result.head())
        print(
            f"波动率统计: 最小值={vol_result['value'].min():.2f}, 最大值={vol_result['value'].max():.2f}, 平均值={vol_result['value'].mean():.2f}"
        )

        # 测试预测聚合函数
        print("\n=== 测试PREDICT聚合函数 ===")
        param_info_pred = {"agg_func": "PREDICT", "pre_period": 30, "post_period": 0}
        pred_result = preparer.calc_param(
            param_info_pred, table_data.reset_index(), param_range
        )
        print(f"波动率预测结果:")
        print(pred_result.head())
        print(
            f"预测统计: 最小值={pred_result['value'].min():.2f}, 最大值={pred_result['value'].max():.2f}, 平均值={pred_result['value'].mean():.2f}"
        )

        # 比较两种方法的结果
        print("\n=== 对比分析 ===")

        # 确保两个DataFrame有相同的索引
        common_index = vol_result.index.intersection(pred_result.index)
        vol_common = vol_result.loc[common_index]["value"]
        pred_common = pred_result.loc[common_index]["value"]

        if len(common_index) > 0:
            print(f"共同数据点数量: {len(common_index)}")
            print(f"历史波动率最后5个值: {vol_common.tail().values}")
            print(f"预测波动率最后5个值: {pred_common.tail().values}")

            # 计算相关性
            correlation = np.corrcoef(vol_common.values, pred_common.values)[0, 1]
            print(f"历史波动率与预测波动率的相关性: {correlation:.4f}")

            # 计算平均差异
            diff = np.abs(vol_common.values - pred_common.values)
            print(f"平均绝对差异: {diff.mean():.4f}")

            if correlation > 0.8:
                print("✓ 预测聚合函数工作正常，与历史波动率高度相关")
            elif correlation > 0.5:
                print("⚠ 预测聚合函数基本正常，但与历史波动率相关性中等")
            else:
                print("✗ 预测聚合函数可能存在问题，与历史波动率相关性较低")
        else:
            print("✗ 没有找到共同的数据点")

        print("\npredict聚合函数测试完成！")

    except Exception as e:
        print(f"测试过程中出现错误: {e}")
        import traceback

        traceback.print_exc()
    finally:
        if "preparer" in locals():
            preparer.conn.close()


if __name__ == "__main__":
    test_predict_aggregation()
