import { ref, reactive } from "vue";

/**
 * 表单状态管理组合式API
 * 提供统一的表单状态管理和错误提示功能
 */
export function useFormState() {
  // 加载状态
  const loading = ref(false);

  // 警告状态
  const alert = reactive({
    visible: false,
    message: "",
    type: "info",
    duration: 3000,
  });

  let alertTimer = null;

  /**
   * 显示警告消息
   * @param {string} message - 消息内容
   * @param {string} type - 消息类型: 'success' | 'warning' | 'error' | 'info'
   * @param {number} duration - 显示时长（毫秒），0表示不自动关闭
   */
  const showAlert = (message, type = "info", duration = 3000) => {
    // 清除之前的定时器
    if (alertTimer) {
      clearTimeout(alertTimer);
      alertTimer = null;
    }

    alert.message = message;
    alert.type = type;
    alert.duration = duration;
    alert.visible = true;

    // 设置自动关闭
    if (duration > 0) {
      alertTimer = setTimeout(() => {
        hideAlert();
      }, duration);
    }
  };

  /**
   * 隐藏警告消息
   */
  const hideAlert = () => {
    alert.visible = false;
    if (alertTimer) {
      clearTimeout(alertTimer);
      alertTimer = null;
    }
  };

  /**
   * 显示成功消息
   * @param {string} message - 消息内容
   * @param {number} duration - 显示时长
   */
  const showSuccess = (message, duration = 3000) => {
    showAlert(message, "success", duration);
  };

  /**
   * 显示警告消息
   * @param {string} message - 消息内容
   * @param {number} duration - 显示时长
   */
  const showWarning = (message, duration = 3000) => {
    showAlert(message, "warning", duration);
  };

  /**
   * 显示错误消息
   * @param {string} message - 消息内容
   * @param {number} duration - 显示时长
   */
  const showError = (message, duration = 5000) => {
    showAlert(message, "error", duration);
  };

  /**
   * 显示信息消息
   * @param {string} message - 消息内容
   * @param {number} duration - 显示时长
   */
  const showInfo = (message, duration = 3000) => {
    showAlert(message, "info", duration);
  };

  /**
   * 设置加载状态
   * @param {boolean} state - 加载状态
   */
  const setLoading = (state) => {
    loading.value = state;
  };

  /**
   * 处理API错误
   * @param {Error} error - 错误对象
   * @param {string} defaultMessage - 默认错误消息
   */
  const handleApiError = (error, defaultMessage = "操作失败，请稍后重试") => {
    console.error("API错误:", error);

    let errorMessage = defaultMessage;

    if (error.response) {
      // 服务器返回了错误响应
      const { status, data } = error.response;

      // 根据状态码提供更具体的错误信息
      if (status === 401) {
        errorMessage = "登录已过期，请重新登录";
      } else if (status === 403) {
        errorMessage = "没有权限执行此操作";
      } else if (status === 404) {
        errorMessage = "请求的资源不存在";
      } else if (status === 422) {
        errorMessage = "提交的数据格式有误";
      } else if (status === 429) {
        errorMessage = "请求过于频繁，请稍后再试";
      } else if (status >= 500) {
        errorMessage = "服务器内部错误，请稍后重试";
      }

      // 尝试从响应中获取更具体的错误信息
      if (data) {
        if (typeof data === "string") {
          errorMessage = data;
        } else if (data.message) {
          errorMessage = data.message;
        } else if (data.error) {
          errorMessage = data.error;
        } else if (data.msg) {
          errorMessage = data.msg;
        }
      }
    } else if (error.message) {
      // 网络错误或其他错误
      if (error.message.includes("Network Error")) {
        errorMessage = "网络连接失败，请检查网络设置";
      } else if (error.message.includes("timeout")) {
        errorMessage = "请求超时，请稍后重试";
      } else {
        errorMessage = error.message;
      }
    }

    showError(errorMessage);
  };

  /**
   * 表单验证失败处理
   * @param {Object} validationErrors - 验证错误对象
   */
  const handleValidationError = (validationErrors) => {
    if (validationErrors && typeof validationErrors === "object") {
      // 获取第一个验证错误消息
      const firstError = Object.values(validationErrors)[0];
      if (Array.isArray(firstError) && firstError.length > 0) {
        showWarning(firstError[0]);
      } else if (typeof firstError === "string") {
        showWarning(firstError);
      } else {
        showWarning("请检查表单信息");
      }
    } else {
      showWarning("请填写完整的表单信息");
    }
  };

  return {
    // 状态
    loading,
    alert,

    // 方法
    setLoading,
    showAlert,
    hideAlert,
    showSuccess,
    showWarning,
    showError,
    showInfo,
    handleApiError,
    handleValidationError,
  };
}
