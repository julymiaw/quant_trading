## 关于权限

为了避免部分用户低门槛无限制的恶意调取数据，更好地保证大多数用户调取数据的稳定性，同时也为了Tushare社区的可持续发展，Pro接口开始引入积分制度。只有具备一定积分级别的用户才能调取相应的API，目前只是一个分级门槛，并不消耗积分。以下只是基础积分权限，积分越多频次（每分钟调取API的次数）越高，除分钟数据和特色数据外5000以上具有相对较高的频次。

以下是各API对应的最低分值，只有达到或超过这个分值才有权限调取数据，请各位用户知悉确认。

获得积分，具体请参阅 [积分获取办法](https://tushare.pro/document/1?doc_id=13)，了解积分与权限的关系，请参阅 [积分频次表](https://tushare.pro/document/1?doc_id=290)。

**股票数据**

| 数据名称                                                        | API              | 描述                                   | 最低分值                            |
| :-------------------------------------------------------------- | :--------------- | :------------------------------------- | :---------------------------------- |
| [日线行情](https://tushare.pro/document/2?doc_id=27)            | daily            | 全部历史，交易日每日15点～17点之间更新 | 120起                               |
| [周线行情](https://tushare.pro/document/2?doc_id=144)           | weekly           | 全部历史，每周五15点～17点之间更新     | 2000                                |
| [月线行情](https://tushare.pro/document/2?doc_id=145)           | monthly          | 全部历史，每月更新                     | 2000                                |
| [复权行情](https://tushare.pro/document/2?doc_id=146)           | pro_bar          | 全部历史，每月更新                     | 2000 （分钟、指数、基金、期货除外） |
| [每日指标数据](https://tushare.pro/document/2?doc_id=32)        | daily_basic      | 交易日每日15点～17点之间更新           | 2000起                              |
| [IPO新股列表](https://tushare.pro/document/2?doc_id=123)        | new_share        | 每日19点更新                           | 120                                 |
| [龙虎榜每日明细](https://tushare.pro/document/2?doc_id=106)     | top_list         | 数据开始于2005年，每日晚8点更新        | 2000                                |
| [龙虎榜机构交易明细](https://tushare.pro/document/2?doc_id=107) | top_inst         | 数据开始于2005年，每日晚8点更新        | 2000                                |
| [股权质押明细](https://tushare.pro/document/2?doc_id=111)       | pledge_detail    | 数据开始于2004年，每日晚9点更新        | 2000                                |
| [股权质押统计](https://tushare.pro/document/2?doc_id=110)       | pledge_stat      | 数据开始于2014年，每日晚9点更新        | 2000                                |
| [融资融券交易汇总](https://tushare.pro/document/2?doc_id=58)    | margin           | 数据开始于2010年，每日9点更新          | 2000                                |
| [融资融交易明细](https://tushare.pro/document/2?doc_id=59)      | margin_detail    | 数据开始于2010年，每日9点更新          | 2000                                |
| [股票回购](https://tushare.pro/document/2?doc_id=124)           | repurchase       | 数据开始于2011年，每日定时更新         | 2000                                |
| [概念股行情](https://tushare.pro/document/2?doc_id=260)         | concept          | 定期更新                               | 5000                                |
| [概念股列表](https://tushare.pro/document/2?doc_id=259)         | concept_detail   | 定期更新                               | 5000                                |
| [限售股解禁](https://tushare.pro/document/2?doc_id=160)         | share_float      | 定期更新                               | 3000                                |
| [大宗交易](https://tushare.pro/document/2?doc_id=161)           | block_trade      | 每日晚9点                              | 2000                                |
| [股东人数](https://tushare.pro/document/2?doc_id=166)           | stk_holdernumber | 不定期更新                             | 2000                                |
| [个股资金流向](https://tushare.pro/document/2?doc_id=170)       | moneyflow        | 交易日19点                             | 2000                                |
| [股东增减持](https://tushare.pro/document/2?doc_id=175)         | stk_holdertrade  | 交易日19点                             | 2000                                |
| [每日涨跌停价格](https://tushare.pro/document/2?doc_id=183)     | stk_limit        | 交易日9点                              | 2000起                              |
| [沪深股通持股明细](https://tushare.pro/document/2?doc_id=188)   | hk_hold          | 下个交易日8点                          | 2000起                              |

**财务数据**

| 数据名称                                                  | API             | 描述                     | 最低分值 |
| :-------------------------------------------------------- | :-------------- | :----------------------- | :------- |
| [利润表](https://tushare.pro/document/2?doc_id=33)        | income          | 全部历史，实时更新       | 2000起   |
| [资产负债表](https://tushare.pro/document/2?doc_id=36)    | balancesheet    | 全部历史，实时更新       | 2000起   |
| [现金流量表](https://tushare.pro/document/2?doc_id=44)    | cashflow        | 全部历史，实时更新       | 2000起   |
| [业绩预告](https://tushare.pro/document/2?doc_id=45)      | forecast        | 全部历史，实时更新       | 2000起   |
| [业绩快报](https://tushare.pro/document/2?doc_id=46)      | express         | 全部历史，实时更新       | 2000起   |
| [分红送股](https://tushare.pro/document/2?doc_id=103)     | dividend        | 全部历史，实时更新       | 2000起   |
| [财务指标数据](https://tushare.pro/document/2?doc_id=79)  | fina_indicator  | 全部历史，随财报实时更新 | 2000起   |
| [财务审计意见](https://tushare.pro/document/2?doc_id=80)  | fina_audit      | 全部历史，随财报实时更新 | 2000起   |
| [主营业务构成](https://tushare.pro/document/2?doc_id=81)  | fina_mainbz     | 全部历史，随财报实时更新 | 2000起   |
| [财报披露计划](https://tushare.pro/document/2?doc_id=162) | disclosure_date | 全部历史，定期更新       | 2000起   |

**基金数据**

| 数据名称                                                      | API            | 描述                       | 最低分值 |
| :------------------------------------------------------------ | :------------- | :------------------------- | :------- |
| [公募基金列表](https://tushare.pro/document/2?doc_id=19)      | fund_basic     | 全部历史，定时更新         | 2000     |
| [公募基金公司](https://tushare.pro/document/2?doc_id=118)     | fund_company   | 全部历史，定时更新         | 2000     |
| [公募基金净值](https://tushare.pro/document/2?doc_id=119)     | fund_nav       | 全部历史，每日定期更新     | 2000     |
| [场内基金日线行情](https://tushare.pro/document/2?doc_id=127) | fund_daily     | 全部历史，每日盘后更新     | 2000     |
| [公募基金分红](https://tushare.pro/document/2?doc_id=120)     | fund_div       | 全部历史，定期更新         | 2000     |
| [公募基金持仓数据](https://tushare.pro/document/2?doc_id=121) | fund_portfolio | 股票持仓数据，定期采集更新 | 2000     |
| [基金复权因子](https://tushare.pro/document/2?doc_id=199)     | fund_adj       | 基金复权因子，每日17点更新 | 5000起   |

**期货数据**

| 数据名称                                                      | API         | 描述                              | 最低分值 |
| :------------------------------------------------------------ | :---------- | :-------------------------------- | :------- |
| [期货合约列表](https://tushare.pro/document/2?doc_id=135)     | fut_basic   | 全部历史                          | 2000     |
| [期货交易日历](https://tushare.pro/document/2?doc_id=137)     | trade_cal   | 数据开始月1996年1月，定期更新     | 2000     |
| [期货日线行情](https://tushare.pro/document/2?doc_id=138)     | fut_daily   | 数据开始月1996年1月，每日盘后更新 | 2000     |
| [每日成交持仓排名](https://tushare.pro/document/2?doc_id=139) | fut_holding | 数据开始月2002年1月，每日盘后更新 | 2000     |
| [仓单日报](https://tushare.pro/document/2?doc_id=140)         | fut_wsr     | 数据开始月2006年1月，每日盘后更新 | 2000     |
| [结算参数](https://tushare.pro/document/2?doc_id=141)         | fut_settle  | 数据开始月2012年1月，每日盘后更新 | 2000     |
| [南华期货指数行情](https://tushare.pro/document/2?doc_id=155) | index_daily | 超过10年历史，每日盘后更新        | 2000     |

**期权数据**

| 数据名称                                                  | API       | 描述                    | 最低分值 |
| :-------------------------------------------------------- | :-------- | :---------------------- | :------- |
| [期权合约列表](https://tushare.pro/document/2?doc_id=158) | opt_basic | 全部历史，每日晚8点更新 | 2000起   |
| [期权日线行情](https://tushare.pro/document/2?doc_id=159) | opt_daily | 全部历史，每日17点更新  | 5000起   |

**债券数据**

| 数据名称                                                    | API      | 描述                   | 最低分值 |
| :---------------------------------------------------------- | :------- | :--------------------- | :------- |
| [可转债基础信息](https://tushare.pro/document/2?doc_id=185) | cb_basic | 全部历史，每日更新     | 2000     |
| [可转债发行数据](https://tushare.pro/document/2?doc_id=186) | cb_issue | 全部历史，每日更新     | 2000     |
| [可转债日线数据](https://tushare.pro/document/2?doc_id=187) | cb_daily | 全部历史，每日17点更新 | 2000     |

**外汇数据**

| 数据名称                                                          | API       | 描述               | 最低分值 |
| :---------------------------------------------------------------- | :-------- | :----------------- | :------- |
| [外汇基础信息（海外）](https://tushare.pro/document/2?doc_id=178) | fx_obasic | 全部历史，每日更新 | 2000     |
| [外汇日线行情](https://tushare.pro/document/2?doc_id=179)         | fx_daily  | 全部历史，每日更新 | 2000     |

**指数数据**

| 数据名称                                                      | API              | 描述                              | 最低分值 |
| :------------------------------------------------------------ | :--------------- | :-------------------------------- | :------- |
| [指数基本信息](https://tushare.pro/document/2?doc_id=94)      | index_basic      | 每日更新                          | 2000     |
| [指数日线行情](https://tushare.pro/document/2?doc_id=95)      | index_daily      | 全部历史，交易日15点～17点更新    | 2000起   |
| [指数周线行情](https://tushare.pro/document/2?doc_id=171)     | index_weekly     | 每周盘后更新                      | 2000起   |
| [指数月线行情](https://tushare.pro/document/2?doc_id=172)     | index_monthly    | 每月盘后更新                      | 2000起   |
| [指数成分和权重](https://tushare.pro/document/2?doc_id=96)    | index_weight     | 月度成分和权重数据                | 2000     |
| [大盘指数每日指标](https://tushare.pro/document/2?doc_id=128) | index_dailybasic | 数据开始月2004年1月，每日盘后更新 | 4000起   |
| [申万行业分类](https://tushare.pro/document/2?doc_id=181)     | index_classify   | 全部分类                          | 2000     |
| [申万行业成分](https://tushare.pro/document/2?doc_id=335)     | index_member_all | 全部数据                          | 2000     |

**港股数据**

| 数据名称                                                  | API      | 描述               | 最低分值 |
| :-------------------------------------------------------- | :------- | :----------------- | :------- |
| [港股列表](https://tushare.pro/document/2?doc_id=191)     | hk_basic | 全部历史，每日更新 | 2000     |
| [港股日线行情](https://tushare.pro/document/2?doc_id=192) | hk_daily | 全部历史，每日更新 | 1000元   |
| [港股分钟行情](https://tushare.pro/document/2?doc_id=304) | hk_mins  | 全部历史，每日更新 | 2000元   |

**行业特色**

| 数据名称                                                           | API                | 描述                       | 最低分值 |
| :----------------------------------------------------------------- | :----------------- | :------------------------- | :------- |
| [台湾电子产业月营收](https://tushare.pro/document/2?doc_id=88)     | tmt_twincome       | 数据开始于2011年，月度更新 | 0        |
| [台湾电子产业月营收明细](https://tushare.pro/document/2?doc_id=87) | tmt_twincomedetail | 数据开始于2011年，月度更新 | 0        |
| [电影月度票房](https://tushare.pro/document/2?doc_id=113)          | bo_monthly         | 数据开始于2008年，月度更新 | 500      |
| [电影周度票房](https://tushare.pro/document/2?doc_id=114)          | bo_weekly          | 数据开始于2008年，每周更新 | 500      |
| [电影日度票房](https://tushare.pro/document/2?doc_id=115)          | bo_daily           | 数据开始于2018年，每日更新 | 500      |
| [影院每日票房](https://tushare.pro/document/2?doc_id=116)          | bo_cinema          | 数据开始于2018年，每日更新 | 500      |
| [全国电影剧本备案数据](https://tushare.pro/document/2?doc_id=156)  | film_record        | 数据开始于2011年，定期更新 | 120起    |
| [全国电视剧本备案数据](https://tushare.pro/document/2?doc_id=180)  | teleplay_record    | 数据开始于2009年，定期更新 | 600起    |

**宏观经济**

| 数据名称                                                      | API          | 描述                       | 最低分值 |
| :------------------------------------------------------------ | :----------- | :------------------------- | :------- |
| [SHIBOR利率数据](https://tushare.pro/document/2?doc_id=149)   | shibor       | 数据开始于2006年，每日12点 | 2000     |
| [SHIBOR报价数据](https://tushare.pro/document/2?doc_id=150)   | shibor_quote | 数据开始于2006年，每日12点 | 2000     |
| [LPR贷款基础利率](https://tushare.pro/document/2?doc_id=151)  | shibor_lpr   | 数据开始于2013年，每日12点 | 120      |
| [LIBOR拆借利率](https://tushare.pro/document/2?doc_id=152)    | libor        | 数据开始于1986年，每日12点 | 120      |
| [HIBOR拆借利率](https://tushare.pro/document/2?doc_id=153)    | hibor        | 数据开始于2002年，每日12点 | 120      |
| [温州民间借贷利率](https://tushare.pro/document/2?doc_id=173) | wz_index     | 数据不定期更新             | 2000     |
| [广州民间借贷利率](https://tushare.pro/document/2?doc_id=174) | gz_index     | 数据不定期更新             | 2000     |