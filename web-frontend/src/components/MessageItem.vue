<template>
  <div class="message-item">
    <div class="message-row" :class="{ 'message-row--user': isUser }">
      <div
        v-if="!isUser"
        class="message-avatar"
      >
        AI
      </div>

      <div
        class="message-bubble"
        :class="{ 'message-bubble--user': isUser }"
        :style="bubbleStyle"
      >
        <div
          class="message-content prose prose-sm max-w-none leading-relaxed"
          v-html="renderedContent"
        ></div>

        <div
          v-if="message.isStreaming"
          class="stream-indicator"
        >
          <span class="dot"></span>
          <span class="dot" style="animation-delay: 0.12s"></span>
          <span class="dot" style="animation-delay: 0.24s"></span>
          <span>正在生成...</span>
        </div>
      </div>

      <div
        v-if="isUser"
        class="message-avatar message-avatar--user"
      >
        你
      </div>
    </div>

    <div class="meta-row" :class="{ 'meta-row--user': isUser }">
      <span>{{ formatTime(message.timestamp) }}</span>

      <button
        v-if="!isUser"
        @click="copyMessage"
        class="copy-btn"
        title="复制内容"
      >
        <svg v-if="!copied" class="icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.6" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
        </svg>
        <svg v-else class="icon text-emerald-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M5 13l4 4L19 7" />
        </svg>
        <span>{{ copied ? '已复制' : '复制' }}</span>
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, onMounted } from 'vue'
import type { ChatMessage } from '@/stores/chat'
import MarkdownIt from 'markdown-it'
import hljs from 'highlight.js'
import 'highlight.js/styles/github.css'

const props = defineProps<{
  message: ChatMessage
}>()

const copied = ref(false)
const isUser = computed(() => props.message.role === 'user')

const bubbleStyle = computed(() => {
  if (isUser.value) {
    return {
      background: 'linear-gradient(135deg, #f5e9dc 0%, #fbf4ec 100%)',
      borderColor: '#ebdfce',
      color: '#473e35'
    }
  }
  return {
    background: '#ffffff',
    borderColor: '#efe2d3',
    color: '#41372f'
  }
})

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
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.6" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
              </svg>
              <span>复制</span>
            </button>
          </div>
          <pre><code class="hljs language-${lang}">${highlighted}</code></pre>
        </div>`
      } catch (__) {
        // ignore
      }
    }
    return `<pre><code class="hljs">${md.utils.escapeHtml(str)}</code></pre>`
  }
})

onMounted(() => {
  if (typeof window !== 'undefined' && !(window as any).copyCode) {
    ;(window as any).copyCode = async (btn: HTMLButtonElement) => {
      const code = decodeURIComponent(btn.getAttribute('data-code') || '')
      try {
        await navigator.clipboard.writeText(code)
        const originalHTML = btn.innerHTML
        btn.innerHTML =
          '<svg class="w-4 h-4 text-emerald-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M5 13l4 4L19 7" /></svg><span>已复制</span>'
        setTimeout(() => {
          btn.innerHTML = originalHTML
        }, 2000)
      } catch (err) {
        console.error('Failed to copy:', err)
      }
    }
  }
})

const renderedContent = computed(() => md.render(props.message.content))

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
    minute: '2-digit'
  })
}
</script>

<style scoped>
.message-item {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.message-row {
  display: flex;
  align-items: flex-start;
  gap: 16px;
}

.message-row--user {
  flex-direction: row-reverse;
}

.message-avatar {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 42px;
  height: 42px;
  border-radius: 18px;
  background: #f0c9b0;
  color: #9a5f42;
  font-size: 13px;
  font-weight: 600;
  box-shadow: 0 6px 16px rgba(198, 159, 130, 0.3);
}

.message-avatar--user {
  background: #d6bba0;
  color: #705843;
}

.message-bubble {
  position: relative;
  max-width: min(720px, 90vw);
  border-radius: 26px;
  border: 1px solid transparent;
  padding: 24px 28px;
  box-shadow: 0 14px 45px rgba(190, 160, 123, 0.18);
}

.message-bubble--user {
  box-shadow: 0 16px 45px rgba(190, 160, 123, 0.2);
}

.message-content {
  color: inherit;
}

:deep(.message-content a) {
  color: #a56c46;
  text-decoration: underline;
}

:deep(.message-content p),
:deep(.message-content ul),
:deep(.message-content ol),
:deep(.message-content pre),
:deep(.message-content blockquote) {
  margin: 0.75em 0;
}

:deep(.message-content ul),
:deep(.message-content ol) {
  padding-left: 1.3em;
}

:deep(.message-content strong) {
  color: #3e352c;
}

:deep(.message-content code) {
  background: rgba(209, 187, 163, 0.35);
  padding: 2px 6px;
  border-radius: 6px;
  font-size: 0.92em;
  color: #4c4035;
}

:deep(.code-block-wrapper) {
  margin: 14px 0;
  border: 1px solid #eadfce;
  border-radius: 18px;
  overflow: hidden;
  background: #f6ede3;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.45);
}

:deep(.code-block-header) {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 16px;
  background: rgba(255, 255, 255, 0.65);
  border-bottom: 1px solid #eadfce;
  color: #857463;
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

:deep(.code-lang) {
  font-weight: 600;
}

:deep(.copy-code-btn) {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: inherit;
  background: none;
  border: none;
  cursor: pointer;
  font-weight: 500;
  font-size: 12px;
  transition: color 0.2s ease;
}

:deep(.copy-code-btn:hover) {
  color: #5f4f42;
}

:deep(pre) {
  margin: 0;
  padding: 18px 20px;
  background: transparent;
}

:deep(code.hljs) {
  background: transparent;
  color: #3c3a38;
}

.stream-indicator {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin-top: 18px;
  font-size: 12px;
  font-weight: 500;
  color: rgba(139, 109, 88, 0.8);
}

.stream-indicator .dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: currentColor;
  animation: bounce 0.9s infinite;
}

.meta-row {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 12px;
  color: #a79b8c;
}

.meta-row--user {
  justify-content: flex-end;
  text-align: right;
}

.copy-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border-radius: 999px;
  border: 1px solid #e4d7c7;
  color: #756a5e;
  background: rgba(247, 240, 232, 0.7);
  transition: all 0.2s ease;
}

.copy-btn:hover {
  border-color: #d9c8b5;
  color: #4c443b;
  transform: translateY(-1px);
}

.copy-btn .icon {
  width: 14px;
  height: 14px;
}

@keyframes bounce {
  0%, 100% {
    transform: translateY(0);
    opacity: 0.6;
  }
  50% {
    transform: translateY(-4px);
    opacity: 1;
  }
}
</style>
