import unittest
import tushare as ts
from tushare_cache_client import TushareCacheClient


class TestTushareCacheClient(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # 初始化本地缓存数据库
        cls.client = TushareCacheClient()
        cls.client.init_all_from_tushare()
        # 初始化 tushare 官方接口
        ts.set_token(cls.client.config["tushare_token"])
        cls.pro = ts.pro_api()

    def assert_df_equal(self, df1, df2, msg="DataFrame内容不一致"):
        # 只比较内容，不比较索引顺序
        self.assertTrue(
            df1.sort_values(list(df1.columns))
            .reset_index(drop=True)
            .equals(df2.sort_values(list(df2.columns)).reset_index(drop=True)),
            msg,
        )

    def test_trade_cal(self):
        # 选取一个常见区间
        df_api = self.pro.trade_cal(
            exchange="SSE", start_date="20240101", end_date="20240110"
        )
        df_cache = self.client.trade_cal(
            exchange="SSE", start_date="20240101", end_date="20240110"
        )
        self.assert_df_equal(df_api[df_cache.columns], df_cache)

    def test_stock_basic(self):
        df_api = self.pro.stock_basic(
            exchange="",
            list_status="L",
            fields="ts_code,symbol,name,area,industry,fullname,enname,cnspell,market,exchange,curr_type,list_status,list_date,delist_date,is_hs,act_name,act_ent_type",
        )
        df_cache = self.client.stock_basic()
        # 只比较两者的主要字段
        self.assert_df_equal(df_api[df_cache.columns], df_cache)

    def test_daily(self):
        # 选取一只股票和一个短时间段
        ts_code = "000001.SZ"
        start_date = "20240101"
        end_date = "20240110"
        df_api = self.pro.daily(
            ts_code=ts_code, start_date=start_date, end_date=end_date
        )
        df_cache = self.client.daily(
            ts_code=ts_code, start_date=start_date, end_date=end_date
        )
        # 只比较两者的主要字段
        self.assert_df_equal(df_api[df_cache.columns], df_cache)

    def test_daily_basic(self):
        ts_code = "000001.SZ"
        start_date = "20240101"
        end_date = "20240110"
        df_api = self.pro.daily_basic(
            ts_code=ts_code, start_date=start_date, end_date=end_date
        )
        df_cache = self.client.daily_basic(
            ts_code=ts_code, start_date=start_date, end_date=end_date
        )
        self.assert_df_equal(df_api[df_cache.columns], df_cache)


if __name__ == "__main__":
    unittest.main()
