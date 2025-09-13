<template>
  <Transition name="fade">
    <div v-if="visible" :class="['form-alert', `form-alert--${type}`]">
      <div class="form-alert__icon">
        <component :is="iconComponent" />
      </div>
      <div class="form-alert__content">
        <p class="form-alert__message">{{ message }}</p>
      </div>
      <div v-if="closable" class="form-alert__close" @click="handleClose">
        <el-icon><Close /></el-icon>
      </div>
    </div>
  </Transition>
</template>

<script>
import { computed } from "vue";
import {
  SuccessFilled,
  WarningFilled,
  CircleCloseFilled,
  InfoFilled,
  Close,
} from "@element-plus/icons-vue";

export default {
  name: "FormAlert",
  components: {
    SuccessFilled,
    WarningFilled,
    CircleCloseFilled,
    InfoFilled,
    Close,
  },
  props: {
    message: {
      type: String,
      default: "",
    },
    type: {
      type: String,
      default: "info",
      validator: (value) =>
        ["success", "warning", "error", "info"].includes(value),
    },
    visible: {
      type: Boolean,
      default: false,
    },
    closable: {
      type: Boolean,
      default: false,
    },
    duration: {
      type: Number,
      default: 3000,
    },
  },
  emits: ["close"],
  setup(props, { emit }) {
    // 计算图标组件
    const iconComponent = computed(() => {
      const iconMap = {
        success: "SuccessFilled",
        warning: "WarningFilled",
        error: "CircleCloseFilled",
        info: "InfoFilled",
      };
      return iconMap[props.type];
    });

    // 处理关闭
    const handleClose = () => {
      emit("close");
    };

    return {
      iconComponent,
      handleClose,
    };
  },
};
</script>

<style scoped>
.form-alert {
  display: flex;
  align-items: center;
  padding: 12px 16px;
  margin-bottom: 16px;
  border-radius: 6px;
  border: 1px solid;
  font-size: 14px;
  line-height: 1.5;
  position: relative;
  transition: all 0.3s ease;
}

.form-alert__icon {
  margin-right: 8px;
  font-size: 16px;
  flex-shrink: 0;
}

.form-alert__content {
  flex: 1;
}

.form-alert__message {
  margin: 0;
  font-weight: 500;
}

.form-alert__close {
  margin-left: 8px;
  cursor: pointer;
  opacity: 0.7;
  transition: opacity 0.2s ease;
  flex-shrink: 0;
}

.form-alert__close:hover {
  opacity: 1;
}

/* Success 样式 */
.form-alert--success {
  background-color: #f0f9ff;
  border-color: #b3e5fc;
  color: #1565c0;
}

.form-alert--success .form-alert__icon {
  color: #4caf50;
}

/* Warning 样式 */
.form-alert--warning {
  background-color: #fffbf0;
  border-color: #ffe082;
  color: #f57c00;
}

.form-alert--warning .form-alert__icon {
  color: #ff9800;
}

/* Error 样式 */
.form-alert--error {
  background-color: #fef7f0;
  border-color: #ffcdd2;
  color: #d32f2f;
}

.form-alert--error .form-alert__icon {
  color: #f44336;
}

/* Info 样式 */
.form-alert--info {
  background-color: #f3f4f6;
  border-color: #d1d5db;
  color: #374151;
}

.form-alert--info .form-alert__icon {
  color: #6b7280;
}

/* 过渡动画 */
.fade-enter-active,
.fade-leave-active {
  transition: all 0.3s ease;
}

.fade-enter-from {
  opacity: 0;
  transform: translateY(-10px);
}

.fade-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}
</style>
