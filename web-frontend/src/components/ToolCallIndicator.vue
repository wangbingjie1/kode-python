<template>
  <div class="tool-call-card bg-gradient-to-r from-indigo-50 to-purple-50 border border-indigo-200 rounded-lg p-4 my-3">
    <div class="flex items-start gap-3">
      <!-- Tool Icon -->
      <div class="tool-icon-wrapper">
        <div class="w-10 h-10 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-lg flex items-center justify-center text-white shadow-md">
          <svg v-if="toolIcon === 'file'" class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          <svg v-else-if="toolIcon === 'terminal'" class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
          </svg>
          <svg v-else-if="toolIcon === 'search'" class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <svg v-else class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
        </div>

        <!-- Pulse Animation for Active Tools -->
        <div v-if="isActive" class="absolute inset-0 rounded-lg bg-indigo-500 animate-ping opacity-20"></div>
      </div>

      <!-- Tool Details -->
      <div class="flex-1 min-w-0">
        <div class="flex items-center gap-2 mb-1">
          <h4 class="font-semibold text-gray-900 text-sm">{{ toolName }}</h4>
          <span
            class="px-2 py-0.5 rounded-full text-xs font-medium"
            :class="statusClass"
          >
            {{ statusText }}
          </span>
        </div>

        <p class="text-sm text-gray-600 mb-2">{{ toolDescription }}</p>

        <!-- Tool Parameters (Collapsible) -->
        <details v-if="params && Object.keys(params).length > 0" class="mt-2">
          <summary class="cursor-pointer text-xs text-indigo-600 hover:text-indigo-800 font-medium">
            查看参数
          </summary>
          <div class="mt-2 bg-white rounded-md p-3 border border-gray-200">
            <pre class="text-xs text-gray-700 overflow-x-auto">{{ formatParams(params) }}</pre>
          </div>
        </details>

        <!-- Tool Result (for completed tools) -->
        <div v-if="result && status === 'completed'" class="mt-3 bg-white rounded-md p-3 border border-green-200">
          <div class="flex items-center gap-2 mb-2">
            <svg class="w-4 h-4 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span class="text-xs font-medium text-green-700">执行结果</span>
          </div>
          <pre class="text-xs text-gray-700 max-h-40 overflow-auto">{{ result }}</pre>
        </div>

        <!-- Error Message -->
        <div v-if="error" class="mt-3 bg-red-50 rounded-md p-3 border border-red-200">
          <div class="flex items-center gap-2 mb-2">
            <svg class="w-4 h-4 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span class="text-xs font-medium text-red-700">执行错误</span>
          </div>
          <pre class="text-xs text-red-700">{{ error }}</pre>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

export interface ToolCall {
  name: string
  description?: string
  params?: Record<string, any>
  status: 'pending' | 'running' | 'completed' | 'error'
  result?: string
  error?: string
}

const props = defineProps<{
  toolCall: ToolCall
}>()

const toolName = computed(() => props.toolCall.name)
const toolDescription = computed(() => props.toolCall.description || '执行工具调用...')
const params = computed(() => props.toolCall.params)
const status = computed(() => props.toolCall.status)
const result = computed(() => props.toolCall.result)
const error = computed(() => props.toolCall.error)
const isActive = computed(() => status.value === 'running')

const toolIcon = computed(() => {
  const name = toolName.value.toLowerCase()
  if (name.includes('file') || name.includes('read') || name.includes('write')) return 'file'
  if (name.includes('bash') || name.includes('execute') || name.includes('command')) return 'terminal'
  if (name.includes('search') || name.includes('grep') || name.includes('find')) return 'search'
  return 'default'
})

const statusClass = computed(() => {
  switch (status.value) {
    case 'pending':
      return 'bg-gray-100 text-gray-700'
    case 'running':
      return 'bg-blue-100 text-blue-700'
    case 'completed':
      return 'bg-green-100 text-green-700'
    case 'error':
      return 'bg-red-100 text-red-700'
    default:
      return 'bg-gray-100 text-gray-700'
  }
})

const statusText = computed(() => {
  switch (status.value) {
    case 'pending':
      return '等待中'
    case 'running':
      return '执行中'
    case 'completed':
      return '已完成'
    case 'error':
      return '失败'
    default:
      return '未知'
  }
})

function formatParams(params: Record<string, any>): string {
  return JSON.stringify(params, null, 2)
}
</script>

<style scoped>
.tool-icon-wrapper {
  position: relative;
}

details summary {
  list-style: none;
}

details summary::-webkit-details-marker {
  display: none;
}

details[open] summary {
  margin-bottom: 0.5rem;
}

pre {
  white-space: pre-wrap;
  word-break: break-word;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
}
</style>
