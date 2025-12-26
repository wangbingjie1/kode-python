<template>
  <div class="fixed inset-0 z-50 flex items-center justify-center bg-black/50" @click.self="handleClose">
    <div class="w-full max-w-2xl rounded-2xl bg-white shadow-2xl max-h-[90vh] flex flex-col">
      <!-- Header -->
      <div class="flex items-center justify-between border-b border-[#eadfd3] px-6 py-4 flex-shrink-0">
        <div>
          <h2 class="text-lg font-semibold text-[#2f2720]">AI 自动分析</h2>
          <p class="mt-1 text-sm text-[#9a8b7c]">
            <template v-if="isAnalyzing">
              正在分析 {{ progress.current }}/{{ progress.total }}...
            </template>
            <template v-else-if="results.length > 0">
              分析完成，已解决 {{ resolvedCount }} 个问题
            </template>
            <template v-else>
              共 {{ pendingCount }} 个待分析问题
            </template>
          </p>
        </div>
        <button
          class="flex h-8 w-8 items-center justify-center rounded-full text-[#9a8b7c] transition hover:bg-[#f0ebe4] hover:text-[#6d5f52]"
          @click="handleClose"
        >
          <svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      <!-- Content -->
      <div class="flex-1 overflow-y-auto px-6 py-4">
        <!-- 未开始：显示开始按钮 -->
        <div v-if="!isAnalyzing && results.length === 0 && !errorMessage" class="text-center py-12">
          <div class="mx-auto h-16 w-16 rounded-full bg-gradient-to-br from-[#5c4f43] to-[#7c6551] flex items-center justify-center mb-4">
            <svg class="h-8 w-8 text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M9.75 3.104v5.714a2.25 2.25 0 01-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.301 24.301 0 014.5 0m0 0v5.714c0 .597.237 1.17.659 1.591L19 14.5M14.25 3.104c.251.023.501.05.75.082M19 14.5l-2.47 2.47a2.25 2.25 0 01-1.591.659H9.061a2.25 2.25 0 01-1.591-.659L5 14.5m14 0l.94 2.06a2.25 2.25 0 01-2.093 3.19H6.153a2.25 2.25 0 01-2.093-3.19L5 14.5" />
            </svg>
          </div>
          <p class="text-[#6d5f52] mb-2">AI 将自动分析待回答的问题</p>
          <p class="text-sm text-[#9a8b7c] mb-6">通过查询数据库数据来验证和解决不确定性问题</p>
          <button
            class="rounded-xl bg-gradient-to-r from-[#5c4f43] to-[#7c6551] px-8 py-3 text-white font-medium transition hover:opacity-90"
            @click="startAnalysis"
          >
            开始分析
          </button>
        </div>

        <!-- 错误状态 -->
        <div v-else-if="errorMessage" class="text-center py-12">
          <div class="mx-auto h-16 w-16 rounded-full bg-rose-100 flex items-center justify-center mb-4">
            <svg class="h-8 w-8 text-rose-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
          </div>
          <p class="text-rose-600 mb-4">{{ errorMessage }}</p>
          <button
            class="rounded-lg bg-[#f0ebe4] px-4 py-2 text-sm text-[#6d5f52] transition hover:bg-[#e5ddd3]"
            @click="errorMessage = ''; startAnalysis()"
          >
            重试
          </button>
        </div>

        <!-- 分析中：显示进度 -->
        <div v-else-if="isAnalyzing" class="space-y-4">
          <!-- 进度条 -->
          <div class="rounded-xl bg-[#f8f6f3] p-4">
            <div class="flex justify-between text-sm mb-2">
              <span class="text-[#6d5f52]">{{ currentQuestion || '准备中...' }}</span>
              <span class="font-medium text-[#5c4f43]">{{ progress.current }}/{{ progress.total }}</span>
            </div>
            <div class="h-2 w-full overflow-hidden rounded-full bg-[#e5ddd3]">
              <div
                class="h-full bg-gradient-to-r from-[#5c4f43] to-[#7c6551] transition-all duration-300"
                :style="{ width: `${progress.total > 0 ? (progress.current / progress.total) * 100 : 0}%` }"
              />
            </div>
          </div>

          <!-- 已完成的结果 -->
          <div v-if="results.length > 0" class="space-y-3">
            <AIAnalysisResultItem
              v-for="result in results"
              :key="result.question_id"
              :result="result"
              :accepting="acceptingIds.includes(result.question_id)"
              @accept="acceptAnswer(result)"
              @ignore="ignoreAnswer(result)"
            />
          </div>
        </div>

        <!-- 分析完成：显示结果列表 -->
        <div v-else-if="results.length > 0" class="space-y-4">
          <!-- 统计信息 -->
          <div class="rounded-xl bg-[#f8f6f3] p-4">
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-4 text-sm flex-wrap">
                <span class="flex items-center gap-1.5">
                  <span class="h-2 w-2 rounded-full bg-emerald-500"></span>
                  已解决: {{ resolvedCount }}
                </span>
                <span class="flex items-center gap-1.5">
                  <span class="h-2 w-2 rounded-full bg-amber-500"></span>
                  部分解决: {{ partialCount }}
                </span>
                <span v-if="skippedCount > 0" class="flex items-center gap-1.5">
                  <span class="h-2 w-2 rounded-full bg-slate-400"></span>
                  需人工: {{ skippedCount }}
                </span>
                <span v-if="failedCount > 0" class="flex items-center gap-1.5">
                  <span class="h-2 w-2 rounded-full bg-rose-500"></span>
                  失败: {{ failedCount }}
                </span>
              </div>
              <span class="text-xs text-[#9a8b7c]">
                {{ acceptedCount }} 个已采纳
              </span>
            </div>
          </div>

          <!-- 结果列表 -->
          <div class="space-y-3">
            <AIAnalysisResultItem
              v-for="result in results"
              :key="result.question_id"
              :result="result"
              :accepting="acceptingIds.includes(result.question_id)"
              @accept="acceptAnswer(result)"
              @ignore="ignoreAnswer(result)"
            />
          </div>
        </div>
      </div>

      <!-- Footer -->
      <div class="flex justify-end gap-3 border-t border-[#eadfd3] px-6 py-4 flex-shrink-0">
        <button
          v-if="isAnalyzing"
          class="rounded-lg bg-rose-100 px-4 py-2 text-sm font-medium text-rose-600 transition hover:bg-rose-200"
          @click="cancelAnalysis"
        >
          取消分析
        </button>
        <button
          class="rounded-lg bg-[#f0ebe4] px-4 py-2 text-sm font-medium text-[#6d5f52] transition hover:bg-[#e5ddd3]"
          @click="handleClose"
        >
          {{ results.length > 0 ? '完成' : '关闭' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onUnmounted } from 'vue'
import { acceptAIAnswer } from '@/services/api'
import AIAnalysisResultItem from './AIAnalysisResultItem.vue'

interface AnalysisResult {
  question_id: string
  question: string
  status: 'resolved' | 'partial' | 'failed' | 'skipped'
  answer?: string
  confidence?: 'high' | 'medium' | 'low'
  reasoning?: string
  error?: string
  // 前端状态
  accepted?: boolean
  ignored?: boolean
}

interface Props {
  connectionName: string
  pendingCount: number
}

const props = defineProps<Props>()

const emit = defineEmits<{
  close: []
  accepted: []
}>()

// 状态
const isAnalyzing = ref(false)
const errorMessage = ref('')
const progress = ref({ current: 0, total: 0 })
const currentQuestion = ref('')
const results = ref<AnalysisResult[]>([])
const acceptingIds = ref<string[]>([])
let eventSource: EventSource | null = null

// 计算属性
const resolvedCount = computed(() => results.value.filter(r => r.status === 'resolved').length)
const partialCount = computed(() => results.value.filter(r => r.status === 'partial').length)
const failedCount = computed(() => results.value.filter(r => r.status === 'failed').length)
const skippedCount = computed(() => results.value.filter(r => r.status === 'skipped').length)
const acceptedCount = computed(() => results.value.filter(r => r.accepted).length)

// 开始分析
const startAnalysis = () => {
  isAnalyzing.value = true
  errorMessage.value = ''
  results.value = []
  progress.value = { current: 0, total: 0 }

  // 构建 SSE URL（EventSource 不支持自定义 headers，需要通过 query parameter 传递 token）
  const baseUrl = import.meta.env.VITE_API_BASE_URL || ''
  const token = localStorage.getItem('access_token')
  let url = `${baseUrl}/api/uncertainty/sidebar/ai-analyze?connection_name=${encodeURIComponent(props.connectionName)}`
  if (token) {
    url += `&token=${encodeURIComponent(token)}`
  }

  eventSource = new EventSource(url)

  eventSource.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)
      handleSSEEvent(data)
    } catch (e) {
      console.error('解析 SSE 数据失败:', e)
    }
  }

  eventSource.onerror = (error) => {
    console.error('SSE 连接错误:', error)
    if (isAnalyzing.value) {
      errorMessage.value = '连接中断，请重试'
      isAnalyzing.value = false
    }
    eventSource?.close()
  }
}

