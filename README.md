# AI驱动的量化交易分析平台

## 项目概述

这是一个校企实习项目，旨在构建一个**AI驱动的量化交易智能分析系统**。该系统能够通过历史数据挖掘和市场特征分析，自动生成高概率的买卖信号，并提供完整的交易闭环，包括数据采集、特征工程、策略建模、实时监控和风险控制。

### 核心功能

- **智能决策**：融合机器学习与深度学习技术生成交易信号
- **全流程覆盖**：从数据采集到风险控制的完整交易闭环
- **多平台支持**：支持Windows/Linux/云平台多环境部署

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

#### 2.3 测试数据库连接

```bash
# 运行数据库连接测试脚本
python test_database_connection.py
```

首次运行会生成config.json配置文件，请按照提示编辑该文件：

1. 修改MySQL密码
2. 添加Tushare API token（需要在[Tushare官网](https://tushare.pro/register)注册获取）

### 3. 数据获取与分析

#### 3.1 获取股票数据

```bash
# 获取配置文件中指定的股票数据
python stock_data_fetcher.py

# 获取全市场数据
python stock_data_fetcher.py --market
```

#### 3.2 查看使用说明

```bash
python stock_data_fetcher.py --help
```

### 4. 策略回测与分析

量化交易系统提供了完整的策略回测功能，可以评估不同策略在历史数据上的表现。

#### 4.1 准备回测数据

在进行回测前，首先需要准备足够的历史数据：

```bash
# 准备指定股票的回测数据（默认3年数据）
python stock_data_fetcher.py --backtest --stocks 000001.SZ,600519.SH

# 自定义历史数据天数
python stock_data_fetcher.py --backtest --stocks 000001.SZ --days 730

# 检查哪些股票有足够的回测数据（数据完整性>95%）
python stock_data_fetcher.py --check
```

> **注意**：高质量回测至少需要1年以上的历史数据，推荐使用3年数据以捕捉不同市场周期。

#### 4.2 运行策略回测

完成数据准备后，可以运行策略回测：

```bash
# 查看可用策略列表
python strategy_backtest.py --list

# 对指定策略和股票进行回测
python strategy_backtest.py --strategy STRAT_001 --stock 000001.SZ

# 指定时间范围和初始资金
python strategy_backtest.py --strategy STRAT_001 --stock 000001.SZ --start 2023-01-01 --end 2025-01-01 --cash 200000
```

回测结果会显示关键指标，如总收益率、年化收益率、最大回撤、夏普比率等，并自动保存到数据库。同时会弹出交互式图表展示回测过程。

#### 4.3 蒙特卡洛模拟

为评估策略的稳健性，系统还提供蒙特卡洛模拟功能：

```bash
# 运行蒙特卡洛模拟（默认50次）
python strategy_backtest.py --strategy STRAT_001 --stock 000001.SZ --montecarlo

# 增加模拟次数提高结果可靠性
python strategy_backtest.py --strategy STRAT_001 --stock 000001.SZ --montecarlo --simulations 100
```

蒙特卡洛模拟会生成收益率分布和最大回撤分布图表，并显示关键统计指标，帮助您评估策略在不同市场环境下的表现稳定性。

> **提示**：回测脚本支持更多参数设置，使用 `python strategy_backtest.py --help` 查看完整帮助信息。

## 项目结构

```plaintext
quant_trading/
├── README.md                # 项目说明文档
├── init_database.sql        # 数据库初始化SQL脚本
├── quant_trading.yml        # Conda环境配置文件
├── test_database_connection.py  # 数据库连接测试脚本
├── stock_data_fetcher.py    # 股票数据获取脚本
├── strategy_backtest.py     # 策略回测脚本
├── config.json              # 配置文件
└── 要求.md                  # 项目需求文档
```

## 数据库结构

系统使用的主要数据表：

- **User** - 用户信息表
- **StockMarketData** - 股票市场数据表
- **TechnicalIndicator** - 技术指标定义表
- **Strategy** - 选股策略表
- **StrategyCondition** - 策略条件表
- **TradingSignal** - 交易信号表
- **BacktestReport** - 回测报告表
- **SystemLog** - 系统日志表

## 技术栈

- **Python 3.9+**：主要编程语言
- **MySQL 8.0+**：数据存储
- **Tushare API**：金融数据获取
- **pandas/numpy**：数据处理
- **pymysql**：数据库连接

## 联系方式

如有任何问题，请联系项目负责人或在项目仓库中提交Issue。
