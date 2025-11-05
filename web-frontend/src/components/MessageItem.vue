<template>
  <article
    class="group flex w-full min-w-0 gap-3 text-sm text-[#3a322b]"
    :class="[rootAlignmentClass, spacingClass]"
  >
    <div v-if="showAvatar" class="flex w-9 flex-shrink-0 justify-center">
      <div
        class="flex h-9 w-9 items-center justify-center rounded-2xl shadow-inner"
        :class="avatarClass"
      >
        <svg
          v-if="isAssistant"
          class="h-4 w-4"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="1.8"
        >
          <path stroke-linecap="round" stroke-linejoin="round" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
        </svg>
        <svg
          v-else-if="isTool"
          class="h-4 w-4"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="1.8"
        >
          <path stroke-linecap="round" stroke-linejoin="round" d="M13 7h8m0 0v8m0-8l-9 9-4-4-6 6" />
        </svg>
        <svg
          v-else
          class="h-4 w-4"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="1.8"
        >
          <path stroke-linecap="round" stroke-linejoin="round" d="M12 12a4 4 0 110-8 4 4 0 010 8zm0 2c-4.418 0-8 2.239-8 5v1h16v-1c0-2.761-3.582-5-8-5z" />
        </svg>
      </div>
    </div>

    <div class="flex max-w-full flex-1 flex-col gap-2" :class="contentAlignmentClass">
      <!-- System message -->
      <div
        v-if="isSystem"
        class="w-full rounded-2xl border border-dashed border-[#e7d9ca] bg-[#fbf3eb] px-4 py-3 text-xs leading-relaxed text-[#7a6a5b]"
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
      <div v-else-if="isThinkingMessage" class="w-full rounded-3xl border border-[#f0e4d8] bg-white/80 p-5 shadow-sm">
        <div class="flex items-center gap-2 text-xs font-medium text-[#b29f8c]">
          <svg class="h-4 w-4 animate-spin-fast" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v4m0 8v4m8-8h-4M8 12H4m12.364-7.364l-2.828 2.828M8.464 15.536l-2.828 2.828m0-12.728l2.828 2.828m8.485 8.485l2.828 2.828" />
          </svg>
          思考中...
        </div>
        <p class="mt-3 text-sm leading-relaxed text-[#5c4f43]">{{ message.content }}</p>
        <div class="mt-4 space-y-2">
          <div class="h-2 w-full rounded-full bg-[#f5e9da]" />
          <div class="h-2 w-11/12 rounded-full bg-[#f3e3d0]" />
          <div class="h-2 w-3/4 rounded-full bg-[#f3e0ca]" />
        </div>
      </div>

      <!-- Assistant / User message -->
      <div
        v-else
        class="relative max-w-full"
        :class="bubbleContainerClass"
      >
        <div class="relative inline-flex max-w-full">
          <button
            v-if="isAssistant || isUser"
            type="button"
            class="absolute right-3 top-3 inline-flex h-8 w-8 items-center justify-center rounded-full bg-white/80 text-[#7a675a] opacity-0 shadow-sm transition hover:bg-white group-hover:opacity-100"
            @click="copyMessage"
          >
            <svg v-if="!copied" class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6">
              <path stroke-linecap="round" stroke-linejoin="round" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
            </svg>
            <svg v-else class="h-4 w-4 text-emerald-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
              <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" />
            </svg>
          </button>
          <div
            class="markdown-content prose-sm max-w-none whitespace-pre-wrap break-words leading-relaxed"
            :class="bubbleClass"
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

const rootAlignmentClass = computed(() => (isUser.value ? 'justify-end text-right' : 'justify-start'))
const contentAlignmentClass = computed(() => (isUser.value ? 'items-end' : 'items-start'))

const showAvatar = computed(() => !isUser.value && !isSystem.value)

const avatarClass = computed(() =>
  isAssistant.value
    ? 'bg-[#f4e7da] text-[#c47a4d]'
    : isTool.value
      ? 'bg-[#e6f1ff] text-[#4c6fb3]'
      : 'bg-[#f4e7da] text-[#c47a4d]',
)

const bubbleClass = computed(() => {
  if (isUser.value) {
    return [
      'rounded-3xl bg-gradient-to-br from-[#d88a5d] to-[#c06d3f] px-5 py-4 text-white shadow-[0_16px_35px_rgba(206,132,78,0.25)] max-w-full lg:max-w-[640px] min-w-0',
      groupRadiusClass.value,
    ]
  }
  return [
    'rounded-3xl border border-[#f0e4d8] bg-white/90 px-5 py-4 text-[#433a32] shadow-[0_20px_45px_rgba(224,198,170,0.16)] backdrop-blur max-w-full lg:max-w-[640px] min-w-0',
    groupRadiusClass.value,
  ]
})

const bubbleContainerClass = computed(() => (isUser.value ? 'ml-auto' : 'mr-auto'))

const groupRadiusClass = computed(() => {
  switch (props.groupBehavior) {
    case 'compact-start':
      return isUser.value ? 'rounded-br-md' : 'rounded-bl-md'
    case 'compact-middle':
      return isUser.value ? 'rounded-br-md rounded-tr-md' : 'rounded-bl-md rounded-tl-md'
    case 'compact-end':
      return isUser.value ? 'rounded-tr-md' : 'rounded-tl-md'
    default:
      return ''
  }
})

const spacingClass = computed(() => {
  switch (props.groupBehavior) {
    case 'compact-start':
      return ''
    case 'compact-middle':
      return '-mt-4'
    case 'compact-end':
      return '-mt-2'
    default:
      return ''
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
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.6" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
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
  margin-bottom: 0.75rem;
}

.markdown-content :deep(p:last-child) {
  margin-bottom: 0;
}

.markdown-content :deep(ul),
.markdown-content :deep(ol) {
  margin: 0.75rem 0;
  padding-left: 1.25rem;
}

.markdown-content :deep(code) {
  background: rgba(244, 231, 218, 0.6);
  border-radius: 0.5rem;
  padding: 0.2rem 0.5rem;
  font-size: 0.875em;
}

.markdown-content :deep(pre) {
  margin: 1rem 0;
  padding: 0.75rem;
  border-radius: 1rem;
  background: #1f2933;
  color: #f8fafc;
  overflow-x: auto;
}

.markdown-content :deep(a) {
  color: #c47a4d;
  text-decoration: underline;
  text-underline-offset: 3px;
}

.markdown-content :deep(blockquote) {
  margin: 1rem 0;
  padding-left: 1rem;
  border-left: 3px solid rgba(212, 132, 80, 0.4);
  color: #6d5f52;
}

.code-block-wrapper {
  border-radius: 1rem;
  overflow: hidden;
  border: 1px solid rgba(244, 231, 218, 0.4);
}

.code-block-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.6rem 0.9rem;
  background: rgba(250, 245, 238, 0.8);
  color: #7a6a5b;
  font-size: 0.75rem;
}

.copy-code-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.3rem 0.6rem;
  border-radius: 9999px;
  border: 1px solid transparent;
  background: rgba(255, 255, 255, 0.8);
  color: #7a6a5b;
  cursor: pointer;
  transition: all 0.18s ease;
  font-weight: 600;
}

.copy-code-btn:hover {
  border-color: rgba(212, 132, 80, 0.26);
  background: rgba(255, 255, 255, 1);
}

.code-block-wrapper pre {
  margin: 0;
}

.animate-spin-fast {
  animation: spin 1.2s linear infinite;
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
