<template>
  <div class="min-w-0">
    <form
      @submit.prevent="handleSubmit"
      class="relative w-full min-w-0 rounded-2xl bg-white/90 px-5 py-4 shadow-[0_12px_28px_rgba(214,189,160,0.18)] sm:px-6 sm:py-5"
    >
      <div class="flex min-w-0 flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div class="relative flex-1 min-w-0">
          <textarea
            ref="textareaRef"
            v-model="message"
            @keydown="handleKeyDown"
            @input="autoResize"
            placeholder="写下你此刻的灵感或问题..."
            class="w-full resize-none overflow-hidden bg-transparent text-sm leading-relaxed text-[#2f2720] placeholder:text-[#b39f8f] focus:outline-none disabled:cursor-not-allowed disabled:text-[#b9ada1]"
            :disabled="disabled"
            :rows="rows"
          ></textarea>
          <span
            v-if="message.length"
            class="pointer-events-none absolute bottom-0 right-0 translate-y-full text-xs text-[#b39f8f]"
          >
            {{ message.length }} 字
          </span>
        </div>

        <div class="flex items-center justify-end gap-2 sm:gap-3">
          <button
            v-if="databases.length > 0 || loadingDatabases"
            type="button"
            class="database-trigger inline-flex items-center gap-2 rounded-full border border-[#eadfd3] bg-white px-3 py-1.5 text-xs font-semibold text-[#6d5f52] shadow-sm transition hover:bg-[#f7efe4]"
            @click="toggleDatabaseDropdown"
          >
            <svg class="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6">
              <path stroke-linecap="round" stroke-linejoin="round" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4" />
            </svg>
            <span>{{ selectedDatabase || '通用模式' }}</span>
            <svg class="h-3 w-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6">
              <path stroke-linecap="round" stroke-linejoin="round" d="M6 9l6 6 6-6" />
            </svg>
          </button>

          <button
            type="button"
            class="inline-flex h-9 w-9 items-center justify-center rounded-full bg-white/80 text-[#a38b75] shadow-inner transition hover:bg-white"
            :class="{ 'opacity-40 cursor-not-allowed': message.length === 0 }"
            :disabled="message.length === 0"
            title="清空输入"
            @click="clearMessage"
          >
            <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
              <path stroke-linecap="round" stroke-linejoin="round" d="M6 6l12 12M6 18L18 6" />
            </svg>
          </button>

          <button
            type="submit"
            :disabled="!canSend"
            class="inline-flex h-11 w-11 items-center justify-center rounded-full bg-gradient-to-br from-[#d88a5d] to-[#c06d3f] text-white shadow-[0_18px_40px_rgba(206,132,78,0.28)] transition hover:-translate-y-0.5 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#d88a5d] disabled:cursor-not-allowed disabled:opacity-60"
            :title="isSending ? '发送中...' : '发送 (Enter)'"
          >
            <svg
              v-if="!isSending"
              class="h-5 w-5"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="1.8"
            >
              <path stroke-linecap="round" stroke-linejoin="round" d="M7 17L17 7m0 0H9m8 0v8" />
            </svg>
            <svg
              v-else
              class="h-5 w-5 animate-spin"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="1.8"
            >
              <circle class="opacity-30" cx="12" cy="12" r="9" />
              <path d="M21 12a9 9 0 00-9-9" stroke-linecap="round" />
            </svg>
          </button>
        </div>
      </div>

      <div
        v-if="showDatabaseDropdown"
        class="database-menu absolute inset-x-0 top-full z-30 mt-3"
      >
        <div class="menu-inner">
          <button
            type="button"
            @click="selectDatabase('')"
            class="menu-item"
            :class="{ active: !selectedDatabase }"
          >
            <div>
              <p class="title">通用对话</p>
              <p class="desc">不连接数据库</p>
            </div>
            <svg v-if="!selectedDatabase" class="h-4 w-4 text-[#c47a4d]" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
              <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" />
            </svg>
          </button>

          <div v-if="databases.length > 0" class="divider"></div>

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
            <svg v-if="selectedDatabase === db.name" class="h-4 w-4 text-[#c47a4d]" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
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
}>()

const message = ref('')
const textareaRef = ref<HTMLTextAreaElement>()
const rows = ref(1)
const selectedDatabase = ref('')
const databases = ref<any[]>([])
const loadingDatabases = ref(false)
const showDatabaseDropdown = ref(false)

const canSend = computed(() => !props.disabled && !props.isSending && message.value.trim().length > 0)

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
    rows.value = 1
    autoResize()
  }
}

function autoResize() {
  nextTick(() => {
    if (!textareaRef.value) return
    textareaRef.value.style.height = 'auto'
    const scrollHeight = textareaRef.value.scrollHeight
    const lineHeight = 24
    const newRows = Math.min(Math.max(Math.ceil(scrollHeight / lineHeight), 1), 8)
    rows.value = newRows
  })
}

function clearMessage() {
  if (message.value.length === 0) return
  message.value = ''
  rows.value = 1
  autoResize()
  nextTick(() => textareaRef.value?.focus())
}

function toggleDatabaseDropdown() {
  showDatabaseDropdown.value = !showDatabaseDropdown.value
}

function selectDatabase(dbName: string) {
  selectedDatabase.value = dbName
  showDatabaseDropdown.value = false
  nextTick(() => textareaRef.value?.focus())
}

function applyQuickPrompt(template: string) {
  message.value = template
  autoResize()
  nextTick(() => textareaRef.value?.focus())
}

function handleClickOutside(event: MouseEvent) {
  const target = event.target as HTMLElement
  if (!target.closest('.database-trigger') && !target.closest('.database-menu')) {
    showDatabaseDropdown.value = false
  }
}
</script>

<style scoped>
textarea {
  min-height: 72px;
  max-height: 260px;
}

.database-menu {
  position: absolute;
}

.menu-inner {
  border-radius: 20px;
  border: 1px solid #eadfd3;
  background: rgba(255, 255, 255, 0.96);
  box-shadow: 0 26px 60px rgba(184, 159, 133, 0.22);
  overflow: hidden;
  backdrop-filter: blur(12px);
}

.menu-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  padding: 14px 18px;
  border: none;
  background: transparent;
  color: #6d5f52;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.menu-item:hover {
  background: rgba(250, 243, 233, 0.82);
}

.menu-item .title {
  font-weight: 600;
  color: #4f443a;
}

.menu-item .desc {
  margin-top: 4px;
  font-size: 12px;
  color: #9a8b7c;
}

.menu-item.active {
  background: rgba(237, 223, 206, 0.9);
}

.divider {
  height: 1px;
  background: linear-gradient(90deg, rgba(237, 224, 210, 0), rgba(237, 224, 210, 0.85), rgba(237, 224, 210, 0));
}
</style>
