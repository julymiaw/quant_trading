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
from datetime import datetime
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

    # 静默的 DB 读写（不做任何 logger 输出）
    def _read_trade_cal_from_db(self, exchange, start_date, end_date, is_open):
        self.connect()
        cur = self.db_conn.cursor()
        try:
            sql = "SELECT exchange, cal_date, is_open, pretrade_date FROM trade_cal WHERE exchange=%s AND cal_date BETWEEN %s AND %s"
            params = [exchange, start_date, end_date]
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
            exchange = df.iloc[0].get("exchange", "SSE")
            start = df["cal_date"].min()
            end = df["cal_date"].max()
            cur.execute(
                "DELETE FROM trade_cal WHERE exchange=%s AND cal_date BETWEEN %s AND %s",
                (exchange, start, end),
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

    # 对外静默查询接口（不进行任何输出或远程调用）
    def trade_cal(
        self,
        exchange: str = "SSE",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        is_open: Optional[int] = None,
    ) -> pd.DataFrame:
        """
        要求必须提供 start_date 和 end_date（格式 YYYYMMDD）
        """
        # 强制要求传入 start_date / end_date
        if not start_date or not end_date:
            raise ValueError(
                "trade_cal: 必须提供 start_date 和 end_date，格式 YYYYMMDD"
            )

        df = self._read_trade_cal_from_db(exchange, start_date, end_date, is_open)
        if df.empty:
            raise RuntimeError("trade_cal 本地缓存为空或不包含所需范围，请先运行初始化")
        return df

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

    # 一次性全量初始化（会产生日志并与 Tushare 交互），仅在需要时调用或由 __main__ 使用
    def init_all_from_tushare(self):
        logger.info("开始从 Tushare 全量初始化 trade_cal 与 stock_basic")

        # 1) trade_cal - 不传参数可获取 SSE 从 1990 到现在的完整日历
        try:
            logger.info("从 Tushare 拉取 trade_cal（全量）...")
            df_cal = self.pro.trade_cal()  # 默认 SSE 全量
            if df_cal is None or df_cal.empty:
                logger.error("Tushare 返回的 trade_cal 为空")
                raise RuntimeError("Tushare trade_cal 返回空")
            written = self._write_trade_cal_to_db(df_cal)
            logger.info(f"trade_cal 写入完成，写入 {written} 条记录")
        except Exception as ex:
            logger.error(f"初始化 trade_cal 失败: {ex}")
            raise

        # 2) stock_basic - 全量一次性拉取并写入
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
