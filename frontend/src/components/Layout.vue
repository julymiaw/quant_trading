<template>
  <div class="app-container">
    <!-- 顶部导航栏 -->
    <header class="navbar">
      <div class="navbar-left">
        <img src="../../logo_seuquant.png" alt="Logo" class="logo" />
        <h1 class="app-title">量化交易选股系统</h1>
      </div>
      <div class="navbar-center">
        <el-menu
          mode="horizontal"
          :default-active="activeMenu"
          class="nav-menu">
          <el-menu-item index="/" @click="$router.push('/')">
            <el-icon><i-ep-home /></el-icon>
            <span>策略管理</span>
          </el-menu-item>
          <el-menu-item
            index="/indicators"
            @click="$router.push('/indicators')">
            <el-icon><i-ep-line-chart /></el-icon>
            <span>指标管理</span>
          </el-menu-item>
          <el-menu-item index="/params" @click="$router.push('/params')">
            <el-icon><i-ep-setting /></el-icon>
            <span>参数管理</span>
          </el-menu-item>
        </el-menu>
      </div>
      <div class="navbar-right">
        <el-button type="text" @click="goBack">
          <el-icon><i-ep-arrow-left /></el-icon>
          返回上一页
        </el-button>
        <el-dropdown>
          <el-button type="primary" icon="User">
            {{ userInfo?.user_name || "用户" }}
            <el-icon class="el-icon--right"><i-ep-caret-bottom /></el-icon>
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
          userInfo?.user_status
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

export default {
  name: "Layout",
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

    // 返回上一页
    const goBack = () => {
      if (window.history.length > 1) {
        window.history.back();
      } else {
        router.push("/");
      }
    };

    // 显示用户信息
    const showUserInfo = () => {
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
}

.logo {
  height: 40px;
  margin-right: 15px;
}

.app-title {
  font-size: 18px;
  font-weight: 600;
  color: #10b981;
  margin: 0;
}

.navbar-center {
  flex: 1;
  display: flex;
  justify-content: center;
}

.nav-menu {
  width: auto !important;
  background-color: transparent !important;
}

.navbar-right {
  display: flex;
  align-items: center;
  gap: 10px;
}

.main-content {
  flex: 1;
  padding: 20px;
  background-color: #f5f5f5;
  overflow-y: auto;
  height: calc(100vh - 60px);
}
</style>
