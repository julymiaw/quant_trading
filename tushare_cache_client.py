#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tushare 本地缓存客户端（tushare_cache）
- 暴露类 TushareCacheClient：方法 trade_cal 与 stock_basic 仅做静默的本地查询（不产生日志）
- 提供 init_all_from_tushare()：一次性从 Tushare 全量拉取 trade_cal 与 stock_basic 并写入本地（此方法会产生日志）
- __main__ 调用 init_all_from_tushare() 以初始化两张表（只在直接运行脚本时执行）
"""

import os
import json
import logging
from typing import Optional
import pandas as pd
import pymysql
import tushare as ts

# logger 仅用于记录与 Tushare 交互的行为（init_all_from_tushare 会使用）
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class TushareCacheClient:
    def __init__(self, config_path: str = "config.json"):
        """
        只加载配置并建立数据库连接（不主动向 Tushare 发送请求）。
        若需从 Tushare 拉取并初始化缓存，请调用 init_all_from_tushare()（仅在需要时运行）。
        """
        self.config = self._load_config(config_path)
        self.db_conn = None
        ts.set_token(self.config.get("tushare_token"))
        self.pro = ts.pro_api()

    def _load_config(self, path):
        if not os.path.exists(path):
            raise FileNotFoundError(f"config not found: {path}")
        with open(path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        if "db_password" not in cfg or "tushare_token" not in cfg:
            raise ValueError("config.json missing required keys")
        return cfg

    def connect(self):
        """建立数据库连接"""
        if self.db_conn:
            return
        cfg = {
            "host": "localhost",
            "port": 3306,
            "user": "root",
            "password": self.config["db_password"],
            "database": "tushare_cache",
            "charset": "utf8mb4",
            "autocommit": False,
        }
        self.db_conn = pymysql.connect(**cfg)

    def close(self):
        if self.db_conn:
            self.db_conn.close()
            self.db_conn = None

    def _read_trade_cal_from_db(self, start_date, end_date, is_open):
        self.connect()
        cur = self.db_conn.cursor()
        try:
            sql = "SELECT exchange, cal_date, is_open, pretrade_date FROM trade_cal WHERE cal_date BETWEEN %s AND %s"
            params = [start_date, end_date]
            if is_open is not None:
                sql += " AND is_open=%s"
                params.append(str(is_open))
            cur.execute(sql, params)
            rows = cur.fetchall()
            if not rows:
                return pd.DataFrame()
            df = pd.DataFrame(
                rows, columns=["exchange", "cal_date", "is_open", "pretrade_date"]
            )
            return df
        finally:
            cur.close()

    def _write_trade_cal_to_db(self, df: pd.DataFrame):
        if df.empty:
            return 0
        self.connect()
        cur = self.db_conn.cursor()
        try:
            start = df["cal_date"].min()
            end = df["cal_date"].max()
            cur.execute(
                "DELETE FROM trade_cal WHERE cal_date BETWEEN %s AND %s",
                (start, end),
            )
            insert_sql = "INSERT INTO trade_cal (exchange, cal_date, is_open, pretrade_date) VALUES (%s,%s,%s,%s)"
            data = []
            for _, row in df.iterrows():
                data.append(
                    (
                        row.get("exchange"),
                        row.get("cal_date"),
                        str(row.get("is_open")),
                        row.get("pretrade_date"),
                    )
                )
            cur.executemany(insert_sql, data)
            self.db_conn.commit()
            return cur.rowcount
        except Exception:
            if self.db_conn:
                self.db_conn.rollback()
            raise
        finally:
            cur.close()

    def trade_cal(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        is_open: Optional[int] = None,
    ) -> pd.DataFrame:
        """
        要求必须提供 start_date 和 end_date（格式 YYYYMMDD）
        """
        if not start_date or not end_date:
            raise ValueError(
                "trade_cal: 必须提供 start_date 和 end_date，格式 YYYYMMDD"
            )

        df = self._read_trade_cal_from_db(start_date, end_date, is_open)
        if df.empty:
            raise RuntimeError("trade_cal 本地缓存为空或不包含所需范围，请先运行初始化")
        return df

    def _read_stock_basic_from_db(self):
        self.connect()
        cur = self.db_conn.cursor()
        try:
            cur.execute(
                "SELECT ts_code,symbol,name,area,industry,fullname,enname,cnspell,market,exchange,curr_type,list_status,list_date,delist_date,is_hs,act_name,act_ent_type FROM stock_basic"
            )
            rows = cur.fetchall()
            if not rows:
                return pd.DataFrame()
            cols = [
                "ts_code",
                "symbol",
                "name",
                "area",
                "industry",
                "fullname",
                "enname",
                "cnspell",
                "market",
                "exchange",
                "curr_type",
                "list_status",
                "list_date",
                "delist_date",
                "is_hs",
                "act_name",
                "act_ent_type",
            ]
            return pd.DataFrame(rows, columns=cols)
        finally:
            cur.close()

    def _write_stock_basic_to_db(self, df: pd.DataFrame):
        if df.empty:
            return 0
        self.connect()
        cur = self.db_conn.cursor()
        try:
            cur.execute("DELETE FROM stock_basic")
            insert_sql = (
                "INSERT INTO stock_basic (ts_code,symbol,name,area,industry,fullname,enname,cnspell,market,exchange,curr_type,list_status,list_date,delist_date,is_hs,act_name,act_ent_type) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
            )
            data = []
            for _, r in df.iterrows():
                data.append(
                    (
                        r.get("ts_code"),
                        r.get("symbol"),
                        r.get("name"),
                        r.get("area"),
                        r.get("industry"),
                        r.get("fullname"),
                        r.get("enname"),
                        r.get("cnspell"),
                        r.get("market"),
                        r.get("exchange"),
                        r.get("curr_type"),
                        r.get("list_status"),
                        r.get("list_date"),
                        r.get("delist_date"),
                        r.get("is_hs"),
                        r.get("act_name"),
                        r.get("act_ent_type"),
                    )
                )
            cur.executemany(insert_sql, data)
            self.db_conn.commit()
            return cur.rowcount
        except Exception:
            if self.db_conn:
                self.db_conn.rollback()
            raise
        finally:
            cur.close()

    def stock_basic(self) -> pd.DataFrame:
        """
        仅从本地 stock_basic 表读取并返回（静默）。若本地无数据则抛出异常，提示先运行初始化脚本。
        """
        df = self._read_stock_basic_from_db()
        if df.empty:
            raise RuntimeError(
                "stock_basic 本地缓存为空，请先运行 tushare_cache_client.py 初始化"
            )
        return df

    def _read_trade_dates(self, start_date: str, end_date: str) -> list:
        """获取指定时间范围内所有交易日（仅开市日）"""
        self.connect()
        cur = self.db_conn.cursor()
        try:
            cur.execute(
                "SELECT cal_date FROM trade_cal WHERE is_open='1' AND cal_date BETWEEN %s AND %s ORDER BY cal_date ASC",
                (start_date, end_date),
            )
            rows = cur.fetchall()
            return [r[0] for r in rows]
        finally:
            cur.close()

    def _read_ts_codes(self, ts_codes: list) -> list:
        """校验并返回有效的ts_code列表"""
        if not ts_codes:
            return []
        self.connect()
        cur = self.db_conn.cursor()
        try:
            format_strings = ",".join(["%s"] * len(ts_codes))
            cur.execute(
                f"SELECT ts_code FROM stock_basic WHERE ts_code IN ({format_strings})",
                tuple(ts_codes),
            )
            rows = cur.fetchall()
            return [r[0] for r in rows]
        finally:
            cur.close()

    def _read_daily_count(self, ts_codes: list, trade_dates: list, table: str) -> int:
        """查询数据库中指定股票和日期范围的总数据行数"""
        if not ts_codes or not trade_dates:
            return 0
        self.connect()
        cur = self.db_conn.cursor()
        try:
            format_codes = ",".join(["%s"] * len(ts_codes))
            format_dates = ",".join(["%s"] * len(trade_dates))
            sql = f"SELECT COUNT(*) FROM {table} WHERE ts_code IN ({format_codes}) AND trade_date IN ({format_dates})"
            cur.execute(sql, tuple(ts_codes) + tuple(trade_dates))
            return cur.fetchone()[0]
        finally:
            cur.close()

    def _delete_daily(self, ts_codes: list, trade_dates: list, table: str):
        """删除数据库中指定股票和日期范围的数据"""
        if not ts_codes or not trade_dates:
            return
        self.connect()
        cur = self.db_conn.cursor()
        try:
            format_codes = ",".join(["%s"] * len(ts_codes))
            format_dates = ",".join(["%s"] * len(trade_dates))
            sql = f"DELETE FROM {table} WHERE ts_code IN ({format_codes}) AND trade_date IN ({format_dates})"
            cur.execute(sql, tuple(ts_codes) + tuple(trade_dates))
            self.db_conn.commit()
        except Exception:
            if self.db_conn:
                self.db_conn.rollback()
            raise
        finally:
            cur.close()

    def _insert_daily(self, df: pd.DataFrame, table: str):
        """插入日线或每日指标数据"""
        if df.empty:
            return 0
        self.connect()
        cur = self.db_conn.cursor()
        try:
            if table == "daily":
                insert_sql = (
                    "INSERT INTO daily (ts_code, trade_date, `open`, high, low, `close`, pre_close, `change`, pct_chg, vol, amount) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
                )
                data = [
                    (
                        r.ts_code,
                        r.trade_date,
                        r.open,
                        r.high,
                        r.low,
                        r.close,
                        r.pre_close,
                        r.change,
                        r.pct_chg,
                        r.vol,
                        r.amount,
                    )
                    for _, r in df.iterrows()
                ]
            elif table == "daily_basic":
                insert_sql = (
                    "INSERT INTO daily_basic (ts_code, trade_date, `close`, turnover_rate, turnover_rate_f, volume_ratio, pe, pe_ttm, pb, ps, ps_ttm, dv_ratio, dv_ttm, total_share, float_share, free_share, total_mv, circ_mv) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
                )
                data = [
                    (
                        r.ts_code,
                        r.trade_date,
                        r.close,
                        r.turnover_rate,
                        r.turnover_rate_f,
                        r.volume_ratio,
                        r.pe,
                        r.pe_ttm,
                        r.pb,
                        r.ps,
                        r.ps_ttm,
                        r.dv_ratio,
                        r.dv_ttm,
                        r.total_share,
                        r.float_share,
                        r.free_share,
                        r.total_mv,
                        r.circ_mv,
                    )
                    for _, r in df.iterrows()
                ]
            else:
                raise ValueError("table must be 'daily' or 'daily_basic'")
            cur.executemany(insert_sql, data)
            self.db_conn.commit()
            return cur.rowcount
        except Exception:
            if self.db_conn:
                self.db_conn.rollback()
            raise
        finally:
            cur.close()

    def daily(
        self,
        ts_code: str = "",
        start_date: str = None,
        end_date: str = None,
    ) -> pd.DataFrame:
        """
        获取日线行情数据，自动分批补全本地缓存，API与Tushare一致。

        返回DataFrame字段说明：
            ts_code      : 股票代码
            trade_date   : 交易日期
            open         : 开盘价
            high         : 最高价
            low          : 最低价
            close        : 收盘价
            pre_close    : 昨收价（除权价，前复权）
            change       : 涨跌额
            pct_chg      : 涨跌幅（基于除权后的昨收计算的涨跌幅：（今收-除权昨收）/除权昨收）
            vol          : 成交量（手）
            amount       : 成交额（千元）
        """
        if not start_date or not end_date:
            raise ValueError("daily: 必须提供 start_date 和 end_date")
        # 股票代码列表
        ts_codes = (
            [c.strip() for c in ts_code.split(",") if c.strip()]
            if ts_code
            else self.stock_basic()["ts_code"].tolist()
        )
        ts_codes = self._read_ts_codes(ts_codes)
        if not ts_codes:
            raise ValueError("未找到有效的 ts_code")
        # 交易日列表
        trade_dates = self._read_trade_dates(start_date, end_date)
        if not trade_dates:
            raise ValueError("指定区间无交易日")
        n_dates = len(trade_dates)
        batch_size = max(1, 6000 // n_dates)
        for i in range(0, len(ts_codes), batch_size):
            batch_codes = ts_codes[i : i + batch_size]
            expected = len(batch_codes) * n_dates
            actual = self._read_daily_count(batch_codes, trade_dates, "daily")
            if actual == expected:
                continue
            # 拉取数据
            code_str = ",".join(batch_codes)
            df = self.pro.daily(
                ts_code=code_str, start_date=start_date, end_date=end_date
            )
            if df is None or len(df) != expected:
                raise RuntimeError(
                    f"Tushare daily 拉取数据不完整: 期望{expected}条，实际{len(df) if df is not None else 0}条"
                )
            self._delete_daily(batch_codes, trade_dates, "daily")
            self._insert_daily(df, "daily")
        # 最终返回本地数据
        self.connect()
        cur = self.db_conn.cursor()
        try:
            format_codes = ",".join(["%s"] * len(ts_codes))
            format_dates = ",".join(["%s"] * len(trade_dates))
            sql = f"SELECT ts_code, trade_date, `open`, high, low, `close`, pre_close, `change`, pct_chg, vol, amount FROM daily WHERE ts_code IN ({format_codes}) AND trade_date IN ({format_dates})"
            cur.execute(sql, tuple(ts_codes) + tuple(trade_dates))
            rows = cur.fetchall()
            cols = [
                "ts_code",
                "trade_date",
                "open",
                "high",
                "low",
                "close",
                "pre_close",
                "change",
                "pct_chg",
                "vol",
                "amount",
            ]
            return pd.DataFrame(rows, columns=cols)
        finally:
            cur.close()

    def daily_basic(
        self,
        ts_code: str = "",
        start_date: str = None,
        end_date: str = None,
    ) -> pd.DataFrame:
        """
        获取每日指标数据，自动分批补全本地缓存，API与Tushare一致。

        返回DataFrame字段说明：
            ts_code          : TS股票代码
            trade_date       : 交易日期
            close            : 当日收盘价
            turnover_rate    : 换手率（%）
            turnover_rate_f  : 换手率（自由流通股）
            volume_ratio     : 量比
            pe               : 市盈率（总市值/净利润，亏损的PE为空）
            pe_ttm           : 市盈率（TTM，亏损的PE为空）
            pb               : 市净率（总市值/净资产）
            ps               : 市销率
            ps_ttm           : 市销率（TTM）
            dv_ratio         : 股息率（%）
            dv_ttm           : 股息率（TTM）（%）
            total_share      : 总股本（万股）
            float_share      : 流通股本（万股）
            free_share       : 自由流通股本（万）
            total_mv         : 总市值（万元）
            circ_mv          : 流通市值（万元）
        """
        if not start_date or not end_date:
            raise ValueError("daily_basic: 必须提供 start_date 和 end_date")
        ts_codes = (
            [c.strip() for c in ts_code.split(",") if c.strip()]
            if ts_code
            else self.stock_basic()["ts_code"].tolist()
        )
        ts_codes = self._read_ts_codes(ts_codes)
        if not ts_codes:
            raise ValueError("未找到有效的 ts_code")
        trade_dates = self._read_trade_dates(start_date, end_date)
        if not trade_dates:
            raise ValueError("指定区间无交易日")
        n_dates = len(trade_dates)
        batch_size = max(1, 6000 // n_dates)
        for i in range(0, len(ts_codes), batch_size):
            batch_codes = ts_codes[i : i + batch_size]
            expected = len(batch_codes) * n_dates
            actual = self._read_daily_count(batch_codes, trade_dates, "daily_basic")
            if actual == expected:
                continue
            code_str = ",".join(batch_codes)
            df = self.pro.daily_basic(
                ts_code=code_str, start_date=start_date, end_date=end_date
            )
            if df is None or len(df) != expected:
                raise RuntimeError(
                    f"Tushare daily_basic 拉取数据不完整: 期望{expected}条，实际{len(df) if df is not None else 0}条"
                )
            self._delete_daily(batch_codes, trade_dates, "daily_basic")
            self._insert_daily(df, "daily_basic")
        # 最终返回本地数据
        self.connect()
        cur = self.db_conn.cursor()
        try:
            format_codes = ",".join(["%s"] * len(ts_codes))
            format_dates = ",".join(["%s"] * len(trade_dates))
            sql = f"SELECT ts_code, trade_date, close, turnover_rate, turnover_rate_f, volume_ratio, pe, pe_ttm, pb, ps, ps_ttm, dv_ratio, dv_ttm, total_share, float_share, free_share, total_mv, circ_mv FROM daily_basic WHERE ts_code IN ({format_codes}) AND trade_date IN ({format_dates})"
            cur.execute(sql, tuple(ts_codes) + tuple(trade_dates))
            rows = cur.fetchall()
            cols = [
                "ts_code",
                "trade_date",
                "close",
                "turnover_rate",
                "turnover_rate_f",
                "volume_ratio",
                "pe",
                "pe_ttm",
                "pb",
                "ps",
                "ps_ttm",
                "dv_ratio",
                "dv_ttm",
                "total_share",
                "float_share",
                "free_share",
                "total_mv",
                "circ_mv",
            ]
            return pd.DataFrame(rows, columns=cols)
        finally:
            cur.close()

    # ========== 指数基本信息 ==========
    def _read_index_basic_from_db(self):
        self.connect()
        cur = self.db_conn.cursor()
        try:
            cur.execute(
                "SELECT ts_code, name, fullname, market, publisher, index_type, category, base_date, base_point, list_date, weight_rule, `desc`, exp_date FROM index_basic",
            )
            rows = cur.fetchall()
            if not rows:
                return pd.DataFrame()
            cols = [
                "ts_code",
                "name",
                "fullname",
                "market",
                "publisher",
                "index_type",
                "category",
                "base_date",
                "base_point",
                "list_date",
                "weight_rule",
                "desc",
                "exp_date",
            ]
            return pd.DataFrame(rows, columns=cols)
        finally:
            cur.close()

    def _write_index_basic_to_db(self, df: pd.DataFrame):
        if df.empty:
            return 0
        # 替换所有 NaN 为 None
        df = df.astype(object).where(pd.notnull(df), None)
        self.connect()
        cur = self.db_conn.cursor()
        try:
            cur.execute("DELETE FROM index_basic")
            insert_sql = (
                "INSERT INTO index_basic (ts_code, name, fullname, market, publisher, index_type, category, base_date, base_point, list_date, weight_rule, `desc`, exp_date) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
            )
            data = [
                (
                    r.get("ts_code"),
                    r.get("name"),
                    r.get("fullname"),
                    r.get("market"),
                    r.get("publisher"),
                    r.get("index_type"),
                    r.get("category"),
                    r.get("base_date"),
                    r.get("base_point"),
                    r.get("list_date"),
                    r.get("weight_rule"),
                    r.get("desc"),
                    r.get("exp_date"),
                )
                for _, r in df.iterrows()
            ]
            cur.executemany(insert_sql, data)
            self.db_conn.commit()
            return cur.rowcount
        except Exception:
            if self.db_conn:
                self.db_conn.rollback()
            raise
        finally:
            cur.close()

    def index_basic(self) -> pd.DataFrame:
        """
        仅从本地 index_basic 表读取并返回（静默）。若本地无数据则抛出异常，提示先运行初始化脚本。
        """
        df = self._read_index_basic_from_db()
        if df.empty:
            raise RuntimeError(
                "index_basic 本地缓存为空，请先运行 tushare_cache_client.py 初始化"
            )
        return df

    # ========== 指数日线行情 ==========
    def _read_index_daily_count(self, ts_codes: list, trade_dates: list) -> int:
        if not ts_codes or not trade_dates:
            return 0
        self.connect()
        cur = self.db_conn.cursor()
        try:
            format_codes = ",".join(["%s"] * len(ts_codes))
            format_dates = ",".join(["%s"] * len(trade_dates))
            sql = f"SELECT COUNT(*) FROM index_daily WHERE ts_code IN ({format_codes}) AND trade_date IN ({format_dates})"
            cur.execute(sql, tuple(ts_codes) + tuple(trade_dates))
            return cur.fetchone()[0]
        finally:
            cur.close()

    def _delete_index_daily(self, ts_codes: list, trade_dates: list):
        if not ts_codes or not trade_dates:
            return
        self.connect()
        cur = self.db_conn.cursor()
        try:
            format_codes = ",".join(["%s"] * len(ts_codes))
            format_dates = ",".join(["%s"] * len(trade_dates))
            sql = f"DELETE FROM index_daily WHERE ts_code IN ({format_codes}) AND trade_date IN ({format_dates})"
            cur.execute(sql, tuple(ts_codes) + tuple(trade_dates))
            self.db_conn.commit()
        except Exception:
            if self.db_conn:
                self.db_conn.rollback()
            raise
        finally:
            cur.close()

    def _insert_index_daily(self, df: pd.DataFrame):
        if df.empty:
            return 0
        self.connect()
        cur = self.db_conn.cursor()
        try:
            insert_sql = (
                "INSERT INTO index_daily (ts_code, trade_date, `close`, `open`, high, low, pre_close, `change`, pct_chg, vol, amount) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
            )
            data = [
                (
                    r.ts_code,
                    r.trade_date,
                    r.close,
                    r.open,
                    r.high,
                    r.low,
                    r.pre_close,
                    r.change,
                    r.pct_chg,
                    r.vol,
                    r.amount,
                )
                for _, r in df.iterrows()
            ]
            cur.executemany(insert_sql, data)
            self.db_conn.commit()
            return cur.rowcount
        except Exception:
            if self.db_conn:
                self.db_conn.rollback()
            raise
        finally:
            cur.close()

    def index_daily(
        self,
        ts_code: str = "",
        start_date: str = None,
        end_date: str = None,
    ) -> pd.DataFrame:
        """
        获取指数日线行情数据，自动分批补全本地缓存，API与Tushare一致。
        """
        if not ts_code or not start_date or not end_date:
            raise ValueError("index_daily: 必须提供 ts_code, start_date 和 end_date")
        ts_codes = [c.strip() for c in ts_code.split(",") if c.strip()]
        trade_dates = self._read_trade_dates(start_date, end_date)
        if not ts_codes or not trade_dates:
            raise ValueError("指数代码或交易日为空")
        n_dates = len(trade_dates)
        batch_size = max(1, 8000 // n_dates)
        for i in range(0, len(ts_codes), batch_size):
            batch_codes = ts_codes[i : i + batch_size]
            expected = len(batch_codes) * n_dates
            actual = self._read_index_daily_count(batch_codes, trade_dates)
            if actual == expected:
                continue
            code_str = ",".join(batch_codes)
            df = self.pro.index_daily(
                ts_code=code_str, start_date=start_date, end_date=end_date
            )
            if df is None or len(df) != expected:
                raise RuntimeError(
                    f"Tushare index_daily 拉取数据不完整: 期望{expected}条，实际{len(df) if df is not None else 0}条"
                )
            self._delete_index_daily(batch_codes, trade_dates)
            self._insert_index_daily(df)
        # 最终返回本地数据
        self.connect()
        cur = self.db_conn.cursor()
        try:
            format_codes = ",".join(["%s"] * len(ts_codes))
            format_dates = ",".join(["%s"] * len(trade_dates))
            sql = f"SELECT ts_code, trade_date, `close`, `open`, high, low, pre_close, `change`, pct_chg, vol, amount FROM index_daily WHERE ts_code IN ({format_codes}) AND trade_date IN ({format_dates})"
            cur.execute(sql, tuple(ts_codes) + tuple(trade_dates))
            rows = cur.fetchall()
            cols = [
                "ts_code",
                "trade_date",
                "close",
                "open",
                "high",
                "low",
                "pre_close",
                "change",
                "pct_chg",
                "vol",
                "amount",
            ]
            return pd.DataFrame(rows, columns=cols)
        finally:
            cur.close()

    # 一次性全量初始化（会产生日志并与 Tushare 交互），仅在需要时调用或由 __main__ 使用
    def init_all_from_tushare(self):
        logger.info("开始从 Tushare 全量初始化 trade_cal 与 stock_basic")

        # 1) trade_cal
        try:
            logger.info("从 Tushare 拉取 trade_cal（全量）...")
            df_cal = self.pro.trade_cal()
            if df_cal is None or df_cal.empty:
                logger.error("Tushare 返回的 trade_cal 为空")
                raise RuntimeError("Tushare trade_cal 返回空")
            written = self._write_trade_cal_to_db(df_cal)
            logger.info(f"trade_cal 写入完成，写入 {written} 条记录")
        except Exception as ex:
            logger.error(f"初始化 trade_cal 失败: {ex}")
            raise

        # 2) stock_basic
        try:
            logger.info("从 Tushare 拉取 stock_basic（全量）...")
            df_basic = self.pro.stock_basic(
                exchange="",
                list_status="L",
                fields="ts_code,symbol,name,area,industry,fullname,enname,cnspell,market,exchange,curr_type,list_status,list_date,delist_date,is_hs,act_name,act_ent_type",
            )
            if df_basic is None or df_basic.empty:
                logger.error("Tushare 返回的 stock_basic 为空")
                raise RuntimeError("Tushare stock_basic 返回空")
            written = self._write_stock_basic_to_db(df_basic)
            logger.info(f"stock_basic 写入完成，写入 {written} 条记录")
        except Exception as ex:
            logger.error(f"初始化 stock_basic 失败: {ex}")
            raise

        # 3) index_basic
        try:
            logger.info("从 Tushare 拉取 index_basic（全量）...")
            fields = "ts_code,name,fullname,market,publisher,index_type,category,base_date,base_point,list_date,weight_rule,desc,exp_date"
            df_index = self.pro.index_basic(market="SSE", fields=fields)
            if df_index is None or df_index.empty:
                logger.error("Tushare 返回的 index_basic 为空")
                raise RuntimeError("Tushare index_basic 返回空")
            written = self._write_index_basic_to_db(df_index)
            logger.info(f"index_basic 写入完成，写入 {written} 条记录")
        except Exception as ex:
            logger.error(f"初始化 index_basic 失败: {ex}")
            raise


if __name__ == "__main__":
    # 只在直接运行时全量初始化两张表
    try:
        client = TushareCacheClient()
        client.init_all_from_tushare()
        logger.info("Tushare 本地缓存初始化完成")
    except Exception as e:
        logger.error(f"初始化失败: {e}")
    finally:
        try:
            client.close()
        except Exception:
            pass
