<template>
  <div class="chat-input-container bg-white border-t border-gray-200 py-4 px-6">
    <div class="max-w-4xl mx-auto">
      <form @submit.prevent="handleSubmit" class="relative">
        <!-- Textarea Input -->
        <div class="relative flex items-end gap-2">
          <div class="flex-1 relative">
            <textarea
              ref="textareaRef"
              v-model="message"
              @keydown="handleKeyDown"
              @input="autoResize"
              placeholder="输入消息... (Shift+Enter 换行)"
              class="w-full px-4 py-3 pr-12 border border-gray-300 rounded-xl resize-none focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
              :class="{ 'opacity-50': disabled }"
              :disabled="disabled"
              :rows="rows"
              :style="{ maxHeight: '200px' }"
            ></textarea>

            <!-- Character Counter -->
            <div
              v-if="message.length > 0"
              class="absolute bottom-2 right-3 text-xs text-gray-400"
            >
              {{ message.length }}
            </div>
          </div>

          <!-- Send Button -->
          <button
            type="submit"
            class="px-6 py-3 bg-gradient-to-r from-blue-600 to-blue-700 text-white rounded-xl hover:from-blue-700 hover:to-blue-800 disabled:opacity-50 disabled:cursor-not-allowed transition-all shadow-md hover:shadow-lg flex items-center gap-2 font-medium"
            :disabled="!canSend"
          >
            <svg v-if="!isSending" class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
            </svg>
            <div v-else class="flex gap-1">
              <div class="w-1.5 h-1.5 bg-white rounded-full animate-bounce"></div>
              <div class="w-1.5 h-1.5 bg-white rounded-full animate-bounce" style="animation-delay: 0.1s"></div>
              <div class="w-1.5 h-1.5 bg-white rounded-full animate-bounce" style="animation-delay: 0.2s"></div>
            </div>
            <span class="hidden sm:inline">{{ isSending ? '发送中' : '发送' }}</span>
          </button>
        </div>

        <!-- Quick Actions Bar -->
        <div class="mt-2 flex items-center justify-between text-xs text-gray-500">
          <div class="flex items-center gap-4">
            <!-- File Attachment (Future) -->
            <button
              type="button"
              class="flex items-center gap-1 hover:text-gray-700 transition-colors"
              disabled
              title="即将推出"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" />
              </svg>
              <span class="hidden sm:inline">附件</span>
            </button>

            <!-- Code Snippet (Future) -->
            <button
              type="button"
              class="flex items-center gap-1 hover:text-gray-700 transition-colors"
              @click="insertCodeBlock"
              title="插入代码块"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
              </svg>
              <span class="hidden sm:inline">代码</span>
            </button>
          </div>

          <!-- Keyboard Hints -->
          <div class="flex items-center gap-3">
            <span class="hidden md:inline">
              <kbd class="px-1.5 py-0.5 bg-gray-100 border border-gray-300 rounded text-xs">Enter</kbd> 发送
            </span>
            <span class="hidden md:inline">
              <kbd class="px-1.5 py-0.5 bg-gray-100 border border-gray-300 rounded text-xs">Shift+Enter</kbd> 换行
            </span>
          </div>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick } from 'vue'

const props = defineProps<{
  disabled?: boolean
  isSending?: boolean
}>()

const emit = defineEmits<{
  send: [message: string]
}>()

const message = ref('')
const textareaRef = ref<HTMLTextAreaElement>()
const rows = ref(1)

const canSend = computed(() => {
  return !props.disabled && !props.isSending && message.value.trim().length > 0
})

watch(() => props.isSending, (sending) => {
  if (!sending) {
    // Focus textarea after sending
    nextTick(() => {
      textareaRef.value?.focus()
    })
  }
})

function handleKeyDown(e: KeyboardEvent) {
  // Enter without Shift = Send
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    if (canSend.value) {
      handleSubmit()
    }
  }
}

function handleSubmit() {
  if (!canSend.value) return

  const msg = message.value.trim()
  if (msg) {
    emit('send', msg)
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
    const lineHeight = 24 // approximate line height
    const newRows = Math.min(Math.max(Math.ceil(scrollHeight / lineHeight), 1), 8)
    rows.value = newRows
  })
}

function insertCodeBlock() {
  const cursorPos = textareaRef.value?.selectionStart || 0
  const textBefore = message.value.substring(0, cursorPos)
  const textAfter = message.value.substring(cursorPos)

  message.value = textBefore + '\n```\n\n```\n' + textAfter

  nextTick(() => {
    if (textareaRef.value) {
      const newCursorPos = cursorPos + 5 // Position cursor inside code block
      textareaRef.value.selectionStart = newCursorPos
      textareaRef.value.selectionEnd = newCursorPos
      textareaRef.value.focus()
    }
  })
}

// Auto-focus on mount
nextTick(() => {
  textareaRef.value?.focus()
})
</script>

<style scoped>
textarea {
  line-height: 1.5;
}

textarea::-webkit-scrollbar {
  width: 8px;
}

textarea::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 4px;
}

textarea::-webkit-scrollbar-thumb {
  background: #888;
  border-radius: 4px;
}

textarea::-webkit-scrollbar-thumb:hover {
  background: #555;
}

kbd {
  font-family: system-ui, -apple-system, sans-serif;
}
</style>
