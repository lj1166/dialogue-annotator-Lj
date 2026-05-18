<template>
  <el-row :gutter="16" class="annotate-layout" align="stretch">
    <el-col :span="6" class="col-panel">
      <el-card shadow="never" class="panel-card panel-fill">
        <template #header>
          <div class="card-header">
            <span>对话列表</span>
            <el-tag size="small" type="info">{{ conversations.length }} 条</el-tag>
          </div>
        </template>
        <el-input
          v-model="keyword"
          placeholder="搜索对话内容"
          clearable
          :prefix-icon="Search"
          class="search-input"
        />
        <el-scrollbar class="panel-scroll">
          <div
            v-for="item in filteredList"
            :key="item.id"
            class="conv-item"
            :class="{ active: item.id === currentId }"
            @click="selectConversation(item.id)"
          >
            <div class="conv-top">
              <span class="conv-id">#{{ item.id }}</span>
              <el-tag v-if="item.fully_annotated" type="success" size="small">已完成</el-tag>
              <el-tag v-else-if="item.annotated_turns > 0" type="warning" size="small">进行中</el-tag>
              <el-tag v-else type="info" size="small">未标注</el-tag>
            </div>
            <p class="conv-preview">{{ item.preview }}</p>
          </div>
        </el-scrollbar>
      </el-card>
    </el-col>

    <el-col :span="11" class="col-panel col-center">
      <el-card shadow="never" class="panel-card panel-chat">
        <template #header>
          <div class="card-header">
            <span>对话 #{{ currentId || '-' }}</span>
            <div>
              <el-button :disabled="!prevId" @click="selectConversation(prevId)">上一条</el-button>
              <el-button :disabled="!nextId" type="primary" @click="selectConversation(nextId)">
                下一条
              </el-button>
            </div>
          </div>
        </template>
        <el-empty v-if="!conversation" description="请选择对话" />
        <el-scrollbar v-else class="chat-scroll">
          <div
            v-for="(turn, index) in conversation.turns"
            :key="index"
            class="turn-row"
            :class="{ selected: index === currentTurnIndex }"
            @click="onTurnClick(index, turn.role)"
          >
            <el-avatar :size="36" :class="turn.role">
              {{ turn.role === 'user' ? '用' : '客' }}
            </el-avatar>
            <div class="bubble" :class="turn.role">
              <div class="role-label">{{ turn.role === 'user' ? '用户' : '客服' }}</div>
              <p>{{ turn.content }}</p>
              <el-tag
                v-if="turn.role === 'assistant' && isTurnAnnotated(index)"
                size="small"
                type="success"
                class="done-tag"
              >
                已标注
              </el-tag>
            </div>
          </div>
        </el-scrollbar>
      </el-card>

      <el-card shadow="never" class="panel-card panel-chart">
        <template #header><span>当前进度</span></template>
        <div ref="miniChartRef" class="mini-chart" />
      </el-card>
    </el-col>

    <el-col :span="7" class="col-panel">
      <el-card shadow="never" class="panel-card panel-annotation panel-fill">
        <template #header><span>质量标注</span></template>
        <el-empty
          v-if="currentTurnIndex === null"
          class="annotation-empty"
          description="点击客服回复进行标注"
        />
        <template v-else>
          <el-scrollbar class="annotation-scroll">
            <el-alert
              title="对每条客服回复标注：是否准确、是否跑题、是否有编造信息"
              type="info"
              :closable="false"
              show-icon
              class="hint"
            />
            <el-card v-if="showAiResult" shadow="never" class="ai-result-card">
              <template #header>
                <span>AI 建议结果</span>
                <el-tag size="small" type="warning">仅供参考</el-tag>
              </template>
              <el-descriptions :column="1" border size="small">
                <el-descriptions-item label="准确性">{{ labelAccurate }}</el-descriptions-item>
                <el-descriptions-item label="是否跑题">{{ labelOffTopic }}</el-descriptions-item>
                <el-descriptions-item label="编造信息">{{ labelFabricated }}</el-descriptions-item>
                <el-descriptions-item v-if="aiReason" label="理由">{{ aiReason }}</el-descriptions-item>
              </el-descriptions>
            </el-card>
            <el-form label-position="top" class="label-form">
              <el-form-item label="是否准确">
                <el-radio-group v-model="form.accurate">
                  <el-radio :label="true">准确</el-radio>
                  <el-radio :label="false">不准确</el-radio>
                </el-radio-group>
              </el-form-item>
              <el-form-item label="是否跑题">
                <el-radio-group v-model="form.off_topic">
                  <el-radio :label="false">不跑题</el-radio>
                  <el-radio :label="true">跑题</el-radio>
                </el-radio-group>
              </el-form-item>
              <el-form-item label="是否有编造信息">
                <el-radio-group v-model="form.fabricated">
                  <el-radio :label="false">无编造</el-radio>
                  <el-radio :label="true">有编造</el-radio>
                </el-radio-group>
              </el-form-item>
              <el-form-item label="备注">
                <el-input v-model="form.note" type="textarea" :rows="3" placeholder="可选备注" />
              </el-form-item>
            </el-form>
          </el-scrollbar>
          <div class="form-actions">
            <el-button type="warning" :loading="aiLoading" @click="requestAi">
              AI 建议 (Ollama)
            </el-button>
            <el-button type="primary" :loading="saving" @click="save">保存标注</el-button>
          </div>
        </template>
      </el-card>
    </el-col>
  </el-row>
