<template>
  <div class="strategy-list-container">
    <!-- 页面标题和操作按钮 -->
    <div class="page-header">
      <h1>策略管理</h1>
      <div class="header-actions">
        <el-select
          v-model="strategyType"
          placeholder="选择策略类型"
          style="width: 150px; margin-right: 10px">
          <el-option label="我的策略" value="my" />
          <el-option label="系统策略" value="system" />
          <el-option label="公开策略" value="public" />
        </el-select>
        <el-button type="primary" @click="addNewStrategy">
          <el-icon><Plus /></el-icon>
          添加策略
        </el-button>
      </div>
    </div>

    <!-- 搜索和筛选区域 -->
    <div class="search-filter-area">
      <el-input
        v-model="searchKeyword"
        placeholder="搜索策略名称"
        prefix-icon="Search"
        class="search-input"
        clearable />
      <el-select
        v-model="scopeType"
        placeholder="策略生效范围"
        style="width: 150px; margin-left: 10px">
        <el-option label="全部" value="all" />
        <el-option label="单只股票" value="single_stock" />
        <el-option label="指数成分股" value="index" />
      </el-select>
      <el-button
        type="primary"
        @click="refreshStrategies"
        style="margin-left: 10px">
        <el-icon><Refresh /></el-icon>
        刷新
      </el-button>
    </div>

    <!-- 策略列表表格 -->
    <div class="table-container">
      <el-table
        v-loading="loading"
        :data="filteredStrategies"
        style="width: 100%"
        border
        row-key="id">
        <el-table-column prop="strategy_name" label="策略名称" min-width="180">
          <template #default="scope">
            <el-link
              type="primary"
              :underline="false"
              @click="goToStrategyDetail(scope.row)">
              {{ scope.row.strategy_name }}
            </el-link>
          </template>
        </el-table-column>
        <el-table-column prop="creator_name" label="创建者" width="120" />
        <el-table-column prop="public" label="是否公开" width="100">
          <template #default="scope">
            <el-switch v-model="scope.row.public" disabled />
          </template>
        </el-table-column>
        <el-table-column prop="scope_type" label="生效范围" width="120">
          <template #default="scope">
            <el-tag
              :type="
                scope.row.scope_type === 'all'
                  ? 'primary'
                  : scope.row.scope_type === 'single_stock'
                  ? 'success'
                  : 'warning'
              ">
              {{
                scope.row.scope_type === "all"
                  ? "全部"
                  : scope.row.scope_type === "single_stock"
                  ? "单只股票"
                  : "指数成分股"
              }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column
          prop="scope_id"
          label="股票/指数ID"
          width="120"
          v-if="showScopeId" />
        <el-table-column prop="position_count" label="持仓数量" width="100" />
        <el-table-column prop="rebalance_interval" label="调仓间隔" width="100">
          <template #default="scope">
            {{ scope.row.rebalance_interval || 0 }}天
          </template>
        </el-table-column>
        <el-table-column
          prop="strategy_desc"
          label="策略描述"
          show-overflow-tooltip
          min-width="200" />
        <el-table-column prop="create_time" label="创建时间" width="160" />
        <el-table-column prop="update_time" label="更新时间" width="160" />
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="scope">
            <el-button
              type="primary"
              size="small"
              @click="goToStrategyDetail(scope.row)"
              v-if="isCurrentUserCreator(scope.row)">
              编辑
            </el-button>
            <el-button
              type="danger"
              size="small"
              @click="deleteStrategy(scope.row)"
              v-if="isCurrentUserCreator(scope.row)">
              删除
            </el-button>
            <el-button
              type="default"
              size="small"
              @click="copyStrategy(scope.row)">
              复制
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 分页控件 -->
    <div class="pagination-container">
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :page-sizes="[10, 20, 50, 100]"
        layout="total, sizes, prev, pager, next, jumper"
        :total="total"
        @size-change="handleSizeChange"
        @current-change="handleCurrentChange" />
    </div>
  </div>
</template>

<script>
import { ref, reactive, computed, onMounted, watch } from "vue";
import { useRouter } from "vue-router";
import { ElMessage, ElMessageBox } from "element-plus";
import { Plus, Search, Refresh } from "@element-plus/icons-vue";
import axios from "axios";

export default {
  name: "StrategyList",
  components: {
    Plus,
    Search,
    Refresh,
  },
  setup() {
    const router = useRouter();
    const loading = ref(false);
    const strategies = ref([]);
    const searchKeyword = ref("");
    const scopeType = ref("all");
    const strategyType = ref("my");
    const currentPage = ref(1);
    const pageSize = ref(10);
    const total = ref(0);

    // 获取用户信息
    const getUserInfo = () => {
      const storedUserInfo = localStorage.getItem("userInfo");
      return storedUserInfo ? JSON.parse(storedUserInfo) : null;
    };

    // 判断是否是当前用户创建的策略
    const isCurrentUserCreator = (strategy) => {
      const userInfo = getUserInfo();
      return userInfo && strategy.creator_name === userInfo.user_name;
    };

    // 计算筛选后的策略列表（后端已处理分页和筛选，前端直接显示）
    const filteredStrategies = computed(() => {
      return strategies.value;
    });

    // 是否显示scope_id列
    const showScopeId = computed(() => {
      return (
        scopeType.value !== "all" || strategies.value.some((s) => s.scope_id)
      );
    });

    // 获取策略列表
    const fetchStrategies = async () => {
      try {
        loading.value = true;

        // 获取用户token
        const token = localStorage.getItem("token");
        if (!token) {
          ElMessage.error("请先登录");
          return;
        }

        // 构建查询参数
        const params = {
          page: currentPage.value,
          page_size: pageSize.value,
          strategy_type: strategyType.value,
          scope_type: scopeType.value === "all" ? "all" : scopeType.value,
        };

        if (searchKeyword.value) {
          params.search = searchKeyword.value;
        }

        // 调用真实的API
        const response = await axios.get(
          "http://localhost:5000/api/strategies",
          {
            params: params,
            headers: {
              Authorization: `Bearer ${token}`,
            },
          }
        );

        if (response.data.code === 200) {
          strategies.value = response.data.data.strategies || [];
          total.value = response.data.data.total || 0;
        } else {
          throw new Error(response.data.message || "获取策略列表失败");
        }
      } catch (error) {
        console.error("获取策略列表失败:", error);
        ElMessage.error("获取策略列表失败，请重试");
      } finally {
        loading.value = false;
      }
    };

    // 刷新策略列表
    const refreshStrategies = () => {
      fetchStrategies();
    };

    // 跳转到策略详情页面
    const goToStrategyDetail = (strategy) => {
      router.push({
        name: "StrategyDetail",
        params: {
          creatorName: strategy.creator_name,
          strategyName: strategy.strategy_name,
        },
      });
    };

    // 添加新策略（直接跳转到详情页面）
    const addNewStrategy = async () => {
      try {
        loading.value = true;

        // 获取用户token
        const token = localStorage.getItem("token");
        if (!token) {
          ElMessage.error("请先登录");
          return;
        }

        // 获取用户信息
        const userInfo = getUserInfo();
        if (!userInfo) {
          ElMessage.error("请先登录");
          return;
        }

        // 创建一个新的策略，使用默认值
        const newStrategyData = {
          strategy_name: `新策略_${Date.now()}`, // 使用时间戳确保唯一性
          public: false, // 新策略默认不公开
          scope_type: "all",
          scope_id: "",
          position_count: 5,
          rebalance_interval: 5,
          buy_fee_rate: 0.001,
          sell_fee_rate: 0.001,
          strategy_desc: "新创建的策略，请编辑详细信息",
          select_func: `def select_func(candidates, params, position_count, current_holdings, date, context=None):
    """
    选股函数 - 根据策略逻辑选择要持有的股票

    参数说明:
    - candidates: 可选股票列表
    - params: 参数字典，包含各种技术指标和数据
    - position_count: 最大持仓股票数量
    - current_holdings: 当前持仓股票列表
    - date: 当前日期
    - context: 上下文对象，可用于存储状态信息

    返回值:
    - 选中的股票列表（最多position_count只）
    """
    # 示例：选择市值最小的position_count只股票
    if not candidates:
        return []

    # 获取股票市值数据
    market_values = []
    for stock in candidates:
        if f"system.total_mv" in params.get(stock, {}):
            mv = params[stock]["system.total_mv"]
            market_values.append((stock, mv))

    # 按市值从小到大排序，选择最小的position_count只
    market_values.sort(key=lambda x: x[1])
    selected = [stock for stock, _ in market_values[:position_count]]

    return selected`,
          risk_control_func: `def risk_control_func(current_holdings, params, date, context=None):
    """
    风险控制函数 - 对当前持仓进行风险控制

    参数说明:
    - current_holdings: 当前持仓股票列表
    - params: 参数字典，包含各种技术指标和数据
    - date: 当前日期
    - context: 上下文对象，可用于存储状态信息

    返回值:
    - 调整后的持仓股票列表（移除了需要卖出的股票）
    """
    if not current_holdings:
        return []

    sell_list = []

    for stock in current_holdings:
        stock_params = params.get(stock, {})

        # 示例风控逻辑：EMA60线下穿时卖出
        if "system.ema_60" in stock_params and "system.close" in stock_params:
            ema_60 = stock_params["system.ema_60"]
            close_price = stock_params["system.close"]

            if close_price < ema_60:
                sell_list.append(stock)

    # 返回剔除卖出股票后的持仓列表
    return [stock for stock in current_holdings if stock not in sell_list]`,
        };

        // 调用API创建新策略
        const response = await axios.post(
          "http://localhost:5000/api/strategies",
          newStrategyData,
          {
            headers: {
              Authorization: `Bearer ${token}`,
              "Content-Type": "application/json",
            },
          }
        );

        if (response.data.code === 200) {
          ElMessage.success("新策略创建成功，正在跳转到编辑页面...");

          // 跳转到新创建的策略详情页面
          router.push({
            name: "StrategyDetail",
            params: {
              creatorName: userInfo.user_name,
              strategyName: newStrategyData.strategy_name,
            },
          });
        } else {
          throw new Error(response.data.message || "创建策略失败");
        }
      } catch (error) {
        console.error("创建策略失败:", error);
        ElMessage.error(
          error.response?.data?.message || "创建策略失败，请重试"
        );
      } finally {
        loading.value = false;
      }
    };

    // 删除策略
    const deleteStrategy = (strategy) => {
      ElMessageBox.confirm(
        `确定要删除策略"${strategy.strategy_name}"吗？`,
        "确认删除",
        {
          confirmButtonText: "确定",
          cancelButtonText: "取消",
          type: "warning",
        }
      )
        .then(async () => {
          try {
            loading.value = true;

            // 获取用户token
            const token = localStorage.getItem("token");
            if (!token) {
              ElMessage.error("请先登录");
              return;
            }

            // 调用删除API
            const response = await axios.delete(
              `http://localhost:5000/api/strategies/${strategy.creator_name}/${strategy.strategy_name}`,
              {
                headers: {
                  Authorization: `Bearer ${token}`,
                },
              }
            );

            if (response.data.code === 200) {
              ElMessage.success("策略删除成功");
              // 重新获取策略列表
              await fetchStrategies();
            } else {
              throw new Error(response.data.message || "删除策略失败");
            }
          } catch (error) {
            console.error("删除策略失败:", error);
            ElMessage.error(
              error.response?.data?.message || "删除策略失败，请重试"
            );
          } finally {
            loading.value = false;
          }
        })
        .catch(() => {
          // 用户取消删除
        });
    };

    // 复制策略
    const copyStrategy = async (strategy) => {
      try {
        loading.value = true;

        // 获取用户token
        const token = localStorage.getItem("token");
        if (!token) {
          ElMessage.error("请先登录");
          return;
        }

        // 获取用户信息
        const userInfo = getUserInfo();
        if (!userInfo) {
          ElMessage.error("请先登录");
          return;
        }

        // 创建复制的策略，使用原策略的数据
        const copiedStrategyData = {
          strategy_name: `复制_${strategy.strategy_name}_${Date.now()}`, // 使用时间戳确保唯一性
          public: false, // 复制的策略默认不公开
          scope_type: strategy.scope_type,
          scope_id: strategy.scope_id || "",
          position_count: strategy.position_count || 5,
          rebalance_interval: strategy.rebalance_interval || 5,
          buy_fee_rate: strategy.buy_fee_rate || 0.001,
          sell_fee_rate: strategy.sell_fee_rate || 0.001,
          strategy_desc: `复制自 ${strategy.strategy_name} - ${
            strategy.strategy_desc || ""
          }`,
          select_func:
            strategy.select_func ||
            `def select_func(candidates, params, position_count, current_holdings, date, context=None):
    """
    选股函数 - 根据策略逻辑选择要持有的股票

    参数说明:
    - candidates: 可选股票列表
    - params: 参数字典，包含各种技术指标和数据
    - position_count: 最大持仓股票数量
    - current_holdings: 当前持仓股票列表
    - date: 当前日期
    - context: 上下文对象，可用于存储状态信息

    返回值:
    - 选中的股票列表（最多position_count只）
    """
    # 示例：选择市值最小的position_count只股票
    if not candidates:
        return []

    # 获取股票市值数据
    market_values = []
    for stock in candidates:
        if f"system.total_mv" in params.get(stock, {}):
            mv = params[stock]["system.total_mv"]
            market_values.append((stock, mv))

    # 按市值从小到大排序，选择最小的position_count只
    market_values.sort(key=lambda x: x[1])
    selected = [stock for stock, _ in market_values[:position_count]]

    return selected`,
          risk_control_func:
            strategy.risk_control_func ||
            `def risk_control_func(current_holdings, params, date, context=None):
    """
    风险控制函数 - 对当前持仓进行风险控制

    参数说明:
    - current_holdings: 当前持仓股票列表
    - params: 参数字典，包含各种技术指标和数据
    - date: 当前日期
    - context: 上下文对象，可用于存储状态信息

    返回值:
    - 调整后的持仓股票列表（移除了需要卖出的股票）
    """
    if not current_holdings:
        return []

    sell_list = []

    for stock in current_holdings:
        stock_params = params.get(stock, {})

        # 示例风控逻辑：EMA60线下穿时卖出
        if "system.ema_60" in stock_params and "system.close" in stock_params:
            ema_60 = stock_params["system.ema_60"]
            close_price = stock_params["system.close"]

            if close_price < ema_60:
                sell_list.append(stock)

    # 返回剔除卖出股票后的持仓列表
    return [stock for stock in current_holdings if stock not in sell_list]`,
        };

        // 调用API创建复制的策略
        const response = await axios.post(
          "http://localhost:5000/api/strategies",
          copiedStrategyData,
          {
            headers: {
              Authorization: `Bearer ${token}`,
              "Content-Type": "application/json",
            },
          }
        );

        if (response.data.code === 200) {
          ElMessage.success("策略复制成功，正在跳转到编辑页面...");

          // 跳转到新复制的策略详情页面
          router.push({
            name: "StrategyDetail",
            params: {
              creatorName: userInfo.user_name,
              strategyName: copiedStrategyData.strategy_name,
            },
          });
        } else {
          throw new Error(response.data.message || "复制策略失败");
        }
      } catch (error) {
        console.error("复制策略失败:", error);
        ElMessage.error(
          error.response?.data?.message || "复制策略失败，请重试"
        );
      } finally {
        loading.value = false;
      }
    };

    // 分页处理
    const handleSizeChange = (newSize) => {
      pageSize.value = newSize;
      currentPage.value = 1;
      fetchStrategies();
    };

    const handleCurrentChange = (newCurrent) => {
      currentPage.value = newCurrent;
      fetchStrategies();
    };

    // 监听筛选条件变化
    watch([strategyType, scopeType], () => {
      currentPage.value = 1;
      fetchStrategies();
    });

    // 监听搜索关键词变化（防抖处理）
    let searchTimeout = null;
    watch(searchKeyword, () => {
      if (searchTimeout) {
        clearTimeout(searchTimeout);
      }
      searchTimeout = setTimeout(() => {
        currentPage.value = 1;
        fetchStrategies();
      }, 500);
    });

    onMounted(() => {
      fetchStrategies();
    });

    return {
      loading,
      strategies,
      searchKeyword,
      scopeType,
      strategyType,
      currentPage,
      pageSize,
      total,
      filteredStrategies,
      showScopeId,
      fetchStrategies,
      refreshStrategies,
      goToStrategyDetail,
      addNewStrategy,
      deleteStrategy,
      copyStrategy,
      handleSizeChange,
      handleCurrentChange,
      isCurrentUserCreator,
    };
  },
};
</script>

<style scoped>
.strategy-list-container {
  background-color: white;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.page-header h1 {
  margin: 0;
  color: #333;
  font-size: 20px;
  font-weight: 600;
}

.header-actions {
  display: flex;
  align-items: center;
}

.search-filter-area {
  display: flex;
  align-items: center;
  margin-bottom: 20px;
}

.search-input {
  width: 300px;
}

.table-container {
  flex: 1;
  overflow: hidden;
  margin-bottom: 20px;
}

.pagination-container {
  margin-top: auto;
  display: flex;
  justify-content: flex-end;
  padding-top: 20px;
  border-top: 1px solid #f0f0f0;
}
</style>
