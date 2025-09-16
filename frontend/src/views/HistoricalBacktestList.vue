<template>
  <div class="backtest-list-container">
    <!-- 页面标题和操作按钮 -->
    <div class="page-header">
      <h1>历史回测</h1>
      <div class="header-actions">
        <el-select
          v-model="backtestType"
          placeholder="选择回测类型"
          style="width: 150px; margin-right: 10px">
          <el-option label="我的回测" value="my" />
          <el-option label="全部回测" value="all" />
        </el-select>
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
        <el-table-column
          prop="initial_capital"
          label="初始资金(元)"
          width="120">
          <template #default="scope">
            {{
              scope.row.initial_capital
                ? Number(scope.row.initial_capital).toLocaleString()
                : "-"
            }}
          </template>
        </el-table-column>
        <el-table-column prop="commission_rate" label="佣金费率" width="100">
          <template #default="scope">
            {{
              scope.row.commission_rate ? `${scope.row.commission_rate}%` : "-"
            }}
          </template>
        </el-table-column>
        <el-table-column prop="slippage_rate" label="滑点率" width="100">
          <template #default="scope">
            {{ scope.row.slippage_rate ? `${scope.row.slippage_rate}%` : "-" }}
          </template>
        </el-table-column>
        <el-table-column prop="run_time" label="发起时间" width="180">
          <template #default="scope">
            {{ formatStartTime(scope.row.run_time) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="scope">
            <el-button
              type="primary"
              size="small"
              @click="viewBacktestReport(scope.row)">
              查看报告
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

    <!-- 回测报告弹窗 -->
    <el-dialog
      title="回测报告"
      v-model="reportDialogVisible"
      width="90%"
      height="90vh"
      append-to-body
      :before-close="handleReportDialogClose">
      <div class="backtest-report-content">
        <div v-if="selectedBacktest" class="report-header">
          <h3>{{ selectedBacktest.strategy_name }} - 回测报告</h3>
          <div class="report-meta">
            <span>策略创建者：{{ selectedBacktest.creator_name }}</span>
            <span
              >时间范围：{{ selectedBacktest.start_date }} 至
              {{ selectedBacktest.end_date }}</span
            >
            <span
              >初始资金：{{
                Number(selectedBacktest.initial_capital).toLocaleString()
              }}元</span
            >
            <span>佣金费率：{{ selectedBacktest.commission_rate }}%</span>
            <span>滑点率：{{ selectedBacktest.slippage_rate }}%</span>
          </div>
        </div>
        <div class="report-charts">
          <!-- 显示真实的回测图表 -->
          <div class="chart-container">
            <h4>回测净值曲线</h4>
            <div class="chart">
              <!-- 如果有matplotlib图表数据，显示base64图片 -->
              <img
                v-if="selectedBacktest?.chart_data"
                :src="selectedBacktest.chart_data"
                alt="回测净值曲线"
                style="width: 100%; height: 100%; object-fit: contain" />
              <!-- 如果有plotly图表数据，显示交互式图表 -->
              <div
                v-else-if="selectedBacktest?.plotly_chart_data"
                id="plotly-chart"
                style="width: 100%; height: 500px"></div>
              <!-- 没有图表数据时的占位符 -->
              <div v-else class="no-chart-placeholder">
                <el-icon size="48"><PictureRounded /></el-icon>
                <p>暂无图表数据</p>
              </div>
            </div>
          </div>
          <div class="chart-container">
            <h4>回测结果统计</h4>
            <div class="stats-grid">
              <div class="stat-item">
                <span class="stat-label">总收益率</span>
                <span
                  :class="[
                    'stat-value',
                    selectedBacktest?.total_return >= 0
                      ? 'positive'
                      : 'negative',
                  ]">
                  {{
                    selectedBacktest?.total_return
                      ? (selectedBacktest.total_return * 100).toFixed(2) + "%"
                      : "--"
                  }}
                </span>
              </div>
              <div class="stat-item">
                <span class="stat-label">年化收益率</span>
                <span
                  :class="[
                    'stat-value',
                    selectedBacktest?.annual_return >= 0
                      ? 'positive'
                      : 'negative',
                  ]">
                  {{
                    selectedBacktest?.annual_return
                      ? (selectedBacktest.annual_return * 100).toFixed(2) + "%"
                      : "--"
                  }}
                </span>
              </div>
              <div class="stat-item">
                <span class="stat-label">最大回撤</span>
                <span class="stat-value negative">
                  {{
                    selectedBacktest?.max_drawdown
                      ? (selectedBacktest.max_drawdown * 100).toFixed(2) + "%"
                      : "--"
                  }}
                </span>
              </div>
              <div class="stat-item">
                <span class="stat-label">Sharpe比率</span>
                <span class="stat-value">
                  {{
                    selectedBacktest?.sharpe_ratio
                      ? selectedBacktest.sharpe_ratio.toFixed(4)
                      : "--"
                  }}
                </span>
              </div>
              <div class="stat-item">
                <span class="stat-label">胜率</span>
                <span
                  :class="[
                    'stat-value',
                    selectedBacktest?.win_rate >= 0.5 ? 'positive' : 'negative',
                  ]">
                  {{
                    selectedBacktest?.win_rate
                      ? (selectedBacktest.win_rate * 100).toFixed(1) + "%"
                      : "--"
                  }}
                </span>
              </div>
              <div class="stat-item">
                <span class="stat-label">交易次数</span>
                <span class="stat-value">
                  {{ selectedBacktest?.trade_count || "--" }}
                </span>
              </div>
              <div class="stat-item">
                <span class="stat-label">初始资金</span>
                <span class="stat-value">
                  {{
                    selectedBacktest?.initial_fund
                      ? Number(selectedBacktest.initial_fund).toLocaleString() +
                        "元"
                      : "--"
                  }}
                </span>
              </div>
              <div class="stat-item">
                <span class="stat-label">最终资金</span>
                <span
                  :class="[
                    'stat-value',
                    (selectedBacktest?.final_fund || 0) >=
                    (selectedBacktest?.initial_fund || 0)
                      ? 'positive'
                      : 'negative',
                  ]">
                  {{
                    selectedBacktest?.final_fund
                      ? Number(selectedBacktest.final_fund).toLocaleString() +
                        "元"
                      : "--"
                  }}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script>
