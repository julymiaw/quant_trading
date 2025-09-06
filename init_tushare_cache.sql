-- 初始化用于缓存 Tushare 原始数据的数据库
DROP DATABASE IF EXISTS tushare_cache;
CREATE DATABASE tushare_cache DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE tushare_cache;

-- 交易日历表，与 Tushare trade_cal 字段保持一致（不加约束）
CREATE TABLE trade_cal (
    exchange VARCHAR(20) NOT NULL,         -- 交易所 SSE上交所 SZSE深交所
    cal_date VARCHAR(8) NOT NULL,          -- 日历日期 YYYYMMDD
    is_open VARCHAR(1),                    -- 是否交易 0休市 1交易
    pretrade_date VARCHAR(8),              -- 上一个交易日 YYYYMMDD

    PRIMARY KEY (exchange, cal_date),
    INDEX idx_is_open (is_open),
    INDEX idx_pretrade_date (pretrade_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Tushare trade_cal 本地缓存';

-- 股票基础信息表，与 Tushare stock_basic 字段保持一致（常用字段）
CREATE TABLE stock_basic (
    ts_code VARCHAR(20) NOT NULL,          -- TS股票代码
    symbol VARCHAR(20),                    -- 股票代码
    name VARCHAR(200),                     -- 股票名称
    area VARCHAR(100),                     -- 所在地域
    industry VARCHAR(100),                 -- 所属行业
    fullname VARCHAR(300),                 -- 股票全称
    enname VARCHAR(300),                   -- 英文全称
    cnspell VARCHAR(100),                  -- 拼音缩写
    market VARCHAR(50),                    -- 市场类型（主板/中小板/创业板/科创板等）
    exchange VARCHAR(20),                  -- 交易所代码
    curr_type VARCHAR(20),                 -- 交易货币
    list_status VARCHAR(10),               -- 上市状态 L上市 D退市 P暂停上市
    list_date VARCHAR(8),                  -- 上市日期 YYYYMMDD
    delist_date VARCHAR(8),                -- 退市日期 YYYYMMDD
    is_hs VARCHAR(10),                     -- 是否沪深港通标的 H沪股通 S深股通 N否
    act_name VARCHAR(200),                 -- 实际控制人名称
    act_ent_type VARCHAR(200),             -- 实际控制人类型

    PRIMARY KEY (ts_code),
    INDEX idx_symbol (symbol),
    INDEX idx_list_status (list_status),
    INDEX idx_exchange (exchange),
    INDEX idx_industry (industry)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Tushare stock_basic 本地缓存';
