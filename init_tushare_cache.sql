-- 初始化用于缓存 Tushare 原始数据的数据库
DROP DATABASE IF EXISTS tushare_cache;
CREATE DATABASE tushare_cache DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE tushare_cache;

-- 交易日历表
CREATE TABLE trade_cal (
    exchange VARCHAR(20) NOT NULL,    -- 交易所 SSE上交所 SZSE深交所
    cal_date VARCHAR(8) NOT NULL,     -- 日历日期 YYYYMMDD
    is_open TINYINT,               -- 是否交易 0休市 1交易
    pretrade_date VARCHAR(8),         -- 上一个交易日 YYYYMMDD

    PRIMARY KEY (exchange, cal_date),
    INDEX idx_is_open (is_open),
    INDEX idx_pretrade_date (pretrade_date)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_unicode_ci COMMENT = 'Tushare trade_cal 本地缓存';

-- 股票基础信息表
CREATE TABLE stock_basic (
    ts_code VARCHAR(20) NOT NULL,     -- TS股票代码
    symbol VARCHAR(20),               -- 股票代码
    `name` VARCHAR(200),              -- 股票名称
    area VARCHAR(100),                -- 所在地域
    industry VARCHAR(100),            -- 所属行业
    fullname VARCHAR(300),            -- 股票全称
    enname VARCHAR(300),              -- 英文全称
    cnspell VARCHAR(100),             -- 拼音缩写
    market VARCHAR(50),               -- 市场类型（主板/中小板/创业板/科创板等）
    `exchange` VARCHAR(20),           -- 交易所代码
    curr_type VARCHAR(20),            -- 交易货币
    list_status VARCHAR(10),          -- 上市状态 L上市 D退市 P暂停上市
    list_date VARCHAR(8),             -- 上市日期 YYYYMMDD
    delist_date VARCHAR(8),           -- 退市日期 YYYYMMDD
    is_hs VARCHAR(10),                -- 是否沪深港通标的 H沪股通 S深股通 N否
    act_name VARCHAR(200),            -- 实际控制人名称
    act_ent_type VARCHAR(200),        -- 实际控制人类型
    PRIMARY KEY (ts_code),
    INDEX idx_symbol (symbol),
    INDEX idx_list_status (list_status),
    INDEX idx_exchange (exchange),
    INDEX idx_industry (industry)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_unicode_ci COMMENT = 'Tushare stock_basic 本地缓存';

-- 日线行情表
CREATE TABLE daily (
    ts_code VARCHAR(20) NOT NULL,     -- 股票代码
    trade_date VARCHAR(8) NOT NULL,   -- 交易日期 YYYYMMDD
    `open` DOUBLE,                    -- 开盘价
    high DOUBLE,                      -- 最高价
    low DOUBLE,                       -- 最低价
    `close` DOUBLE,                   -- 收盘价
    pre_close DOUBLE,                 -- 昨收价【除权价，前复权】
    `change` DOUBLE,                  -- 涨跌额
    pct_chg DOUBLE,                   -- 涨跌幅【基于除权后的昨收计算的涨跌幅：（今收-除权昨收）/除权昨收】
    vol DOUBLE,                       -- 成交量（手）
    amount DOUBLE,                    -- 成交额（千元）
    PRIMARY KEY (ts_code, trade_date),
    INDEX idx_trade_date (trade_date),
    INDEX idx_ts_code (ts_code)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_unicode_ci COMMENT = 'Tushare daily 本地缓存';

-- 每日指标表
CREATE TABLE daily_basic (
    ts_code VARCHAR(20) NOT NULL,     -- TS股票代码
    trade_date VARCHAR(8) NOT NULL,   -- 交易日期 YYYYMMDD
    `close` DOUBLE,                   -- 当日收盘价
    turnover_rate DOUBLE,             -- 换手率（%）
    turnover_rate_f DOUBLE,           -- 换手率（自由流通股）
    volume_ratio DOUBLE,              -- 量比
    pe DOUBLE,                        -- 市盈率（总市值/净利润，亏损的PE为空）
    pe_ttm DOUBLE,                    -- 市盈率（TTM，亏损的PE为空）
    pb DOUBLE,                        -- 市净率（总市值/净资产）
    ps DOUBLE,                        -- 市销率
    ps_ttm DOUBLE,                    -- 市销率（TTM）
    dv_ratio DOUBLE,                  -- 股息率（%）
    dv_ttm DOUBLE,                    -- 股息率（TTM）（%）
    total_share DOUBLE,               -- 总股本（万股）
    float_share DOUBLE,               -- 流通股本（万股）
    free_share DOUBLE,                -- 自由流通股本（万）
    total_mv DOUBLE,                  -- 总市值（万元）
    circ_mv DOUBLE,                   -- 流通市值（万元）
    PRIMARY KEY (ts_code, trade_date),
    INDEX idx_trade_date (trade_date),
    INDEX idx_ts_code (ts_code)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_unicode_ci COMMENT = 'Tushare daily_basic 本地缓存';