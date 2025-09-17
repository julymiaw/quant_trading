<template>
  <div class="backtest-report-container">
    <!-- 页面头部 -->
    <div class="report-header">
      <div class="header-content">
        <div class="header-left">
          <h1 class="report-title">
            {{ reportData?.strategy_name || "回测报告" }}
          </h1>
          <div class="report-meta">
            <span class="meta-item"
              >策略创建者：{{ reportData?.creator_name }}</span
            >
            <span class="meta-item"
              >回测时间：{{ reportData?.start_date }} 至
              {{ reportData?.end_date }}</span
            >
            <span class="meta-item"
              >报告生成：{{
                formatTime(reportData?.report_generate_time)
              }}</span
            >
          </div>
        </div>
        <div class="header-actions">
          <el-button @click="goBack">
            <el-icon><ArrowLeft /></el-icon>
            返回列表
          </el-button>
          <el-button type="danger" @click="deleteReport">
            <el-icon><Delete /></el-icon>
            删除报告
          </el-button>
        </div>
      </div>
    </div>

    <!-- 加载状态 -->
    <div v-if="loading" class="loading-container">
      <el-skeleton :rows="8" animated />
    </div>

    <!-- 报告内容 -->
    <div v-else-if="reportData" class="report-content">
      <!-- 收益概述 -->
      <div class="dailybars-results active" id="tab-summaryinfo">
        <div class="title">收益概述</div>
        <div class="top-level-stats-container">
          <!-- 第一行统计 -->
          <div class="data-group">
            <div class="top-level-stat">
              <div class="stat-label">总收益率</div>
              <div
                :class="[
                  'stat-value',
                  getReturnClass(reportData.total_return),
                ]">
                {{ formatPercent(reportData.total_return) }}
              </div>
            </div>
            <div class="top-level-stat">
              <div class="stat-label">年化收益率</div>
              <div
                :class="[
                  'stat-value',
                  getReturnClass(reportData.annual_return),
                ]">
                {{ formatPercent(reportData.annual_return) }}
              </div>
            </div>
            <div class="top-level-stat">
              <div class="stat-label">最大回撤</div>
              <div class="stat-value negative">
                {{ formatPercent(reportData.max_drawdown) }}
              </div>
            </div>
            <div class="top-level-stat">
              <div class="stat-label">夏普比率</div>
              <div class="stat-value">
                {{ formatNumber(reportData.sharpe_ratio, 4) }}
              </div>
            </div>
            <div class="top-level-stat">
              <div class="stat-label">胜率</div>
              <div
                :class="['stat-value', getWinRateClass(reportData.win_rate)]">
                {{ formatPercent(reportData.win_rate) }}
              </div>
            </div>
          </div>

          <!-- 第二行统计 -->
          <div class="data-group">
            <div class="top-level-stat">
              <div class="stat-label">初始资金</div>
              <div class="stat-value">
                {{ formatCurrency(reportData.initial_fund) }}
              </div>
            </div>
            <div class="top-level-stat">
              <div class="stat-label">最终资金</div>
              <div
                :class="[
                  'stat-value',
                  getFinalFundClass(
                    reportData.initial_fund,
                    reportData.final_fund
                  ),
                ]">
                {{ formatCurrency(reportData.final_fund) }}
              </div>
            </div>
            <div class="top-level-stat">
              <div class="stat-label">交易次数</div>
              <div class="stat-value">
                {{ reportData.trade_count || 0 }}
              </div>
            </div>
            <div class="top-level-stat">
              <div class="stat-label">盈亏比</div>
              <div class="stat-value">
                {{ formatNumber(reportData.profit_loss_ratio, 3) }}
              </div>
            </div>
            <div class="top-level-stat">
              <div class="stat-label">报告状态</div>
              <div class="stat-value">
                <el-tag
                  :type="
                    reportData.report_status === 'completed'
                      ? 'success'
                      : 'warning'
                  "
                  size="small">
                  {{
                    reportData.report_status === "completed"
                      ? "已完成"
                      : "处理中"
                  }}
                </el-tag>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 聚宽风格的三张图表 -->
      <div class="charts-section">
        <!-- 收益图表 -->
        <div class="chart-section">
          <div class="chart-header">
            <h3>收益</h3>
            <div class="chart-legend">
              <span class="legend-item strategy">
                <span class="legend-color strategy-color"></span>
                策略收益
              </span>
              <span class="legend-item benchmark">
                <span class="legend-color benchmark-color"></span>
                {{ reportData?.benchmark_name || "沪深300" }}
              </span>
              <span class="legend-item excess">
                <span class="legend-color excess-color"></span>
                超额收益
              </span>
            </div>
          </div>
          <div class="chart-container">
            <div
              v-if="reportData?.plotly_chart_data?.returns_chart"
              id="returns-chart"
              class="plotly-chart"></div>
            <div v-else class="no-chart-placeholder">
              <el-icon size="48"><PictureRounded /></el-icon>
              <p>暂无收益图表数据</p>
            </div>
          </div>
        </div>

        <!-- 每日盈亏图表 -->
        <div class="chart-section">
          <div class="chart-header">
            <h3>每日盈亏</h3>
            <div class="chart-legend">
              <span class="legend-item profit">
                <span class="legend-color profit-color"></span>
                当日盈利
              </span>
              <span class="legend-item loss">
                <span class="legend-color loss-color"></span>
                当日亏损
              </span>
            </div>
          </div>
          <div class="chart-container">
            <div
              v-if="reportData?.plotly_chart_data?.daily_pnl_chart"
              id="daily-pnl-chart"
              class="plotly-chart"></div>
            <div v-else class="no-chart-placeholder">
              <el-icon size="48"><PictureRounded /></el-icon>
              <p>暂无盈亏图表数据</p>
            </div>
          </div>
        </div>

        <!-- 每日买卖图表 -->
        <div class="chart-section">
          <div class="chart-header">
            <h3>每日买卖</h3>
            <div class="chart-legend">
              <span class="legend-item open">
                <span class="legend-color open-color"></span>
                当日开仓
              </span>
              <span class="legend-item close">
                <span class="legend-color close-color"></span>
                当日平仓
              </span>
            </div>
          </div>
          <div class="chart-container">
            <div
              v-if="reportData?.plotly_chart_data?.daily_trades_chart"
              id="daily-trades-chart"
              class="plotly-chart"></div>
            <div v-else class="no-chart-placeholder">
              <el-icon size="48"><PictureRounded /></el-icon>
              <p>暂无交易图表数据</p>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 错误状态 -->
    <div v-else class="error-container">
      <el-result icon="error" title="加载失败" sub-title="无法加载回测报告数据">
        <template #extra>
          <el-button type="primary" @click="loadReport">重新加载</el-button>
          <el-button @click="goBack">返回列表</el-button>
        </template>
      </el-result>
    </div>
  </div>
