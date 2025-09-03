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
-- 2. 创建股票市场数据表
-- =============================================
CREATE TABLE StockMarketData (
    stock_code VARCHAR(20) NOT NULL,
    trade_date DATE NOT NULL,
    open_price DECIMAL(10,3) NOT NULL,
    high_price DECIMAL(10,3) NOT NULL,
    low_price DECIMAL(10,3) NOT NULL,
    close_price DECIMAL(10,3) NOT NULL,
    pre_close_price DECIMAL(10,3) NOT NULL,
    change_amount DECIMAL(10,3) NOT NULL,
    change_percent DECIMAL(8,4) NOT NULL,
    volume BIGINT NOT NULL,
    amount DECIMAL(15,3) NOT NULL,
    data_source ENUM('tushare', 'akshare') NOT NULL,
    collect_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    PRIMARY KEY (stock_code, trade_date),
    INDEX idx_stock_code (stock_code),
    INDEX idx_trade_date (trade_date),
    INDEX idx_collect_time (collect_time),
    
    CONSTRAINT chk_prices_positive CHECK (
        open_price > 0 AND high_price > 0 AND 
        low_price > 0 AND close_price > 0 AND pre_close_price > 0
    ),
    CONSTRAINT chk_high_low_logic CHECK (
        high_price >= GREATEST(open_price, close_price, low_price) AND
        low_price <= LEAST(open_price, close_price, high_price)
    ),
    CONSTRAINT chk_volume_amount CHECK (volume >= 0 AND amount >= 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='股票市场数据表';

-- 1. 股票基本信息表
CREATE TABLE StockBasic (
    stock_code VARCHAR(20) NOT NULL,
    stock_name VARCHAR(100) NOT NULL,
    area VARCHAR(50),
    industry VARCHAR(50),
    market VARCHAR(20),
    list_status VARCHAR(10),
    list_date DATE,
    is_hs VARCHAR(10),
    data_source VARCHAR(20) NOT NULL,
    collect_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    PRIMARY KEY (stock_code),
    INDEX idx_industry (industry),
    INDEX idx_list_status (list_status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='股票基本信息表';

-- 2. 股票估值数据表
CREATE TABLE StockValuation (
    stock_code VARCHAR(20) NOT NULL,
    trade_date DATE NOT NULL,
    pe_ratio DECIMAL(10,4),
    pb_ratio DECIMAL(10,4),
    ps_ratio DECIMAL(10,4),
    market_cap DECIMAL(20,4),
    circulating_market_cap DECIMAL(20,4),
    turnover_ratio DECIMAL(10,4),
    data_source VARCHAR(20) NOT NULL,
    collect_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    PRIMARY KEY (stock_code, trade_date),
    INDEX idx_stock_code (stock_code),
    INDEX idx_trade_date (trade_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='股票估值数据表';

-- 3. 资产负债表
CREATE TABLE BalanceSheet (
    stock_code VARCHAR(20) NOT NULL,
    report_period DATE NOT NULL,
    announcement_date DATE NOT NULL,
    total_assets DECIMAL(20,4),
    total_liability DECIMAL(20,4),
    total_current_assets DECIMAL(20,4),
    total_current_liability DECIMAL(20,4),
    fixed_assets DECIMAL(20,4),
    cash_equivalents DECIMAL(20,4),
    total_equity DECIMAL(20,4),
    data_source VARCHAR(20) NOT NULL,
    collect_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    PRIMARY KEY (stock_code, report_period),
    INDEX idx_stock_code (stock_code),
    INDEX idx_report_period (report_period)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='资产负债表';

-- 4. 利润表
CREATE TABLE IncomeStatement (
    stock_code VARCHAR(20) NOT NULL,
    report_period DATE NOT NULL,
    announcement_date DATE NOT NULL,
    total_revenue DECIMAL(20,4),
    operating_profit DECIMAL(20,4),
    total_profit DECIMAL(20,4),
    net_profit DECIMAL(20,4),
    eps_basic DECIMAL(10,4),
    data_source VARCHAR(20) NOT NULL,
    collect_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    PRIMARY KEY (stock_code, report_period),
    INDEX idx_stock_code (stock_code),
    INDEX idx_report_period (report_period)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='利润表';

-- 5. 指数成分股表
CREATE TABLE IndexComponent (
    index_code VARCHAR(20) NOT NULL,
    stock_code VARCHAR(20) NOT NULL,
    weight DECIMAL(10,6),
    is_current BOOLEAN NOT NULL DEFAULT TRUE,
    data_source VARCHAR(20) NOT NULL,
    collect_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    PRIMARY KEY (index_code, stock_code),
    INDEX idx_index_code (index_code),
    INDEX idx_stock_code (stock_code),
    INDEX idx_is_current (is_current)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='指数成分股表';

-- 8. 交易日历表
CREATE TABLE TradingCalendar (
    exchange VARCHAR(20) NOT NULL,
    cal_date DATE NOT NULL,
    is_open TINYINT(1) NOT NULL,
    pretrade_date DATE,
    data_source VARCHAR(20) NOT NULL,
    collect_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    PRIMARY KEY (exchange, cal_date),
    INDEX idx_exchange (exchange),
    INDEX idx_cal_date (cal_date),
    INDEX idx_is_open (is_open)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='交易日历表';

-- =============================================
-- 3. 创建技术指标定义表
-- =============================================
CREATE TABLE TechnicalIndicator (
    indicator_id VARCHAR(50) NOT NULL,
    indicator_name VARCHAR(100) NOT NULL,
    indicator_type ENUM('technical', 'fundamental') NOT NULL,
    calculation_method VARCHAR(100) NOT NULL,
    min_value DECIMAL(15,6),
    max_value DECIMAL(15,6),
    default_period INT,
    description TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    
    PRIMARY KEY (indicator_id),
    INDEX idx_indicator_type (indicator_type),
    INDEX idx_is_active (is_active),

    CONSTRAINT chk_period_positive CHECK (default_period IS NULL OR default_period > 0),
    CONSTRAINT chk_value_range CHECK (min_value IS NULL OR max_value IS NULL OR min_value <= max_value)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='技术指标定义表';

-- =============================================
-- 4. 创建策略表
-- =============================================
CREATE TABLE Strategy (
    strategy_id VARCHAR(50) NOT NULL,
    strategy_name VARCHAR(100) NOT NULL,
    strategy_type ENUM('builtin', 'custom') NOT NULL,
    creator_id VARCHAR(50) NOT NULL,
    strategy_desc TEXT,
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    PRIMARY KEY (strategy_id),
    INDEX idx_creator_id (creator_id),
    INDEX idx_strategy_type (strategy_type),

    CONSTRAINT fk_strategy_creator FOREIGN KEY (creator_id) REFERENCES User(user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='选股策略表';

-- =============================================
-- 5. 创建策略条件表
-- =============================================
CREATE TABLE StrategyCondition (
    condition_id VARCHAR(50) NOT NULL,
    strategy_id VARCHAR(50) NOT NULL,
    indicator_id VARCHAR(50) NOT NULL,
    condition_type ENUM('greater', 'less', 'between', 'cross_up', 'cross_down') NOT NULL,
    threshold_min DECIMAL(20,6),
    threshold_max DECIMAL(20,6),
    signal_action ENUM('buy', 'sell', 'hold') NOT NULL,
    condition_order INT NOT NULL,
    
    PRIMARY KEY (condition_id),
    INDEX idx_strategy_order (strategy_id, condition_order),
    INDEX idx_indicator_id (indicator_id),
    
    CONSTRAINT fk_condition_strategy FOREIGN KEY (strategy_id) REFERENCES Strategy(strategy_id) ON DELETE CASCADE,
    CONSTRAINT fk_condition_indicator FOREIGN KEY (indicator_id) REFERENCES TechnicalIndicator(indicator_id),
    
    CONSTRAINT chk_condition_order CHECK (condition_order > 0),
    CONSTRAINT chk_threshold_logic CHECK (
        threshold_min IS NULL OR threshold_max IS NULL OR threshold_min <= threshold_max
    )
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='策略条件表';

-- =============================================
-- 6. 创建交易信号表
-- =============================================
CREATE TABLE TradingSignal (
    signal_id VARCHAR(50) NOT NULL,
    user_id VARCHAR(50) NOT NULL,
    strategy_id VARCHAR(50) NOT NULL,
    stock_code VARCHAR(20) NOT NULL,
    trade_date DATE NOT NULL,
    signal_type ENUM('buy', 'sell', 'hold') NOT NULL,
    confidence DECIMAL(5,4) NOT NULL,
    signal_price DECIMAL(10,3),
    trigger_reason VARCHAR(500),
    generate_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    PRIMARY KEY (signal_id),
    INDEX idx_user_generate_time (user_id, generate_time),
    INDEX idx_stock_trade_date (stock_code, trade_date),
    INDEX idx_strategy_id (strategy_id),
    
    CONSTRAINT fk_signal_user FOREIGN KEY (user_id) REFERENCES User(user_id),
    CONSTRAINT fk_signal_strategy FOREIGN KEY (strategy_id) REFERENCES Strategy(strategy_id),
    
    CONSTRAINT chk_confidence CHECK (confidence BETWEEN 0 AND 1),
    CONSTRAINT chk_signal_price CHECK (signal_price IS NULL OR signal_price > 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='交易信号表';

-- =============================================
-- 7. 创建回测报告表
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
-- 8. 创建系统日志表
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

-- =============================================
-- 9. 插入初始化数据
-- =============================================

-- 插入管理员用户（密码需要在应用层哈希处理）
INSERT INTO User (user_id, user_account, user_password, user_role, user_status, user_email) 
VALUES ('admin_001', 'admin', 'hashed_password_here', 'admin', 'active', 'admin@quanttrading.com');

-- 插入常用技术指标定义
INSERT INTO TechnicalIndicator (indicator_id, indicator_name, indicator_type, calculation_method, min_value, max_value, default_period, description) VALUES
('RSI', 'RSI相对强弱指标', 'momentum', 'talib.RSI', 0, 100, 14, 'RSI指标用于判断股票超买超卖状态'),
('MACD', 'MACD指标', 'trend', 'talib.MACD', NULL, NULL, NULL, 'MACD用于判断趋势变化和买卖时机'),
('BOLL', '布林带指标', 'volatility', 'talib.BBANDS', NULL, NULL, 20, '布林带用于判断价格波动区间'),
('MA5', '5日移动平均线', 'trend', 'talib.SMA', NULL, NULL, 5, '短期趋势指标'),
('MA20', '20日移动平均线', 'trend', 'talib.SMA', NULL, NULL, 20, '中期趋势指标'),
('VOLUME_MA', '成交量移动平均', 'volume', 'talib.SMA', NULL, NULL, 10, '成交量趋势指标'),
('VOLATILITY_PREDICT', '预测波动率', 'custom', 'custom_model', 0, 1, NULL, 'AI模型预测的未来波动率');

-- 添加新的技术指标
INSERT INTO TechnicalIndicator (indicator_id, indicator_name, indicator_type, calculation_method, min_value, max_value, default_period, description) VALUES
('MARKET_CAP', '市值', 'fundamental', 'valuation.market_cap', NULL, NULL, NULL, '公司总市值'),
('PB_RATIO', '市净率', 'fundamental', 'valuation.pb_ratio', NULL, NULL, NULL, '市净率指标'),
('DEBT_RATIO', '资产负债率', 'fundamental', 'custom', 0, 1, NULL, '总负债/总资产'),
('CURRENT_RATIO', '流动比率', 'fundamental', 'custom', 0, NULL, NULL, '流动资产/流动负债'),
('DUAL_THRUST', '通道突破', 'custom', 'custom', NULL, NULL, 10, 'Dual Thrust策略指标');

-- 插入小市值策略
INSERT INTO Strategy (strategy_id, strategy_name, strategy_type, creator_id, strategy_desc) VALUES
('STRAT_004', '小市值策略', 'builtin', 'admin_001', '筛选出市值介于20-30亿的股票，选取其中市值最小的三只股票，每天开盘买入，持有五个交易日，然后调仓。');

-- 插入双均线策略
INSERT INTO Strategy (strategy_id, strategy_name, strategy_type, creator_id, strategy_desc) VALUES
('STRAT_005', '双均线策略', 'builtin', 'admin_001', '通过5日均线和价格的关系进行买卖。当价格上穿5日均线1%时买入，当价格下穿5日均线时卖出。');

-- 插入银行股轮动策略
INSERT INTO Strategy (strategy_id, strategy_name, strategy_type, creator_id, strategy_desc) VALUES
('STRAT_006', '银行股轮动策略', 'builtin', 'admin_001', '始终持有沪深300银行指数成分股中市净率最低的股份制银行，每周检查一次，如果发现有新的股份制银行市净率低于原有的股票，则予以换仓。');

-- 插入低估价值选股策略
INSERT INTO Strategy (strategy_id, strategy_name, strategy_type, creator_id, strategy_desc) VALUES
('STRAT_007', '低估价值选股策略', 'builtin', 'admin_001', '1.市净率小于2；2.负债比例高于市场平均值；3.企业的流动资产至少是流动负债的1.2倍；4.每年四次调仓，即在1/4/7/10月调仓；5.可加入止损(十天HS300跌幅达10%清仓)。');

-- 插入Dual Thrust策略
INSERT INTO Strategy (strategy_id, strategy_name, strategy_type, creator_id, strategy_desc) VALUES
('STRAT_008', 'Dual Thrust策略', 'builtin', 'admin_001', '1.首先计算Range=Max(HH-LC,HC-LL)；2.设定上轨=Open+K1*Range，下轨=Open-K2*Range；3.当价格向上突破上轨时买入，当价格向下突破下轨时卖出。');

-- 为策略添加条件
-- 小市值策略条件
INSERT INTO StrategyCondition (condition_id, strategy_id, indicator_id, condition_type, threshold_min, threshold_max, signal_action, condition_order) VALUES
('COND_005', 'STRAT_004', 'MARKET_CAP', 'between', 2000000000, 3000000000, 'buy', 1);

-- 双均线策略条件
INSERT INTO StrategyCondition (condition_id, strategy_id, indicator_id, condition_type, threshold_min, threshold_max, signal_action, condition_order) VALUES
('COND_006', 'STRAT_005', 'MA5', 'greater', 1.01, NULL, 'buy', 1),
('COND_007', 'STRAT_005', 'MA5', 'less', NULL, 1.0, 'sell', 2);

-- 银行股轮动策略条件
INSERT INTO StrategyCondition (condition_id, strategy_id, indicator_id, condition_type, threshold_min, threshold_max, signal_action, condition_order) VALUES
('COND_008', 'STRAT_006', 'PB_RATIO', 'less', NULL, NULL, 'buy', 1);

-- 低估价值选股策略条件
INSERT INTO StrategyCondition (condition_id, strategy_id, indicator_id, condition_type, threshold_min, threshold_max, signal_action, condition_order) VALUES
('COND_009', 'STRAT_007', 'PB_RATIO', 'less', NULL, 2.0, 'buy', 1),
('COND_010', 'STRAT_007', 'DEBT_RATIO', 'greater', NULL, NULL, 'buy', 2),
('COND_011', 'STRAT_007', 'CURRENT_RATIO', 'greater', 1.2, NULL, 'buy', 3);

-- Dual Thrust策略条件
INSERT INTO StrategyCondition (condition_id, strategy_id, indicator_id, condition_type, threshold_min, threshold_max, signal_action, condition_order) VALUES
('COND_012', 'STRAT_008', 'DUAL_THRUST', 'greater', NULL, NULL, 'buy', 1),
('COND_013', 'STRAT_008', 'DUAL_THRUST', 'less', NULL, NULL, 'sell', 2);

-- =============================================
-- 10. 创建视图（便于查询）
-- =============================================

-- 策略详情视图
CREATE VIEW StrategyDetail AS
SELECT 
    s.strategy_id,
    s.strategy_name,
    s.strategy_type,
    u.user_account as creator_name,
    s.strategy_desc,
    s.create_time,
    COUNT(sc.condition_id) as condition_count
FROM Strategy s
LEFT JOIN User u ON s.creator_id = u.user_id
LEFT JOIN StrategyCondition sc ON s.strategy_id = sc.strategy_id
GROUP BY s.strategy_id, s.strategy_name, s.strategy_type, u.user_account, s.strategy_desc, s.create_time;

-- 最新股价视图
CREATE VIEW LatestStockPrice AS
SELECT s.stock_code, 
       s.trade_date as latest_date, 
       s.close_price as latest_price,
       s.change_percent, 
       s.volume
FROM StockMarketData s
JOIN (
    SELECT stock_code, MAX(trade_date) as max_date
    FROM StockMarketData
    GROUP BY stock_code
) t ON s.stock_code = t.stock_code AND s.trade_date = t.max_date;

-- =============================================
-- 11. 创建存储过程（数据清理）
-- =============================================

DELIMITER //

-- 清理过期日志存储过程
CREATE PROCEDURE CleanExpiredLogs(IN days_to_keep INT)
BEGIN
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        RESIGNAL;
    END;
    
    START TRANSACTION;
    DELETE FROM SystemLog 
    WHERE operation_time < DATE_SUB(NOW(), INTERVAL days_to_keep DAY);
    COMMIT;
END //

DELIMITER ;

-- =============================================
-- 12. 设置数据库优化参数
-- =============================================

-- 记录初始化完成日志
INSERT INTO SystemLog (log_id, operator_id, operator_role, operation_type, operation_content, operation_result) 
VALUES (UUID(), 'admin_001', 'admin', 'data_sync', '数据库初始化完成', 'success');

-- =============================================
-- 初始化完成提示
-- =============================================
SELECT 'Database initialization completed successfully!' as status;
SELECT COUNT(*) as total_tables FROM information_schema.tables WHERE table_schema = 'quantitative_trading';
SELECT table_name, table_comment FROM information_schema.tables WHERE table_schema = 'quantitative_trading' ORDER BY table_name;