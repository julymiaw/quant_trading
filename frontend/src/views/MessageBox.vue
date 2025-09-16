<template>
  <div class="message-box-container">
    <!-- 页面标题和操作按钮 -->
    <div class="page-header">
      <h1>消息箱</h1>
      <div class="header-actions">
        <el-select
          v-model="messageType"
          placeholder="选择消息类型"
          style="width: 150px; margin-right: 10px">
          <el-option label="全部消息" value="all" />
          <el-option label="回测完成" value="backtest_complete" />
          <el-option label="数据准备完成" value="backtest_data_ready" />
          <el-option label="系统通知" value="system_notice" />
          <el-option label="错误提醒" value="error_alert" />
        </el-select>
        <el-select
          v-model="statusFilter"
          placeholder="消息状态"
          style="width: 120px; margin-right: 10px">
          <el-option label="全部" value="all" />
          <el-option label="未读" value="unread" />
          <el-option label="已读" value="read" />
        </el-select>
        <el-button type="primary" @click="refreshMessages">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
      </div>
    </div>

    <!-- 消息列表表格 -->
    <div class="table-container">
      <el-table
        v-loading="loading"
        :data="messages"
        style="width: 100%"
        border
        row-key="message_id"
        height="100%"
        :resizable="false">
        <el-table-column prop="message_type" label="消息类型" width="120">
          <template #default="scope">
            <el-tag :type="getMessageTypeColor(scope.row.message_type)">
              {{ getMessageTypeName(scope.row.message_type) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="title" label="消息标题" min-width="200">
          <template #default="scope">
            <div
              class="message-title"
              :class="{ 'unread-title': scope.row.status === 'unread' }"
              @click="openMessageDetail(scope.row)">
              {{ scope.row.title }}
            </div>
          </template>
        </el-table-column>
        <el-table-column
          prop="content_preview"
          label="消息摘要"
          min-width="300" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="scope">
            <el-tag
              :type="scope.row.status === 'unread' ? 'warning' : 'success'">
              {{ scope.row.status === "unread" ? "未读" : "已读" }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="接收时间" width="160">
          <template #default="scope">
            {{ formatDateTime(scope.row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="scope">
            <el-button
              type="primary"
              size="small"
              @click="openMessageDetail(scope.row)">
              查看详情
            </el-button>
            <el-button
              type="warning"
              size="small"
              @click="markAsRead(scope.row)"
              v-if="scope.row.status === 'unread'">
              标记已读
            </el-button>
            <el-button
              type="danger"
              size="small"
              @click="deleteMessage(scope.row)">
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

    <!-- 消息详情弹窗 -->
    <el-dialog
      v-model="messageDetailVisible"
      :title="selectedMessage?.title || '消息详情'"
      width="600px"
      :before-close="handleMessageDetailClose">
      <div v-if="selectedMessage" class="message-detail">
        <el-descriptions :column="1" border>
          <el-descriptions-item label="消息类型">
            <el-tag :type="getMessageTypeColor(selectedMessage.message_type)">
              {{ getMessageTypeName(selectedMessage.message_type) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="消息状态">
            <el-tag
              :type="
                selectedMessage.status === 'unread' ? 'warning' : 'success'
              ">
              {{ selectedMessage.status === "unread" ? "未读" : "已读" }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="接收时间">
            {{ formatDateTime(selectedMessage.created_at) }}
          </el-descriptions-item>
          <el-descriptions-item label="阅读时间" v-if="selectedMessage.read_at">
            {{ formatDateTime(selectedMessage.read_at) }}
          </el-descriptions-item>
        </el-descriptions>

        <div class="message-content">
          <h4>消息内容：</h4>
          <p>{{ selectedMessage.content }}</p>
        </div>

        <!-- 如果有链接，显示操作按钮 -->
        <div class="message-actions" v-if="selectedMessage.link_url">
          <el-button type="primary" @click="handleMessageLink(selectedMessage)">
            <el-icon><Link /></el-icon>
            {{ getActionButtonText(selectedMessage.message_type) }}
          </el-button>
        </div>
      </div>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="messageDetailVisible = false">关闭</el-button>
          <el-button
            type="warning"
            @click="markAsReadInDetail"
            v-if="selectedMessage?.status === 'unread'">
            标记已读
          </el-button>
          <el-button type="danger" @click="deleteMessageInDetail">
            删除消息
          </el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import { ref, reactive, computed, onMounted, watch } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { Refresh, Link } from "@element-plus/icons-vue";
import { useRouter, useRoute } from "vue-router";
import axios from "axios";

export default {
  name: "MessageBox",
  components: {
    Refresh,
    Link,
  },
  setup() {
    const router = useRouter();
    const route = useRoute();
    const loading = ref(false);
    const messages = ref([]);
    const messageType = ref("all");
    const statusFilter = ref("all");
    const currentPage = ref(1);
    const pageSize = ref(10);
    const total = ref(0);

    // 弹窗相关状态
    const messageDetailVisible = ref(false);
    const selectedMessage = ref(null);

    // 获取消息类型显示名称
    const getMessageTypeName = (type) => {
      const typeMap = {
        backtest_data_ready: "数据准备完成",
        backtest_complete: "回测完成",
        system_notice: "系统通知",
        error_alert: "错误提醒",
      };
      return typeMap[type] || type;
    };

    // 获取消息类型颜色
    const getMessageTypeColor = (type) => {
      const colorMap = {
        backtest_data_ready: "info",
        backtest_complete: "success",
        system_notice: "warning",
        error_alert: "danger",
      };
      return colorMap[type] || "info";
    };

    // 获取操作按钮文本
    const getActionButtonText = (type) => {
      if (type === "backtest_complete") {
        return "查看回测报告";
      }
      return "查看详情";
    };

    // 格式化日期时间
    const formatDateTime = (dateTimeString) => {
      if (!dateTimeString) return "-";
      const date = new Date(dateTimeString);
      return date.toLocaleString("zh-CN");
    };

    // 获取消息列表
    const fetchMessages = async () => {
      try {
        loading.value = true;

        const token = localStorage.getItem("token");
        if (!token) {
          ElMessage.error("请先登录");
          return;
        }

        const queryParams = new URLSearchParams({
          page: currentPage.value.toString(),
          page_size: pageSize.value.toString(),
          status: statusFilter.value,
          message_type: messageType.value,
        });

        const response = await axios.get(`/api/messages?${queryParams}`, {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });

        if (response.data.success) {
          messages.value = response.data.data.messages || [];
          total.value = response.data.data.total || 0;
        } else {
          messages.value = [];
          total.value = 0;
        }
      } catch (error) {
        console.error("获取消息列表失败:", error);
        ElMessage.error("获取消息列表失败，请重试");
      } finally {
        loading.value = false;
      }
    };

    // 刷新消息列表
    const refreshMessages = () => {
      currentPage.value = 1;
      fetchMessages();
    };

    // 监听筛选条件变化
    watch([messageType, statusFilter], () => {
      refreshMessages();
    });

    // 分页处理
    const handleSizeChange = (newSize) => {
      pageSize.value = newSize;
      currentPage.value = 1;
      fetchMessages();
    };

    const handleCurrentChange = (newPage) => {
      currentPage.value = newPage;
      fetchMessages();
    };

    // 打开消息详情
    const openMessageDetail = (message) => {
      selectedMessage.value = message;
      messageDetailVisible.value = true;

      // 如果是未读消息，自动标记为已读
      if (message.status === "unread") {
        markAsReadSilent(message.message_id);
      }
    };

    // 关闭消息详情弹窗
    const handleMessageDetailClose = () => {
      messageDetailVisible.value = false;
      selectedMessage.value = null;
    };

    // 标记消息为已读
    const markAsRead = async (message) => {
      try {
        const token = localStorage.getItem("token");
        if (!token) return;

        await axios.put(
          `/api/messages/${message.message_id}/read`,
          {},
          {
            headers: {
              Authorization: `Bearer ${token}`,
            },
          }
        );

        // 更新本地状态
        message.status = "read";
        message.read_at = new Date().toISOString();

        ElMessage.success("已标记为已读");
      } catch (error) {
        console.error("标记已读失败:", error);
        ElMessage.error("标记已读失败");
      }
    };

    // 静默标记为已读（不显示成功消息）
    const markAsReadSilent = async (messageId) => {
      try {
        const token = localStorage.getItem("token");
        if (!token) return;

        await axios.put(
          `/api/messages/${messageId}/read`,
          {},
          {
            headers: {
              Authorization: `Bearer ${token}`,
            },
          }
        );

        // 更新列表中的消息状态
        const message = messages.value.find((m) => m.message_id === messageId);
        if (message) {
          message.status = "read";
          message.read_at = new Date().toISOString();
        }
      } catch (error) {
        console.error("标记已读失败:", error);
      }
    };

    // 在详情弹窗中标记已读
    const markAsReadInDetail = async () => {
      if (selectedMessage.value) {
        await markAsRead(selectedMessage.value);
        selectedMessage.value.status = "read";
        selectedMessage.value.read_at = new Date().toISOString();
      }
    };

    // 删除消息
    const deleteMessage = async (message) => {
      try {
        await ElMessageBox.confirm(
          `确定要删除消息"${message.title}"吗？`,
          "确认删除",
          {
            confirmButtonText: "确定",
            cancelButtonText: "取消",
            type: "warning",
          }
        );

        const token = localStorage.getItem("token");
        if (!token) return;

        await axios.delete(`/api/messages/${message.message_id}`, {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });

        ElMessage.success("消息已删除");
        fetchMessages(); // 重新获取列表
      } catch (error) {
        if (error !== "cancel") {
          console.error("删除消息失败:", error);
          ElMessage.error("删除消息失败");
        }
      }
    };

    // 在详情弹窗中删除消息
    const deleteMessageInDetail = async () => {
      if (selectedMessage.value) {
        await deleteMessage(selectedMessage.value);
        messageDetailVisible.value = false;
        selectedMessage.value = null;
      }
    };

    // 处理消息链接
    const handleMessageLink = (message) => {
      if (message.link_url && message.link_params) {
        try {
          // 调试信息
          console.log("link_params type:", typeof message.link_params);
          console.log("link_params value:", message.link_params);

          let params;
          if (typeof message.link_params === "string") {
            params = JSON.parse(message.link_params);
          } else {
            // 如果已经是对象，直接使用
            params = message.link_params;
          }

          if (message.link_url === "/backtests") {
            // 跳转到回测报告页面
            router.push({
              name: "HistoricalBacktestList",
              query: {
                open_report: params.report_id,
                strategy_name: params.strategy_name,
              },
            });
          }
          messageDetailVisible.value = false;
        } catch (e) {
          console.error("解析链接参数失败:", e);
          ElMessage.error("链接参数错误");
        }
      }
    };

    // 组件挂载时获取数据
    onMounted(() => {
      fetchMessages();

      // 检查路由参数，如果有 open_message，自动打开对应消息
      if (route.query.open_message) {
        const messageId = route.query.open_message;
        // 延迟一段时间确保消息列表已加载
        setTimeout(() => {
          const message = messages.value.find(
            (m) => m.message_id === messageId
          );
          if (message) {
            openMessageDetail(message);
          }
        }, 1000);
      }
    });

    return {
      loading,
      messages,
      messageType,
      statusFilter,
      currentPage,
      pageSize,
      total,
      messageDetailVisible,
      selectedMessage,
      getMessageTypeName,
      getMessageTypeColor,
      getActionButtonText,
      formatDateTime,
      fetchMessages,
      refreshMessages,
      handleSizeChange,
      handleCurrentChange,
      openMessageDetail,
      handleMessageDetailClose,
      markAsRead,
      markAsReadInDetail,
      deleteMessage,
      deleteMessageInDetail,
      handleMessageLink,
    };
  },
};
</script>

<style scoped>
.message-box-container {
  padding: 20px;
  height: calc(100vh - 60px - 40px); /* 减去导航栏高度 */
  display: flex;
  flex-direction: column;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding-bottom: 15px;
  border-bottom: 2px solid #e4e7ed;
}

.page-header h1 {
  margin: 0;
  color: #303133;
  font-size: 24px;
  font-weight: 600;
}

.header-actions {
  display: flex;
  align-items: center;
}

.table-container {
  flex: 1;
  margin-bottom: 20px;
}

.message-title {
  cursor: pointer;
  color: #409eff;
  transition: color 0.2s;
}

.message-title:hover {
  color: #66b1ff;
}

.unread-title {
  font-weight: bold;
  color: #e6a23c;
}

.unread-title:hover {
  color: #ebb563;
}

.pagination-container {
  display: flex;
  justify-content: center;
  padding: 20px 0;
  border-top: 1px solid #ebeef5;
}

.message-detail {
  margin-bottom: 20px;
}

.message-content {
  margin: 20px 0;
}

.message-content h4 {
  margin-bottom: 10px;
  color: #303133;
}

.message-content p {
  line-height: 1.6;
  color: #606266;
  white-space: pre-wrap;
}

.message-actions {
  margin-top: 20px;
  text-align: center;
}
</style>
