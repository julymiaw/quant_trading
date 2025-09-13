-- =============================================
-- 量化交易系统数据库初始化脚本
-- 数据库：MySQL 8.0+
-- 创建日期：2025-08-30
-- =============================================

-- 创建数据库
DROP DATABASE IF EXISTS quantitative_trading;
CREATE DATABASE quantitative_trading DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE quantitative_trading;

-- =============================================
-- 1. 创建用户表
-- =============================================
CREATE TABLE User (
    user_id VARCHAR(50) NOT NULL COMMENT '用户唯一ID',
    user_name VARCHAR(50) NOT NULL COMMENT '用户名（唯一，仅允许英文、数字、下划线，不能与Tushare表名重复）',
    user_password VARCHAR(255) NOT NULL COMMENT '用户密码（加密存储）',
    user_role ENUM('admin', 'analyst') NOT NULL DEFAULT 'analyst' COMMENT '用户角色',
    user_status ENUM('active', 'inactive', 'locked') NOT NULL DEFAULT 'active' COMMENT '用户状态',
    user_email VARCHAR(100) COMMENT '邮箱',
    user_phone VARCHAR(20) COMMENT '手机号',
    user_create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    user_last_login_time DATETIME COMMENT '最后登录时间',

    PRIMARY KEY (user_id),
    UNIQUE KEY uk_user_name (user_name),
    INDEX idx_user_email (user_email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户信息表';

-- =============================================
-- 2. 创建指标表
-- =============================================

CREATE TABLE Indicator (
    creator_name VARCHAR(50) NOT NULL COMMENT '指标创建者用户名，引用User.user_name',
    indicator_name VARCHAR(100) NOT NULL COMMENT '指标名称',
    calculation_method TEXT NOT NULL COMMENT '指标计算函数',
    description TEXT COMMENT '指标说明',
    is_active BOOLEAN NOT NULL DEFAULT TRUE COMMENT '是否启用',
    creation_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (creator_name, indicator_name),
    INDEX idx_creator_name (creator_name),
    INDEX idx_is_active (is_active),
    CONSTRAINT fk_indicator_creator FOREIGN KEY (creator_name) REFERENCES User(user_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='技术/自定义指标定义表';

-- =============================================
-- 3. 创建策略表
-- =============================================
CREATE TABLE Strategy (
    creator_name VARCHAR(50) NOT NULL COMMENT '策略创建者用户名，引用User.user_name',
    strategy_name VARCHAR(100) NOT NULL COMMENT '策略名称',
    public BOOLEAN NOT NULL DEFAULT TRUE COMMENT '是否公开（管理员创建的为public，用户可选）',
    scope_type ENUM('all', 'single_stock', 'index') NOT NULL COMMENT '策略生效范围类型',
    scope_id VARCHAR(50) COMMENT '股票ID或指数ID（仅当scope_type为单只或指数时填写）',
    select_func TEXT NOT NULL COMMENT '调仓选股函数，调仓日调用，返回目标持仓',
    risk_control_func TEXT COMMENT '风险控制函数，每日调用，仅允许卖出，返回调整后持仓',
    position_count INT COMMENT '持仓股票数量（仅全部/指数时有效）',
    rebalance_interval INT COMMENT '调仓间隔（单位：交易日，仅全部/指数时有效）',
    buy_fee_rate DECIMAL(8,6) NOT NULL DEFAULT 0.001 COMMENT '买入手续费率',
    sell_fee_rate DECIMAL(8,6) NOT NULL DEFAULT 0.001 COMMENT '卖出手续费率',
    strategy_desc TEXT COMMENT '策略描述',
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',

    PRIMARY KEY (creator_name, strategy_name),
    INDEX idx_creator_name (creator_name),
    INDEX idx_scope_type (scope_type),
    INDEX idx_scope_id (scope_id),
    CONSTRAINT fk_strategy_creator FOREIGN KEY (creator_name) REFERENCES User(user_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='选股策略表';

-- =============================================
-- 4. 创建参数表、参数-指标关系表、参数-策略关系表
-- =============================================
CREATE TABLE Param (
    creator_name VARCHAR(50) NOT NULL COMMENT '参数创建者用户名',
    param_name VARCHAR(50) NOT NULL COMMENT '参数唯一名称',
    data_id VARCHAR(100) NOT NULL COMMENT '数据来源ID，如daily.close或system.MACD',
    param_type ENUM('table', 'indicator') NOT NULL COMMENT '参数类型：table=查Tushare表，indicator=引用其他指标',
    pre_period INT DEFAULT 0 COMMENT '向前取历史天数',
    post_period INT DEFAULT 0 COMMENT '向后预测天数',
    agg_func VARCHAR(50) DEFAULT NULL COMMENT '聚合函数，如SMA、EMA、MAX等',
    creation_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (creator_name, param_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='参数定义表';

CREATE TABLE IndicatorParamRel (
    indicator_creator_name VARCHAR(50) NOT NULL COMMENT '指标创建者用户名',
    indicator_name VARCHAR(100) NOT NULL COMMENT '指标名称',
    param_creator_name VARCHAR(50) NOT NULL COMMENT '参数创建者用户名',
    param_name VARCHAR(50) NOT NULL COMMENT '参数唯一名称',
    PRIMARY KEY (indicator_creator_name, indicator_name, param_creator_name, param_name),
    CONSTRAINT fk_rel_indicator FOREIGN KEY (indicator_creator_name, indicator_name) REFERENCES Indicator(creator_name, indicator_name),
    CONSTRAINT fk_rel_param_indicator FOREIGN KEY (param_creator_name, param_name) REFERENCES Param(creator_name, param_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='指标与参数关系表';

CREATE TABLE StrategyParamRel (
    strategy_creator_name VARCHAR(50) NOT NULL COMMENT '策略创建者用户名',
    strategy_name VARCHAR(100) NOT NULL COMMENT '策略名称',
    param_creator_name VARCHAR(50) NOT NULL COMMENT '参数创建者用户名',
    param_name VARCHAR(50) NOT NULL COMMENT '参数唯一ID',
    PRIMARY KEY (strategy_creator_name, strategy_name, param_creator_name, param_name),
    CONSTRAINT fk_rel_strategy FOREIGN KEY (strategy_creator_name, strategy_name) REFERENCES Strategy(creator_name, strategy_name),
    CONSTRAINT fk_rel_param_strategy FOREIGN KEY (param_creator_name, param_name) REFERENCES Param(creator_name, param_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='策略与参数关系表';

-- =============================================
-- 5. 创建交易信号表
-- =============================================
CREATE TABLE TradingSignal (
    signal_id VARCHAR(50) NOT NULL COMMENT '信号唯一ID',
    user_name VARCHAR(50) NOT NULL COMMENT '生成信号的用户名，引用User.user_name',
    creator_name VARCHAR(50) NOT NULL COMMENT '策略创建者用户名，引用Strategy.creator_name',
    strategy_name VARCHAR(100) NOT NULL COMMENT '策略名称，引用Strategy.strategy_name',
    stock_code VARCHAR(20) NOT NULL COMMENT '股票代码',
    trade_date DATE NOT NULL COMMENT '信号生成日期',
    signal_type ENUM('buy', 'sell', 'risk_control') NOT NULL COMMENT '信号类型',
    trigger_reason VARCHAR(500) COMMENT '触发原因',
    generate_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '信号生成时间',

    PRIMARY KEY (signal_id),
    INDEX idx_user_generate_time (user_name, generate_time),
    INDEX idx_stock_trade_date (stock_code, trade_date),
    INDEX idx_strategy (creator_name, strategy_name),
    CONSTRAINT fk_signal_user FOREIGN KEY (user_name) REFERENCES User(user_name),
    CONSTRAINT fk_signal_strategy FOREIGN KEY (creator_name, strategy_name) REFERENCES Strategy(creator_name, strategy_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='交易信号表';

-- =============================================
-- 6. 创建回测报告表
-- =============================================
-- 回测报告表 - 增强版，支持指数回测
CREATE TABLE BacktestReport (
    report_id VARCHAR(50) NOT NULL COMMENT '回测报告唯一ID',
    creator_name VARCHAR(50) NOT NULL COMMENT '策略创建者用户名，引用Strategy.creator_name',
    strategy_name VARCHAR(100) NOT NULL COMMENT '策略名称，引用Strategy.strategy_name',
    user_name VARCHAR(50) NOT NULL COMMENT '回测发起用户',
    backtest_type ENUM('STOCK', 'INDEX') NOT NULL DEFAULT 'STOCK' COMMENT '回测类型',
    stock_code VARCHAR(20) NOT NULL COMMENT '单股票代码或指数代码',
    component_count INT DEFAULT NULL COMMENT '指数成分股数量',
    start_date DATE NOT NULL COMMENT '回测起始日期',
    end_date DATE NOT NULL COMMENT '回测结束日期',
    initial_fund DECIMAL(15,2) NOT NULL COMMENT '初始资金',
    final_fund DECIMAL(15,2) NOT NULL COMMENT '回测结束资金',
    total_return DECIMAL(8,4) NOT NULL COMMENT '总收益率',
    annual_return DECIMAL(8,4) NOT NULL COMMENT '年化收益率',
    max_drawdown DECIMAL(8,4) NOT NULL COMMENT '最大回撤',
    sharpe_ratio DECIMAL(8,4) COMMENT '夏普比率',
    win_rate DECIMAL(5,4) COMMENT '胜率',
    profit_loss_ratio DECIMAL(8,4) COMMENT '盈亏比',
    trade_count INT NOT NULL COMMENT '交易次数',
    report_generate_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '报告生成时间',
    report_status ENUM('generating', 'completed', 'failed') NOT NULL DEFAULT 'generating' COMMENT '报告状态',

    PRIMARY KEY (report_id),
    INDEX idx_strategy_generate_time (creator_name, strategy_name, report_generate_time),
    INDEX idx_user_name (user_name),
    INDEX idx_stock_code (stock_code),
    INDEX idx_backtest_type (backtest_type),
    CONSTRAINT fk_report_strategy FOREIGN KEY (creator_name, strategy_name) REFERENCES Strategy(creator_name, strategy_name),
    CONSTRAINT fk_report_user FOREIGN KEY (user_name) REFERENCES User(user_name),

    CONSTRAINT chk_date_range CHECK (end_date >= start_date),
    CONSTRAINT chk_funds CHECK (initial_fund > 0 AND final_fund >= 0),
    CONSTRAINT chk_drawdown CHECK (max_drawdown >= 0),
    CONSTRAINT chk_win_rate CHECK (win_rate IS NULL OR win_rate BETWEEN 0 AND 1),
    CONSTRAINT chk_ratio CHECK (profit_loss_ratio IS NULL OR profit_loss_ratio >= 0),
    CONSTRAINT chk_trade_count CHECK (trade_count >= 0),
    CONSTRAINT chk_component_count CHECK (component_count IS NULL OR component_count > 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='回测报告表';

-- =============================================
-- 7. 创建系统日志表
-- =============================================
CREATE TABLE SystemLog (
    log_id VARCHAR(50) NOT NULL COMMENT '日志唯一ID',
    operator_name VARCHAR(50) COMMENT '操作用户（可为空，系统操作时为空）',
    operator_role ENUM('admin', 'analyst', 'system') COMMENT '操作用户角色或系统',
    operation_type ENUM('login', 'strategy_create', 'backtest', 'signal_generate', 'data_sync') NOT NULL COMMENT '操作类型',
    operation_content TEXT NOT NULL COMMENT '操作内容描述',
    operation_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '操作时间',
    operation_result ENUM('success', 'failed', 'warning') NOT NULL COMMENT '操作结果',
    error_info TEXT COMMENT '错误信息',

    PRIMARY KEY (log_id),
    INDEX idx_operator_time (operator_name, operation_time),
    INDEX idx_operation_type (operation_type),
    INDEX idx_operation_time (operation_time),
    CONSTRAINT fk_log_operator FOREIGN KEY (operator_name) REFERENCES User(user_name) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='系统日志表';

-- =============================================
-- 8. 初始数据插入示例（按依赖顺序调整，去除冗余）
-- =============================================

-- 1. 插入管理员用户
INSERT INTO User (user_id, user_name, user_password, user_role, user_status, user_create_time)
VALUES ('1', 'system', '******', 'admin', 'active', '2025-09-01');

-- 2. 插入参数表数据（所有参数，先插入参数实体）
INSERT INTO Param (creator_name, param_name, data_id, param_type, pre_period, post_period, agg_func)
VALUES
('system', 'daily_ema_12', 'daily.close', 'table', 12, 0, 'EMA'),
('system', 'daily_ema_26', 'daily.close', 'table', 26, 0, 'EMA'),
('system', 'total_mv', 'daily_basic.total_mv', 'table', 0, 0, NULL),
('system', 'close', 'daily.close', 'table', 0, 0, NULL),
('system', 'high', 'daily.high', 'table', 0, 0, NULL),
('system', 'low', 'daily.low', 'table', 0, 0, NULL),
('system', 'open', 'daily.open', 'table', 0, 0, NULL),
('system', 'ema_5', 'daily.close', 'table', 5, 0, 'EMA'),
('system', 'macd_ema_9', 'system.MACD', 'indicator', 9, 0, 'EMA'),
('system', 'ema_60', 'daily.close', 'table', 60, 0, 'EMA');

-- 3. 插入MACD指标
INSERT INTO Indicator (creator_name, indicator_name, calculation_method, description, is_active)
VALUES (
    'system',
    'MACD',
    'def calculation_method(params):\n    return params["system.daily_ema_12"] - params["system.daily_ema_26"]',
    'MACD线=12日EMA-26日EMA',
    TRUE
);

-- 4. 插入策略（小市值策略、双均线策略、MACD策略）
INSERT INTO Strategy (
    creator_name, strategy_name, public, scope_type, scope_id, select_func, risk_control_func,
    position_count, rebalance_interval, buy_fee_rate, sell_fee_rate, strategy_desc, create_time, update_time
) VALUES
(
    'system',
    '小市值策略',
    TRUE,
    'all',
    NULL,
    'def select_func(candidates, params, position_count, current_holdings, date, context=None):\n    filtered = [s for s in candidates if 2e9 <= params[s]["system.total_mv"] <= 3e9]\n    sorted_stocks = sorted(filtered, key=lambda s: params[s]["system.total_mv"])\n    return sorted_stocks[:position_count]',
    'def risk_control_func(current_holdings, params, date, context=None):\n    sell_list = []\n    for stock in current_holdings:\n        if params[stock]["system.ema_60"] > params[stock]["system.close"]:\n            sell_list.append(stock)\n    return [h for h in current_holdings if h not in sell_list]',
    3,
    5,
    0.0003,
    0.0013,
    '市值20-30亿，市值最小的3只',
    NOW(),
    NOW()
),
(
    'system',
    '双均线策略',
    TRUE,
    'single_stock',
    '000001.SZ',
    'def select_func(candidates, params, position_count, current_holdings, date, context=None):\n    stock = candidates[0]\n    close = params[stock]["system.close"]\n    ema_5 = params[stock]["system.ema_5"]\n    if close > 1.01 * ema_5:\n        return [stock]\n    elif close < ema_5:\n        return []\n    return current_holdings',
    'def risk_control_func(current_holdings, params, date, context=None):\n    sell_list = []\n    for stock in current_holdings:\n        if params[stock]["system.ema_60"] > params[stock]["system.close"]:\n            sell_list.append(stock)\n    return [h for h in current_holdings if h not in sell_list]',
    1,
    1,
    0.0003,
    0.0013,
    '5日均线上穿/下穿日线，择时买卖',
    NOW(),
    NOW()
),
(
    'system',
    'MACD策略',
    TRUE,
    'single_stock',
    '000001.SZ',
    'def select_func(candidates, params, position_count, current_holdings, date, context=None):\n    stock = candidates[0]\n    macd_ema_9 = params[stock]["system.macd_ema_9"]\n    close = params[stock]["system.close"]\n    if macd_ema_9 < close:\n        return [stock]\n    elif macd_ema_9 > close:\n        return []\n    return current_holdings',
    'def risk_control_func(current_holdings, params, date, context=None):\n    sell_list = []\n    for stock in current_holdings:\n        if params[stock]["system.ema_60"] > params[stock]["system.close"]:\n            sell_list.append(stock)\n    return [h for h in current_holdings if h not in sell_list]',
    1,
    1,
    0.0003,
    0.0013,
    '9日MACD线下穿日线买入，上穿卖出',
    NOW(),
    NOW()
);

-- 5. 插入指标与参数关系表（MACD指标参数）
INSERT INTO IndicatorParamRel (indicator_creator_name, indicator_name, param_creator_name, param_name)
VALUES
('system', 'MACD', 'system', 'daily_ema_12'),
('system', 'MACD', 'system', 'daily_ema_26');

-- 6. 插入策略与参数关系表（小市值策略、双均线策略、MACD策略、风控函数参数）
INSERT INTO StrategyParamRel (strategy_creator_name, strategy_name, param_creator_name, param_name)
VALUES
-- 小市值策略参数
('system', '小市值策略', 'system', 'total_mv'),
('system', '小市值策略', 'system', 'close'),
('system', '小市值策略', 'system', 'high'),
('system', '小市值策略', 'system', 'low'),
('system', '小市值策略', 'system', 'open'),
('system', '小市值策略', 'system', 'ema_60'),
-- 双均线策略参数
('system', '双均线策略', 'system', 'close'),
('system', '双均线策略', 'system', 'high'),
('system', '双均线策略', 'system', 'low'),
('system', '双均线策略', 'system', 'open'),
('system', '双均线策略', 'system', 'ema_5'),
('system', '双均线策略', 'system', 'ema_60'),
-- MACD策略参数
('system', 'MACD策略', 'system', 'macd_ema_9'),
('system', 'MACD策略', 'system', 'close'),
('system', 'MACD策略', 'system', 'high'),
('system', 'MACD策略', 'system', 'low'),
('system', 'MACD策略', 'system', 'open'),
('system', 'MACD策略', 'system', 'ema_60');