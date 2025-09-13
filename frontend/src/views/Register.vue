<template>
  <div class="register-container">
    <div class="register-form-wrapper">
      <div class="register-header">
        <img src="../../logo_seuquant.png" alt="Logo" class="register-logo" />
        <h2>注册账号</h2>
        <p>加入量化交易选股系统</p>
      </div>
      
      <el-form
        ref="registerFormRef"
        :model="registerForm"
        :rules="registerRules"
        class="register-form"
        label-width="80px"
      >
        <el-form-item label="用户名" prop="userName">
          <el-input
            v-model="registerForm.userName"
            placeholder="请输入用户名（仅允许英文、数字、下划线）"
            prefix-icon="User"
          />
        </el-form-item>
        
        <el-form-item label="密码" prop="password">
          <el-input
            v-model="registerForm.password"
            type="password"
            placeholder="请输入密码（6-20位）"
            prefix-icon="Lock"
            show-password
          />
        </el-form-item>
        
        <el-form-item label="确认密码" prop="confirmPassword">
          <el-input
            v-model="registerForm.confirmPassword"
            type="password"
            placeholder="请再次输入密码"
            prefix-icon="Lock"
            show-password
          />
        </el-form-item>
        
        <el-form-item label="邮箱" prop="email">
          <el-input
            v-model="registerForm.email"
            placeholder="请输入邮箱"
            prefix-icon="Message"
          />
        </el-form-item>
        
        <el-form-item label="手机号" prop="phone">
          <el-input
            v-model="registerForm.phone"
            placeholder="请输入手机号（选填）"
            prefix-icon="Phone"
          />
        </el-form-item>
        
        <el-form-item>
          <el-button
            type="primary"
            :loading="loading"
            @click="handleRegister"
            style="width: 100%"
          >
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
</template>

<script>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import axios from 'axios'

export default {
  name: 'Register',
  setup() {
    const router = useRouter()
    const registerFormRef = ref(null)
    const loading = ref(false)
    
    // 注册表单数据
    const registerForm = reactive({
      userName: '',
      password: '',
      confirmPassword: '',
      email: '',
      phone: ''
    })
    
    // 表单验证规则
    const registerRules = {
      userName: [
        { required: true, message: '请输入用户名', trigger: 'blur' },
        { pattern: /^[a-zA-Z0-9_]+$/, message: '用户名仅允许英文、数字、下划线', trigger: 'blur' },
        { min: 3, max: 50, message: '用户名长度在 3 到 50 个字符', trigger: 'blur' }
      ],
      password: [
        { required: true, message: '请输入密码', trigger: 'blur' },
        { min: 6, max: 20, message: '密码长度在 6 到 20 个字符', trigger: 'blur' }
      ],
      confirmPassword: [
        { required: true, message: '请确认密码', trigger: 'blur' },
        {
          validator: (rule, value, callback) => {
            if (value !== registerForm.password) {
              callback(new Error('两次输入的密码不一致'))
            } else {
              callback()
            }
          },
          trigger: 'blur'
        }
      ],
      email: [
        { required: true, message: '请输入邮箱', trigger: 'blur' },
        { type: 'email', message: '请输入有效的邮箱地址', trigger: 'blur' }
      ],
      phone: [
        {
          pattern: /^1[3-9]\d{9}$/,
          message: '请输入有效的手机号',
          trigger: 'blur',
          required: false
        }
      ]
    }
    
    // 处理注册
    const handleRegister = async () => {
      try {
        if (!registerForm.userName || !registerForm.password || !registerForm.confirmPassword) {
          ElMessage.warning('请填写完整信息')
          return
        }
        
        if (registerForm.password !== registerForm.confirmPassword) {
          ElMessage.warning('两次输入的密码不一致')
          return
        }
        
        // 验证表单
        await registerFormRef.value.validate()
        
        loading.value = true
        
        // 发送真实的注册请求，路径与baseURL配置匹配
        const response = await axios.post('/auth/register', registerForm)
        
        ElMessage.success(response.data.message || '注册成功')
        
        // 注册成功后跳转到登录页面
        router.push('/login')
      } catch (error) {
        console.error('注册失败:', error)
        if (error.name === 'ValidationError') {
          ElMessage.error('请检查表单信息')
        } else {
          ElMessage.error(error.response?.data?.message || '注册失败，请稍后重试')
        }
      } finally {
        loading.value = false
      }
    }
    
    // 跳转到登录页面
    const goToLogin = () => {
      router.push('/login')
    }
    
    return {
      registerFormRef,
      registerForm,
      registerRules,
      loading,
      handleRegister,
      goToLogin
    }
  }
}
</script>

<style scoped>
.register-container {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  background-color: #f0f9f4;
}

.register-form-wrapper {
  background-color: white;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  padding: 30px;
  width: 450px;
}

.register-header {
  text-align: center;
  margin-bottom: 25px;
}

.register-logo {
  height: 60px;
  margin-bottom: 15px;
}

.register-header h2 {
  margin: 0 0 5px 0;
  color: #10b981;
  font-size: 22px;
  font-weight: 600;
}

.register-header p {
  margin: 0;
  color: #666;
  font-size: 14px;
}

.register-form {
  width: 100%;
}

.register-form-footer {
  text-align: center;
  margin-top: 10px;
}
</style>