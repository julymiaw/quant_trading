# AI驱动的量化交易分析平台

## 项目概述

这是一个校企实习项目，旨在构建一个**AI驱动的量化交易智能分析系统**。该系统专注于通过历史数据分析，支持策略回测和交易信号生成，包括数据采集、策略建模和风险评估等核心功能。

### 核心功能

- **回测分析**：支持多种策略在历史数据上的回测和性能评估
- **数据管理**：高效获取和管理股票历史行情数据
- **策略评估**：对交易策略进行量化评估和风险分析
- **基本面分析**：支持市值、市净率等基本面指标的获取和分析
- **指数成分股**：支持沪深300等主要指数成分股的获取和回测

## 快速开始

### 1. 准备工作

#### 1.1 安装MySQL数据库

我们使用MySQL 8.x作为数据库，Windows用户可以通过以下步骤安装：

```bash
# 使用Windows包管理器winget安装MySQL
winget install Oracle.MySQL
```

安装完成后：

1. 在开始菜单中找到并运行"MySQL 8.4 Configurator"
2. 按照向导完成初始配置
3. 设置root用户密码并牢记（后续配置需要）
4. 确保MySQL服务已启动

> **注意**：如果winget安装失败，可以从[MySQL官方网站](https://dev.mysql.com/downloads/mysql/)下载安装包手动安装。

#### 1.2 克隆项目

```bash
git clone https://github.com/julymiaw/quant_trading.git
cd quant_trading
```

### 2. 环境配置

#### 2.1 创建Python虚拟环境

我们使用Conda管理Python环境：

```bash
# 使用项目提供的配置文件创建虚拟环境
conda env create -f quant_trading.yml

# 激活环境
conda activate quant_trading
```

> **注意**：如果你没有安装Conda，请先从[Miniconda官网](https://docs.conda.io/en/latest/miniconda.html)下载并安装。

#### 2.2 初始化数据库

```bash
# 确保使用UTF-8编码，避免中文乱码
chcp 65001

# 使用root用户登录MySQL并执行初始化脚本
mysql -u root -p < init_database.sql
```

系统会提示输入之前设置的MySQL root密码。

#### 2.3 测试连接

```bash
# 运行连接测试工具
python connection_tester.py
```

首次运行会生成config.json配置文件，请按照提示编辑该文件：

1. 修改MySQL密码
2. 添加Tushare API token（需要在[Tushare官网](https://tushare.pro/register)注册获取）

此工具会测试数据库连接和Tushare API，并生成API可用性报告，帮助您了解当前可用的数据接口。

### 3. 准备回测数据

股票数据获取脚本专注于为回测准备历史数据：

```bash
# 查看使用说明
python stock_data_fetcher.py --help

# 准备指定股票的回测数据（默认3年数据）
python stock_data_fetcher.py --backtest --stocks 000001.SZ,600519.SH

# 自定义历史数据天数
python stock_data_fetcher.py --backtest --stocks 000001.SZ --days 730

# 使用指数成分股进行回测（如沪深300）
python stock_data_fetcher.py --backtest --index 000300.SH

# 检查哪些股票有足够的回测数据（数据完整性>95%）
python stock_data_fetcher.py --check
```

> **注意**：每次运行数据准备命令时，系统会自动获取股票基本信息、估值数据、财务数据等所有回测必要的数据，无需单独执行额外命令。

### 4. 策略回测与分析

完成数据准备后，可以运行策略回测：

```bash
# 查看可用策略列表
python strategy_backtest.py --list

# 对指定策略和股票进行回测
python strategy_backtest.py --strategy STRAT_001 --stock 000001.SZ

# 指定时间范围和初始资金
python strategy_backtest.py --strategy STRAT_001 --stock 000001.SZ --start 2023-01-01 --end 2025-01-01 --cash 200000

# 使用指数成分股进行回测（如沪深300）
python strategy_backtest.py --strategy STRAT_001 --index 000300.SH --start 2023-01-01 --end 2025-01-01
```

我们现在支持的策略包括：

- **STRAT_001** - 小市值策略：筛选市值20-30亿的股票，选取最小的三只
- **STRAT_002** - 双均线策略：使用5日均线和价格关系进行买卖信号生成
- **STRAT_003** - 银行股轮动策略：持有沪深300银行指数成分股中市净率最低的股票
- **STRAT_004** - 低估价值选股策略：基于市净率、负债比率和流动比率的综合筛选
- **STRAT_005** - Dual Thrust策略：基于价格通道突破的策略

### 使用指数成分股进行回测

当您使用`--index`参数获取数据后，可以直接在回测中引用该指数：

```bash
# 获取沪深300指数的所有成分股数据
python stock_data_fetcher.py --backtest --index 000300.SH

# 使用沪深300指数成分股进行回测
python strategy_backtest.py --strategy STRAT_001 --index 000300.SH --start 2023-01-01 --end 2025-01-01 --cash 1000000
```

系统会自动：

1. 从数据库中读取指数的成分股列表
2. 对每只成分股应用选定的策略
3. 根据策略生成买卖信号
4. 综合计算整个投资组合的表现

您还可以使用以下参数优化回测过程：

```bash
# 限制使用指数成分股中的前N只进行回测
python strategy_backtest.py --strategy STRAT_001 --index 000300.SH --top 50 --start 2023-01-01 --end 2025-01-01

# 使用指数成分股中权重最高的前20%进行回测
python strategy_backtest.py --strategy STRAT_001 --index 000300.SH --weight-percent 20 --start 2023-01-01 --end 2025-01-01

# 同时测试多个策略在指数成分股上的表现
python strategy_backtest.py --strategy STRAT_001,STRAT_003 --index 000300.SH --start 2023-01-01 --end 2025-01-01
```

#### 小市值策略回测示例

以下是使用小市值策略在沪深300成分股上进行回测的完整示例：

```bash
# 首先准备必要的数据
python stock_data_fetcher.py --backtest --index 000300.SH

# 使用小市值策略进行回测
python strategy_backtest.py --strategy STRAT_001 --index 000300.SH --start 2023-08-25 --end 2025-08-24 --cash 1000000
```

预期结果：
- 总收益率: 约32.6%
- 年化收益率: 约15.8%
- 最大回撤: 约14.2%
- 夏普比率: 约1.21

> **注意**：实际回测结果可能因数据更新时间和市场变化而有所不同。您可以与聚宽平台上的同策略结果进行对比分析。

## 项目结构

```plaintext
quant_trading/
├── README.md                # 项目说明文档
├── init_database.sql        # 数据库初始化SQL脚本
├── quant_trading.yml        # Conda环境配置文件
├── connection_tester.py     # 数据库和API连接测试工具
├── stock_data_fetcher.py    # 回测数据准备脚本
├── strategy_backtest.py     # 策略回测脚本
├── config.json              # 配置文件
└── api_reports/             # API可用性报告目录
```

## 数据库结构

系统使用的主要数据表：

- **StockMarketData** - 股票市场数据表
- **StockBasic** - 股票基本信息表
- **StockValuation** - 股票估值数据表
- **BalanceSheet** - 资产负债表
- **IncomeStatement** - 利润表
- **IndexComponent** - 指数成分股表
- **Strategy** - 选股策略表
- **BacktestReport** - 回测报告表

## 技术栈

- **Python 3.9+**：主要编程语言
- **MySQL 8.0+**：数据存储
- **Tushare API**：金融数据获取
- **pandas/numpy**：数据处理
- **pymysql**：数据库连接
- **Backtrader**：回测框架

## 联系方式

如有任何问题，请联系项目负责人或在项目仓库中提交Issue。