import { ref, reactive, computed, onMounted, watch, nextTick } from "vue";
import { useRouter, useRoute } from "vue-router";
import { ElMessage } from "element-plus";
import { Search, Refresh, PictureRounded } from "@element-plus/icons-vue";
import axios from "axios";

// 动态导入Plotly用于渲染交互式图表
let Plotly = null;
const loadPlotly = async () => {
  if (!Plotly) {
    try {
      Plotly = await import("plotly.js-dist");
    } catch (error) {
      console.warn("Plotly未安装，将无法显示交互式图表");
    }
  }
  return Plotly;
};

export default {
  name: "HistoricalBacktestList",
  components: {
    Search,
    Refresh,
    PictureRounded,
  },
  setup() {
    const router = useRouter();
    const route = useRoute();
    const loading = ref(false);
    const backtests = ref([]);
    const searchKeyword = ref("");
    const timeRange = ref("all");
    const backtestType = ref("my");
    const currentPage = ref(1);
    const pageSize = ref(10);
    const total = ref(0);
    const reportDialogVisible = ref(false);
    const selectedBacktest = ref(null);

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
          backtests.value = response.data.data.list || [];
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

    // 从API获取回测报告详情
    const fetchBacktestReport = async (reportId) => {
      try {
        const token = localStorage.getItem("token");
        if (!token) {
          ElMessage.error("请先登录");
          return null;
        }

        const response = await axios.get(`/api/backtest/report/${reportId}`, {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });

        if (response.data.success) {
          return response.data.data;
        } else {
          ElMessage.error("获取回测报告失败");
          return null;
        }
      } catch (error) {
        console.error("获取回测报告失败:", error);
        ElMessage.error("获取回测报告失败");
        return null;
      }
    };

    // 渲染Plotly图表
    const renderPlotlyChart = async (chartData) => {
      const PlotlyLib = await loadPlotly();
      if (!PlotlyLib || !chartData) return;

      const chartDiv = document.getElementById("plotly-chart");
      if (!chartDiv) return;

      try {
        await PlotlyLib.newPlot(chartDiv, chartData.data, chartData.layout, {
          responsive: true,
          displayModeBar: true,
          modeBarButtonsToRemove: [
            "pan2d",
            "lasso2d",
            "autoScale2d",
            "select2d",
          ],
          displaylogo: false,
        });
      } catch (error) {
        console.error("渲染Plotly图表失败:", error);
      }
    };

    // 查看回测报告
    const viewBacktestReport = async (backtest) => {
      // 如果传入的是 report_id 字符串，先获取完整报告数据
      if (typeof backtest === "string") {
        const reportData = await fetchBacktestReport(backtest);
        if (reportData) {
          selectedBacktest.value = reportData;
          reportDialogVisible.value = true;
        }
      } else {
        // 如果传入的是完整的backtest对象
        selectedBacktest.value = backtest;
        reportDialogVisible.value = true;
      }

      // 等待弹窗渲染完成后，初始化图表
      await nextTick();

      // 如果有plotly图表数据，渲染交互式图表
      if (selectedBacktest.value?.plotly_chart_data) {
        await renderPlotlyChart(selectedBacktest.value.plotly_chart_data);
      }
    };

    // 处理来自消息通知的报告查看请求
    const handleRouteQuery = async () => {
      if (route.query.open_report) {
        const reportId = route.query.open_report;
        const strategyName = route.query.strategy_name;

        // 延迟一段时间确保页面已加载
        setTimeout(async () => {
          await viewBacktestReport(reportId);
          // 清除路由参数避免重复触发
          router.replace({ name: "HistoricalBacktestList" });
        }, 500);
      }
    };

    // 处理报告弹窗关闭
    const handleReportDialogClose = async () => {
      // 销毁Plotly图表实例
      const chartDiv = document.getElementById("plotly-chart");
      if (chartDiv && Plotly) {
        try {
          await Plotly.purge(chartDiv);
        } catch (error) {
          console.warn("销毁图表失败:", error);
        }
      }

      reportDialogVisible.value = false;
      selectedBacktest.value = null;
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
          if (!item.run_time) return false;
          const itemDate = new Date(item.run_time);
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
      backtestType,
      currentPage,
      pageSize,
      total,
      reportDialogVisible,
      selectedBacktest,
      filteredBacktests,
      formatStartTime,
      fetchBacktests,
      refreshBacktests,
      goToStrategyDetail,
      viewBacktestReport,
      handleReportDialogClose,
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

/* 回测报告弹窗样式 */
.backtest-report-content {
  height: calc(90vh - 120px);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.report-header {
  margin-bottom: 20px;
  padding-bottom: 15px;
  border-bottom: 1px solid #e6e6e6;
}

.report-header h3 {
  margin: 0 0 10px 0;
  font-size: 18px;
  color: #333;
}

.report-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 15px;
  font-size: 14px;
  color: #666;
}

.report-charts {
  flex: 1;
  overflow-y: auto;
}

.chart-container {
  margin-bottom: 30px;
}

.chart-container h4 {
  margin: 0 0 15px 0;
  font-size: 16px;
  color: #333;
}

.chart {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 20px;
}

.stat-item {
  background-color: #f8f9fa;
  padding: 20px;
  border-radius: 8px;
  text-align: center;
}

.stat-label {
  display: block;
  font-size: 14px;
  color: #666;
  margin-bottom: 8px;
}

.stat-value {
  display: block;
  font-size: 24px;
  font-weight: 600;
  color: #333;
}

.stat-value.positive {
  color: #10b981;
}

.stat-value.negative {
  color: #ef4444;
}

.no-chart-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 300px;
  color: #999;
  background-color: #f8f9fa;
  border-radius: 8px;
}

.no-chart-placeholder p {
  margin: 10px 0 0 0;
  font-size: 14px;
}
</style>
