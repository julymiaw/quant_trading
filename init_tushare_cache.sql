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
    ts_code VARCHAR(20) NOT NULL COMMENT 'Tushare股票代码',
    symbol VARCHAR(20) COMMENT '股票代码(不含后缀)',
    `name` VARCHAR(200) COMMENT '股票名称',
    area VARCHAR(100) COMMENT '所在地域',
    industry VARCHAR(100) COMMENT '所属行业',
    fullname VARCHAR(300) COMMENT '股票全称',
    enname VARCHAR(300) COMMENT '英文全称',
    cnspell VARCHAR(100) COMMENT '拼音缩写',
    market VARCHAR(50) COMMENT '市场类型(主板/创业板/科创板等)',
    `exchange` VARCHAR(20) COMMENT '交易所代码',
    curr_type VARCHAR(20) COMMENT '交易货币',
    list_status VARCHAR(10) COMMENT '上市状态(L上市/D退市/P暂停)',
    list_date VARCHAR(8) COMMENT '上市日期(YYYYMMDD)',
    delist_date VARCHAR(8) COMMENT '退市日期(YYYYMMDD)',
    is_hs VARCHAR(10) COMMENT '沪深港通标的(H沪股通/S深股通/N否)',
    act_name VARCHAR(200) COMMENT '实际控制人名称',
    act_ent_type VARCHAR(200) COMMENT '实际控制人类型',
    PRIMARY KEY (ts_code),
    INDEX idx_symbol (symbol),
    INDEX idx_list_status (list_status),
    INDEX idx_exchange (exchange),
    INDEX idx_industry (industry)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_unicode_ci COMMENT = 'Tushare stock_basic 本地缓存';

-- 日线行情表
CREATE TABLE daily (
    ts_code VARCHAR(20) NOT NULL COMMENT '股票代码',
    trade_date VARCHAR(8) NOT NULL COMMENT '交易日期(YYYYMMDD格式)',
    `open` DOUBLE COMMENT '开盘价(元)',
    high DOUBLE COMMENT '最高价(元)',
    low DOUBLE COMMENT '最低价(元)',
    `close` DOUBLE COMMENT '收盘价(元)',
    pre_close DOUBLE COMMENT '昨收价(元,除权价)',
    `change` DOUBLE COMMENT '涨跌额(元)',
    pct_chg DOUBLE COMMENT '涨跌幅(%)',
    vol DOUBLE COMMENT '成交量(手)',
    amount DOUBLE COMMENT '成交额(千元)',
    PRIMARY KEY (ts_code, trade_date),
    INDEX idx_trade_date (trade_date),
    INDEX idx_ts_code (ts_code)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_unicode_ci COMMENT = 'Tushare daily 本地缓存';

-- 每日指标表
CREATE TABLE daily_basic (
    ts_code VARCHAR(20) NOT NULL COMMENT '股票代码',
    trade_date VARCHAR(8) NOT NULL COMMENT '交易日期(YYYYMMDD格式)',
    `close` DOUBLE COMMENT '当日收盘价(元)',
    turnover_rate DOUBLE COMMENT '换手率(%)',
    turnover_rate_f DOUBLE COMMENT '换手率-自由流通股(%)',
    volume_ratio DOUBLE COMMENT '量比',
    pe DOUBLE COMMENT '市盈率(总市值/净利润)',
    pe_ttm DOUBLE COMMENT '市盈率TTM(滚动12个月)',
    pb DOUBLE COMMENT '市净率(总市值/净资产)',
    ps DOUBLE COMMENT '市销率',
    ps_ttm DOUBLE COMMENT '市销率TTM(滚动12个月)',
    dv_ratio DOUBLE COMMENT '股息率(%)',
    dv_ttm DOUBLE COMMENT '股息率TTM(%)',
    total_share DOUBLE COMMENT '总股本(万股)',
    float_share DOUBLE COMMENT '流通股本(万股)',
    free_share DOUBLE COMMENT '自由流通股本(万股)',
    total_mv DOUBLE COMMENT '总市值(万元)',
    circ_mv DOUBLE COMMENT '流通市值(万元)',
    PRIMARY KEY (ts_code, trade_date),
    INDEX idx_trade_date (trade_date),
    INDEX idx_ts_code (ts_code)
) ENGINE = InnoDB DEFAULT CHARSET = utf8mb4 COLLATE = utf8mb4_unicode_ci COMMENT = 'Tushare daily_basic 本地缓存';

-- 指数基本信息表
CREATE TABLE index_basic (
    ts_code VARCHAR(20) NOT NULL COMMENT 'Tushare指数代码',
    name VARCHAR(100) COMMENT '指数简称',
    fullname VARCHAR(200) COMMENT '指数全称',
    market VARCHAR(20) COMMENT '市场',
    publisher VARCHAR(100) COMMENT '发布方',
    index_type VARCHAR(50) COMMENT '指数风格',
    category VARCHAR(50) COMMENT '指数类别',
    base_date VARCHAR(8) COMMENT '基期日期',
    base_point DOUBLE COMMENT '基点',
    list_date VARCHAR(8) COMMENT '发布日期',
    weight_rule VARCHAR(100) COMMENT '加权方式',
    `desc` TEXT COMMENT '指数描述',
    exp_date VARCHAR(8) COMMENT '终止日期',

    PRIMARY KEY (ts_code),
    INDEX idx_market (market),
    INDEX idx_category (category)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Tushare index_basic 本地缓存';

-- 指数日线行情表
CREATE TABLE index_daily (
    ts_code VARCHAR(20) NOT NULL COMMENT 'Tushare指数代码',
    trade_date VARCHAR(8) NOT NULL COMMENT '交易日期(YYYYMMDD)',
    `close` DOUBLE COMMENT '收盘点位',
    `open` DOUBLE COMMENT '开盘点位',
    high DOUBLE COMMENT '最高点位',
    low DOUBLE COMMENT '最低点位',
    pre_close DOUBLE COMMENT '昨日收盘点位',
    `change` DOUBLE COMMENT '涨跌点数',
    pct_chg DOUBLE COMMENT '涨跌幅(%)',
    vol DOUBLE COMMENT '成交量(手)',
    amount DOUBLE COMMENT '成交额(千元)',

    PRIMARY KEY (ts_code, trade_date),
    INDEX idx_trade_date (trade_date),
    INDEX idx_ts_code (ts_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Tushare index_daily 本地缓存';