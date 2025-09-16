<script setup>
import { ref } from "vue";
const matplotlibImage = ref("");
const plotlyData = ref(null);
const loading = ref(false);
const error = ref("");

async function fetchMatplotlibPng() {
  loading.value = true;
  error.value = "";
  try {
    const res = await fetch("http://localhost:5000/api/plot/matplotlib-png");
    if (!res.ok) throw new Error("请求失败");
    const data = await res.json();
    matplotlibImage.value = data.image;
  } catch (e) {
    error.value = e.message || "请求出错";
  } finally {
    loading.value = false;
  }
}

async function fetchPlotlyChart() {
  loading.value = true;
  error.value = "";
  try {
    const res = await fetch(
      "http://localhost:5000/api/plot/plotly-interactive"
    );
    if (!res.ok) throw new Error("请求失败");
    const data = await res.json();
    plotlyData.value = data.plot_data;

    // 使用Plotly.js渲染（需要先引入plotly.js）
    setTimeout(() => {
      if (window.Plotly && plotlyData.value) {
        window.Plotly.newPlot(
          "plotly-chart",
          plotlyData.value.data,
          plotlyData.value.layout
        );
      }
    }, 100);
  } catch (e) {
    error.value = e.message || "请求出错";
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <h1>Matplotlib & Plotly 交互式图表 Demo</h1>

  <div style="margin: 1em 0">
    <button
      @click="fetchMatplotlibPng"
      :disabled="loading"
      style="margin-right: 1em">
      {{ loading ? "加载中..." : "获取Matplotlib静态图" }}
    </button>
    <button @click="fetchPlotlyChart" :disabled="loading">
      {{ loading ? "加载中..." : "获取Plotly交互式图" }}
    </button>
  </div>

  <div v-if="error" style="color: red; margin: 1em 0">{{ error }}</div>

  <!-- Matplotlib静态图展示 -->
  <div
    v-if="matplotlibImage"
    style="margin-top: 2em; border: 1px solid #eee; padding: 1em">
    <h3>Matplotlib生成的静态图：</h3>
    <img
      :src="matplotlibImage"
      alt="Matplotlib图表"
      style="max-width: 100%; height: auto" />
  </div>

  <!-- Plotly交互式图展示 -->
  <div
    v-if="plotlyData"
    style="margin-top: 2em; border: 1px solid #eee; padding: 1em">
    <h3>Plotly交互式图表：</h3>
    <div id="plotly-chart" style="width: 100%; height: 400px"></div>
    <p style="font-size: 0.9em; color: #666; margin-top: 1em">
      ⚠️ 需要引入Plotly.js才能显示交互功能
    </p>
  </div>
</template>

<style scoped></style>
