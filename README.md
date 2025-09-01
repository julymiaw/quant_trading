# AI驱动的量化交易分析平台

## 项目概述

这是一个校企实习项目，旨在构建一个**AI驱动的量化交易智能分析系统**。该系统专注于通过历史数据分析，支持策略回测和交易信号生成，包括数据采集、策略建模和风险评估等核心功能。

### 核心功能

- **回测分析**：支持多种策略在历史数据上的回测和性能评估
- **数据管理**：高效获取和管理股票历史行情数据
- **策略评估**：对交易策略进行量化评估和风险分析

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

# 检查哪些股票有足够的回测数据（数据完整性>95%）
python stock_data_fetcher.py --check
```

> **注意**：高质量回测至少需要1年以上的历史数据，推荐使用3年数据以捕捉不同市场周期。

### 4. 策略回测与分析

完成数据准备后，可以运行策略回测：

```bash
# 查看可用策略列表
python strategy_backtest.py --list

# 对指定策略和股票进行回测
python strategy_backtest.py --strategy STRAT_001 --stock 000001.SZ

# 指定时间范围和初始资金
python strategy_backtest.py --strategy STRAT_001 --stock 000001.SZ --start 2023-01-01 --end 2025-01-01 --cash 200000
```

回测结果会显示关键指标，如总收益率、年化收益率、最大回撤、夏普比率等，并自动保存到数据库。

> **提示**：回测脚本支持更多参数设置，使用 `python strategy_backtest.py --help` 查看完整帮助信息。

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
- **Strategy** - 选股策略表
- **BacktestReport** - 回测报告表

## 技术栈

- **Python 3.9+**：主要编程语言
- **MySQL 8.0+**：数据存储
- **Tushare API**：金融数据获取
- **pandas/numpy**：数据处理
- **pymysql**：数据库连接

## 联系方式

如有任何问题，请联系项目负责人或在项目仓库中提交Issue。
