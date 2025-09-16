# 量化交易系统 API 测试指南

## 概述

本测试套件为量化交易系统提供了全面的API测试覆盖，包括功能测试、安全测试和性能测试。

## 测试脚本列表

### 1. 🔐 用户认证API测试 (`test_auth_api.py`)

- **功能**: 测试用户登录、注册、信息获取等认证功能
- **测试内容**:
  - 健康检查
  - 用户注册
  - 用户登录
  - 获取用户信息
  - 无效登录处理
  - 重复注册检查
  - 未授权访问拦截

### 2. 🔧 参数管理API测试 (`test_param_api.py`)

- **功能**: 测试参数的增删改查、智能搜索建议等功能
- **测试内容**:
  - 参数列表获取
  - 参数创建
  - 参数更新
  - 智能搜索建议
  - 重复参数处理
  - 不存在参数处理
  - 参数删除

### 3. 📈 策略管理API测试 (`test_strategy_api.py`)

- **功能**: 测试策略的增删改查、复制、参数关系管理等功能
- **测试内容**:
  - 策略列表获取
  - 策略创建
  - 策略详情获取
  - 策略更新
  - 策略复制
  - 策略参数关系管理
  - 重复策略处理
  - 策略删除

### 4. 📊 指标管理API测试 (`test_indicator_api.py`)

- **功能**: 测试指标的增删改查、复制、参数关系管理等功能
- **测试内容**:
  - 指标列表获取
  - 指标创建
  - 指标更新
  - 指标状态切换
  - 指标复制
  - 指标参数关系管理
  - 重复指标处理
  - 指标删除

### 5. 📧 消息系统API测试 (`test_message_api.py`)

- **功能**: 测试消息的获取、标记已读、删除等功能
- **测试内容**:
  - 消息列表获取
  - 分页消息获取
  - 消息类型过滤
  - 消息状态过滤
  - 消息标记已读
  - 重复标记处理
  - 消息删除
  - 不存在消息处理

### 6. 🚀 回测系统API测试 (`test_backtest_api.py`)

- **功能**: 测试完整的回测工作流程
- **测试内容**:
  - 用户登录
  - 回测任务启动
  - 异步消息通知
  - 回测结果查询
  - 端到端流程验证

### 7. 🛡️ 权限安全测试 (`test_security.py`)

- **功能**: 测试跨用户访问权限控制，确保数据隔离
- **测试内容**:
  - 跨用户参数访问
  - 跨用户策略访问
  - 跨用户指标访问
  - 跨用户消息访问
  - 跨用户回测报告访问
  - 无效token处理

### 8. ⚡ 性能和压力测试 (`test_performance.py`)

- **功能**: 测试API在高并发情况下的性能表现
- **测试内容**:
  - 健康检查API性能
  - 各种列表API性能
  - 登录API性能
  - 搜索建议API性能
  - 内存泄漏测试
  - 并发处理能力测试

### 9. 🎯 集成测试套件 (`test_suite.py`)

- **功能**: 统一的测试入口，管理所有测试脚本
- **特性**:
  - 交互式测试模式
  - 选择性测试运行
  - 快速测试模式
  - 详细测试报告
  - 命令行参数支持

## 使用方法

### 前提条件

1. **启动后端服务器**:

   ```bash
   python app.py
   ```

   确保服务器运行在 `http://localhost:5000`

2. **安装依赖**:

   ```bash
   pip install requests
   ```

### 运行测试

#### 方法一: 使用集成测试套件（推荐）

```bash
# 交互式模式
python test_suite.py

# 运行所有测试
python test_suite.py --all

# 运行快速测试（跳过性能和安全测试）
python test_suite.py --quick

# 查看帮助
python test_suite.py --help
```

#### 方法二: 单独运行测试脚本

```bash
# 运行用户认证测试
python test_auth_api.py

# 运行参数管理测试
python test_param_api.py

# 运行策略管理测试
python test_strategy_api.py

# 运行指标管理测试
python test_indicator_api.py

# 运行消息系统测试
python test_message_api.py

# 运行回测系统测试
python test_backtest_api.py

# 运行安全测试
python test_security.py

# 运行性能测试
python test_performance.py
```

## 测试配置

### 认证配置

大部分测试使用系统用户进行认证:

- 用户名: `system`
- 密码: `Admin@2025!SeQuan`

### 测试数据

- 测试会创建临时数据，测试结束后自动清理
- 不会影响现有的生产数据
- 安全测试会创建临时用户，测试后需手动清理

### 性能基准

- 响应时间 < 1000ms 为优秀
- 并发成功率 > 95% 为良好
- 内存使用增长 < 50% 为正常

## 测试报告

测试完成后会显示详细报告，包括：

- 总测试数和通过率
- 每个测试的详细结果
- 性能统计数据
- 错误信息和建议

## 故障排除

### 常见问题

1. **连接服务器失败**
   - 检查 `app.py` 是否已启动
   - 确认服务器运行在正确端口 (5000)
   - 检查防火墙设置

2. **认证失败**
   - 检查数据库中是否存在 `system` 用户
   - 确认密码是否正确
   - 检查数据库连接

3. **测试超时**
   - 检查数据库响应速度
   - 确认网络连接稳定
   - 调整测试脚本中的超时设置

4. **权限测试失败**
   - 确认用户数据隔离机制正常工作
   - 检查JWT token验证逻辑
   - 验证API权限控制实现

### 调试建议

1. **启用详细日志**:
   修改 `app.py` 中的日志级别为 `DEBUG`

2. **检查数据库状态**:

   ```sql
   SELECT COUNT(*) FROM User;
   SELECT COUNT(*) FROM Strategy;
   SELECT COUNT(*) FROM BacktestReport;
   ```

3. **监控系统资源**:
   - CPU 使用率
   - 内存使用量  
   - 数据库连接数

## 性能优化建议

基于测试结果，可以考虑以下优化：

1. **数据库优化**:
   - 添加必要的索引
   - 优化查询语句
   - 使用连接池

2. **缓存优化**:
   - 实现Redis缓存
   - 缓存频繁查询的数据
   - 设置合理的过期时间

3. **API优化**:
   - 实现分页查询
   - 添加请求频率限制
   - 优化数据传输格式

4. **安全加固**:
   - 实现更强的密码策略
   - 添加登录失败限制
   - 启用HTTPS

## 持续集成

建议将测试脚本集成到CI/CD流程中：

```yaml
# 示例 GitHub Actions 配置
name: API Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Setup Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Start server
        run: python app.py &
      - name: Run tests
        run: python test_suite.py --all
```

## 联系信息

如有问题或建议，请联系开发团队或提交Issue。