// 处理 SSE 事件
const handleSSEEvent = (data: any) => {
  switch (data.type) {
    case 'start':
      progress.value.total = data.metadata?.analyzable_count || data.metadata?.total_questions || 0
      break

    case 'progress':
      progress.value.current = data.metadata?.current || 0
      progress.value.total = data.metadata?.total || progress.value.total
      currentQuestion.value = data.metadata?.question || ''
      break

    case 'question_result':
      results.value.push({
        question_id: data.metadata?.question_id,
        question: data.metadata?.question,
        status: data.metadata?.status || 'failed',
        answer: data.metadata?.answer || data.content,
        confidence: data.metadata?.confidence,
        reasoning: data.metadata?.reasoning,
        error: data.metadata?.error,
      })
      break

    case 'complete':
      isAnalyzing.value = false
      eventSource?.close()
      break

    case 'error':
      errorMessage.value = data.content || '分析失败'
      isAnalyzing.value = false
      eventSource?.close()
      break

    case 'cancelled':
      isAnalyzing.value = false
      eventSource?.close()
      break
  }
}

// 取消分析
const cancelAnalysis = () => {
  eventSource?.close()
  isAnalyzing.value = false
}

// 记录是否有任何采纳操作（用于关闭时通知父组件刷新）
const hasAccepted = ref(false)

// 采纳答案
const acceptAnswer = async (result: AnalysisResult) => {
  if (!result.answer || result.accepted) return

  acceptingIds.value.push(result.question_id)

  try {
    await acceptAIAnswer({
      connection_name: props.connectionName,
      uncertainty_id: result.question_id,
      answer: result.answer,
      confidence: result.confidence,
      reasoning: result.reasoning,
    })

    result.accepted = true
    hasAccepted.value = true
    // 不在这里 emit('accepted')，等关闭弹窗时再统一刷新
  } catch (error: any) {
    console.error('采纳答案失败:', error)
    errorMessage.value = error.message || '采纳失败'
  } finally {
    acceptingIds.value = acceptingIds.value.filter(id => id !== result.question_id)
  }
}

// 忽略答案
const ignoreAnswer = (result: AnalysisResult) => {
  result.ignored = true
}

// 关闭弹窗
const handleClose = () => {
  if (isAnalyzing.value) {
    cancelAnalysis()
  }
  // 如果有采纳过答案，通知父组件刷新列表
  if (hasAccepted.value) {
    emit('accepted')
  }
  emit('close')
}

// 清理
onUnmounted(() => {
  eventSource?.close()
})
</script>
