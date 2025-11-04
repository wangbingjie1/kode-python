<template>
  <div class="input-shell">
    <form @submit.prevent="handleSubmit" class="input-card">
      <div class="relative">
        <textarea
          ref="textareaRef"
          v-model="message"
          @keydown="handleKeyDown"
          @input="autoResize"
          placeholder="写下你此刻的灵感或问题..."
          class="prompt-field"
          :disabled="disabled"
          :rows="rows"
        ></textarea>

        <div class="card-accessories database-dropdown">
          <div class="tools">
            <button
              v-if="databases.length > 0 || loadingDatabases"
              type="button"
              @click="toggleDatabaseDropdown"
              class="tool-btn database-trigger"
              :title="selectedDatabase ? `已连接: ${selectedDatabase}` : '选择数据库'"
            >
              <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.6" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4" />
              </svg>
              <span v-if="selectedDatabase" class="status-dot"></span>
            </button>

            <button type="button" @click="insertCodeBlock" class="tool-btn" title="插入代码块">
              <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.6" d="M16 18l6-6-6-6M8 6l-6 6 6 6" />
              </svg>
            </button>

            <button
              type="button"
              class="tool-btn"
              :class="{ disabled: message.length === 0 }"
              @click="clearMessage"
              :disabled="message.length === 0"
              title="清空输入"
            >
              <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M6 6l12 12M6 18L18 6" />
              </svg>
            </button>
          </div>

          <div class="meta">
            <button
              type="button"
              class="meta-select database-trigger"
              @click="toggleDatabaseDropdown"
            >
              <span class="label">{{ selectedDatabase || '通用模式' }}</span>
              <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.6" d="M6 9l6 6 6-6" />
              </svg>
            </button>

            <button
              type="submit"
              :disabled="!canSend"
              class="send-btn"
              :title="isSending ? '发送中...' : '发送 (Enter)'"
            >
              <svg
                v-if="!isSending"
                class="h-5 w-5"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M7 17L17 7m0 0H9m8 0v8" />
              </svg>
              <div v-else class="loading-dots">
                <div></div>
                <div></div>
                <div></div>
              </div>
            </button>
          </div>
        </div>

        <div v-if="showDatabaseDropdown" class="database-menu">
          <div class="menu-inner">
            <button
              type="button"
              @click="selectDatabase('')"
              class="menu-item"
              :class="{ active: !selectedDatabase }"
            >
              <span class="title">通用对话</span>
              <span class="desc">不连接数据库</span>
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
              <span class="title">{{ db.name }}</span>
              <span class="desc">{{ db.db_type }}</span>
            </button>
          </div>
        </div>

        <div v-if="message.length > 0" class="char-counter">
          {{ message.length }}
        </div>
      </div>
    </form>

    <div class="quick-actions">
      <button
        v-for="item in quickActions"
        :key="item.label"
        type="button"
        class="quick-btn"
        @click="applyQuickPrompt(item.template)"
      >
        <span class="icon">
          <svg v-if="item.icon === 'write'" class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.6" d="M12 20h9" />
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.6" d="M16.5 3.5a2.121 2.121 0 013 3L7 19l-4 1 1-4 12.5-12.5z" />
          </svg>
          <svg v-else-if="item.icon === 'learn'" class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.6" d="M12 4.5L3 9l9 4.5L21 9 12 4.5z" />
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.6" d="M7 11.5V16a5 5 0 0010 0v-4.5" />
          </svg>
          <svg v-else-if="item.icon === 'code'" class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.6" d="M16 18l6-6-6-6M8 6l-6 6 6 6" />
          </svg>
          <svg v-else-if="item.icon === 'life'" class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.6" d="M12 8v8m-4-4h8" />
            <circle cx="12" cy="12" r="9" stroke-width="1.6" />
          </svg>
          <svg v-else class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.6" d="M4 4h16v16H4z" />
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.6" d="M4 7h16M4 17h16M7 7v10" />
          </svg>
        </span>
        <span>{{ item.label }}</span>
      </button>
    </div>
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

interface QuickAction {
  label: string
  template: string
  icon: 'write' | 'learn' | 'code' | 'life' | 'mail'
}

const quickActions: QuickAction[] = [
  {
    label: 'Write',
    template: '请帮我撰写一封语气真诚的邮件，主题是：',
    icon: 'write',
  },
  {
    label: 'Learn',
    template: '向我解释这个概念并给出实际案例：',
    icon: 'learn',
  },
  {
    label: 'Code',
    template: '请检查以下代码的潜在问题，并给出改进建议：',
    icon: 'code',
  },
  {
    label: 'Life stuff',
    template: '帮我规划一个轻松的周末活动，包含时间安排：',
    icon: 'life',
  },
  {
    label: 'From Gmail',
    template: '根据以下邮件内容生成一份简要回复：',
    icon: 'mail',
  },
]

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

