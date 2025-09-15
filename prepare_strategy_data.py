#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
量化交易系统 - 数据准备模块
功能：为指定策略准备回测所需的全部数据（股票列表、参数、指标、原始行情等）
"""

import argparse
import bisect
import json
import os
import pandas as pd
from collections import defaultdict
from typing import Dict, Set, Tuple, List

import pymysql
import numpy as np

# 假设有如下数据库/缓存/接口工具
from tushare_cache_client import TushareCacheClient

# 回测模块必需的参数列表（由回测模块同学要求）
# 这些参数必须出现在所有策略的准备数据中，以确保回测功能正常运行
REQUIRED_PARAMS = [
    ("system", "close"),  # 收盘价 - 基础价格数据
    ("system", "high"),  # 最高价 - 日内高点数据
    ("system", "low"),  # 最低价 - 日内低点数据
    ("system", "open"),  # 开盘价 - 日内开盘数据
]


# ========== 1. 解析命令行参数 ==========
def parse_args():
    parser = argparse.ArgumentParser(description="为策略准备回测数据")
    parser.add_argument(
        "--strategy", required=True, help="策略名，格式 creator_name.strategy_name"
    )
    parser.add_argument("--start", required=True, help="回测开始日期 YYYY-MM-DD")
    parser.add_argument("--end", required=True, help="回测结束日期 YYYY-MM-DD")
    parser.add_argument("--config", default="config.json", help="配置文件路径")
    parser.add_argument("--output", default=None, help="输出目录（默认自动生成）")
    return parser.parse_args()


# ========== 2. 数据准备主流程 ==========
class DataPreparer:
    def __init__(self, config_path: str):
        self.client = TushareCacheClient(config_path)
        # 读取数据库配置
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        self.conn = pymysql.connect(
            host="localhost",
            user="root",
            password=config["db_password"],
            database="quantitative_trading",
            charset="utf8mb4",
        )
        # 缓存，避免重复查表
        self.param_cache = {}
        self.indicator_cache = {}
        self.indicator_param_cache = {}
        # 初始化交易日历缓存
        self.trade_dates = self._get_all_trade_dates()

    def _get_all_trade_dates(self) -> list:
        # 获取所有交易日（升序）
        df = self.client.trade_cal(
            start_date="19900101", end_date="21000101", is_open=1
        )
        return sorted(df["cal_date"].tolist())

    def correct_to_trade_date(self, date: str, direction: str = "forward") -> str:
        """
        将date纠正为最近的交易日。
        direction: "forward"（向后/更大）或 "backward"（向前/更小）
        """
        date_str = date.replace("-", "")
        trade_dates = self.trade_dates
        if date_str in trade_dates:
            return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
        if direction == "forward":
            # 找到第一个大于等于date的交易日
            idx = bisect.bisect_left(trade_dates, date_str)
            if idx < len(trade_dates):
                d = trade_dates[idx]
                return f"{d[:4]}-{d[4:6]}-{d[6:]}"
        else:
            # 找到最后一个小于等于date的交易日
            idx = bisect.bisect_right(trade_dates, date_str) - 1
            if idx >= 0:
                d = trade_dates[idx]
                return f"{d[:4]}-{d[4:6]}-{d[6:]}"
        raise ValueError(f"无法纠正为交易日: {date}")

    def get_strategy_info(self, creator_name: str, strategy_name: str) -> Dict:
        # 查询Strategy表，获取scope_type、scope_id等
        sql = """
            SELECT scope_type, scope_id, benchmark_index
            FROM Strategy
            WHERE creator_name=%s AND strategy_name=%s
        """
        with self.conn.cursor() as cur:
            cur.execute(sql, (creator_name, strategy_name))
            row = cur.fetchone()
            if not row:
                raise ValueError(f"未找到策略 {creator_name}.{strategy_name}")
            return {"scope_type": row[0], "scope_id": row[1], "benchmark_index": row[2]}

    def get_strategy_params(
        self, creator_name: str, strategy_name: str
    ) -> List[Tuple[str, str]]:
        # 查询StrategyParamRel，返回所有参数 (param_creator_name, param_name)
        sql = """
            SELECT param_creator_name, param_name
            FROM StrategyParamRel
            WHERE strategy_creator_name=%s AND strategy_name=%s
        """
        with self.conn.cursor() as cur:
            cur.execute(sql, (creator_name, strategy_name))
            return list(cur.fetchall())

    def get_param_info(self, creator_name: str, param_name: str) -> Dict:
        # 查询Param表，返回参数详情
        sql = """
            SELECT data_id, param_type, pre_period, post_period, agg_func
            FROM Param
            WHERE creator_name=%s AND param_name=%s
        """
        with self.conn.cursor() as cur:
            cur.execute(sql, (creator_name, param_name))
            row = cur.fetchone()
            if not row:
                raise ValueError(f"未找到参数 {creator_name}.{param_name}")
            return {
                "data_id": row[0],
                "param_type": row[1],
                "pre_period": row[2],
                "post_period": row[3],
                "agg_func": row[4],
            }

    def get_indicator_params(
        self, creator_name: str, indicator_name: str
    ) -> List[Tuple[str, str]]:
        # 查询IndicatorParamRel，返回所有参数 (param_creator_name, param_name)
        sql = """
            SELECT param_creator_name, param_name
            FROM IndicatorParamRel
            WHERE indicator_creator_name=%s AND indicator_name=%s
        """
        with self.conn.cursor() as cur:
            cur.execute(sql, (creator_name, indicator_name))
            return list(cur.fetchall())

    def get_indicator_info(self, creator_name: str, indicator_name: str) -> Dict:
        # 查询Indicator表，返回指标详情
        sql = """
            SELECT calculation_method, description, is_active
            FROM Indicator
            WHERE creator_name=%s AND indicator_name=%s
        """
        with self.conn.cursor() as cur:
            cur.execute(sql, (creator_name, indicator_name))
            row = cur.fetchone()
            if not row:
                raise ValueError(f"未找到指标 {creator_name}.{indicator_name}")
            return {
                "calculation_method": row[0],
                "description": row[1],
                "is_active": row[2],
            }

    def get_stock_list(self, scope_type: str, scope_id: str) -> List[str]:
        # 根据scope_type和scope_id，返回股票代码列表
        if scope_type == "all":
            df = self.client.stock_basic()
            return df["ts_code"].tolist()
        elif scope_type == "index":
            return self.client.get_latest_index_members(scope_id)
        elif scope_type == "single_stock":
            return [scope_id]
        else:
            raise ValueError(f"未知scope_type: {scope_type}")

    def get_trade_date_shift(self, date: str, shift: int) -> str:
        """
        根据交易日历，将date向前(负)或向后(正)移动shift个交易日，返回新的日期（YYYY-MM-DD）。
        假设date一定是交易日。
        """
        date_str = date.replace("-", "")
        trade_dates = self.trade_dates
        idx = trade_dates.index(date_str)
        new_idx = idx + shift
        if new_idx < 0 or new_idx >= len(trade_dates):
            raise ValueError(f"交易日偏移超出范围: {date} shift={shift}")
        return pd.to_datetime(trade_dates[new_idx]).strftime("%Y-%m-%d")

    def build_dependency_dag(
        self, params: List[Tuple[str, str]], start_date=None, end_date=None
    ) -> Dict:
        """
        递归构建依赖DAG，返回每个节点的最大访问范围
        节点格式：("param", creator_name, param_name) 或 ("indicator", creator_name, indicator_name) 或 ("table", data_id)
        返回：
            {
                "order": [节点, ...],  # 后序遍历去重后的计算顺序
                "ranges": {节点: (min_date, max_date), ...},  # 每节点最大访问范围
            }
        """
        order = []
        ranges = dict()

        def update_range(node, cur_start, cur_end):
            # 更新节点的最大访问范围
            if node in ranges:
                prev_start, prev_end = ranges[node]
                new_start = min(prev_start, cur_start)
                new_end = max(prev_end, cur_end)
                ranges[node] = (new_start, new_end)
            else:
                ranges[node] = (cur_start, cur_end)

        def dfs_param(creator_name, param_name, cur_start, cur_end):
            node = ("param", creator_name, param_name)
            # 查询参数信息（带缓存）
            if (creator_name, param_name) not in self.param_cache:
                param_info = self.get_param_info(creator_name, param_name)
                self.param_cache[(creator_name, param_name)] = param_info
            else:
                param_info = self.param_cache[(creator_name, param_name)]
            # 先更新range（用当前访问范围）
            update_range(node, cur_start, cur_end)
            pre_period = param_info["pre_period"] or 0
            post_period = param_info["post_period"] or 0
            # 用交易日历扩展
            min_date = self.get_trade_date_shift(cur_start, -pre_period)
            max_date = self.get_trade_date_shift(cur_end, post_period)
            # 递归处理子节点
            if param_info["param_type"] == "indicator":
                indicator_creator, indicator_name = param_info["data_id"].split(".", 1)
                dfs_indicator(
                    indicator_creator,
                    indicator_name,
                    min_date,
                    max_date,
                )
            elif param_info["param_type"] == "table":
                dfs_table(
                    param_info["data_id"],
                    min_date,
                    max_date,
                )
            order.append(node)

        def dfs_indicator(creator_name, indicator_name, cur_start, cur_end):
            node = ("indicator", creator_name, indicator_name)
            update_range(node, cur_start, cur_end)
            # 查询指标信息（带缓存）
            if (creator_name, indicator_name) not in self.indicator_cache:
                indicator_info = self.get_indicator_info(creator_name, indicator_name)
                self.indicator_cache[(creator_name, indicator_name)] = indicator_info
            else:
                indicator_info = self.indicator_cache[(creator_name, indicator_name)]
            # 查询指标所需参数（带缓存）
            if (creator_name, indicator_name) not in self.indicator_param_cache:
                indicator_params = self.get_indicator_params(
                    creator_name, indicator_name
                )
                self.indicator_param_cache[(creator_name, indicator_name)] = (
                    indicator_params
                )
            else:
                indicator_params = self.indicator_param_cache[
                    (creator_name, indicator_name)
                ]
            # 递归处理所有参数
            for p_creator, p_id in indicator_params:
                dfs_param(p_creator, p_id, cur_start, cur_end)
            order.append(node)

        def dfs_table(data_id, cur_start, cur_end):
            node = ("table", data_id)
            update_range(node, cur_start, cur_end)
            order.append(node)

        # 入口：所有策略参数
        for p_creator, p_id in params:
            dfs_param(p_creator, p_id, start_date, end_date)

        # 去重，保留首次出现顺序
        seen = set()
        order_unique = []
        for node in order:
            if node not in seen:
                order_unique.append(node)
                seen.add(node)

        return {"order": order_unique, "ranges": ranges}

    def get_table_data(
        self, table_field: str, stock_list: list, start_date: str, end_date: str
    ) -> pd.DataFrame:
        """
        按表名.字段名、股票列表、日期范围获取原始数据。
        返回DataFrame: index=[ts_code, trade_date]，columns=[value]
        """
        table, field = table_field.split(".", 1)
        if table == "daily":
            df = self.client.daily(
                ts_code=",".join(stock_list),
                start_date=start_date.replace("-", ""),
                end_date=end_date.replace("-", ""),
            )
        elif table == "daily_basic":
            df = self.client.daily_basic(
                ts_code=",".join(stock_list),
                start_date=start_date.replace("-", ""),
                end_date=end_date.replace("-", ""),
            )
        else:
            raise ValueError(f"暂不支持的表: {table}")
        # 只保留需要的字段
        df = df[["ts_code", "trade_date", field]].copy()
        df.rename(columns={field: "value"}, inplace=True)
        df["trade_date"] = pd.to_datetime(df["trade_date"])
        # 补全所有股票和所有目标交易日
        trade_dates = self.trade_dates
        start_idx = trade_dates.index(start_date.replace("-", ""))
        end_idx = trade_dates.index(end_date.replace("-", ""))
        target_dates = [pd.to_datetime(d) for d in trade_dates[start_idx : end_idx + 1]]
        full_index = pd.MultiIndex.from_product(
            [stock_list, target_dates], names=["ts_code", "trade_date"]
        )
        df = df.set_index(["ts_code", "trade_date"]).reindex(full_index)
        return df

    def calc_param(
        self, param_info: dict, data_df: pd.DataFrame, param_range: tuple
    ) -> pd.DataFrame:
        """
        对原始data_df（index=[ts_code, trade_date], value列）按聚合函数聚合，得到参数在param_range内的值。
        param_info: 包含agg_func, pre_period, post_period等
        param_range: (start_date, end_date)，均为YYYY-MM-DD
        返回DataFrame: index=[ts_code, trade_date]，columns=[value]
        """
        agg_func = param_info["agg_func"]
        pre_period = param_info["pre_period"] or 0
        post_period = param_info["post_period"] or 0

        # 如果没有聚合，直接裁剪到param_range并返回
        if not agg_func or (pre_period == 0 and post_period == 0):
            mask = (data_df["trade_date"] >= param_range[0]) & (
                data_df["trade_date"] <= param_range[1]
            )
            return data_df[mask].set_index(["ts_code", "trade_date"])

        # 需要聚合时，先保证输入数据范围覆盖param_range向前/向后
        # 计算聚合所需的完整输入范围
        start_full = self.get_trade_date_shift(param_range[0], -pre_period)
        end_full = self.get_trade_date_shift(param_range[1], post_period)
        mask_full = (data_df["trade_date"] >= start_full) & (
            data_df["trade_date"] <= end_full
        )
        df = data_df[mask_full].copy()

        result = []
        for ts_code, group in df.groupby("ts_code"):
            group = group.sort_values("trade_date")
            values = group["value"].values
            if agg_func.upper() == "EMA":
                ema = pd.Series(values).ewm(span=pre_period, adjust=False).mean().values
                group["value"] = ema
            elif agg_func.upper() in ("SMA", "MA"):
                window = pre_period + post_period + 1
                group["value"] = (
                    pd.Series(values)
                    .rolling(window=window, min_periods=window)
                    .mean()
                    .shift(-post_period)
                    .values
                )
            else:
                raise ValueError(f"暂不支持的聚合函数: {agg_func}")
            result.append(group)
        df_out = pd.concat(result)

        # 最后只保留param_range内的结果
        mask2 = (df_out["trade_date"] >= param_range[0]) & (
            df_out["trade_date"] <= param_range[1]
        )
        return df_out[mask2].set_index(["ts_code", "trade_date"])

    def calc_indicator(
        self, indicator_info: dict, param_dict: dict, stock_list: list, date_list: list
    ) -> pd.DataFrame:
        """
        计算指标节点。indicator_info包含calculation_method（字符串），param_dict为所有依赖参数的DataFrame。
        stock_list: 股票代码列表
        date_list: 日期列表（已是交易日）
        返回DataFrame: index=[ts_code, trade_date]，columns=[value]
        """
        # 动态执行指标函数
        local_env = {}
        exec(indicator_info["calculation_method"], {}, local_env)
        calc_func = local_env.get("calculation_method")
        # 构造params字典，key为"creator.param_name"，value为DataFrame（index=[ts_code, trade_date]）
        # param_dict: {("param", creator, param_name): DataFrame}
        # 先合并所有参数为一个大表
        param_keys = [k for k in param_dict if k[0] == "param"]
        # 以股票和日期为索引，构造params["creator.param_name"][ts_code, trade_date]
        params = {}
        for k in param_keys:
            creator, param_name = k[1], k[2]
            df = param_dict[k]
            params[f"{creator}.{param_name}"] = df["value"]
        # 结果DataFrame
        index = pd.MultiIndex.from_product(
            [stock_list, date_list], names=["ts_code", "trade_date"]
        )
        result = pd.DataFrame(index=index)
        # 对每个股票、每个日期，按位计算
        for ts_code in stock_list:
            for trade_date in date_list:
                key = (ts_code, trade_date)
                # 构造params子字典
                params_slice = {k: v.get(key, np.nan) for k, v in params.items()}
                try:
                    val = calc_func(params_slice)
                except Exception:
                    val = np.nan
                result.loc[key, "value"] = val
        return result

    def compute_all(self, order: list, ranges: dict, stock_list: list):
        """
        按照order顺序，依次计算所有节点的值，结果存储到self.node_values
        """
        self.node_values = {}
        for node in order:
            if node[0] == "table":
                table_field = node[1]
                start, end = ranges[node]
                # 用真实交易日
                trade_dates = self.trade_dates
                start_idx = trade_dates.index(start.replace("-", ""))
                end_idx = trade_dates.index(end.replace("-", ""))
                date_list = [
                    pd.to_datetime(d).strftime("%Y-%m-%d")
                    for d in trade_dates[start_idx : end_idx + 1]
                ]
                df = self.get_table_data(table_field, stock_list, start, end)
                self.node_values[node] = df
            elif node[0] == "param":
                param_info = self.param_cache[(node[1], node[2])]
                data_node = None
                if param_info["param_type"] == "indicator":
                    indicator_creator, indicator_name = param_info["data_id"].split(
                        ".", 1
                    )
                    data_node = ("indicator", indicator_creator, indicator_name)
                elif param_info["param_type"] == "table":
                    data_node = ("table", param_info["data_id"])
                data_df = self.node_values[data_node]
                param_range = ranges[node]
                df = self.calc_param(param_info, data_df.reset_index(), param_range)
                self.node_values[node] = df
            elif node[0] == "indicator":
                indicator_info = self.indicator_cache[(node[1], node[2])]
                indicator_params = self.indicator_param_cache[(node[1], node[2])]
                param_dict = {
                    ("param", p_creator, p_id): self.node_values[
                        ("param", p_creator, p_id)
                    ]
                    for p_creator, p_id in indicator_params
                }
                start, end = ranges[node]
                # 用真实交易日
                trade_dates = self.trade_dates
                start_idx = trade_dates.index(start.replace("-", ""))
                end_idx = trade_dates.index(end.replace("-", ""))
                date_list = [
                    pd.to_datetime(d).strftime("%Y-%m-%d")
                    for d in trade_dates[start_idx : end_idx + 1]
                ]
                df = self.calc_indicator(
                    indicator_info, param_dict, stock_list, date_list
                )
                self.node_values[node] = df

    def prepare_data(
        self, strategy_fullname: str, start_date: str, end_date: str
    ) -> Dict:
        # 1. 解析策略名
        creator_name, strategy_name = strategy_fullname.split(".", 1)
        # 2. 获取策略信息
        strategy_info = self.get_strategy_info(creator_name, strategy_name)
        scope_type = strategy_info["scope_type"]
        scope_id = strategy_info["scope_id"]
        # 3. 获取股票列表
        stock_list = self.get_stock_list(scope_type, scope_id)
        # 4. 获取策略参数
        strategy_params = self.get_strategy_params(creator_name, strategy_name)
        # 检查并补充回测模块必需的参数
        for required_param in REQUIRED_PARAMS:
            if required_param not in strategy_params:
                strategy_params.append(required_param)
        # 5. 纠正start_date和end_date为交易日
        start_date_corr = self.correct_to_trade_date(start_date, direction="forward")
        end_date_corr = self.correct_to_trade_date(end_date, direction="backward")
        # 如果策略定义了基准指数，提前准备基准指数日线数据（在后续会保存到输出目录）
        benchmark_df = None
        benchmark_index = strategy_info.get("benchmark_index")
        if benchmark_index:
            try:
                benchmark_df = self.client.index_daily(
                    ts_code=benchmark_index,
                    start_date=start_date_corr.replace("-", ""),
                    end_date=end_date_corr.replace("-", ""),
                )
                # 统一trade_date格式为 YYYY-MM-DD
                benchmark_df = benchmark_df.copy()
                benchmark_df["trade_date"] = pd.to_datetime(
                    benchmark_df["trade_date"]
                ).dt.strftime("%Y-%m-%d")
            except Exception as e:
                # 不阻塞主流程，但记录异常
                print(f"警告：获取基准指数 {benchmark_index} 日线数据失败: {e}")
        # 6. 构建依赖DAG，推导所有需要准备的数据节点及其最大范围
        dag_info = self.build_dependency_dag(
            strategy_params, start_date_corr, end_date_corr
        )
        # 7. 计算所有节点的值
        self.compute_all(dag_info["order"], dag_info["ranges"], stock_list)
        # 8. 合并所有参数节点为大表
        param_nodes = [node for node in dag_info["order"] if node[0] == "param"]
        param_frames = []
        param_names = []
        for node in param_nodes:
            df = self.node_values[node].copy()
            param_name = f"{node[1]}.{node[2]}"
            df = df.rename(columns={"value": param_name})
            param_frames.append(df[[param_name]])
            param_names.append(param_name)
        # 合并为大表
        if param_frames:
            # 构造目标区间的完整MultiIndex（用真实交易日）
            trade_dates = self.trade_dates
            start_idx = trade_dates.index(start_date_corr.replace("-", ""))
            end_idx = trade_dates.index(end_date_corr.replace("-", ""))
            target_dates = [
                pd.to_datetime(d).strftime("%Y-%m-%d")
                for d in trade_dates[start_idx : end_idx + 1]
            ]
            full_index = pd.MultiIndex.from_product(
                [stock_list, target_dates], names=["ts_code", "trade_date"]
            )
            # 每个参数都reindex到full_index
            param_frames_reindexed = []
            for df in param_frames:
                param_frames_reindexed.append(df.reindex(full_index))
            big_df = pd.concat(param_frames_reindexed, axis=1)
            big_df = big_df.reset_index()
            big_df["trade_date"] = big_df["trade_date"].astype(str)
        else:
            big_df = pd.DataFrame()

        # 9. 保存为csv/parquet
        output_base = (
            self.output_path if hasattr(self, "output_path") else "prepared_data"
        )
        big_df.to_csv(f"{output_base}_params.csv", index=False)
        # big_df.to_parquet(f"{output_base}_params.parquet", index=False)

        benchmark_data_path = None
        if benchmark_df is not None:
            benchmark_data_path = f"{output_base}_benchmark.csv"
            try:
                benchmark_df.to_csv(benchmark_data_path, index=False)
            except Exception as e:
                print(f"警告：保存基准指数数据到 {benchmark_data_path} 失败: {e}")

        result = {
            "stock_list": stock_list,
            "dag_info": dag_info,
            "param_data_path": f"{output_base}_params.csv",
            "param_columns": param_names,
        }
        if benchmark_data_path:
            result["benchmark_data_path"] = benchmark_data_path
            result["benchmark_index"] = benchmark_index
        return result


def tuple_to_str(t):
    if isinstance(t, tuple):
        return "|".join(str(x) for x in t)
    return str(t)


def dag_info_to_jsonable(dag_info):
    # order: list of tuple -> list of str
    order = [tuple_to_str(node) for node in dag_info["order"]]
    # ranges: dict of tuple->tuple -> dict of str->tuple
    ranges = {tuple_to_str(k): v for k, v in dag_info["ranges"].items()}
    return {"order": order, "ranges": ranges}


# ========== 3. 主入口 ==========
def main():
    # ====== 临时代码：写死参数，便于调试 ======
    class Args:
        strategy = "system.小市值策略"
        # strategy = "system.双均线策略"
        # strategy = "system.MACD策略"
        start = "2025-08-01"
        end = "2025-08-31"
        config = "config.json"
        output = None

    args = Args()
    # ====== 生产环境请恢复为 args = parse_args() ======
    # args = parse_args()
    # 生成输出目录和文件名
    strategy_dir = args.strategy.replace(".", "_")
    output_dir = args.output or os.path.join("data_prepared", strategy_dir)
    os.makedirs(output_dir, exist_ok=True)
    output_json = os.path.join(output_dir, "prepared_data.json")
    output_csv_prefix = os.path.join(output_dir, "prepared_data")

    preparer = DataPreparer(args.config)
    preparer.output_path = output_csv_prefix  # 用于csv/parquet等文件前缀
    result = preparer.prepare_data(args.strategy, args.start, args.end)
    # 保存流程和参数信息到json，修正tuple为str
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(
            {
                "stock_list": result["stock_list"],
                "dag_info": dag_info_to_jsonable(result["dag_info"]),
                "param_data_path": result["param_data_path"],
                "param_columns": result["param_columns"],
            },
            f,
            ensure_ascii=False,
            indent=2,
        )


if __name__ == "__main__":
    main()
