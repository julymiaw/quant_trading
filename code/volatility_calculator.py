import numpy as np
import numpy as np
import pandas as pd

def historical_volatility(prices, window=3):
    """
    计算滚动历史波动率，为每一天输出一个值。

    :param prices: List, array or Pandas Series of historical prices.
    :param window: 计算波动率的滚动窗口大小（默认30天）。
    :return: 年化历史波动率数组（百分比），与输入prices长度相同。
    """

    # 确保输入是NumPy数组
    prices_arr = np.asarray(prices)
    
    # 计算日简单收益率
    returns = np.diff(prices_arr) / prices_arr[:-1]
    
    # 创建一个数组来存储结果，初始值为NaN（因为前window天数据不足）
    volatility_series = np.full_like(prices_arr, 0, dtype=float)
    
    # 从第window天开始计算滚动波动率
    # 第i天的波动率基于 returns[i-window:i] 计算
    for i in range(1, len(returns) + 1):
        # 获取当前窗口内的收益率
        current_window = min(i, window)
        window_returns = returns[i - current_window:i]
        
        # 计算窗口内收益率的标准差（日波动率）
        daily_vol = np.std(window_returns)
        
        # 年化波动率并转换为百分比
        annual_vol = daily_vol * np.sqrt(252) * 100
        
        # 将结果存储在对应位置（注意索引对齐：波动率对应的是窗口结束的那一天）
        volatility_series[i] = annual_vol
    
    return volatility_series

def parkinson_volatility(highs, lows, period=30):
    """
    Calculate the Parkinson volatility of a series of high and low prices.

    :param highs: List or array of historical high prices.
    :param lows: List or array of historical low prices.
    :param period: The period over which to calculate volatility (default is 30).
    :return: The Parkinson volatility as a percentage.
    """

    if len(highs) != len(lows):
        raise ValueError("Highs and lows must have the same length.")

    # Calculate the logarithmic range
    log_range = np.log(highs / lows)

    # Calculate the variance using Parkinson's formula
    variance = (1 / (4 * np.log(2))) * np.mean(log_range ** 2)

    # Annualize the volatility
    annualized_volatility = np.sqrt(variance) * np.sqrt(252)  # Assuming 252 trading days in a year

    # Convert to percentage
    return annualized_volatility * 100

def garman_klass_volatility(opens, highs, lows, closes, period=30):
    """
    Calculate the Garman-Klass volatility of a series of open, high, low, and close prices.

    :param opens: List or array of historical open prices.
    :param highs: List or array of historical high prices.
    :param lows: List or array of historical low prices.
    :param closes: List or array of historical close prices.
    :param period: The period over which to calculate volatility (default is 30).
    :return: The Garman-Klass volatility as a percentage.
    """

    if not (len(opens) == len(highs) == len(lows) == len(closes)):
        raise ValueError("All price lists must have the same length.")

    # Calculate the logarithmic ranges
    log_hl = np.log(highs / lows)
    log_co = np.log(closes / opens)

    # Calculate the variance using Garman-Klass formula
    variance = (0.5 * np.mean(log_hl ** 2)) - (2 * np.log(2) - 1) * np.mean(log_co ** 2)

    # Annualize the volatility
    annualized_volatility = np.sqrt(variance) * np.sqrt(252)  # Assuming 252 trading days in a year

    # Convert to percentage
    return annualized_volatility * 100

def rogers_satchel_volatility(highs, lows, closes, period=30):
    """
    Calculate the Rogers-Satchel volatility of a series of high, low, and close prices.

    :param highs: List or array of historical high prices.
    :param lows: List or array of historical low prices.
    :param closes: List or array of historical close prices.
    :param period: The period over which to calculate volatility (default is 30).
    :return: The Rogers-Satchel volatility as a percentage.
    """

    if not (len(highs) == len(lows) == len(closes)):
        raise ValueError("All price lists must have the same length.")

    # Calculate the logarithmic ranges
    log_hl = np.log(highs / lows)
    log_hc = np.log(highs / closes)
    log_lc = np.log(lows / closes)

    # Calculate the variance using Rogers-Satchel formula
    variance = (0.511 * np.mean(log_hl ** 2)) - (0.019 * np.mean(log_hc * log_lc))

    # Annualize the volatility
    annualized_volatility = np.sqrt(variance) * np.sqrt(252)  # Assuming 252 trading days in a year

    # Convert to percentage
    return annualized_volatility * 100

def yang_zhang_volatility(opens, highs, lows, closes, period=30):
    """
    Calculate the Yang-Zhang volatility of a series of open, high, low, and close prices.

    :param opens: List or array of historical open prices.
    :param highs: List or array of historical high prices.
    :param lows: List or array of historical low prices.
    :param closes: List or array of historical close prices.
    :param period: The period over which to calculate volatility (default is 30).
    :return: The Yang-Zhang volatility as a percentage.
    """

    if not (len(opens) == len(highs) == len(lows) == len(closes)):
        raise ValueError("All price lists must have the same length.")

    # Calculate the logarithmic returns
    log_oc = np.log(closes / opens)
    log_hl = np.log(highs / lows)
    log_co_prev = np.log(closes[1:] / closes[:-1])
    log_oc_prev = np.log(opens[1:] / closes[:-1])

    # Calculate the components of the variance
    sigma_o = np.var(log_oc)
    sigma_c = np.var(log_co_prev)
    sigma_rs = np.var(log_hl)

    # Calculate the weights
    k = 0.34 / (1.34 + (period + 1) / (period - 1))

    # Calculate the Yang-Zhang variance
    variance = sigma_o + k * sigma_c + (1 - k) * sigma_rs

    # Annualize the volatility
    annualized_volatility = np.sqrt(variance) * np.sqrt(252)  # Assuming 252 trading days in a year

    # Convert to percentage
    return annualized_volatility * 100

def ewma_volatility(prices, alpha=0.94):
    """
    Calculate the Exponentially Weighted Moving Average (EWMA) volatility of a series of prices.

    :param prices: List or array of historical prices.
    :param alpha: The smoothing factor (default is 0.94).
    :return: The EWMA volatility as a percentage.
    """

    # Calculate daily returns
    returns = np.diff(prices) / prices[:-1]

    # Initialize the EWMA variance
    ewma_variance = 0
    ewma_volatilities = []

    for r in returns:
        ewma_variance = alpha * ewma_variance + (1 - alpha) * (r ** 2)
        ewma_volatilities.append(np.sqrt(ewma_variance))

    # Annualize the volatility
    annualized_volatility = np.array(ewma_volatilities) * np.sqrt(252)  # Assuming 252 trading days in a year

    # Convert to percentage
    return annualized_volatility[-1] * 100 if len(annualized_volatility) > 0 else 0