#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
波动率预测系统使用示例
展示如何在量化策略中使用修正后的波动率指标和参数
"""


def create_volatility_strategy_example():
    """创建一个使用波动率预测的策略示例"""

    strategy_example = """
-- =========================================
-- 波动率预测策略示例
-- =========================================

-- 1. 策略基本信息
INSERT INTO Strategy (
    creator_name,
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
    strategy_desc
) VALUES (
    'system',
    '波动率预测择时策略',
    TRUE,
    'single_stock',
    '000001.SZ',
    '000300.SH',
    -- 选股函数：基于波动率预测进行择时
    'def select_func(candidates, params, position_count, current_holdings, date, context=None):
        stock = candidates[0]
        
        # 获取当前波动率和预测波动率
        current_vol = params[stock]["system.historical_volatility_30d"]
        predict_vol_1day = params[stock]["system.predict_volatility_1day"]
        predict_vol_3day = params[stock]["system.predict_volatility_3day"]
        
        # 获取Parkinson和Garman-Klass波动率作为参考
        parkinson_vol = params[stock]["system.parkinson_volatility_30d"]
        gk_vol = params[stock]["system.garman_klass_volatility_30d"]
        
        # 波动率择时逻辑
        # 1. 预测波动率下降 -> 买入信号（市场趋稳）
        # 2. 当前波动率相对较低 -> 买入信号（低风险入场）
        # 3. 多种波动率指标确认 -> 增强信号可靠性
        
        vol_trend_down = predict_vol_1day < current_vol * 0.95  # 预测1天波动率下降5%以上
        vol_continue_down = predict_vol_3day < predict_vol_1day * 0.98  # 预测趋势持续
        vol_relatively_low = current_vol < (parkinson_vol + gk_vol) / 2 * 0.9  # 当前波动率相对较低
        
        if vol_trend_down and vol_continue_down and vol_relatively_low:
            return [stock]  # 买入信号
        elif predict_vol_1day > current_vol * 1.05:  # 预测波动率上升5%以上
            return []  # 卖出信号
        else:
            return current_holdings  # 保持现状
    ',
    
    -- 风控函数：基于波动率进行风险控制
    'def risk_control_func(current_holdings, params, date, context=None):
        sell_list = []
        for stock in current_holdings:
            # 获取波动率参数
            current_vol = params[stock]["system.historical_volatility_30d"]
            predict_vol_1day = params[stock]["system.predict_volatility_1day"]
            gk_vol = params[stock]["system.garman_klass_volatility_30d"]
            
            # 风控条件
            # 1. 预测波动率急剧上升 -> 止损
            # 2. Garman-Klass波动率过高 -> 止损
            # 3. 波动率持续上升趋势 -> 止损
            
            vol_spike = predict_vol_1day > current_vol * 1.2  # 预测波动率上升20%以上
            vol_too_high = gk_vol > current_vol * 1.5  # GK波动率过高
            
            if vol_spike or vol_too_high:
                sell_list.append(stock)
        
        return [h for h in current_holdings if h not in sell_list]
    ',
    1,  -- 持股数量
    1,  -- 每日调仓
    0.0003,
    0.0013,
    '基于波动率预测的择时策略：低波动率买入，高波动率卖出，多种波动率指标综合判断'
);

-- 2. 策略参数关系（该策略需要的参数）
INSERT INTO StrategyParamRel (
    strategy_creator_name,
    strategy_name,
    param_creator_name,
    param_name
) VALUES
    -- 基础OHLC参数（回测必需）
    ('system', '波动率预测择时策略', 'system', 'close'),
    ('system', '波动率预测择时策略', 'system', 'high'),
    ('system', '波动率预测择时策略', 'system', 'low'),
    ('system', '波动率预测择时策略', 'system', 'open'),
    
    -- 波动率参数
    ('system', '波动率预测择时策略', 'system', 'historical_volatility_30d'),
    ('system', '波动率预测择时策略', 'system', 'parkinson_volatility_30d'),
    ('system', '波动率预测择时策略', 'system', 'garman_klass_volatility_30d'),
    
    -- 预测参数
    ('system', '波动率预测择时策略', 'system', 'predict_volatility_1day'),
    ('system', '波动率预测择时策略', 'system', 'predict_volatility_3day');
"""

    print("=" * 80)
    print("📈 波动率预测系统使用示例")
    print("=" * 80)

    print("\n🎯 策略设计思路")
    print("-" * 50)
    print("1. 📊 多维度波动率分析")
    print("   - 历史波动率：基于收盘价的经典波动率")
    print("   - Parkinson波动率：基于高低价的日内波动率")
    print("   - Garman-Klass波动率：基于OHLC的综合波动率")

    print("\n2. 🔮 预测驱动决策")
    print("   - 1天预测：短期波动率趋势判断")
    print("   - 3天预测：中期波动率趋势确认")
    print("   - 趋势分析：波动率变化方向和幅度")

    print("\n3. ⚖️ 风险控制")
    print("   - 波动率急剧上升时止损")
    print("   - 多指标确认避免误判")
    print("   - 动态调整仓位")

    print("\n📋 策略参数使用")
    print("-" * 50)
    print("基础参数（回测必需）：")
    print("  - system.close, system.high, system.low, system.open")

    print("\n波动率参数（策略核心）：")
    print("  - system.historical_volatility_30d：30天历史波动率平均")
    print("  - system.parkinson_volatility_30d：30天Parkinson波动率平均")
    print("  - system.garman_klass_volatility_30d：30天GK波动率平均")

    print("\n预测参数（决策依据）：")
    print("  - system.predict_volatility_1day：1天波动率预测")
    print("  - system.predict_volatility_3day：3天波动率预测")

    print("\n🏃‍♂️ 策略执行逻辑")
    print("-" * 50)
    print("买入条件（同时满足）：")
    print("  ✅ 预测1天波动率下降5%以上")
    print("  ✅ 预测3天波动率继续下降")
    print("  ✅ 当前波动率相对较低")

    print("\n卖出条件（任一满足）：")
    print("  ❌ 预测1天波动率上升5%以上")
    print("  ❌ 预测波动率急剧上升20%以上（风控）")
    print("  ❌ GK波动率过高（风控）")

    print("\n📊 数据流向")
    print("-" * 50)
    print("原始数据 → 波动率指标 → 波动率参数 → 预测参数 → 策略决策")
    print("  OHLC   →   计算波动率  →  时间窗口处理 →   预测算法  →   买卖信号")

    print("\n💻 SQL代码")
    print("-" * 50)
    print(strategy_example)

    print("\n" + "=" * 80)
    print("🎉 示例创建完成！")
    print("这个策略完整展示了如何使用修正后的波动率预测系统")
    print("=" * 80)


if __name__ == "__main__":
    create_volatility_strategy_example()
