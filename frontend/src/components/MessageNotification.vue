<template>
  <div class="message-notifications">
    <!-- 消息通知弹窗 -->
    <transition-group
      name="notification"
      tag="div"
      class="notification-container">
      <div
        v-for="notification in notifications"
        :key="notification.id"
        class="notification-item"
        :class="getNotificationClass(notification.type)"
        @click="handleNotificationClick(notification)">
        <div class="notification-header">
          <div class="notification-title">{{ notification.title }}</div>
          <button
            class="close-btn"
            @click.stop="removeNotification(notification.id)">
            <el-icon><Close /></el-icon>
          </button>
        </div>
        <div class="notification-content">{{ notification.content }}</div>
        <div class="notification-footer">
          <div class="notification-time">
            {{ formatTime(notification.created_at) }}
          </div>
          <div class="countdown-bar">
            <div
              class="countdown-progress"
              :style="{ width: getCountdownWidth(notification) + '%' }"></div>
          </div>
        </div>
      </div>
    </transition-group>
  </div>
</template>

<script>
import { ref, reactive, onMounted, onUnmounted } from "vue";
import { Close } from "@element-plus/icons-vue";
import { ElMessage } from "element-plus";
import { useRouter } from "vue-router";
import axios from "axios";

export default {
  name: "MessageNotification",
  components: {
    Close,
  },
  setup() {
    const router = useRouter();
    const notifications = ref([]);
    const pollingInterval = ref(null);
    const countdownIntervals = reactive({});

    // 获取消息通知类型的样式类
    const getNotificationClass = (type) => {
      const typeMap = {
        backtest_data_ready: "info",
        backtest_complete: "success",
        system_notice: "warning",
        error_alert: "error",
      };
      return `notification-${typeMap[type] || "info"}`;
    };

    // 格式化时间
    const formatTime = (timeString) => {
      const date = new Date(timeString);
      return date.toLocaleTimeString("zh-CN", {
        hour: "2-digit",
        minute: "2-digit",
      });
    };

    // 计算倒计时进度条宽度
    const getCountdownWidth = (notification) => {
      const elapsed = Date.now() - new Date(notification.show_time).getTime();
      const duration = notification.duration || 8000; // 默认8秒
      const remaining = Math.max(0, duration - elapsed);
      return (remaining / duration) * 100;
    };

    // 轮询获取新消息
    const pollMessages = async () => {
      try {
        const token = localStorage.getItem("token");
        if (!token) return;

        const response = await axios.get(
          "/api/messages?status=unread&page=1&page_size=5",
          {
            headers: {
              Authorization: `Bearer ${token}`,
            },
          }
        );

        if (response.data.success) {
          const messages = response.data.data.messages;

          // 检查是否有新消息
          messages.forEach((message) => {
            const exists = notifications.value.find(
              (n) => n.message_id === message.message_id
            );
            if (!exists) {
              showNotification(message);
            }
          });
        }
      } catch (error) {
        console.error("轮询消息失败:", error);
      }
    };

    // 显示通知
    const showNotification = (message) => {
      const notification = {
        ...message,
        id: message.message_id,
        show_time: new Date().toISOString(),
        duration: 8000, // 8秒后自动消失
      };

      notifications.value.push(notification);

      // 自动标记为已读
      markAsRead(message.message_id);

      // 设置倒计时自动消失
      const countdownId = setInterval(() => {
        const elapsed = Date.now() - new Date(notification.show_time).getTime();
        if (elapsed >= notification.duration) {
          removeNotification(notification.id);
        }
      }, 100);

      countdownIntervals[notification.id] = countdownId;
    };

    // 移除通知
    const removeNotification = (id) => {
      const index = notifications.value.findIndex((n) => n.id === id);
      if (index > -1) {
        notifications.value.splice(index, 1);
      }

      // 清除倒计时
      if (countdownIntervals[id]) {
        clearInterval(countdownIntervals[id]);
        delete countdownIntervals[id];
      }
    };

    // 点击通知处理
    const handleNotificationClick = (notification) => {
      // 如果有链接，处理链接跳转
      if (notification.link_url && notification.link_params) {
        try {
          let params;
          if (typeof notification.link_params === "string") {
            params = JSON.parse(notification.link_params);
          } else {
            // 如果已经是对象，直接使用
            params = notification.link_params;
          }

          if (notification.link_url === "/backtests") {
            // 跳转到回测报告页面并打开弹窗
            router.push({
              name: "HistoricalBacktestList",
              query: {
                open_report: params.report_id,
                strategy_name: params.strategy_name,
              },
            });
          }
        } catch (e) {
          console.error("解析链接参数失败:", e);
        }
      }

      // 总是跳转到消息箱并打开对应消息
      router.push({
        name: "MessageBox",
        query: { open_message: notification.message_id },
      });

      removeNotification(notification.id);
    };

    // 标记消息为已读
    const markAsRead = async (messageId) => {
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
      } catch (error) {
        console.error("标记消息已读失败:", error);
      }
    };

    // 组件挂载时开始轮询
    onMounted(() => {
      pollMessages(); // 立即执行一次
      pollingInterval.value = setInterval(pollMessages, 3000); // 每3秒轮询一次
    });

    // 组件卸载时清理
    onUnmounted(() => {
      if (pollingInterval.value) {
        clearInterval(pollingInterval.value);
      }

      // 清理所有倒计时
      Object.values(countdownIntervals).forEach((intervalId) => {
        clearInterval(intervalId);
      });
    });

    return {
      notifications,
      getNotificationClass,
      formatTime,
      getCountdownWidth,
      handleNotificationClick,
      removeNotification,
    };
  },
};
</script>

