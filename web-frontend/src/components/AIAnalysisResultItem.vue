<template>
  <div
    class="rounded-xl border p-4 transition"
    :class="itemClass"
  >
    <div class="flex items-start gap-3">
      <!-- 状态图标 -->
      <div
        class="mt-0.5 flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full"
        :class="iconClass"
      >
        <svg v-if="result.status === 'resolved'" class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" />
        </svg>
        <svg v-else-if="result.status === 'partial'" class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v2m0 4h.01" />
        </svg>
        <svg v-else-if="result.status === 'skipped'" class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
        </svg>
        <svg v-else class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
        </svg>
      </div>

      <!-- 内容 -->
      <div class="flex-1 min-w-0">
        <!-- 问题 -->
        <p class="text-sm font-medium text-[#3d3430] leading-relaxed">
          {{ result.question }}
        </p>

        <!-- AI 答案 -->
        <div v-if="result.answer && !result.error" class="mt-2 rounded-lg bg-blue-50 p-3">
          <p class="text-sm text-blue-700 whitespace-pre-wrap">{{ result.answer }}</p>
          <div class="mt-2 flex items-center gap-3 text-xs">
            <span v-if="result.confidence" class="text-blue-500">
              置信度: {{ confidenceLabel }}
            </span>
            <button
              v-if="result.reasoning"
              class="text-blue-600 hover:underline"
              @click="showReasoning = !showReasoning"
            >
              {{ showReasoning ? '收起推理' : '查看推理' }}
            </button>
          </div>
          <!-- 推理过程 -->
          <div v-if="showReasoning && result.reasoning" class="mt-2 pt-2 border-t border-blue-100">
            <p class="text-xs text-blue-600 whitespace-pre-wrap">{{ result.reasoning }}</p>
          </div>
        </div>

        <!-- 错误/跳过信息 -->
        <div
          v-if="result.error"
          class="mt-2 rounded-lg p-3"
          :class="result.status === 'skipped' ? 'bg-slate-50' : 'bg-rose-50'"
        >
          <p class="text-sm" :class="result.status === 'skipped' ? 'text-slate-600' : 'text-rose-600'">
            {{ result.error }}
          </p>
        </div>

        <!-- 已采纳/已忽略状态 -->
        <div v-if="result.accepted" class="mt-2 flex items-center gap-1.5 text-xs text-emerald-600">
          <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" />
          </svg>
          已采纳
        </div>
        <div v-else-if="result.ignored" class="mt-2 text-xs text-[#9a8b7c]">
          已忽略
        </div>
      </div>

      <!-- 操作按钮 -->
      <div v-if="!result.accepted && !result.ignored && result.answer" class="flex flex-shrink-0 gap-2">
        <button
          class="rounded-lg bg-emerald-500 px-3 py-1.5 text-xs font-medium text-white transition hover:bg-emerald-600 disabled:opacity-50"
          :disabled="accepting"
          @click="$emit('accept')"
        >
          {{ accepting ? '保存...' : '采纳' }}
        </button>
        <button
          class="rounded-lg bg-[#f0ebe4] px-3 py-1.5 text-xs font-medium text-[#6d5f52] transition hover:bg-[#e5ddd3]"
          @click="$emit('ignore')"
        >
          忽略
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'

interface AnalysisResult {
  question_id: string
  question: string
  status: 'resolved' | 'partial' | 'failed' | 'skipped'
  answer?: string
  confidence?: 'high' | 'medium' | 'low'
  reasoning?: string
  error?: string
  accepted?: boolean
  ignored?: boolean
}

interface Props {
  result: AnalysisResult
  accepting?: boolean
}

const props = defineProps<Props>()

defineEmits<{
  accept: []
  ignore: []
}>()

const showReasoning = ref(false)

const itemClass = computed(() => {
  if (props.result.accepted) {
    return 'border-emerald-200 bg-emerald-50/50'
  }
  if (props.result.ignored) {
    return 'border-[#eadfd3] bg-[#faf8f5] opacity-60'
  }
  switch (props.result.status) {
    case 'resolved':
      return 'border-emerald-200 bg-white'
    case 'partial':
      return 'border-amber-200 bg-white'
    case 'failed':
      return 'border-rose-200 bg-white'
    case 'skipped':
      return 'border-slate-200 bg-slate-50/50'
    default:
      return 'border-[#eadfd3] bg-white'
  }
})

const iconClass = computed(() => {
  switch (props.result.status) {
    case 'resolved':
      return 'bg-emerald-100 text-emerald-600'
    case 'partial':
      return 'bg-amber-100 text-amber-600'
    case 'failed':
      return 'bg-rose-100 text-rose-600'
    case 'skipped':
      return 'bg-slate-100 text-slate-500'
    default:
      return 'bg-gray-100 text-gray-600'
  }
})

const confidenceLabel = computed(() => {
  switch (props.result.confidence) {
    case 'high':
      return '高'
    case 'medium':
      return '中'
    case 'low':
      return '低'
    default:
      return props.result.confidence
  }
})
</script>
