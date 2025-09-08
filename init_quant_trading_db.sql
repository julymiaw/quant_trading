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
    user_id VARCHAR(50) NOT NULL,
    user_account VARCHAR(50) NOT NULL,
    user_password VARCHAR(255) NOT NULL,
    user_role ENUM('admin', 'analyst', 'viewer') NOT NULL DEFAULT 'viewer',
    user_status ENUM('active', 'inactive', 'locked') NOT NULL DEFAULT 'active',
    user_email VARCHAR(100),
    user_phone VARCHAR(20),
    user_create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    user_last_login_time DATETIME,
    
    PRIMARY KEY (user_id),
    UNIQUE KEY uk_user_account (user_account),
    INDEX idx_user_email (user_email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户信息表';

-- =============================================
-- 2. 创建技术指标定义表
-- =============================================
CREATE TABLE TechnicalIndicator (
    indicator_id VARCHAR(50) NOT NULL,
    indicator_name VARCHAR(100) NOT NULL,
    indicator_type ENUM('technical', 'fundamental') NOT NULL,
    calculation_method TEXT NOT NULL,
    default_pre_period INT DEFAULT 0,
    default_post_period INT DEFAULT 0,
    description TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    
    PRIMARY KEY (indicator_id),
    INDEX idx_indicator_type (indicator_type),
    INDEX idx_is_active (is_active),

    CONSTRAINT chk_pre_period_non_negative CHECK (default_pre_period >= 0),
    CONSTRAINT chk_post_period_non_negative CHECK (default_post_period >= 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='技术指标定义表';

-- =============================================
-- 3. 创建策略表
-- =============================================
CREATE TABLE Strategy (
    strategy_id VARCHAR(50) NOT NULL,
    strategy_name VARCHAR(100) NOT NULL,
    strategy_type ENUM('builtin', 'custom') NOT NULL,
    creator_id VARCHAR(50) NOT NULL,
    scope_type ENUM('all', 'single_stock', 'index') NOT NULL,
    scope_id VARCHAR(50),
    position_count INT,
    rebalance_interval INT,
    buy_fee_rate DECIMAL(8,6) NOT NULL DEFAULT 0.001,
    sell_fee_rate DECIMAL(8,6) NOT NULL DEFAULT 0.001,
    strategy_desc TEXT,
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (strategy_id),
    INDEX idx_creator_id (creator_id),
    INDEX idx_strategy_type (strategy_type),
    INDEX idx_scope_type (scope_type),
    INDEX idx_scope_id (scope_id),

    CONSTRAINT fk_strategy_creator FOREIGN KEY (creator_id) REFERENCES User(user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='选股策略表';

-- =============================================
-- 4. 创建策略条件表
-- =============================================
CREATE TABLE StrategyCondition (
    condition_id VARCHAR(50) NOT NULL,
    strategy_id VARCHAR(50) NOT NULL,
    indicator_id VARCHAR(50) NOT NULL,
    condition_type ENUM('greater', 'less', 'between', 'cross_up', 'cross_down') NOT NULL,
    threshold_min VARCHAR(50),           -- 可为数值或指标ID
    min_type ENUM('value', 'indicator'), -- 下界类型
    threshold_max VARCHAR(50),           -- 可为数值或指标ID
    max_type ENUM('value', 'indicator'), -- 上界类型
    signal_action ENUM('buy', 'sell', 'risk_control') NOT NULL,
    condition_order INT NOT NULL,

    PRIMARY KEY (condition_id),
    INDEX idx_strategy_order (strategy_id, condition_order),
    INDEX idx_indicator_id (indicator_id),

    CONSTRAINT fk_condition_strategy FOREIGN KEY (strategy_id) REFERENCES Strategy(strategy_id) ON DELETE CASCADE,
    CONSTRAINT fk_condition_indicator FOREIGN KEY (indicator_id) REFERENCES TechnicalIndicator(indicator_id),
    CONSTRAINT chk_condition_order CHECK (condition_order > 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='策略条件表，支持数值/指标混合阈值及风险控制信号';

-- =============================================
-- 5. 创建交易信号表
-- =============================================
CREATE TABLE TradingSignal (
    signal_id VARCHAR(50) NOT NULL,
    user_id VARCHAR(50) NOT NULL,
    strategy_id VARCHAR(50) NOT NULL,
    stock_code VARCHAR(20) NOT NULL,
    trade_date DATE NOT NULL,
    signal_type ENUM('buy', 'sell', 'risk_control') NOT NULL,
    trigger_reason VARCHAR(500),
    generate_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (signal_id),
    INDEX idx_user_generate_time (user_id, generate_time),
    INDEX idx_stock_trade_date (stock_code, trade_date),
    INDEX idx_strategy_id (strategy_id),

    CONSTRAINT fk_signal_user FOREIGN KEY (user_id) REFERENCES User(user_id),
    CONSTRAINT fk_signal_strategy FOREIGN KEY (strategy_id) REFERENCES Strategy(strategy_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='交易信号表';

-- =============================================
-- 6. 创建回测报告表
-- =============================================
-- 回测报告表 - 增强版，支持指数回测
CREATE TABLE BacktestReport (
    report_id VARCHAR(50) NOT NULL,
    strategy_id VARCHAR(50) NOT NULL,
    user_id VARCHAR(50) NOT NULL,
    backtest_type ENUM('STOCK', 'INDEX') NOT NULL DEFAULT 'STOCK',
    stock_code VARCHAR(20) NOT NULL COMMENT '单股票代码或指数代码',
    component_count INT DEFAULT NULL COMMENT '指数成分股数量',
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    initial_fund DECIMAL(15,2) NOT NULL,
    final_fund DECIMAL(15,2) NOT NULL,
    total_return DECIMAL(8,4) NOT NULL,
    annual_return DECIMAL(8,4) NOT NULL,
    max_drawdown DECIMAL(8,4) NOT NULL,
    sharpe_ratio DECIMAL(8,4),
    win_rate DECIMAL(5,4),
    profit_loss_ratio DECIMAL(8,4),
    trade_count INT NOT NULL,
    report_generate_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    report_status ENUM('generating', 'completed', 'failed') NOT NULL DEFAULT 'generating',
    
    PRIMARY KEY (report_id),
    INDEX idx_strategy_generate_time (strategy_id, report_generate_time),
    INDEX idx_user_id (user_id),
    INDEX idx_stock_code (stock_code),
    INDEX idx_backtest_type (backtest_type),
    
    CONSTRAINT fk_report_strategy FOREIGN KEY (strategy_id) REFERENCES Strategy(strategy_id),
    CONSTRAINT fk_report_user FOREIGN KEY (user_id) REFERENCES User(user_id),
    
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
    log_id VARCHAR(50) NOT NULL,
    operator_id VARCHAR(50),
    operator_role ENUM('admin', 'analyst', 'viewer', 'system'),
    operation_type ENUM('login', 'strategy_create', 'backtest', 'signal_generate', 'data_sync') NOT NULL,
    operation_content TEXT NOT NULL,
    operation_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    operation_result ENUM('success', 'failed', 'warning') NOT NULL,
    error_info TEXT,
    
    PRIMARY KEY (log_id),
    INDEX idx_operator_time (operator_id, operation_time),
    INDEX idx_operation_type (operation_type),
    INDEX idx_operation_time (operation_time),
    
    CONSTRAINT fk_log_operator FOREIGN KEY (operator_id) REFERENCES User(user_id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='系统日志表';
