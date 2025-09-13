<template>
  <div class="login-page">
    <!-- 顶部淡绿色条 -->
    <div class="login-header-bar">
      <img src="/logo_seuquant.png" alt="Logo" class="header-logo" />
    </div>

    <!-- 主内容区域 -->
    <div class="login-content-container">
      <!-- 登录表单卡片 -->
      <div class="login-form-card">
        <!-- Logo -->
        <div class="form-logo-container">
          <img src="/logo_seuquant.png" alt="Logo" class="form-logo" />
        </div>

        <!-- 手机号输入框 -->
        <div class="form-item">
          <el-input
            v-model="loginForm.userName"
            placeholder="手机号"
            prefix-icon="User"
            :style="inputStyle"
            autoComplete="off" />
        </div>

        <!-- 密码输入框 -->
        <div class="form-item">
          <el-input
            v-model="loginForm.password"
            type="password"
            placeholder="请输入密码"
            prefix-icon="Lock"
            show-password
            :style="inputStyle"
            autoComplete="off" />
        </div>

        <!-- 登录提示消息 -->
        <FormAlert
          :visible="alert.visible"
          :message="alert.message"
          :type="alert.type"
          @close="hideAlert" />

        <!-- 登录按钮 -->
        <el-button
          type="primary"
          :loading="loading"
          @click="handleLogin"
          :style="buttonStyle">
          登录
        </el-button>

        <!-- 忘记密码链接 -->
        <div class="form-links">
          <el-link
            type="primary"
            :underline="false"
            @click="showForgotPassword">
            忘记密码?
          </el-link>
        </div>

        <!-- 注册链接 -->
        <div class="form-links register-link">
          <span>还没有账号？</span>
          <el-link type="primary" :underline="false" @click="goToRegister">
            立即注册
          </el-link>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { reactive } from "vue";
import { useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { User, Lock } from "@element-plus/icons-vue";
import axios from "axios";
import FormAlert from "../components/FormAlert.vue";
import { useFormState } from "../composables/useFormState.js";

export default {
  name: "Login",
  components: {
    User,
    Lock,
    FormAlert,
  },
  setup() {
    const router = useRouter();

    // 使用表单状态管理
    const {
      loading,
      alert,
      setLoading,
      hideAlert,
      showWarning,
      showError,
      showInfo,
      handleApiError,
    } = useFormState();

    // 登录表单数据
    const loginForm = reactive({
      userName: "",
      password: "",
    });

    // 样式定义
    const inputStyle = {
      width: "100%",
      height: "44px",
      fontSize: "14px",
    };

    const buttonStyle = {
      width: "100%",
      height: "44px",
      backgroundColor: "#e8f5e9",
      color: "#333",
      border: "none",
      borderRadius: "4px",
      fontSize: "16px",
      fontWeight: "500",
    };

    const alertStyle = {
      marginBottom: "16px",
      borderRadius: "4px",
      width: "100%",
      textAlign: "center",
      height: "60px",
      lineHeight: "60px",
      color: "#333", // 确保文字颜色可见
      fontSize: "14px", // 设置字体大小
      background: "rgba(245, 108, 108, 0.1)", // 为error类型添加背景色
      borderColor: "#ffccc7", // 为error类型添加边框颜色
    };

    // 处理登录
    const handleLogin = async () => {
      try {
        if (!loginForm.userName || !loginForm.password) {
          showWarning("请输入手机号和密码");
          return;
        }

        setLoading(true);

        // 发送真实的登录请求，路径与baseURL配置匹配
        const response = await axios.post("/auth/login", loginForm);

        // 处理登录成功响应
        const { data } = response.data;

        // 保存token和用户信息
        localStorage.setItem("token", data.token);
        localStorage.setItem("userInfo", JSON.stringify(data.userInfo));

        ElMessage.success("登录成功");

        // 跳转到首页（策略管理页面）
        router.push("/");
      } catch (error) {
        handleApiError(error, "登录失败，请稍后再试");
      } finally {
        setLoading(false);
      }
    };

    // 跳转到注册页面
    const goToRegister = () => {
      router.push("/register");
    };

    // 忘记密码处理
    const showForgotPassword = () => {
      showInfo("忘记密码功能即将上线");
    };

    return {
      loginForm,
      loading,
      alert,
      inputStyle,
      buttonStyle,
      handleLogin,
      goToRegister,
      showForgotPassword,
      hideAlert,
    };
  },
};
</script>

<style scoped>
.login-page {
  display: flex;
  flex-direction: column;
  height: 100vh;
  overflow: hidden;
}

/* 顶部淡绿色条 */
.login-header-bar {
  background-color: #e8f5e9;
  height: 64px;
  width: 100%;
  position: fixed;
  top: 0;
  left: 0;
  z-index: 1000;
  display: flex;
  align-items: center;
  padding-left: 24px;
}

.header-logo {
  height: 40px;
  width: auto;
}

/* 主内容区域 */
.login-content-container {
  padding-top: 64px;
  flex: 1;
  display: flex;
  justify-content: center;
  align-items: center;
  height: calc(100vh - 64px);
  overflow-y: auto;
}

/* 登录表单卡片 */
.login-form-card {
  background-color: white;
  border: 1px solid #e0e0e0;
  border-radius: 4px;
  padding: 32px;
  width: 400px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

/* Logo */
.form-logo-container {
  text-align: center;
  margin-bottom: 32px;
}

.form-logo {
  height: 60px;
  width: auto;
}

/* 表单项目 */
.form-item {
  margin-bottom: 24px;
}

/* 表单链接 */
.form-links {
  margin-top: 16px;
  text-align: right;
}

.register-link {
  text-align: center;
  margin-top: 24px;
}

.register-link span {
  color: #666;
  font-size: 14px;
  margin-right: 8px;
}
</style>