</template>

<script>
import { ref, onMounted, nextTick } from "vue";
import { useRouter, useRoute } from "vue-router";
import { ElMessage, ElMessageBox } from "element-plus";
import { ArrowLeft, Delete, PictureRounded } from "@element-plus/icons-vue";
import axios from "axios";

// 动态导入Plotly
let Plotly = null;
const loadPlotly = async () => {
  if (!Plotly) {
    try {
      Plotly = await import("plotly.js-dist");
    } catch (error) {
      console.error("Plotly库加载失败:", error);
      return null;
    }
  }
  return Plotly;
};

export default {
  name: "BacktestReport",
  components: {
    ArrowLeft,
    Delete,
    PictureRounded,
  },
  setup() {
    const router = useRouter();
    const route = useRoute();
    const loading = ref(true);
    const reportData = ref(null);

    // 获取报告数据
    const loadReport = async () => {
      try {
        loading.value = true;
        const reportId = route.params.reportId;

        if (!reportId) {
          ElMessage.error("缺少报告ID");
          goBack();
          return;
        }

        const token = localStorage.getItem("token");
        if (!token) {
          ElMessage.error("请先登录");
          router.push("/login");
          return;
        }

        const response = await axios.get(`/api/backtest/report/${reportId}`, {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });

        if (response.data.success) {
          reportData.value = response.data.data;

          // 渲染图表 - 等待DOM更新完成
          if (reportData.value?.plotly_chart_data) {
            // 使用setTimeout确保DOM完全更新
            setTimeout(async () => {
              await renderChart();
            }, 100);
          }
        } else {
          ElMessage.error("获取报告数据失败");
        }
      } catch (error) {
        console.error("加载报告失败:", error);
        ElMessage.error("加载报告失败");
      } finally {
        loading.value = false;
      }
    };

    // 渲染Plotly图表
    const renderChart = async () => {
      const PlotlyLib = await loadPlotly();

      if (!PlotlyLib || !reportData.value?.plotly_chart_data) {
        return;
      }

      const chartData = reportData.value.plotly_chart_data;

      // 通用的图表配置
      const commonConfig = {
        responsive: true,
        displayModeBar: true,
        modeBarButtonsToRemove: ["pan2d", "lasso2d", "autoScale2d", "select2d"],
        displaylogo: false,
      };

      const commonLayoutUpdate = {
        paper_bgcolor: "rgba(0,0,0,0)",
        plot_bgcolor: "rgba(0,0,0,0)",
        font: {
          family:
            '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
          size: 12,
          color: "#333",
        },
        margin: { t: 40, r: 40, b: 40, l: 80 },
      };

      // 渲染收益图表
      if (chartData.returns_chart) {
        const returnsDiv = await waitForElement("returns-chart");
        if (returnsDiv) {
          try {
            await PlotlyLib.newPlot(
              returnsDiv,
              chartData.returns_chart.data,
              {
                ...chartData.returns_chart.layout,
                ...commonLayoutUpdate,
              },
              commonConfig
            );
          } catch (error) {
            console.error("渲染收益图表失败:", error);
          }
        }
      }

      // 渲染每日盈亏图表
      if (chartData.daily_pnl_chart) {
        const pnlDiv = await waitForElement("daily-pnl-chart");
        if (pnlDiv) {
          try {
            await PlotlyLib.newPlot(
              pnlDiv,
              chartData.daily_pnl_chart.data,
              {
                ...chartData.daily_pnl_chart.layout,
                ...commonLayoutUpdate,
              },
              commonConfig
            );
          } catch (error) {
            console.error("渲染盈亏图表失败:", error);
          }
        }
      }

      // 渲染每日买卖图表
      if (chartData.daily_trades_chart) {
        const tradesDiv = await waitForElement("daily-trades-chart");
        if (tradesDiv) {
          try {
            await PlotlyLib.newPlot(
              tradesDiv,
              chartData.daily_trades_chart.data,
              {
                ...chartData.daily_trades_chart.layout,
                ...commonLayoutUpdate,
              },
              commonConfig
            );
          } catch (error) {
            console.error("渲染交易图表失败:", error);
          }
        }
      }
    };

    // 等待DOM元素准备就绪的辅助函数
    const waitForElement = async (elementId, maxAttempts = 30) => {
      let element = null;
      let attempts = 0;

      while (!element && attempts < maxAttempts) {
        element = document.getElementById(elementId);
        if (!element) {
          await new Promise((resolve) => setTimeout(resolve, 100));
          attempts++;
        }
      }

      return element;
    };

    // 格式化函数
    const formatPercent = (value) => {
      if (value === null || value === undefined) return "--";
      return `${(value * 100).toFixed(2)}%`;
    };

    const formatNumber = (value, decimals = 2) => {
      if (value === null || value === undefined) return "--";
      return Number(value).toFixed(decimals);
    };

    const formatCurrency = (value) => {
      if (value === null || value === undefined) return "--";
      return `¥${Number(value).toLocaleString()}`;
    };

    const formatTime = (time) => {
      if (!time) return "--";
      return new Date(time).toLocaleString("zh-CN");
    };

    // 样式类函数
    const getReturnClass = (value) => {
      if (value > 0) return "positive";
      if (value < 0) return "negative";
      return "";
    };

    const getWinRateClass = (value) => {
      if (value >= 0.5) return "positive";
      return "negative";
    };

    const getFinalFundClass = (initial, final) => {
      if (final > initial) return "positive";
      if (final < initial) return "negative";
      return "";
    };

    // 操作函数
    const goBack = () => {
      router.push("/backtest");
    };

    const deleteReport = async () => {
      try {
        await ElMessageBox.confirm(
          `确定要删除回测报告 "${reportData.value?.strategy_name}" 吗？此操作不可撤销。`,
          "删除确认",
          {
            confirmButtonText: "确定删除",
            cancelButtonText: "取消",
            type: "warning",
            confirmButtonClass: "el-button--danger",
          }
        );

        const token = localStorage.getItem("token");
        const response = await axios.delete(
          `/api/backtest/report/${route.params.reportId}`,
          {
            headers: {
              Authorization: `Bearer ${token}`,
            },
          }
        );

        if (response.data.code === 200) {
          ElMessage.success("回测报告删除成功");
          goBack();
        } else {
          ElMessage.error(response.data.message || "删除失败");
        }
      } catch (error) {
        if (error === "cancel") return;
        console.error("删除回测报告失败:", error);
        ElMessage.error("删除回测报告失败");
      }
    };

    onMounted(() => {
      loadReport();
    });

    return {
      loading,
      reportData,
      loadReport,
      goBack,
      deleteReport,
      formatPercent,
      formatNumber,
      formatCurrency,
      formatTime,
      getReturnClass,
      getWinRateClass,
      getFinalFundClass,
    };
  },
};
</script>