</template>

<script setup>
import { computed, inject, nextTick, onMounted, onUnmounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Search } from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import {
  aiSuggest,
  getAnnotation,
  getConversation,
  getConversations,
  getStats,
  saveAnnotation,
} from '../api'

const emit = defineEmits(['stats-updated'])
const refreshStats = inject('refreshStats', () => {})

const conversations = ref([])
const conversation = ref(null)
const currentId = ref('')
const currentTurnIndex = ref(null)
const keyword = ref('')
const saving = ref(false)
const aiLoading = ref(false)
const aiReason = ref('')
const hasAiFilled = ref(false)
const annotationMap = ref({})
const miniChartRef = ref(null)
let miniChart = null

const form = reactive({
  accurate: null,
  off_topic: null,
  fabricated: null,
  note: '',
})

const filteredList = computed(() => {
  if (!keyword.value) return conversations.value
  const k = keyword.value.toLowerCase()
  return conversations.value.filter((c) => c.preview.toLowerCase().includes(k) || c.id.includes(k))
})

const ids = computed(() => conversations.value.map((c) => c.id))
const prevId = computed(() => {
  const i = ids.value.indexOf(currentId.value)
  return i > 0 ? ids.value[i - 1] : ''
})
const nextId = computed(() => {
  const i = ids.value.indexOf(currentId.value)
  return i >= 0 && i < ids.value.length - 1 ? ids.value[i + 1] : ''
})

const showAiResult = computed(
  () => hasAiFilled.value || !!aiReason.value || form.accurate !== null
)

const labelAccurate = computed(() => {
  if (form.accurate === true) return '准确'
  if (form.accurate === false) return '不准确'
  return '未选择'
})
const labelOffTopic = computed(() => {
  if (form.off_topic === true) return '跑题'
  if (form.off_topic === false) return '不跑题'
  return '未选择'
})
const labelFabricated = computed(() => {
  if (form.fabricated === true) return '有编造'
  if (form.fabricated === false) return '无编造'
  return '未选择'
})

function isTurnAnnotated(index) {
  const key = `${currentId.value}:${index}`
  const ann = annotationMap.value[key]
  return ann && ann.accurate !== null && ann.off_topic !== null && ann.fabricated !== null
}

async function loadList() {
  const { data } = await getConversations()
  conversations.value = data
  if (!currentId.value && data.length) {
    await selectConversation(data[0].id)
  }
}

async function selectConversation(id) {
  currentId.value = id
  currentTurnIndex.value = null
  hasAiFilled.value = false
  const { data } = await getConversation(id)
  conversation.value = data
  const firstAssistant = data.turns.findIndex((t) => t.role === 'assistant')
  if (firstAssistant >= 0) {
    await onTurnClick(firstAssistant, 'assistant')
  }
  await refreshMiniChart()
}

async function onTurnClick(index, role) {
  if (role !== 'assistant') {
    ElMessage.info('请选中客服(assistant)回复进行标注')
    return
  }
  currentTurnIndex.value = index
  aiReason.value = ''
  hasAiFilled.value = false
  Object.assign(form, { accurate: null, off_topic: null, fabricated: null, note: '' })
  try {
    const { data } = await getAnnotation(currentId.value, index)
    if (data) {
      form.accurate = data.accurate
      form.off_topic = data.off_topic
      form.fabricated = data.fabricated
      form.note = data.note || ''
      aiReason.value = data.ai_reason || ''
      hasAiFilled.value = !!(data.ai_reason || data.accurate !== null)
    }
  } catch {
    /* 无历史标注 */
  }
}

async function save() {
  if (currentTurnIndex.value === null) return
  if (form.accurate === null || form.off_topic === null || form.fabricated === null) {
    ElMessage.warning('请完成三个维度的标注')
    return
  }
  saving.value = true
  try {
    await saveAnnotation({
      conversation_id: currentId.value,
      turn_index: currentTurnIndex.value,
      accurate: form.accurate,
      off_topic: form.off_topic,
      fabricated: form.fabricated,
      note: form.note,
    })
    const key = `${currentId.value}:${currentTurnIndex.value}`
    annotationMap.value[key] = { ...form }
    ElMessage.success('保存成功')
    await loadList()
    refreshStats?.()
    emit('stats-updated')
    await refreshMiniChart()
  } finally {
    saving.value = false
  }
}

