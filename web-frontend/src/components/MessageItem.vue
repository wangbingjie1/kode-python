<template>
  <div
    class="flex items-start gap-3 group"
    :class="message.role === 'user' ? 'flex-row-reverse' : ''"
  >
    <!-- Avatar -->
    <div
      class="w-8 h-8 rounded-lg flex-shrink-0 flex items-center justify-center text-white font-bold text-xs"
      :class="message.role === 'user' ? 'bg-gradient-to-br from-blue-500 to-blue-600' : 'bg-gradient-to-br from-purple-500 to-purple-600'"
    >
      {{ message.role === 'user' ? '我' : 'AI' }}
    </div>

    <!-- Message Bubble -->
    <div class="flex-1 max-w-[80%]">
      <div
        class="rounded-xl px-4 py-3 shadow-sm"
        :class="message.role === 'user'
          ? 'bg-blue-600 text-white'
          : 'bg-white border border-gray-200'"
      >
        <!-- Markdown Content -->
        <div
          class="prose prose-sm max-w-none"
          :class="message.role === 'user' ? 'prose-invert' : ''"
          v-html="renderedContent"
        ></div>

        <!-- Streaming Indicator -->
        <div v-if="message.isStreaming" class="mt-2 flex items-center gap-2 text-xs opacity-70">
          <div class="flex gap-1">
            <div class="w-1.5 h-1.5 bg-current rounded-full animate-bounce"></div>
            <div class="w-1.5 h-1.5 bg-current rounded-full animate-bounce" style="animation-delay: 0.1s"></div>
            <div class="w-1.5 h-1.5 bg-current rounded-full animate-bounce" style="animation-delay: 0.2s"></div>
          </div>
          <span>思考中</span>
        </div>
      </div>

      <!-- Timestamp and Actions -->
      <div
        class="mt-1 px-2 flex items-center gap-2 text-xs text-gray-500"
        :class="message.role === 'user' ? 'flex-row-reverse' : ''"
      >
        <span>{{ formatTime(message.timestamp) }}</span>

        <!-- Copy Button (for assistant messages) -->
        <button
          v-if="message.role === 'assistant'"
          @click="copyMessage"
          class="opacity-0 group-hover:opacity-100 p-1 hover:bg-gray-100 rounded transition-all"
          title="复制内容"
        >
          <svg v-if="!copied" class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
          </svg>
          <svg v-else class="w-3.5 h-3.5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
          </svg>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, onMounted } from 'vue'
import type { ChatMessage } from '@/stores/chat'
import MarkdownIt from 'markdown-it'
import hljs from 'highlight.js'
import 'highlight.js/styles/github-dark.css'

const props = defineProps<{
  message: ChatMessage
}>()

const copied = ref(false)

// Initialize MarkdownIt immediately, not in onMounted
const md: MarkdownIt = new MarkdownIt({
  html: false,
  linkify: true,
  typographer: true,
  highlight: function (str, lang) {
    if (lang && hljs.getLanguage(lang)) {
      try {
        const highlighted = hljs.highlight(str, { language: lang }).value
        return `<div class="code-block-wrapper">
          <div class="code-block-header">
            <span class="code-lang">${lang}</span>
            <button class="copy-code-btn" onclick="window.copyCode(this)" data-code="${encodeURIComponent(str)}">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
              </svg>
              <span>复制</span>
            </button>
          </div>
          <pre><code class="hljs language-${lang}">${highlighted}</code></pre>
        </div>`
      } catch (__) {
        // Language not found, fall through
      }
    }
    return `<pre><code class="hljs">${md.utils.escapeHtml(str)}</code></pre>`
  }
})

// Add global copy function once
onMounted(() => {
  if (typeof window !== 'undefined' && !(window as any).copyCode) {
    (window as any).copyCode = async (btn: HTMLButtonElement) => {
      const code = decodeURIComponent(btn.getAttribute('data-code') || '')
      try {
        await navigator.clipboard.writeText(code)
        const originalHTML = btn.innerHTML
        btn.innerHTML = '<svg class="w-4 h-4 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" /></svg><span>已复制</span>'
        setTimeout(() => {
          btn.innerHTML = originalHTML
        }, 2000)
      } catch (err) {
        console.error('Failed to copy:', err)
      }
    }
  }
})

const renderedContent = computed(() => {
  return md.render(props.message.content)
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

function formatTime(date: Date): string {
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  const seconds = Math.floor(diff / 1000)
  const minutes = Math.floor(seconds / 60)
  const hours = Math.floor(minutes / 60)

  if (seconds < 60) return '刚刚'
  if (minutes < 60) return `${minutes} 分钟前`
  if (hours < 24) return `${hours} 小时前`

  return date.toLocaleString('zh-CN', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}
</script>

<style scoped>
:deep(.prose) {
  color: inherit;
}

:deep(.prose p) {
  margin: 0.5em 0;
}

:deep(.prose ul),
:deep(.prose ol) {
  margin: 0.5em 0;
  padding-left: 1.5em;
}

:deep(.prose code) {
  background: rgba(0, 0, 0, 0.1);
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 0.9em;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
}

:deep(.prose-invert code) {
  background: rgba(255, 255, 255, 0.2);
}

:deep(.code-block-wrapper) {
  margin: 12px 0;
  border-radius: 8px;
  overflow: hidden;
  background: #1e1e1e;
}

:deep(.code-block-header) {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  background: #2d2d2d;
  border-bottom: 1px solid #3d3d3d;
}

:deep(.code-lang) {
  font-size: 12px;
  color: #888;
  font-family: monospace;
  text-transform: uppercase;
}

:deep(.copy-code-btn) {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 8px;
  background: #3d3d3d;
  border: none;
  border-radius: 4px;
  color: #aaa;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

:deep(.copy-code-btn:hover) {
  background: #4d4d4d;
  color: #fff;
}

:deep(.code-block-wrapper pre) {
  margin: 0;
  padding: 12px;
  overflow-x: auto;
}

:deep(.code-block-wrapper code) {
  background: none;
  padding: 0;
  font-size: 13px;
  line-height: 1.6;
}
</style>
