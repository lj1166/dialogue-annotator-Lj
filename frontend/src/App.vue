<template>
  <el-container class="app-layout">
    <el-header class="app-header">
      <div class="brand">
        <el-icon><ChatDotRound /></el-icon>
        <span>对话质量标注工具</span>
      </div>
      <el-menu mode="horizontal" :ellipsis="false" router :default-active="route.path">
        <el-menu-item index="/annotate">标注工作台</el-menu-item>
        <el-menu-item index="/stats">统计看板</el-menu-item>
      </el-menu>
      <div class="header-actions">
        <el-progress
          :percentage="stats.progress_percent"
          :stroke-width="10"
          style="width: 160px; margin-right: 16px"
        />
        <span class="progress-text">{{ stats.annotated_turns }}/{{ stats.total_assistant_turns }}</span>
        <el-button type="primary" plain @click="download(exportJsonUrl, 'annotations_export.json')">
          导出 JSON
        </el-button>
        <el-button type="success" plain @click="download(exportCsvUrl, 'annotations_export.csv')">
          导出 CSV
        </el-button>
      </div>
    </el-header>
    <el-main>
      <router-view @stats-updated="loadStats" />
    </el-main>
  </el-container>
</template>

<script setup>
import { onMounted, provide, reactive } from 'vue'
import { useRoute } from 'vue-router'
import { ChatDotRound } from '@element-plus/icons-vue'
import { exportCsvUrl, exportJsonUrl, getStats } from './api'

const route = useRoute()
const stats = reactive({
  progress_percent: 0,
  annotated_turns: 0,
  total_assistant_turns: 0,
})

async function loadStats() {
  const { data } = await getStats()
  Object.assign(stats, data)
}

function download(url, filename) {
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  link.click()
}

provide('refreshStats', loadStats)

onMounted(loadStats)
</script>

<style>
* {
  box-sizing: border-box;
}
html,
body,
#app {
  margin: 0;
  height: 100%;
  font-family: 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif;
  background: #f5f7fa;
}
.app-layout {
  min-height: 100vh;
}
.app-header {
  display: flex;
  align-items: center;
  gap: 24px;
  background: #fff;
  border-bottom: 1px solid #ebeef5;
  padding: 0 20px;
}
.brand {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  font-size: 16px;
  color: #303133;
  white-space: nowrap;
}
.header-actions {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 8px;
}
.progress-text {
  font-size: 13px;
  color: #606266;
  margin-right: 8px;
}
.el-main {
  padding: 16px 20px;
}
</style>
