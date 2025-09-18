import tushare as ts
import numpy as np
from arch import arch_model
from torch.utils.data import TensorDataset, DataLoader
import torch
import pandas as pd

pro = ts.pro_api('60d29499510471150805842b1c7fc97e3a7ece2676b4ead1707f94d0')
data = pro.stock_basic(exchange='', list_status='L', fields='ts_code,symbol,name,area,industry,list_date')
name = data['ts_code']
start_date = "20240101"
# start_date = "20240101"
end_date = "20241231"
WINDOW_SIZE = 30
BATCH_SIZE = 32
mu_hats = []
garch_vars = []
true_vars = []
X_lstm = []
y_true_var = [] 
y_garch_var = []


for code in name:
    mu_hats = []
    garch_vars = []
    true_vars = []
    X_lstm = []
    y_true_var = [] 
    y_garch_var = []
    print(code)
    df = pro.daily(ts_code=code, start_date=start_date, end_date=end_date)
    # print(df)
    if df.empty:
        continue
    prices = df['close']
    log_returns = np.log(prices / prices.shift(1))
    print(log_returns)
    log_returns = log_returns.dropna()
    returns_array = log_returns.values
    # print(log_returns)
    for t in range(WINDOW_SIZE, len(returns_array)):
        # 1. 获取当前窗口的收益率数据
        window_data = returns_array[t - WINDOW_SIZE : t]
        
        # 2. 拟合GARCH(1,1)模型
        model = arch_model(window_data * 100, vol='Garch', p=1, q=1, mean='Constant') # 乘以100改善拟合稳定性
        res = model.fit(disp='off')
        
        # 3. 预测下一期的均值和方差
        forecast = res.forecast(horizon=1)
        pred_mu = forecast.mean.iloc[-1, 0] / 100 # 还原尺度
        pred_garch_var = forecast.variance.iloc[-1, 0] / 10000 # 还原尺度
        
        # 4. 获取真实的收益率，并计算真实方差
        actual_return_t = returns_array[t]
        true_var_t = (actual_return_t - pred_mu)**2
        
        # 5. 存储结果
        mu_hats.append(pred_mu)
        garch_vars.append(pred_garch_var)
        true_vars.append(true_var_t)

        # print(mu_hats)
        # print(garch_vars)
        # print(true_vars)
    
    for i in range(len(true_vars) - WINDOW_SIZE):
        # 输入X是过去的真实方差
        X_lstm.append(true_vars[i : i + WINDOW_SIZE])
        
        # 目标y是第91天的真实方差和GARCH预测方差
        y_true_var.append(true_vars[i + WINDOW_SIZE])
        y_garch_var.append(garch_vars[i + WINDOW_SIZE])
    # print(X_lstm)