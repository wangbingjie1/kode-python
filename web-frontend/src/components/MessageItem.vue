<template>
  <article
    class="group flex w-full min-w-0 gap-4 text-[15px] leading-relaxed"
    :class="[spacingClass]"
  >
    <!-- Avatar -->
    <div v-if="showAvatar" class="flex w-8 flex-shrink-0 justify-center pt-0.5">
      <div
        class="flex h-8 w-8 items-center justify-center rounded-full"
        :class="avatarClass"
      >
        <svg
          v-if="isAssistant"
          class="h-4 w-4"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
        >
          <path stroke-linecap="round" stroke-linejoin="round" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
        </svg>
        <svg
          v-else-if="isTool"
          class="h-4 w-4"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
        >
          <path stroke-linecap="round" stroke-linejoin="round" d="M13 7h8m0 0v8m0-8l-9 9-4-4-6 6" />
        </svg>
        <svg
          v-else
          class="h-4 w-4"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
        >
          <path stroke-linecap="round" stroke-linejoin="round" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
        </svg>
      </div>
    </div>

    <!-- Spacer for user messages (no avatar) -->
    <div v-else class="w-8 flex-shrink-0"></div>

    <!-- Content -->
    <div class="flex max-w-full flex-1 flex-col gap-3 min-w-0">
      <!-- System message -->
      <div
        v-if="isSystem"
        class="w-full rounded-lg border border-gray-200 bg-gray-50 px-4 py-3 text-sm text-gray-600"
        v-html="renderedContent"
      />

      <!-- Tool call -->
      <div v-else-if="isTool" class="w-full">
        <ToolCallItem
          v-if="message.toolCall"
          :tool-name="message.toolCall.toolName"
          :tool-args="message.toolCall.toolArgs"
          :tool-result="message.toolCall.toolResult"
          :tool-error="message.toolCall.toolError"
          :status="message.toolCall.status"
        />
      </div>

      <!-- Assistant thinking -->
      <div v-else-if="isThinkingMessage" class="w-full">
        <div class="flex items-center gap-2 text-sm text-gray-500">
          <svg class="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v4m0 8v4m8-8h-4M8 12H4m12.364-7.364l-2.828 2.828M8.464 15.536l-2.828 2.828m0-12.728l2.828 2.828m8.485 8.485l2.828 2.828" />
          </svg>
          <span>思考中...</span>
        </div>
        <p class="mt-2 text-gray-700">{{ message.content }}</p>
      </div>

      <!-- Assistant / User message (no bubble, just text) -->
      <div
        v-else
        class="relative max-w-full"
      >
        <div class="relative group/message">
          <!-- Copy button -->
          <button
            v-if="isAssistant || isUser"
            type="button"
            class="absolute -left-10 top-0 inline-flex h-7 w-7 items-center justify-center rounded-md text-gray-400 opacity-0 transition hover:bg-gray-100 hover:text-gray-600 group-hover/message:opacity-100"
            @click="copyMessage"
          >
            <svg v-if="!copied" class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
            </svg>
            <svg v-else class="h-4 w-4 text-green-600" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" />
            </svg>
          </button>

          <!-- Message content -->
          <div
            class="markdown-content prose max-w-none text-gray-900"
            :class="messageClass"
            v-html="renderedContent"
          />
        </div>
      </div>
    </div>
  </article>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import MarkdownIt from 'markdown-it'
import hljs from 'highlight.js'
import 'highlight.js/styles/github.css'
import type { ChatMessage } from '@/stores/chat'
import ToolCallItem from './ToolCallItem.vue'

const props = defineProps<{
  message: ChatMessage
  groupBehavior?: 'standalone' | 'compact-start' | 'compact-middle' | 'compact-end'
}>()

const copied = ref(false)

const isUser = computed(() => props.message.role === 'user')
const isSystem = computed(() => props.message.role === 'system')
const isAssistant = computed(() => props.message.role === 'assistant')
const isTool = computed(() => props.message.role === 'tool')
const isThinkingMessage = computed(() => props.message.isStreaming && props.message.metadata?.isThinking === true)

const showAvatar = computed(() => !isSystem.value)

const avatarClass = computed(() =>
  isAssistant.value
    ? 'bg-gray-900 text-white'
    : isTool.value
      ? 'bg-blue-500 text-white'
      : 'bg-gray-200 text-gray-700',
)

const messageClass = computed(() => {
  return isUser.value ? 'text-gray-700' : ''
})

const spacingClass = computed(() => {
  switch (props.groupBehavior) {
    case 'compact-middle':
    case 'compact-end':
      return 'mt-2'
    default:
      return 'mt-8'
  }
})

