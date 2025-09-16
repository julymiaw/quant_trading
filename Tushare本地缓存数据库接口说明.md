# Tushare本地缓存数据库接口说明

---

本项目实现了 Tushare 主要行情与基础数据的本地缓存，极大提升了数据访问效率，降低了对 Tushare 官方接口的依赖。本文档介绍本地缓存数据库支持的 API 及其用法。

## 支持的API列表

- 交易日历（trade_cal）
- 股票基础信息（stock_basic）
- 日线行情（daily）
- 每日指标（daily_basic）
- 指数基础信息（index_basic）
- 指数日线行情（index_daily）

---

## 1. 交易日历（trade_cal）

**功能**：获取上交所（SSE）交易日历。

**方法签名**：

```python
client.trade_cal(start_date: str, end_date: str, is_open: Optional[int] = None) -> pd.DataFrame
```

**参数说明**：

- `start_date`：开始日期（YYYYMMDD，必填）
- `end_date`：结束日期（YYYYMMDD，必填）
- `is_open`：是否交易日（0休市，1交易，选填）

**返回字段**：

- exchange：交易所（SSE）
- cal_date：日历日期
- is_open：是否交易
- pretrade_date：上一个交易日

**示例**：

```python
df = client.trade_cal(start_date="20240101", end_date="20240131")
```

---

## 2. 股票基础信息（stock_basic）

**功能**：获取所有A股的基础信息。

**方法签名**：

```python
client.stock_basic() -> pd.DataFrame
```

**返回字段**（与Tushare官方一致）：

- ts_code, symbol, name, area, industry, fullname, enname, cnspell, market, exchange, curr_type, list_status, list_date, delist_date, is_hs, act_name, act_ent_type

**示例**：

```python
df = client.stock_basic()
```

---

## 3. 日线行情（daily）

**功能**：获取A股日线行情，自动补全本地缓存。

**方法签名**：

```python
client.daily(ts_code: str = "", start_date: str, end_date: str) -> pd.DataFrame
```

**参数说明**：

- `ts_code`：股票代码（可多个，逗号分隔，留空为全部）
- `start_date`、`end_date`：日期区间（YYYYMMDD，必填）

**返回字段**：

- ts_code, trade_date, open, high, low, close, pre_close, change, pct_chg, vol, amount

**示例**：

```python
df = client.daily(ts_code="000001.SZ", start_date="20240101", end_date="20240110")
```

---

## 4. 每日指标（daily_basic）

**功能**：获取A股每日重要基本面指标，自动补全本地缓存。

**方法签名**：

```python
client.daily_basic(ts_code: str = "", start_date: str, end_date: str) -> pd.DataFrame
```

**参数说明**：

- `ts_code`：股票代码（可多个，逗号分隔，留空为全部）
- `start_date`、`end_date`：日期区间（YYYYMMDD，必填）

**返回字段**（与Tushare官方一致）：

- ts_code, trade_date, close, turnover_rate, turnover_rate_f, volume_ratio, pe, pe_ttm, pb, ps, ps_ttm, dv_ratio, dv_ttm, total_share, float_share, free_share, total_mv, circ_mv

**示例**：

```python
df = client.daily_basic(ts_code="000001.SZ", start_date="20240101", end_date="20240110")
```

---

## 5. 指数基础信息（index_basic）

**功能**：获取上交所（SSE）全部指数基础信息。

**方法签名**：

```python
client.index_basic() -> pd.DataFrame
```

**返回字段**（与Tushare官方一致）：

- ts_code, name, fullname, market, publisher, index_type, category, base_date, base_point, list_date, weight_rule, desc, exp_date

**示例**：

```python
df = client.index_basic()
```

---

## 6. 指数日线行情（index_daily）

**功能**：获取指数日线行情，自动补全本地缓存。

**方法签名**：

```python
client.index_daily(ts_code: str, start_date: str, end_date: str) -> pd.DataFrame
```

**参数说明**：

- `ts_code`：指数代码（必填，支持多个，逗号分隔）
- `start_date`、`end_date`：日期区间（YYYYMMDD，必填）

**返回字段**：

- ts_code, trade_date, close, open, high, low, pre_close, change, pct_chg, vol, amount

**示例**：

```python
df = client.index_daily(ts_code="000001.SH", start_date="20240101", end_date="20240110")
```

---

## 使用说明

1. **初始化数据库**：首次使用请运行 `python tushare_cache_client.py` 或调用 `client.init_all_from_tushare()`，自动全量拉取并缓存所有基础数据。
2. **本地优先**：所有API均优先从本地数据库读取，若本地无数据或不全，部分API会自动联网补全。
3. **仅支持SSE**：本地缓存仅支持上交所（SSE）相关数据，其他市场暂不支持。
4. **字段一致性**：所有表字段与Tushare官方接口保持一致，便于数据对比和迁移。

---

## 依赖环境

- Python 3.7+
- pandas
- pymysql
- tushare

---

## 联系与反馈

如有问题或建议，请联系项目维护者。