<style scoped>
.backtest-report-container {
  min-height: 100vh;
  background-color: #f5f7fa;
}

.report-header {
  background: white;
  border-bottom: 1px solid #e4e7ed;
  padding: 20px 0;
}

.header-content {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.report-title {
  margin: 0 0 8px 0;
  font-size: 24px;
  font-weight: 600;
  color: #303133;
}

.report-meta {
  display: flex;
  gap: 24px;
  font-size: 14px;
  color: #606266;
}

.meta-item {
  display: flex;
  align-items: center;
}

.header-actions {
  display: flex;
  gap: 12px;
}

.loading-container,
.error-container {
  max-width: 1200px;
  margin: 40px auto;
  padding: 0 20px;
}

.report-content {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
}

/* 参考聚宽样式 */
.dailybars-results {
  background: white;
  border-radius: 8px;
  margin-bottom: 24px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.title {
  font-size: 18px;
  font-weight: 600;
  color: #303133;
  padding: 20px 24px 16px 24px;
  border-bottom: 1px solid #f0f0f0;
}

.top-level-stats-container {
  padding: 24px;
}

.data-group {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 24px;
  margin-bottom: 24px;
}

.data-group:last-child {
  margin-bottom: 0;
}

.top-level-stat {
  text-align: center;
  padding: 16px;
  background: #fafafa;
  border-radius: 6px;
  border: 1px solid #f0f0f0;
}

.stat-label {
  font-size: 14px;
  color: #606266;
  margin-bottom: 8px;
  font-weight: 500;
}

.stat-value {
  font-size: 20px;
  font-weight: 600;
  color: #303133;
}

.stat-value.positive {
  color: #67c23a;
}

.stat-value.negative {
  color: #f56c6c;
}

.charts-section {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.chart-section {
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  overflow: hidden;
}

.chart-header {
  padding: 16px 20px;
  border-bottom: 1px solid #f0f0f0;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.chart-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.chart-legend {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
}

.legend-item {
  display: flex;
  align-items: center;
  font-size: 13px;
  color: #606266;
}

.legend-color {
  width: 10px;
  height: 10px;
  border-radius: 2px;
  margin-right: 6px;
}

/* 图例颜色配置 */
.strategy-color {
  background: #4572a7;
}

.benchmark-color {
  background: #aa4643;
}

.excess-color {
  background: #89a54e;
}

.profit-color {
  background: #89a54e;
}

.loss-color {
  background: #80699b;
}

.open-color {
  background: #18a5ca;
}

.close-color {
  background: #db843d;
}

.chart-container {
  padding: 16px 20px 20px 20px;
}

.plotly-chart {
  width: 100%;
  height: 300px;
}

.no-chart-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 250px;
  color: #999;
  background: #fafafa;
  border-radius: 8px;
}

.no-chart-placeholder p {
  margin: 12px 0 0 0;
  font-size: 14px;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .header-content {
    flex-direction: column;
    align-items: flex-start;
    gap: 16px;
  }

  .report-meta {
    flex-direction: column;
    gap: 8px;
  }

  .data-group {
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: 16px;
  }

  .chart-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }
}
</style>
