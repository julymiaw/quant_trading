#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试波动率参数计算是否正确
"""

import sys
import os
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

from tushare_cache_client import TushareCacheClient
from builtin_params import (
    historical_volatility_param,
    parkinson_volatility_param,
    garman_klass_volatility_param,
)
from volatility_calculator import (
    historical_volatility as original_historical_volatility,
)


def test_volatility_params():
    """测试波动率参数计算"""
    print("开始测试波动率参数...")

    # 初始化Tushare客户端
    client = TushareCacheClient()

    # 获取测试数据 - 使用.SZ结尾的股票代码
    ts_code = "000001.SZ"  # 平安银行
    end_date = "20241001"
    start_date = "20240801"

    print(f"获取 {ts_code} 从 {start_date} 到 {end_date} 的数据...")

    try:
        # 获取日线数据
        daily_data = client.daily(
            ts_code=ts_code, start_date=start_date, end_date=end_date
        )
        if daily_data.empty:
            print("没有获取到数据，请检查日期范围和股票代码")
            return

        print(f"获取到 {len(daily_data)} 条数据")
        print("数据样例:")
        print(daily_data.head())

        # 提取价格数据
        closes = daily_data["close"].values
        highs = daily_data["high"].values
        lows = daily_data["low"].values
        opens = daily_data["open"].values

        print(f"\n价格数据长度: {len(closes)}")
        print(f"收盘价范围: {closes.min():.2f} - {closes.max():.2f}")

        # 测试历史波动率计算
        print("\n=== 测试历史波动率计算 ===")

        # 使用我们的新实现
        window = 30
        vol_new = historical_volatility_param(closes, window)

        # 使用原始实现对比（如果长度足够）
        if len(closes) >= window:
            vol_original = original_historical_volatility(closes, window)

            print(f"新实现波动率 (前5个值): {vol_new[:5]}")
            print(f"原实现波动率 (前5个值): {vol_original[:5]}")

            # 比较非零值的差异
            non_zero_mask = (vol_new != 0) & (vol_original != 0)
            if np.any(non_zero_mask):
                diff = np.abs(vol_new[non_zero_mask] - vol_original[non_zero_mask])
                print(
                    f"差异统计 - 最大差异: {diff.max():.6f}, 平均差异: {diff.mean():.6f}"
                )

                if diff.max() < 1e-6:
                    print("✓ 历史波动率计算结果一致")
                else:
                    print("✗ 历史波动率计算结果存在差异")
            else:
                print("没有有效的对比数据点")
        else:
            print(f"数据长度不足{window}天，无法计算完整波动率")

        # 测试Parkinson波动率
        print("\n=== 测试Parkinson波动率计算 ===")
        try:
            parkinson_vol = parkinson_volatility_param(highs, lows, window)
            print(f"Parkinson波动率 (最后5个值): {parkinson_vol[-5:]}")
            print("✓ Parkinson波动率计算成功")
        except Exception as e:
            print(f"✗ Parkinson波动率计算失败: {e}")

        # 测试Garman-Klass波动率
        print("\n=== 测试Garman-Klass波动率计算 ===")
        try:
            gk_vol = garman_klass_volatility_param(opens, highs, lows, closes, window)
            print(f"Garman-Klass波动率 (最后5个值): {gk_vol[-5:]}")
            print("✓ Garman-Klass波动率计算成功")
        except Exception as e:
            print(f"✗ Garman-Klass波动率计算失败: {e}")

        # 比较不同波动率方法的结果
        print("\n=== 波动率方法对比 ===")
        if len(closes) >= window:
            # 取最后几个有效值进行对比
            last_idx = -5
            print(f"历史波动率: {vol_new[last_idx:]}")
            if "parkinson_vol" in locals():
                print(f"Parkinson波动率: {parkinson_vol[last_idx:]}")
            if "gk_vol" in locals():
                print(f"Garman-Klass波动率: {gk_vol[last_idx:]}")

        print("\n波动率参数测试完成！")

    except Exception as e:
        print(f"测试过程中出现错误: {e}")
        import traceback

        traceback.print_exc()
    finally:
        client.close()


if __name__ == "__main__":
    test_volatility_params()