function insertCodeBlock() {
  const cursorPos = textareaRef.value?.selectionStart ?? 0
  const textBefore = message.value.substring(0, cursorPos)
  const textAfter = message.value.substring(cursorPos)
  message.value = `${textBefore}\n\`\`\`\n\n\`\`\`\n${textAfter}`
  nextTick(() => {
    if (textareaRef.value) {
      const newCursorPos = cursorPos + 5
      textareaRef.value.selectionStart = newCursorPos
      textareaRef.value.selectionEnd = newCursorPos
      textareaRef.value.focus()
      autoResize()
    }
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
.input-shell {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.input-card {
  position: relative;
  border-radius: 28px;
  border: 1px solid #eadfcf;
  background: rgba(255, 255, 255, 0.92);
  box-shadow: 0 18px 45px rgba(181, 154, 120, 0.18);
  padding: 24px 28px 28px;
  backdrop-filter: blur(6px);
}

.prompt-field {
  width: 100%;
  border: none;
  background: transparent;
  resize: none;
  font-size: 16px;
  line-height: 1.6;
  color: #463f38;
  padding-right: 130px;
  min-height: 120px;
  outline: none;
  font-family: 'Inter', system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}

.prompt-field::placeholder {
  color: #b2a69a;
}

.prompt-field:disabled {
  color: #b9ada1;
  cursor: not-allowed;
}

.card-accessories {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  margin-top: 18px;
}

.tools {
  display: flex;
  align-items: center;
  gap: 10px;
}

.tool-btn {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 38px;
  height: 38px;
  border-radius: 12px;
  border: 1px solid transparent;
  background: #f6ede3;
  color: #7f7468;
  transition: all 0.2s ease;
}

.tool-btn:hover:not(.disabled) {
  border-color: #e5d9ca;
  color: #5f564d;
  transform: translateY(-1px);
}

.tool-btn:active:not(.disabled) {
  transform: translateY(0);
}

.tool-btn.disabled {
  opacity: 0.35;
  cursor: not-allowed;
}

.status-dot {
  position: absolute;
  top: 6px;
  right: 6px;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #50b36c;
  border: 1.5px solid white;
}

.meta {
  display: flex;
  align-items: center;
  gap: 12px;
}

.meta-select {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  border-radius: 9999px;
  border: 1px solid #e7d8c7;
  background: #f9f1e6;
  color: #6a6156;
  font-size: 13px;
  font-weight: 600;
  transition: all 0.2s ease;
}

.meta-select:hover {
  border-color: #ddcbb7;
  color: #514940;
}

.meta-select:focus {
  outline: none;
  box-shadow: 0 0 0 3px rgba(216, 198, 180, 0.35);
}

.meta-select .label {
  letter-spacing: 0.02em;
}

.send-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 44px;
  height: 44px;
  border-radius: 16px;
  border: none;
  background: linear-gradient(145deg, #f0b8a0 0%, #e39c84 100%);
  color: white;
  box-shadow: 0 12px 25px rgba(225, 150, 120, 0.45);
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease, opacity 0.2s ease;
}

.send-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 16px 30px rgba(225, 150, 120, 0.55);
}

.send-btn:active:not(:disabled) {
  transform: translateY(0);
}

.send-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
  box-shadow: none;
}

.loading-dots {
  display: flex;
  gap: 4px;
}

.loading-dots div {
  width: 4px;
  height: 4px;
  background: white;
  border-radius: 999px;
  animation: bounce 0.6s infinite;
}

.loading-dots div:nth-child(2) {
  animation-delay: 0.1s;
}

.loading-dots div:nth-child(3) {
  animation-delay: 0.2s;
}

@keyframes bounce {
  0%, 100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-4px);
  }
}

.database-menu {
  position: absolute;
  bottom: calc(100% + 12px);
  left: 0;
  width: 280px;
  max-height: 320px;
  overflow-y: auto;
  border-radius: 18px;
  border: 1px solid #eadfcf;
  background: #fffaf4;
  box-shadow: 0 25px 60px rgba(120, 90, 60, 0.18);
  z-index: 50;
  animation: fadeIn 0.18s ease-out;
}

.menu-inner {
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.menu-item {
  width: 100%;
  text-align: left;
  border: none;
  background: transparent;
  border-radius: 12px;
  padding: 10px 12px;
  color: #5a5147;
  display: flex;
  flex-direction: column;
  gap: 4px;
  transition: all 0.2s ease;
}

.menu-item:hover {
  background: rgba(239, 224, 208, 0.6);
}

.menu-item.active {
  background: rgba(234, 198, 164, 0.35);
  color: #9a684e;
}

.menu-item .title {
  font-weight: 600;
}

.menu-item .desc {
  font-size: 12px;
  color: #887b70;
}

.divider {
  height: 1px;
  background: rgba(232, 218, 202, 0.7);
}

.char-counter {
  position: absolute;
  top: 16px;
  right: 24px;
  font-size: 12px;
  color: #b0a599;
  letter-spacing: 0.05em;
}

.quick-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 10px;
}

.quick-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 9px 16px;
  border-radius: 14px;
  border: 1px solid #eadfcf;
  background: #f6ede3;
  color: #665c52;
  font-size: 13px;
  font-weight: 600;
  transition: all 0.2s ease;
  box-shadow: 0 6px 18px rgba(190, 165, 130, 0.12);
}

.quick-btn:hover {
  transform: translateY(-1px);
  border-color: #decfbf;
  color: #4f463d;
}

.quick-btn:active {
  transform: translateY(0);
}

.quick-btn .icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  height: 18px;
  color: #a97b5e;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(6px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@media (max-width: 640px) {
  .input-card {
    padding: 20px 18px 24px;
  }

  .prompt-field {
    padding-right: 0;
    min-height: 100px;
  }

  .meta {
    width: 100%;
    justify-content: space-between;
  }

  .meta-select {
    flex: 1;
    justify-content: center;
  }

  .send-btn {
    width: 42px;
    height: 42px;
  }

  .database-menu {
    left: 0;
    right: 0;
    margin: 0 auto;
  }
}
</style>
