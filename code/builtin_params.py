#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
内置参数定义模块
定义系统内置的技术指标参数配置信息
注意：波动率计算逻辑现在由指标处理，不再由参数处理
"""

# 定义波动率参数配置信息（现在基于波动率指标）
VOLATILITY_PARAMS = {
    "historical_volatility_30d": {
        "param_name": "historical_volatility_30d",
        "data_id": "system.historical_volatility",
        "param_type": "indicator",
        "pre_period": 30,
        "post_period": 0,
        "agg_func": "SMA",
        "description": "基于历史波动率指标的30天平均参数",
    },
    "parkinson_volatility_30d": {
        "param_name": "parkinson_volatility_30d",
        "data_id": "system.parkinson_volatility",
        "param_type": "indicator",
        "pre_period": 30,
        "post_period": 0,
        "agg_func": "SMA",
        "description": "基于Parkinson波动率指标的30天平均参数",
    },
    "garman_klass_volatility_30d": {
        "param_name": "garman_klass_volatility_30d",
        "data_id": "system.garman_klass_volatility",
        "param_type": "indicator",
        "pre_period": 30,
        "post_period": 0,
        "agg_func": "SMA",
        "description": "基于Garman-Klass波动率指标的30天平均参数",
    },
}

# 定义预测参数配置信息
PREDICT_PARAMS = {
    "predict_volatility_1day": {
        "param_name": "predict_volatility_1day",
        "data_id": "system.historical_volatility_30d",
        "param_type": "indicator",
        "pre_period": 30,
        "post_period": 0,
        "agg_func": "PREDICT",
        "description": "基于历史波动率预测未来1天的波动率参数",
    },
    "predict_volatility_2day": {
        "param_name": "predict_volatility_2day",
        "data_id": "system.predict_volatility_1day",
        "param_type": "indicator",
        "pre_period": 30,
        "post_period": 0,
        "agg_func": "PREDICT",
        "description": "基于1天预测结果预测未来2天的波动率参数",
    },
    "predict_volatility_3day": {
        "param_name": "predict_volatility_3day",
        "data_id": "system.predict_volatility_2day",
        "param_type": "indicator",
        "pre_period": 30,
        "post_period": 0,
        "agg_func": "PREDICT",
        "description": "基于2天预测结果预测未来3天的波动率参数",
    },
    "predict_volatility_4day": {
        "param_name": "predict_volatility_4day",
        "data_id": "system.predict_volatility_3day",
        "param_type": "indicator",
        "pre_period": 30,
        "post_period": 0,
        "agg_func": "PREDICT",
        "description": "基于3天预测结果预测未来4天的波动率参数",
    },
    "predict_volatility_5day": {
        "param_name": "predict_volatility_5day",
        "data_id": "system.predict_volatility_4day",
        "param_type": "indicator",
        "pre_period": 30,
        "post_period": 0,
        "agg_func": "PREDICT",
        "description": "基于4天预测结果预测未来5天的波动率参数",
    },
}
