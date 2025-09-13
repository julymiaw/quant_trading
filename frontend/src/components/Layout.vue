<template>
  <div class="app-container">
    <!-- 顶部导航栏 -->
    <header class="navbar">
      <div class="navbar-left">
        <img src="/logo_seuquant.png" alt="Logo" class="logo" />
        <h1 class="app-title">量化交易选股系统</h1>
      </div>
      <div class="navbar-center">
        <el-menu
          mode="horizontal"
          :default-active="activeMenu"
          class="nav-menu">
          <el-menu-item index="/" @click="$router.push('/')">
            <el-icon><HomeFilled /></el-icon>
            <span>策略管理</span>
          </el-menu-item>
          <el-menu-item
            index="/indicators"
            @click="$router.push('/indicators')">
            <el-icon><DataAnalysis /></el-icon>
            <span>指标管理</span>
          </el-menu-item>
          <el-menu-item index="/params" @click="$router.push('/params')">
            <el-icon><Setting /></el-icon>
            <span>参数管理</span>
          </el-menu-item>
        </el-menu>
      </div>
      <div class="navbar-right">
        <el-button type="text" @click="goBack">
          <el-icon><ArrowLeft /></el-icon>
          返回上一页
        </el-button>
        <el-dropdown>
          <el-button type="primary">
            <el-icon><User /></el-icon>
            {{ userInfo?.user_name || "用户" }}
            <el-icon class="el-icon--right"><CaretBottom /></el-icon>
          </el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item @click="showUserInfo"
                >用户信息</el-dropdown-item
              >
              <el-dropdown-item divided @click="logout"
                >退出登录</el-dropdown-item
              >
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </header>

    <!-- 主内容区 -->
    <main class="main-content">
      <router-view />
    </main>

    <!-- 用户信息弹窗 -->
    <el-dialog
      title="用户信息"
      v-model="userInfoDialogVisible"
      width="400px"
      :before-close="handleUserInfoDialogClose">
      <el-descriptions :column="1" border>
        <el-descriptions-item label="用户名">{{
          userInfo?.user_name
        }}</el-descriptions-item>
        <el-descriptions-item label="用户角色">{{
          userInfo?.user_role === "admin" ? "管理员" : "分析师"
        }}</el-descriptions-item>
        <el-descriptions-item label="用户状态">{{
          formatUserStatus(userInfo?.user_status)
        }}</el-descriptions-item>
        <el-descriptions-item label="邮箱" v-if="userInfo?.user_email">{{
          userInfo?.user_email
        }}</el-descriptions-item>
        <el-descriptions-item label="手机号" v-if="userInfo?.user_phone">{{
          userInfo?.user_phone
        }}</el-descriptions-item>
        <el-descriptions-item label="创建时间">{{
          formatDate(userInfo?.user_create_time)
        }}</el-descriptions-item>
        <el-descriptions-item label="最后登录时间">{{
          formatDate(userInfo?.user_last_login_time)
        }}</el-descriptions-item>
      </el-descriptions>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="userInfoDialogVisible = false">关闭</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import { onMounted, ref, computed } from "vue";
import { useRouter } from "vue-router";
import {
  HomeFilled,
  DataAnalysis,
  Setting,
  ArrowLeft,
  CaretBottom,
  User,
} from "@element-plus/icons-vue";

