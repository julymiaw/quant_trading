<template>
  <div class="register-page">
    <!-- 顶部淡绿色条 -->
    <div class="register-header-bar">
      <img src="/logo_seuquant.png" alt="Logo" class="header-logo" />
    </div>

    <!-- 主内容区域 -->
    <div class="register-content-container">
      <!-- 注册表单卡片 -->
      <div class="register-form-card">
        <!-- Logo和标题 -->
        <div class="form-logo-container">
          <img src="/logo_seuquant.png" alt="Logo" class="form-logo" />
          <h2 class="form-title">注册账号</h2>
          <p class="form-subtitle">加入量化交易选股系统</p>
        </div>

        <!-- 注册提示消息 -->
        <FormAlert
          :visible="alert.visible"
          :message="alert.message"
          :type="alert.type"
          @close="hideAlert" />

        <el-form
          ref="registerFormRef"
          :model="registerForm"
          :rules="registerRules"
          class="register-form"
          label-width="80px">
          <el-form-item label="用户名" prop="userName">
            <el-input
              v-model="registerForm.userName"
              placeholder="请输入用户名（仅允许英文、数字、下划线）"
              prefix-icon="User" />
          </el-form-item>

          <el-form-item label="密码" prop="password">
            <el-input
              v-model="registerForm.password"
              type="password"
              placeholder="请输入密码（6-20位）"
              prefix-icon="Lock"
              show-password />
          </el-form-item>

          <el-form-item label="确认密码" prop="confirmPassword">
            <el-input
              v-model="registerForm.confirmPassword"
              type="password"
              placeholder="请再次输入密码"
              prefix-icon="Lock"
              show-password />
          </el-form-item>

          <el-form-item label="邮箱" prop="email">
            <el-input
              v-model="registerForm.email"
              placeholder="请输入邮箱"
              prefix-icon="Message" />
          </el-form-item>

          <el-form-item label="手机号" prop="phone">
            <el-input
              v-model="registerForm.phone"
              placeholder="请输入手机号（选填）"
              prefix-icon="Phone" />
          </el-form-item>

          <el-form-item>
            <el-button
              type="primary"
              :loading="loading"
              @click="handleRegister"
              style="width: 100%">
              注册
            </el-button>
          </el-form-item>

          <el-form-item>
            <div class="register-form-footer">
              <span>已有账号？</span>
              <el-link type="primary" :underline="false" @click="goToLogin">
                立即登录
              </el-link>
            </div>
          </el-form-item>
        </el-form>
      </div>
    </div>
  </div>
</template>
<script>
import { ref, reactive } from "vue";
import { useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import axios from "axios";
import FormAlert from "../components/FormAlert.vue";
import { useFormState } from "../composables/useFormState.js";

export default {
  name: "Register",
  components: {
    FormAlert,
  },
  setup() {
    const router = useRouter();
    const registerFormRef = ref(null);

    // 使用表单状态管理
    const {
      loading,
      alert,
      setLoading,
      hideAlert,
      showWarning,
      showError,
      showSuccess,
      handleApiError,
      handleValidationError,
    } = useFormState();

    // 注册表单数据
    const registerForm = reactive({
      userName: "",
      password: "",
      confirmPassword: "",
      email: "",
      phone: "",
    });

    // 表单验证规则
    const registerRules = {
      userName: [
        { required: true, message: "请输入用户名", trigger: "blur" },
        {
          pattern: /^[a-zA-Z0-9_]+$/,
          message: "用户名仅允许英文、数字、下划线",
          trigger: "blur",
        },
        {
          min: 3,
          max: 50,
          message: "用户名长度在 3 到 50 个字符",
          trigger: "blur",
        },
      ],
      password: [
        { required: true, message: "请输入密码", trigger: "blur" },
        {
          min: 6,
          max: 20,
          message: "密码长度在 6 到 20 个字符",
          trigger: "blur",
        },
      ],
      confirmPassword: [
        { required: true, message: "请确认密码", trigger: "blur" },
        {
          validator: (rule, value, callback) => {
            if (value !== registerForm.password) {
              callback(new Error("两次输入的密码不一致"));
            } else {
              callback();
            }
          },
          trigger: "blur",
        },
      ],
      email: [
        { required: true, message: "请输入邮箱", trigger: "blur" },
        { type: "email", message: "请输入有效的邮箱地址", trigger: "blur" },
      ],
      phone: [
        {
          pattern: /^1[3-9]\d{9}$/,
          message: "请输入有效的手机号",
          trigger: "blur",
          required: false,
        },
      ],
    };

    // 处理注册
    const handleRegister = async () => {
      try {
        // 基本字段验证
        if (
          !registerForm.userName ||
          !registerForm.password ||
          !registerForm.confirmPassword ||
          !registerForm.email
        ) {
          showWarning("请填写完整的必填信息");
          return;
        }

        // 密码确认验证
        if (registerForm.password !== registerForm.confirmPassword) {
          showWarning("两次输入的密码不一致");
          return;
        }

        // Element Plus表单验证
        try {
          await registerFormRef.value.validate();
        } catch (validationError) {
          handleValidationError(validationError);
          return;
        }

        setLoading(true);

        // 发送注册请求
        const response = await axios.post("/auth/register", registerForm);

        showSuccess(response.data.message || "注册成功");

        // 延迟跳转，让用户看到成功消息
        setTimeout(() => {
          router.push("/login");
        }, 1500);
      } catch (error) {
        console.error("注册失败:", error);
        handleApiError(error, "注册失败，请稍后重试");
      } finally {
        setLoading(false);
      }
    };

    // 跳转到登录页面
    const goToLogin = () => {
      router.push("/login");
    };

    return {
      registerFormRef,
      registerForm,
      registerRules,
      loading,
      alert,
      handleRegister,
      goToLogin,
      hideAlert,
    };
  },
};
</script>

<style scoped>
.register-page {
  display: flex;
  flex-direction: column;
  height: 100vh;
  overflow: hidden;
}

/* 顶部淡绿色条 */
.register-header-bar {
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
.register-content-container {
  padding-top: 64px;
  flex: 1;
  display: flex;
  justify-content: center;
  align-items: center;
  height: calc(100vh - 64px);
  overflow-y: auto;
}

/* 注册表单卡片 */
.register-form-card {
  background-color: white;
  border: 1px solid #e0e0e0;
  border-radius: 4px;
  padding: 32px;
  width: 450px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

/* Logo和标题 */
.form-logo-container {
  text-align: center;
  margin-bottom: 32px;
}

.form-logo {
  height: 60px;
  width: auto;
  margin-bottom: 16px;
}

.form-title {
  margin: 0 0 8px 0;
  color: #10b981;
  font-size: 22px;
  font-weight: 600;
}

.form-subtitle {
  margin: 0;
  color: #666;
  font-size: 14px;
}

/* 表单 */
.register-form {
  width: 100%;
}

/* 表单项间距调整 */
.register-form .el-form-item {
  margin-bottom: 20px;
}

/* 注册按钮样式 */
.register-form .el-button--primary {
  background-color: #e8f5e9;
  color: #333;
  border: none;
  height: 44px;
  font-size: 16px;
  font-weight: 500;
}

.register-form .el-button--primary:hover {
  background-color: #d4eed6;
}

/* 底部链接 */
.register-form-footer {
  text-align: center;
  margin-top: 10px;
}

.register-form-footer span {
  color: #666;
  font-size: 14px;
  margin-right: 8px;
}
</style>
