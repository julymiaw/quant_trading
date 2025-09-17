<template>
  <div class="backtest-list-container">
    <!-- 页面标题和操作按钮 -->
    <div class="page-header">
      <h1>历史回测</h1>
      <div class="header-actions">
        <el-button type="primary" @click="refreshBacktests">
          <el-icon><Refresh /></el-icon>
          刷新
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
        v-model="timeRange"
        placeholder="时间范围"
        style="width: 120px; margin-left: 10px">
        <el-option label="全部" value="all" />
        <el-option label="一周内" value="week" />
        <el-option label="一月内" value="month" />
        <el-option label="三月内" value="quarter" />
      </el-select>
    </div>

    <!-- 回测列表表格 -->
    <div class="table-container">
      <el-table
        v-loading="loading"
        :data="filteredBacktests"
        style="width: 100%"
        border
        row-key="id"
        height="100%"
        :resizable="false">
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
        <el-table-column prop="creator_name" label="策略创建者" width="120" />
        <el-table-column prop="start_date" label="开始日期" width="140" />
        <el-table-column prop="end_date" label="结束日期" width="140" />
        <el-table-column prop="initial_fund" label="初始资金(元)" width="120">
          <template #default="scope">
            {{
              scope.row.initial_fund
                ? Number(scope.row.initial_fund).toLocaleString()
                : "-"
            }}
          </template>
        </el-table-column>

        <el-table-column
          prop="report_generate_time"
          label="完成时间"
          width="180">
          <template #default="scope">
            {{ formatStartTime(scope.row.report_generate_time) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="scope">
            <el-button
              type="primary"
              size="small"
              @click="viewBacktestReport(scope.row)">
              查看报告
            </el-button>
            <el-button
              type="danger"
              size="small"
              @click="deleteBacktestReport(scope.row)"
              style="margin-left: 8px">
              删除
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
import { ref, computed, onMounted } from "vue";
import { useRouter, useRoute } from "vue-router";
import { ElMessage, ElMessageBox } from "element-plus";
import { Search, Refresh } from "@element-plus/icons-vue";
import axios from "axios";

export default {
  name: "HistoricalBacktestList",
  components: {
    Search,
    Refresh,
  },
  setup() {
    const router = useRouter();
    const route = useRoute();
    const loading = ref(false);
    const backtests = ref([]);
    const searchKeyword = ref("");
    const timeRange = ref("all");
    const currentPage = ref(1);
    const pageSize = ref(10);
    const total = ref(0);

    // 获取用户信息
    const getUserInfo = () => {
      const storedUserInfo = localStorage.getItem("userInfo");
      return storedUserInfo ? JSON.parse(storedUserInfo) : null;
    };

    // 格式化发起时间
    const formatStartTime = (startTime) => {
      if (!startTime) return "-";

      // 假设startTime是日期时间字符串
      try {
        const date = new Date(startTime);
        return date.toLocaleString("zh-CN", {
          year: "numeric",
          month: "2-digit",
          day: "2-digit",
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
        });
      } catch (error) {
        return startTime;
      }
    };

    // 获取回测数据 - 从后端API获取真实数据
    const fetchBacktests = async () => {
      loading.value = true;
      try {
        const token = localStorage.getItem("token");
        if (!token) {
          ElMessage.error("请先登录");
          return;
        }

        // 构建查询参数
        const queryParams = new URLSearchParams({
          page: currentPage.value.toString(),
          page_size: pageSize.value.toString(),
        });

        const response = await axios.get(`/api/backtests?${queryParams}`, {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });

        if (response.data.code === 200) {
          backtests.value = (response.data.data.list || []).map(
            processBacktestData
          );
          total.value = response.data.data.total || 0;
        } else {
          backtests.value = [];
          total.value = 0;
          ElMessage.error(response.data.message || "获取回测数据失败");
        }
      } catch (error) {
        ElMessage.error("获取回测数据失败");
        console.error("获取回测数据失败:", error);
      } finally {
        loading.value = false;
      }
    };

    // 刷新回测数据
    const refreshBacktests = () => {
      currentPage.value = 1;
      fetchBacktests();
    };

    // 跳转到策略详情
    const goToStrategyDetail = (backtest) => {
      router.push(
        `/strategy/${backtest.creator_name}/${backtest.strategy_name}`
      );
    };

    // 处理回测数据的数值字段类型转换
    const processBacktestData = (data) => {
      if (!data) return data;

      // 确保数值字段是数字类型
      const numericFields = [
        "total_return",
        "annual_return",
        "max_drawdown",
        "sharpe_ratio",
        "win_rate",
        "profit_loss_ratio",
        "initial_fund",
        "final_fund",
        "trade_count",
      ];

      const processed = { ...data };
      numericFields.forEach((field) => {
        if (processed[field] !== null && processed[field] !== undefined) {
          const numValue = Number(processed[field]);
          // 如果转换结果是NaN，根据字段类型设置默认值
          if (isNaN(numValue)) {
            if (field === "initial_fund" || field === "final_fund") {
              processed[field] = 0;
            } else if (field === "trade_count") {
              processed[field] = 0;
            } else {
              processed[field] = 0; // 比率类型默认为0
            }
          } else {
            processed[field] = numValue;
          }
        }
      });

      return processed;
    };

    // 查看回测报告 - 跳转到专门的报告页面
    const viewBacktestReport = (backtest) => {
      let reportId;

      // 获取报告ID
      if (typeof backtest === "string") {
        reportId = backtest;
      } else {
        reportId = backtest.report_id;
      }

      if (!reportId) {
        ElMessage.error("无法获取报告ID");
        return;
      }

      // 跳转到专门的回测报告页面
      router.push({
        name: "BacktestReport",
        params: { reportId: reportId },
      });
    };

    // 处理来自消息通知的报告查看请求
    const handleRouteQuery = () => {
      if (route.query.open_report) {
        const reportId = route.query.open_report;

        // 延迟一段时间确保页面已加载
        setTimeout(() => {
          viewBacktestReport(reportId);
          // 清除路由参数避免重复触发
          router.replace({ name: "HistoricalBacktestList" });
        }, 500);
      }
    };

    // 删除回测报告
    const deleteBacktestReport = async (backtest) => {
      try {
        const confirmResult = await ElMessageBox.confirm(
          `确定要删除回测报告 "${backtest.strategy_name}" 吗？此操作不可撤销。`,
          "删除确认",
          {
            confirmButtonText: "确定删除",
            cancelButtonText: "取消",
            type: "warning",
            confirmButtonClass: "el-button--danger",
          }
        );

        if (confirmResult === "confirm") {
          const token = localStorage.getItem("token");
          if (!token) {
            ElMessage.error("请先登录");
            return;
          }

          const response = await axios.delete(
            `/api/backtest/report/${backtest.report_id}`,
            {
              headers: {
                Authorization: `Bearer ${token}`,
              },
            }
          );

          if (response.data.code === 200) {
            ElMessage.success("回测报告删除成功");
            // 刷新列表
            fetchBacktests();
          } else {
            ElMessage.error(response.data.message || "删除失败");
          }
        }
      } catch (error) {
        if (error === "cancel") {
          // 用户取消删除，不显示错误信息
          return;
        }
        console.error("删除回测报告失败:", error);
        ElMessage.error("删除回测报告失败");
      }
    };

    // 分页处理
    const handleSizeChange = (size) => {
      pageSize.value = size;
      fetchBacktests();
    };

    const handleCurrentChange = (current) => {
      currentPage.value = current;
      fetchBacktests();
    };

    // 计算筛选后的回测列表
    const filteredBacktests = computed(() => {
      let filtered = [...backtests.value];

      // 根据搜索关键词筛选策略名称（部分匹配）
      if (searchKeyword.value.trim()) {
        const keyword = searchKeyword.value.toLowerCase().trim();
        filtered = filtered.filter((item) =>
          item.strategy_name.toLowerCase().includes(keyword)
        );
      }

      // 根据时间范围筛选发起时间
      if (timeRange.value && timeRange.value !== "all") {
        const now = new Date();
        let startDate = new Date();

        switch (timeRange.value) {
          case "week":
            // 一周内
            startDate.setDate(now.getDate() - 7);
            break;
          case "month":
            // 一月内
            startDate.setMonth(now.getMonth() - 1);
            break;
          case "quarter":
            // 三月内
            startDate.setMonth(now.getMonth() - 3);
            break;
          default:
            break;
        }

        filtered = filtered.filter((item) => {
          if (!item.report_generate_time) return false;
          const itemDate = new Date(item.report_generate_time);
          return itemDate >= startDate && itemDate <= now;
        });
      }

      // 更新总条数
      total.value = filtered.length;

      // 分页处理
      const startIndex = (currentPage.value - 1) * pageSize.value;
      const endIndex = startIndex + pageSize.value;
      return filtered.slice(startIndex, endIndex);
    });

    onMounted(() => {
      fetchBacktests();
      handleRouteQuery(); // 处理路由参数
    });

    return {
      loading,
      backtests,
      searchKeyword,
      timeRange,
      currentPage,
      pageSize,
      total,
      filteredBacktests,
      formatStartTime,
      fetchBacktests,
      refreshBacktests,
      goToStrategyDetail,
      viewBacktestReport,
      deleteBacktestReport,
      handleSizeChange,
      handleCurrentChange,
    };
  },
};
</script>

<style scoped>
.backtest-list-container {
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background-color: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
  padding: 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.page-header h1 {
  margin: 0;
  font-size: 24px;
  color: #333;
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
