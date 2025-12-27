<template>
  <div class="min-w-0">
    <form
      @submit.prevent="handleSubmit"
      class="relative w-full min-w-0 rounded-xl border border-gray-300 bg-white px-4 py-3 shadow-lg transition focus-within:border-gray-400 focus-within:shadow-xl"
    >
      <div class="flex min-w-0 flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div class="relative flex-1 min-w-0">
          <textarea
            ref="textareaRef"
            v-model="message"
            @keydown="handleKeyDown"
            @input="handleInput"
            placeholder="发送消息..."
            class="w-full resize-none overflow-hidden bg-transparent text-[15px] leading-[1.5] text-gray-900 placeholder:text-gray-400 focus:outline-none disabled:cursor-not-allowed disabled:text-gray-400"
            :disabled="disabled"
            :style="{ height: textareaHeight }"
          ></textarea>
        </div>

        <div class="flex items-center justify-end gap-2 flex-shrink-0">
          <button
            v-if="databases.length > 0 || loadingDatabases"
            type="button"
            class="database-trigger inline-flex items-center gap-1.5 rounded-lg border px-2.5 py-1.5 text-xs font-medium transition hover:bg-gray-50"
            :class="selectedDatabase ? 'border-gray-200 bg-white text-gray-700' : 'border-orange-300 bg-orange-50 text-orange-700'"
            @click="toggleDatabaseDropdown"
          >
            <svg class="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4" />
            </svg>
            <span>{{ selectedDatabase || '选择数据库' }}</span>
            <svg class="h-3 w-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M6 9l6 6 6-6" />
            </svg>
          </button>

          <!-- 停止按钮 (仅在 AI 正在回复时显示) -->
          <button
            v-if="isSending"
            type="button"
            @click="handleStop"
            class="inline-flex h-9 items-center gap-1.5 rounded-lg border border-red-200 bg-white px-3 py-1.5 text-xs font-medium text-red-600 transition hover:bg-red-50 hover:border-red-300"
            title="停止生成"
          >
            <svg class="h-3.5 w-3.5" viewBox="0 0 24 24" fill="currentColor">
              <rect x="6" y="6" width="12" height="12" rx="1" />
            </svg>
            <span>停止</span>
          </button>

          <!-- 发送按钮 (仅在 AI 未回复时显示) -->
          <button
            v-if="!isSending"
            type="submit"
            :disabled="!canSend"
            class="inline-flex h-9 w-9 items-center justify-center rounded-lg bg-gray-900 text-white transition hover:bg-gray-800 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-gray-900 disabled:cursor-not-allowed disabled:opacity-40"
            :title="!selectedDatabase ? '请先选择数据库' : '发送 (Enter)'"
          >
            <svg
              class="h-4 w-4"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
            >
              <path stroke-linecap="round" stroke-linejoin="round" d="M7 17L17 7m0 0H9m8 0v8" />
            </svg>
          </button>
        </div>
      </div>

      <!-- Database dropdown - positioned above -->
      <div
        v-if="showDatabaseDropdown"
        class="database-menu absolute inset-x-0 bottom-full z-30 mb-2"
      >
        <div class="menu-inner">
          <!-- 提示文字 -->
          <div v-if="databases.length === 0" class="menu-hint">
            <p>暂无可用数据库</p>
            <p class="text-xs text-gray-500">请先在设置中添加数据库连接</p>
          </div>

          <button
            v-for="db in databases"
            :key="db.name"
            type="button"
            @click="selectDatabase(db.name)"
            class="menu-item"
            :class="{ active: selectedDatabase === db.name }"
          >
            <div>
              <p class="title">{{ db.name }}</p>
              <p class="desc">{{ db.db_type }}</p>
            </div>
            <svg v-if="selectedDatabase === db.name" class="h-4 w-4 text-gray-900" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" />
            </svg>
          </button>
        </div>
      </div>
    </form>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick, onMounted, onUnmounted } from 'vue'
import api from '@/services/api'

const props = defineProps<{
  disabled?: boolean
  isSending?: boolean
}>()

const emit = defineEmits<{
  send: [message: string, databaseName?: string]
  stop: []
  'database-change': [databaseName: string]
}>()

const message = ref('')
const textareaRef = ref<HTMLTextAreaElement>()
const textareaHeight = ref('48px')
const selectedDatabase = ref('')
const databases = ref<any[]>([])
const loadingDatabases = ref(false)
const showDatabaseDropdown = ref(false)

// 必须选择数据库才能发送消息
const canSend = computed(() => {
  return !props.disabled && !props.isSending && message.value.trim().length > 0 && selectedDatabase.value !== ''
})

onMounted(async () => {
  await loadDatabases()
  document.addEventListener('click', handleClickOutside)
  nextTick(() => textareaRef.value?.focus())
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
})

async function loadDatabases() {
  loadingDatabases.value = true
  try {
    const response = await api.get('/database/connections')
    databases.value = Array.isArray(response.data) ? response.data : []
  } catch (error) {
    console.error('[ChatInput] Failed to load databases:', error)
  } finally {
    loadingDatabases.value = false
  }
}

watch(() => props.isSending, (sending) => {
  if (!sending) {
    nextTick(() => textareaRef.value?.focus())
  }
})

function handleKeyDown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    if (canSend.value) handleSubmit()
  }
}

function handleSubmit() {
  if (!canSend.value) return
  const msg = message.value.trim()
  if (msg) {
    emit('send', msg, selectedDatabase.value || undefined)
    message.value = ''
    textareaHeight.value = '48px'
  }
}

function handleInput() {
  if (!textareaRef.value) return

  // Reset height to get accurate scrollHeight
  textareaRef.value.style.height = '48px'

  const scrollHeight = textareaRef.value.scrollHeight
  const maxHeight = 200 // 最大高度 200px

  if (scrollHeight > 48) {
    const newHeight = Math.min(scrollHeight, maxHeight)
    textareaHeight.value = `${newHeight}px`
  } else {
    textareaHeight.value = '48px'
  }
}

function toggleDatabaseDropdown() {
  showDatabaseDropdown.value = !showDatabaseDropdown.value
}

function selectDatabase(dbName: string) {
  selectedDatabase.value = dbName
  showDatabaseDropdown.value = false
  emit('database-change', dbName)
  nextTick(() => textareaRef.value?.focus())
}

function handleClickOutside(event: MouseEvent) {
  const target = event.target as HTMLElement
  if (!target.closest('.database-trigger') && !target.closest('.database-menu')) {
    showDatabaseDropdown.value = false
  }
}

function handleStop() {
  emit('stop')
}
</script>

<style scoped>
textarea {
  min-height: 48px;
  max-height: 200px;
  line-height: 1.5;
}

.database-menu {
  position: absolute;
}

.menu-inner {
  border-radius: 0.75rem;
  border: 1px solid #e5e7eb;
  background: white;
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.1);
  overflow: hidden;
}

.menu-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  padding: 0.75rem 1rem;
  border: none;
  background: transparent;
  color: #374151;
  font-size: 0.875rem;
  cursor: pointer;
  transition: all 0.15s ease;
}

.menu-item:hover {
  background: #f9fafb;
}

.menu-item .title {
  font-weight: 600;
  color: #111827;
}

.menu-item .desc {
  margin-top: 0.125rem;
  font-size: 0.75rem;
  color: #6b7280;
}

.menu-item.active {
  background: #f3f4f6;
}

.divider {
  height: 1px;
  background: #e5e7eb;
}

.menu-hint {
  padding: 0.75rem 1rem;
  text-align: center;
  color: #6b7280;
  font-size: 0.875rem;
}
</style>
