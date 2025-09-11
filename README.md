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

### 3. 初始化数据库

数据库初始化分为**两步**，请依次执行以下两个SQL脚本：

```bash
# 确保使用UTF-8编码，避免中文乱码
chcp 65001

# 1. 初始化Tushare原始数据缓存库
mysql -u root -p < init_tushare_cache.sql

# 2. 初始化量化交易业务数据库
mysql -u root -p < init_quant_trading_db.sql
```

系统会提示输入之前设置的MySQL root密码。

### 4. 配置与测试

```bash
# 运行连接测试工具
python connection_tester.py
```

首次运行会生成config.json配置文件，请按照提示编辑该文件：

1. 修改MySQL密码
2. 添加Tushare API token（需要在[Tushare官网](https://tushare.pro/register)注册获取）

此工具会测试数据库连接和Tushare API，并生成API可用性报告，帮助您了解当前可用的数据接口。

### 5. 准备回测数据

请使用新的数据准备API脚本为策略准备回测数据：

```bash
# 为指定策略准备回测数据
python prepare_strategy_data.py --strategy system.双均线策略 --start 2025-08-01 --end 2025-08-31

python prepare_strategy_data.py --strategy system.MACD策略 --start 2025-08-01 --end 2025-08-31
```

脚本会自动为策略准备所需的参数数据，并输出到指定目录下的csv和json文件。

---

## 项目结构

```plaintext
quant_trading/
├── README.md                # 项目说明文档
├── init_tushare_cache.sql   # Tushare原始数据缓存库初始化脚本
├── init_quant_trading_db.sql# 量化交易业务数据库初始化脚本
├── quant_trading.yml        # Conda环境配置文件
├── connection_tester.py     # 数据库和API连接测试工具
├── prepare_strategy_data.py # 回测数据准备脚本（新API）
├── config.json              # 配置文件
└── api_reports/             # API可用性报告目录
```

## 数据库结构

系统使用的主要数据表：

- **Tushare缓存库**：trade_cal、stock_basic、daily、daily_basic、index_basic、index_daily等
- **业务库**：User、Indicator、Param、Strategy、StrategyParamRel、IndicatorParamRel、TradingSignal、BacktestReport、SystemLog等

## 技术栈

- **Python 3.9+**：主要编程语言
- **MySQL 8.0+**：数据存储
- **Tushare API**：金融数据获取
- **pandas/numpy**：数据处理
- **pymysql**：数据库连接

## 联系方式

如有任何问题，请联系项目负责人或在项目仓库中提交Issue。
