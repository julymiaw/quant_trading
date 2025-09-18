#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试predict聚合函数是否正常工作
"""

import sys
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tushare_cache_client import TushareCacheClient
from prepare_strategy_data import DataPreparer


def test_predict_aggregation():
    """测试predict聚合函数"""
    print("开始测试predict聚合函数...")

    # 初始化数据准备器
    preparer = DataPreparer("config.json")

    # 获取测试数据
    ts_code = "000001.SZ"
    end_date = "20241001"
    start_date = "20240701"  # 更长的时间范围以获得更多数据

    print(f"获取 {ts_code} 从 {start_date} 到 {end_date} 的数据...")

    try:
        # 获取日线数据
        daily_data = preparer.client.daily(
            ts_code=ts_code, start_date=start_date, end_date=end_date
        )
        if daily_data.empty:
            print("没有获取到数据，请检查日期范围和股票代码")
            return

        print(f"获取到 {len(daily_data)} 条数据")

        # 提取收盘价数据
        closes = daily_data["close"].values
        print(f"收盘价数据长度: {len(closes)}")
        print(f"收盘价范围: {closes.min():.2f} - {closes.max():.2f}")

        # 测试历史波动率计算
        print("\n=== 测试历史波动率聚合函数 ===")
        window = 30
        hist_volatility = preparer._apply_volatility(closes, window)
        print(f"历史波动率计算成功，长度: {len(hist_volatility)}")
        print(f"历史波动率样例 (最后10个值): {hist_volatility[-10:]}")

        # 测试预测波动率计算
        print("\n=== 测试预测波动率聚合函数 ===")
        pred_volatility = preparer._apply_predict_volatility(closes, window)
        print(f"预测波动率计算成功，长度: {len(pred_volatility)}")
        print(f"预测波动率样例 (最后10个值): {pred_volatility[-10:]}")

        # 比较两种波动率的差异
        print("\n=== 对比分析 ===")

        # 计算有效数据范围（去除前面的零值）
        valid_mask = (hist_volatility != 0) & (pred_volatility != 0)
        if np.any(valid_mask):
            valid_hist = hist_volatility[valid_mask]
            valid_pred = pred_volatility[valid_mask]

            # 计算统计指标
            correlation = np.corrcoef(valid_hist, valid_pred)[0, 1]
            mae = np.mean(np.abs(valid_hist - valid_pred))
            rmse = np.sqrt(np.mean((valid_hist - valid_pred) ** 2))

            print(f"有效数据点数量: {len(valid_hist)}")
            print(f"相关系数: {correlation:.4f}")
            print(f"平均绝对误差 (MAE): {mae:.4f}")
            print(f"均方根误差 (RMSE): {rmse:.4f}")

            # 显示一些样例对比
            print(f"\n样例对比 (最后10个有效值):")
            for i in range(max(0, len(valid_hist) - 10), len(valid_hist)):
                if i < len(valid_hist):
                    print(
                        f"  历史: {valid_hist[i]:.4f}, 预测: {valid_pred[i]:.4f}, 差异: {valid_pred[i] - valid_hist[i]:.4f}"
                    )

        # 可视化对比（如果数据足够）
        if len(hist_volatility) > window:
            try:
                # 创建时间序列图
                dates = pd.to_datetime(daily_data["trade_date"], format="%Y%m%d")

                plt.figure(figsize=(12, 6))
                plt.plot(dates, hist_volatility, label="历史波动率", alpha=0.7)
                plt.plot(dates, pred_volatility, label="预测波动率", alpha=0.7)
                plt.xlabel("日期")
                plt.ylabel("波动率")
                plt.title(f"{ts_code} 波动率对比")
                plt.legend()
                plt.grid(True, alpha=0.3)
                plt.xticks(rotation=45)
                plt.tight_layout()

                # 保存图片
                plot_path = os.path.join("code", "volatility_comparison.png")
                plt.savefig(plot_path, dpi=300, bbox_inches="tight")
                print(f"\n可视化结果已保存到: {plot_path}")
                plt.close()

            except Exception as e:
                print(f"可视化过程中出现错误: {e}")

        print("\n✓ predict聚合函数测试完成！")

        # 测试结论
        if np.any(valid_mask):
            if correlation > 0.8:
                print("✓ 相关性良好，预测函数工作正常")
            elif correlation > 0.5:
                print("⚠ 相关性中等，预测函数基本正常，可进一步优化")
            else:
                print("⚠ 相关性较低，预测函数可能需要改进")
        else:
            print("⚠ 没有足够的有效数据进行对比分析")

    except Exception as e:
        print(f"测试过程中出现错误: {e}")
        import traceback

        traceback.print_exc()
    finally:
        preparer.client.close()


if __name__ == "__main__":
    test_predict_aggregation()
