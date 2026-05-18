<template>
  <el-row :gutter="16">
    <el-col :span="8">
      <el-card shadow="never">
        <template #header>标注进度</template>
        <div ref="progressRef" class="chart-box" />
        <el-statistic title="已完成" :value="stats.annotated_turns" />
        <el-statistic title="总计" :value="stats.total_assistant_turns" class="stat-gap" />
      </el-card>
    </el-col>
    <el-col :span="8">
      <el-card shadow="never">
        <template #header>准确性分布</template>
        <div ref="accurateRef" class="chart-box" />
        <p class="chart-hint">基于已标注 {{ stats.annotated_turns }} 条</p>
      </el-card>
    </el-col>
    <el-col :span="8">
      <el-card shadow="never">
        <template #header>跑题 / 编造统计</template>
        <div ref="qualityRef" class="chart-box" />
        <p class="chart-hint">左右分别为两个独立维度，各占已标注条数 100%</p>
      </el-card>
    </el-col>
  </el-row>
</template>

<script setup>
import { inject, onMounted, onUnmounted, reactive, ref } from 'vue'
import * as echarts from 'echarts'
import { getStats } from '../api'

const refreshStats = inject('refreshStats', () => {})
const stats = reactive({
  annotated_turns: 0,
  total_assistant_turns: 0,
  progress_percent: 0,
  accurate_count: 0,
  inaccurate_count: 0,
  off_topic_count: 0,
  on_topic_count: 0,
  fabricated_count: 0,
  not_fabricated_count: 0,
})

const progressRef = ref(null)
const accurateRef = ref(null)
const qualityRef = ref(null)
let charts = []

async function load() {
  const { data } = await getStats()
  Object.assign(stats, data)
  renderCharts()
  refreshStats?.()
}

function pieTooltip(total) {
  return {
    trigger: 'item',
    formatter: (p) => {
      const pct = total ? ((p.value / total) * 100).toFixed(1) : 0
      return `${p.name}<br/>${p.value} 条（占已标注 ${pct}%）`
    },
  }
}

function renderCharts() {
  charts.forEach((c) => c.dispose())
  charts = []

  const progress = echarts.init(progressRef.value)
  progress.setOption({
    series: [
      {
        type: 'gauge',
        min: 0,
        max: 100,
        progress: { show: true },
        detail: { formatter: '{value}%', fontSize: 18 },
        data: [{ value: stats.progress_percent, name: '完成率' }],
      },
    ],
  })

  const accurate = echarts.init(accurateRef.value)
  accurate.setOption({
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: ['准确', '不准确'] },
    yAxis: { type: 'value', minInterval: 1 },
    series: [
      {
        type: 'bar',
        data: [stats.accurate_count, stats.inaccurate_count],
        itemStyle: {
          color: (p) => (p.dataIndex === 0 ? '#67c23a' : '#f56c6c'),
        },
      },
    ],
  })

  const n = stats.annotated_turns
  const quality = echarts.init(qualityRef.value)
  quality.setOption({
    tooltip: pieTooltip(n),
    legend: { bottom: 0, itemGap: 16 },
    title: [
      { text: '是否跑题', left: '22%', top: '6%', textAlign: 'center', textStyle: { fontSize: 13 } },
      { text: '是否编造', left: '72%', top: '6%', textAlign: 'center', textStyle: { fontSize: 13 } },
    ],
    series: [
      {
        type: 'pie',
        radius: '48%',
        center: ['25%', '52%'],
        label: { formatter: '{b}\n{c}' },
        color: ['#f56c6c', '#67c23a'],
        data: [
          { value: stats.off_topic_count, name: '跑题' },
          { value: stats.on_topic_count, name: '不跑题' },
        ],
      },
      {
        type: 'pie',
        radius: '48%',
        center: ['75%', '52%'],
        label: { formatter: '{b}\n{c}' },
        color: ['#e6a23c', '#409eff'],
        data: [
          { value: stats.fabricated_count, name: '有编造' },
          { value: stats.not_fabricated_count, name: '无编造' },
        ],
      },
    ],
  })

  charts = [progress, accurate, quality]
}

function onResize() {
  charts.forEach((c) => c.resize())
}

onMounted(async () => {
  await load()
  window.addEventListener('resize', onResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', onResize)
  charts.forEach((c) => c.dispose())
})

defineExpose({ load })
</script>

<style scoped>
.chart-box {
  height: 280px;
}
.stat-gap {
  margin-top: 12px;
}
.chart-hint {
  margin: 0;
  font-size: 12px;
  color: #909399;
  text-align: center;
}
</style>
