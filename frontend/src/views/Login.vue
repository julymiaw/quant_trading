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
            autoComplete="off"
          />
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
            autoComplete="off"
          />
        </div>
        
        <!-- 登录错误提示 -->
        <div v-if="showAlert" style="margin: 10px 0; padding: 15px; background: #fff3cd; border: 1px solid #ffeaa7; border-radius: 4px; text-align: center;">
          <p style="margin: 0; color: #856404;">{{ alertMessage }}</p>
        </div>
        
        <!-- 登录按钮 -->
        <el-button
          type="primary"
          :loading="loading"
          @click="handleLogin"
          :style="buttonStyle"
        >
          登录
        </el-button>
        
        <!-- 忘记密码链接 -->
        <div class="form-links">
          <el-link type="primary" :underline="false" @click="showForgotPassword">
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
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock } from '@element-plus/icons-vue'
import axios from 'axios'

export default {
  name: 'Login',
  components: {
    User,
    Lock
  },
  setup() {
    const router = useRouter()
    const loading = ref(false)
    const showAlert = ref(false)
    const alertMessage = ref('测试错误信息') // 设置默认测试值，方便查看
    const alertType = ref('info')
    
    // 登录表单数据
    const loginForm = reactive({
      userName: '',
      password: ''
    })
    
    // 样式定义
    const inputStyle = {
      width: '100%',
      height: '44px',
      fontSize: '14px'
    }
    
    const buttonStyle = {
      width: '100%',
      height: '44px',
      backgroundColor: '#e8f5e9',
      color: '#333',
      border: 'none',
      borderRadius: '4px',
      fontSize: '16px',
      fontWeight: '500'
    }
    
    const alertStyle = {
      marginBottom: '16px',
      borderRadius: '4px',
      width: '100%',
      textAlign: 'center',
      height: '60px',
      lineHeight: '60px',
      color: '#333', // 确保文字颜色可见
      fontSize: '14px', // 设置字体大小
      background: 'rgba(245, 108, 108, 0.1)', // 为error类型添加背景色
      borderColor: '#ffccc7' // 为error类型添加边框颜色
    }
    
    // 处理登录
    const handleLogin = async () => {
      try {
        if (!loginForm.userName || !loginForm.password) {
          showAlert.value = true
          alertMessage.value = '请输入手机号和密码'
          alertType.value = 'warning'
          
          // 设置3秒后自动隐藏提示信息
          setTimeout(() => {
            showAlert.value = false
          }, 3000)
          
          return
        }
        
        loading.value = true
        
        // 发送真实的登录请求，路径与baseURL配置匹配
        const response = await axios.post('/auth/login', loginForm)
        
        // 处理登录成功响应
        const { data } = response.data
        
        // 保存token和用户信息
        localStorage.setItem('token', data.token)
        localStorage.setItem('userInfo', JSON.stringify(data.userInfo))
        
        ElMessage.success('登录成功')
        
        // 跳转到首页（策略管理页面）
        router.push('/')
      } catch (error) {
        console.error('登录失败:', error)
        showAlert.value = true
        
        // 增强错误信息处理，根据不同的HTTP状态码显示不同的错误信息
        let errorMsg = '登录失败，请稍后再试'
        
        // 详细记录错误结构，便于调试
        console.log('完整错误对象:', error)
        console.log('错误响应:', error.response)
        
        if (error.response) {
          // 服务器返回了错误响应
          console.log('错误状态码:', error.response.status)
          console.log('错误数据:', error.response.data)
          
          // 根据状态码给出明确提示
          if (error.response.status === 401) {
            errorMsg = '用户名或密码错误'
          } else if (error.response.status === 400) {
            errorMsg = '请填写完整的登录信息'
          } else if (error.response.status === 500) {
            errorMsg = '服务器内部错误，请稍后再试'
          }
          
          // 尝试从响应中获取更具体的错误信息
          if (error.response.data) {
            // 尝试不同的字段名获取错误信息
            if (typeof error.response.data === 'string') {
              errorMsg = error.response.data
            } else if (error.response.data.message) {
              errorMsg = error.response.data.message
            } else if (error.response.data.error) {
              errorMsg = error.response.data.error
            } else if (error.response.data.msg) {
              errorMsg = error.response.data.msg
            } else {
              // 尝试将整个data对象转为字符串
              try {
                errorMsg = JSON.stringify(error.response.data)
              } catch (e) {
                console.error('无法序列化错误数据:', e)
              }
            }
          }
        } else if (error.message) {
          // 网络错误或其他错误
          errorMsg = error.message
        }
        
        // 确保错误消息不为空
        if (!errorMsg || errorMsg.trim() === '') {
          errorMsg = '登录失败，未知错误'
        }
        
        alertMessage.value = errorMsg
        alertType.value = 'error'
        
        console.log('设置错误信息:', {showAlert: showAlert.value, alertMessage: alertMessage.value})
        
        // 设置3秒后自动隐藏错误信息
        const timer = setTimeout(() => {
          console.log('3秒后自动隐藏提示信息')
          showAlert.value = false
          console.log('设置showAlert为false后:', showAlert.value)
        }, 3000)
        
        // 再次确认alertMessage的值
        setTimeout(() => {
          console.log('100ms后再次检查alertMessage:', alertMessage.value)
        }, 100)
        
        console.log('创建的定时器ID:', timer)
      } finally {
        loading.value = false
      }
    }
    
    // 跳转到注册页面
    const goToRegister = () => {
      router.push('/register')
    }
    
    // 忘记密码处理
    const showForgotPassword = () => {
      showAlert.value = true
      alertMessage.value = '忘记密码功能即将上线'
      alertType.value = 'info'
      
      // 设置3秒后自动隐藏提示信息
      setTimeout(() => {
        showAlert.value = false
      }, 3000)
    }
    
    return {
      loginForm,
      loading,
      showAlert,
      alertMessage,
      alertType,
      inputStyle,
      buttonStyle,
      alertStyle,
      handleLogin,
      goToRegister,
      showForgotPassword
    }
  }
}
</script>

<style scoped>
.login-page {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
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
  min-height: calc(100vh - 64px);
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