async function requestAi() {
  if (currentTurnIndex.value === null) return
  aiLoading.value = true
  try {
    const { data } = await aiSuggest({
      conversation_id: currentId.value,
      turn_index: currentTurnIndex.value,
    })
    aiReason.value = data.reason || ''
    if (!data.available) {
      ElMessage.warning(data.message || 'AI 不可用，请手动标注')
      return
    }
    if (data.accurate !== null && data.accurate !== undefined) form.accurate = data.accurate
    if (data.off_topic !== null && data.off_topic !== undefined) form.off_topic = data.off_topic
    if (data.fabricated !== null && data.fabricated !== undefined) form.fabricated = data.fabricated
    hasAiFilled.value = true
    const filled =
      data.accurate !== null && data.off_topic !== null && data.fabricated !== null
    if (filled) {
      ElMessage.success('AI 建议已填入，请确认后保存')
    } else {
      ElMessage.warning('AI 返回不完整，请根据理由手动选择标签')
    }
  } catch (err) {
    const msg = err.response?.data?.detail || err.message || '请求失败'
    ElMessage.error(`AI 建议失败：${msg}`)
  } finally {
    aiLoading.value = false
  }
}

async function refreshMiniChart() {
  const { data } = await getStats()
  await nextTick()
  if (!miniChartRef.value) return
  if (!miniChart) miniChart = echarts.init(miniChartRef.value)
  miniChart.setOption({
    tooltip: { trigger: 'item' },
    series: [
      {
        type: 'pie',
        radius: ['45%', '70%'],
        label: { show: true, formatter: '{b}\n{d}%' },
        data: [
          { value: data.annotated_turns, name: '已标注', itemStyle: { color: '#67c23a' } },
          {
            value: data.total_assistant_turns - data.annotated_turns,
            name: '未标注',
            itemStyle: { color: '#dcdfe6' },
          },
        ],
      },
    ],
  })
  miniChart.resize()
}

function resizeChart() {
  miniChart?.resize()
}

onMounted(async () => {
  await loadList()
  window.addEventListener('resize', resizeChart)
})

onUnmounted(() => {
  window.removeEventListener('resize', resizeChart)
  miniChart?.dispose()
})
</script>

<style scoped>
.annotate-layout {
  height: calc(100vh - 88px);
  min-height: 560px;
}

.col-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.col-center {
  gap: 12px;
}

.panel-card {
  border-radius: 8px;
  display: flex;
  flex-direction: column;
}

.panel-fill {
  flex: 1;
  min-height: 0;
  height: 100%;
}

.panel-chat {
  flex: 1;
  min-height: 0;
}

.panel-annotation {
  flex: 1;
  min-height: 0;
  height: 100%;
}

.panel-annotation :deep(.el-card__body) {
  overflow: hidden;
}

.annotation-empty {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}

.panel-chart {
  flex-shrink: 0;
}

.panel-card :deep(.el-card__body) {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  padding-bottom: 12px;
}

.panel-scroll,
.chat-scroll,
.annotation-scroll {
  flex: 1;
  min-height: 0;
}

.chat-scroll {
  height: 100%;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.search-input {
  margin-bottom: 12px;
  flex-shrink: 0;
}

.conv-item {
  padding: 10px 12px;
  border-radius: 8px;
  cursor: pointer;
  margin-bottom: 8px;
  border: 1px solid transparent;
  transition: all 0.2s;
}

.conv-item:hover {
  background: #f5f7fa;
}

.conv-item.active {
  background: #ecf5ff;
  border-color: #b3d8ff;
}

.conv-top {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.conv-id {
  font-weight: 600;
  color: #409eff;
}

.conv-preview {
  margin: 0;
  font-size: 13px;
  color: #606266;
  line-height: 1.4;
}

.turn-row {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
  padding: 8px;
  border-radius: 8px;
  cursor: pointer;
}

.turn-row.selected {
  background: #fdf6ec;
}

.el-avatar.user {
  background: #409eff;
}

.el-avatar.assistant {
  background: #67c23a;
}

.bubble {
  flex: 1;
  padding: 12px 14px;
  border-radius: 8px;
  background: #fff;
  border: 1px solid #ebeef5;
}

.bubble.user {
  border-left: 3px solid #409eff;
}

.bubble.assistant {
  border-left: 3px solid #67c23a;
}

.role-label {
  font-size: 12px;
  color: #909399;
  margin-bottom: 4px;
}

.bubble p {
  margin: 0;
  line-height: 1.6;
  color: #303133;
}

.done-tag {
  margin-top: 8px;
}

.hint {
  margin-bottom: 12px;
}

.ai-result-card {
  margin-bottom: 12px;
  background: #fdf6ec;
  border: 1px solid #faecd8;
}

.ai-result-card :deep(.el-card__header) {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
}

.label-form {
  padding-bottom: 8px;
}

.form-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  padding-top: 12px;
  border-top: 1px solid #ebeef5;
  flex-shrink: 0;
}

.mini-chart {
  height: 180px;
}
</style>
