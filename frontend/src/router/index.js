import { createRouter, createWebHistory } from "vue-router";

// 路由配置
const routes = [
  {
    path: "/login",
    name: "Login",
    component: () => import("../views/Login.vue"),
    meta: {
      requiresAuth: false,
    },
  },
  {
    path: "/register",
    name: "Register",
    component: () => import("../views/Register.vue"),
    meta: {
      requiresAuth: false,
    },
  },
  {
    path: "/",
    name: "Layout",
    component: () => import("../components/Layout.vue"),
    meta: {
      requiresAuth: true,
    },
    children: [
      {
        path: "",
        name: "StrategyList",
        component: () => import("../views/StrategyList.vue"),
      },
      {
        path: "strategy/:creatorName/:strategyName",
        name: "StrategyDetail",
        component: () => import("../views/StrategyDetail.vue"),
        props: true,
      },
      {
        path: "indicators",
        name: "IndicatorManagement",
        component: () => import("../views/IndicatorList.vue"),
      },
      {
        path: "params",
        name: "ParamManagement",
        component: () => import("../views/ParamList.vue"),
      },
      {
        path: "backtest",
        name: "HistoricalBacktestList",
        component: () => import("../views/HistoricalBacktestList.vue"),
      },
      {
        path: "messages",
        name: "MessageBox",
        component: () => import("../views/MessageBox.vue"),
      },
    ],
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

// 路由守卫
router.beforeEach((to, from, next) => {
  const isAuthenticated = localStorage.getItem("token") !== null;

  if (to.meta.requiresAuth && !isAuthenticated) {
    next("/login");
  } else if (
    (to.path === "/login" || to.path === "/register") &&
    isAuthenticated
  ) {
    next("/");
  } else {
    next();
  }
});

export default router;