export default {
  name: "Layout",
  components: {
    HomeFilled,
    DataAnalysis,
    Setting,
    ArrowLeft,
    CaretBottom,
    User,
  },
  setup() {
    const router = useRouter();
    const userInfo = ref(null);
    const userInfoDialogVisible = ref(false);
    const activeMenu = computed(() => {
      return router.currentRoute.value.path;
    });

    // 格式化日期
    const formatDate = (dateString) => {
      if (!dateString) return "N/A";
      const date = new Date(dateString);
      return date.toLocaleString("zh-CN");
    };

    // 格式化用户状态
    const formatUserStatus = (status) => {
      if (!status) return "未知";
      switch (status) {
        case "active":
          return "正常";
        case "inactive":
          return "未激活";
        case "locked":
          return "已锁定";
        default:
          return status;
      }
    };

    // 返回上一页
    const goBack = () => {
      if (window.history.length > 1) {
        window.history.back();
      } else {
        router.push("/");
      }
    };

    // 显示用户信息
    const showUserInfo = async () => {
      try {
        // 从后端获取最新的用户信息
        const token = localStorage.getItem("token");
        if (!token) {
          console.error("未找到token");
          return;
        }

        const response = await fetch("http://localhost:5000/user/info", {
          method: "GET",
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
          },
        });

        if (response.ok) {
          const result = await response.json();
          if (result.code === 200) {
            // 更新用户信息
            userInfo.value = result.data;
            // 同时更新localStorage中的用户信息
            localStorage.setItem("userInfo", JSON.stringify(result.data));
          } else {
            console.error("获取用户信息失败:", result.message);
          }
        } else {
          console.error("网络请求失败:", response.status);
        }
      } catch (error) {
        console.error("获取用户信息出错:", error);
      }

      userInfoDialogVisible.value = true;
    };

    // 处理用户信息弹窗关闭
    const handleUserInfoDialogClose = () => {
      userInfoDialogVisible.value = false;
    };

    // 退出登录
    const logout = async () => {
      try {
        // 这里可以添加退出登录的API调用
        // await axios.post('/api/logout')

        // 清除本地存储
        localStorage.removeItem("token");
        localStorage.removeItem("userInfo");

        // 跳转到登录页面
        router.push("/login");
      } catch (error) {
        console.error("退出登录失败:", error);
      }
    };

    // 初始化用户信息
    const initUserInfo = () => {
      const storedUserInfo = localStorage.getItem("userInfo");
      if (storedUserInfo) {
        try {
          userInfo.value = JSON.parse(storedUserInfo);
        } catch (error) {
          console.error("解析用户信息失败:", error);
        }
      }
    };

    onMounted(() => {
      initUserInfo();
    });

    return {
      userInfo,
      userInfoDialogVisible,
      activeMenu,
      formatDate,
      formatUserStatus,
      goBack,
      showUserInfo,
      handleUserInfoDialogClose,
      logout,
    };
  },
};
</script>

<style scoped>
.app-container {
  height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.navbar {
  background-color: #f0f9f4;
  border-bottom: 1px solid #d9f2e6;
  padding: 0 20px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 60px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.navbar-left {
  display: flex;
  align-items: center;
  flex-shrink: 0; /* 防止左侧区域缩小 */
  min-width: 320px; /* 确保有足够空间显示完整标题 */
}

.logo {
  height: 40px;
  margin-right: 15px;
  flex-shrink: 0; /* logo不缩小 */
}

.app-title {
  font-size: 18px;
  font-weight: 600;
  color: #10b981;
  margin: 0;
  white-space: nowrap; /* 防止文字换行 */
  /* 移除省略设置，让文字完整显示 */
}

.navbar-center {
  flex: 1; /* 占据剩余空间 */
  display: flex;
  justify-content: center;
  min-width: 400px; /* 确保菜单有足够空间展开 */
  margin: 0 15px; /* 适当边距 */
}

.nav-menu {
  background-color: transparent !important;
  width: 100% !important; /* 让菜单占满容器宽度 */
}

.navbar-right {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0; /* 防止右侧区域缩小 */
  min-width: 200px; /* 确保右侧按钮有足够空间 */
}

.main-content {
  flex: 1;
  padding: 20px;
  background-color: #f5f5f5;
  overflow-y: auto;
  height: calc(100vh - 60px);
}

/* 响应式设计 */
@media (max-width: 1200px) {
  .navbar-left {
    min-width: 300px;
  }

  .navbar-center {
    min-width: 350px;
  }

  .navbar-right {
    min-width: 180px;
  }

  .app-title {
    font-size: 16px;
  }
}

@media (max-width: 1000px) {
  .navbar {
    padding: 0 15px;
  }

  .navbar-left {
    min-width: 280px;
  }

  .navbar-center {
    min-width: 300px;
    margin: 0 10px;
  }

  .navbar-right {
    min-width: 160px;
    gap: 8px;
  }

  .app-title {
    font-size: 15px;
  }

  .logo {
    height: 35px;
    margin-right: 12px;
  }
}

@media (max-width: 850px) {
  .navbar-left {
    min-width: 250px;
  }

  .navbar-center {
    min-width: 250px;
    margin: 0 8px;
  }

  .navbar-right {
    min-width: 140px;
    gap: 5px;
  }

  .app-title {
    font-size: 14px;
  }

  .logo {
    height: 32px;
    margin-right: 10px;
  }
}

@media (max-width: 768px) {
  .navbar {
    padding: 0 10px;
  }

  .navbar-left {
    min-width: 220px;
  }

  .navbar-center {
    min-width: 200px;
    margin: 0 5px;
  }

  .navbar-right {
    min-width: 120px;
    gap: 3px;
  }

  .app-title {
    font-size: 13px;
  }

  .logo {
    height: 30px;
    margin-right: 8px;
  }
}
</style>