<style scoped>
.message-notifications {
  position: fixed;
  top: 80px;
  right: 20px;
  z-index: 2000;
  width: 350px;
}

.notification-container {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.notification-item {
  background: white;
  border-radius: 8px;
  padding: 16px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  cursor: pointer;
  transition: all 0.3s ease;
  border-left: 4px solid #409eff;
}

.notification-item:hover {
  transform: translateX(-5px);
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.2);
}

.notification-success {
  border-left-color: #67c23a;
}

.notification-warning {
  border-left-color: #e6a23c;
}

.notification-error {
  border-left-color: #f56c6c;
}

.notification-info {
  border-left-color: #409eff;
}

.notification-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.notification-title {
  font-weight: 600;
  font-size: 14px;
  color: #303133;
}

.close-btn {
  background: none;
  border: none;
  cursor: pointer;
  color: #909399;
  font-size: 14px;
  padding: 2px;
  border-radius: 2px;
  transition: all 0.2s;
}

.close-btn:hover {
  background: #f5f7fa;
  color: #606266;
}

.notification-content {
  font-size: 13px;
  color: #606266;
  line-height: 1.4;
  margin-bottom: 12px;
}

.notification-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.notification-time {
  font-size: 12px;
  color: #909399;
}

.countdown-bar {
  width: 100px;
  height: 3px;
  background: #f5f7fa;
  border-radius: 2px;
  overflow: hidden;
}

.countdown-progress {
  height: 100%;
  background: #409eff;
  transition: width 0.1s linear;
  border-radius: 2px;
}

.notification-success .countdown-progress {
  background: #67c23a;
}

.notification-warning .countdown-progress {
  background: #e6a23c;
}

.notification-error .countdown-progress {
  background: #f56c6c;
}

/* 动画效果 */
.notification-enter-active,
.notification-leave-active {
  transition: all 0.3s ease;
}

.notification-enter-from {
  opacity: 0;
  transform: translateX(100%);
}

.notification-leave-to {
  opacity: 0;
  transform: translateX(100%);
}

.notification-move {
  transition: transform 0.3s ease;
}
</style>
