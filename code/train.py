from utils import load_data
import volatility_calculator
import numpy as np
from arch import arch_model
def train_model(security, start_date, end_date, window=3):
    print("Training model...")
    prices, highs, lows, opens, closes = load_data(security, start_date, end_date)
    volatility = volatility_calculator.historical_volatility(prices, window)
    volatility_log = np.log(volatility + 0.0001) * 100
    # volatility_log = volatility * 100

    model = arch_model(volatility_log, vol='Garch', p=1, q=1, mean='Constant')
    model_fit = model.fit(update_freq=0, disp='off') # 拟合模型
    forecast_horizon = 5 # 预测未来5天
    forecasts = model_fit.forecast(horizon=forecast_horizon, reindex=False)
    print("Predicted conditional variance for next day:", forecasts.variance.values[-1, 0])
    print("Predicted conditional variance for day 5:", forecasts.variance.values[-1, 4])
    predicted_volatility = np.exp(np.sqrt(forecasts.variance.values[-1, :]) / 100) # 除以100还原尺度
    annualized_vol = predicted_volatility
    print("Annualized Volatility Forecasts for next 5 days:", annualized_vol)

train_model('000001.XSHE', '2024-07-01', '2024-10-01', window=3)