const md: MarkdownIt = new MarkdownIt({
  html: false,
  linkify: true,
  typographer: true,
  highlight: (str, lang) => {
    if (lang && hljs.getLanguage(lang)) {
      try {
        const highlighted = hljs.highlight(str, { language: lang }).value
        return `<div class="code-block-wrapper">
          <div class="code-block-header">
            <span class="code-lang">${lang}</span>
            <button class="copy-code-btn" onclick="window.copyCode(this)" data-code="${encodeURIComponent(str)}">
              <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
              </svg>
              <span>复制</span>
            </button>
          </div>
          <pre><code class="hljs language-${lang}">${highlighted}</code></pre>
        </div>`
      } catch (err) {
        console.error('[MessageItem] highlight error:', err)
      }
    }
    return `<pre><code class="hljs">${md.utils.escapeHtml(str)}</code></pre>`
  },
})

const renderedContent = computed(() => md.render(props.message.content))

onMounted(() => {
  if (typeof window !== 'undefined' && !(window as any).copyCode) {
    ;(window as any).copyCode = async (btn: HTMLButtonElement) => {
      const code = decodeURIComponent(btn.getAttribute('data-code') || '')
      try {
        await navigator.clipboard.writeText(code)
        const originalHTML = btn.innerHTML
        btn.innerHTML =
          '<svg class="w-3.5 h-3.5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" /></svg><span>已复制</span>'
        setTimeout(() => {
          btn.innerHTML = originalHTML
        }, 2000)
      } catch (err) {
        console.error('Failed to copy:', err)
      }
    }
  }
})

async function copyMessage() {
  try {
    await navigator.clipboard.writeText(props.message.content)
    copied.value = true
    setTimeout(() => {
      copied.value = false
    }, 2000)
  } catch (err) {
    console.error('Failed to copy:', err)
  }
}

</script>

<style scoped>
.markdown-content :deep(p) {
  margin-bottom: 1rem;
  line-height: 1.75;
}

.markdown-content :deep(p:last-child) {
  margin-bottom: 0;
}

.markdown-content :deep(ul),
.markdown-content :deep(ol) {
  margin: 1rem 0;
  padding-left: 1.5rem;
  line-height: 1.75;
}

.markdown-content :deep(li) {
  margin: 0.5rem 0;
}

.markdown-content :deep(code) {
  background: #f3f4f6;
  border-radius: 0.25rem;
  padding: 0.125rem 0.375rem;
  font-size: 0.875em;
  font-family: 'Monaco', 'Menlo', 'Courier New', monospace;
}

.markdown-content :deep(pre) {
  margin: 1.5rem 0;
  padding: 0;
  border-radius: 0.5rem;
  background: #1f2937;
  overflow: hidden;
}

.markdown-content :deep(pre code) {
  display: block;
  padding: 1rem;
  background: transparent;
  color: #f3f4f6;
  overflow-x: auto;
}

.markdown-content :deep(a) {
  color: #2563eb;
  text-decoration: underline;
  text-underline-offset: 2px;
}

.markdown-content :deep(a:hover) {
  color: #1d4ed8;
}

.markdown-content :deep(blockquote) {
  margin: 1.5rem 0;
  padding-left: 1rem;
  border-left: 3px solid #d1d5db;
  color: #6b7280;
}

.markdown-content :deep(h1),
.markdown-content :deep(h2),
.markdown-content :deep(h3),
.markdown-content :deep(h4),
.markdown-content :deep(h5),
.markdown-content :deep(h6) {
  margin-top: 1.5rem;
  margin-bottom: 0.75rem;
  font-weight: 600;
  line-height: 1.25;
}

.markdown-content :deep(h1) { font-size: 1.5rem; }
.markdown-content :deep(h2) { font-size: 1.25rem; }
.markdown-content :deep(h3) { font-size: 1.125rem; }

.code-block-wrapper {
  border-radius: 0.5rem;
  overflow: hidden;
  border: 1px solid #e5e7eb;
  margin: 1.5rem 0;
}

.code-block-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.5rem 0.75rem;
  background: #f9fafb;
  border-bottom: 1px solid #e5e7eb;
  font-size: 0.75rem;
}

.code-lang {
  font-weight: 600;
  color: #6b7280;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.copy-code-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.25rem 0.5rem;
  border-radius: 0.375rem;
  border: 1px solid #d1d5db;
  background: white;
  color: #6b7280;
  cursor: pointer;
  transition: all 0.15s ease;
  font-weight: 500;
  font-size: 0.75rem;
}

.copy-code-btn:hover {
  border-color: #9ca3af;
  background: #f9fafb;
}

.code-block-wrapper pre {
  margin: 0;
  background: #1f2937;
}

.code-block-wrapper pre code {
  padding: 1rem;
}

@keyframes spin {
  0% {
    transform: rotate(0deg);
  }
  100% {
    transform: rotate(360deg);
  }
}
</style>
