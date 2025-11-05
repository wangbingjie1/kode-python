<template>
  <aside :class="panelClass">
    <header class="flex items-center justify-between px-5 pb-4 pt-6">
      <div>
        <p class="text-xs font-semibold uppercase tracking-[0.26em] text-[#b6a493]">Conversation</p>
        <p class="mt-2 text-lg font-semibold text-[#2f2720]">{{ conversationTitle }}</p>
      </div>
      <button
        type="button"
        class="flex h-9 w-9 items-center justify-center rounded-full border border-transparent text-[#a38b75] transition hover:border-[#eadfd3] hover:bg-white/80 hover:text-[#7c6551]"
        aria-label="关闭上下文"
        @click="$emit('close')"
      >
        <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
          <path stroke-linecap="round" stroke-linejoin="round" d="M6 6l12 12M6 18L18 6" />
        </svg>
      </button>
    </header>

    <div class="flex-1 overflow-y-auto px-5 pb-8">
      <section class="rounded-2xl border border-[#eadfd3] bg-white/80 p-4 shadow-sm">
        <div class="flex items-center justify-between text-sm font-medium text-[#6d5f52]">
          <span class="flex items-center gap-2">
            <span class="text-xs uppercase tracking-wide text-[#b6a493]">连接状态</span>
          </span>
          <span
            class="inline-flex items-center gap-2 rounded-full px-3 py-1 text-xs font-semibold shadow-inner"
            :class="isConnected ? 'bg-[#e9f8f1] text-[#0a7f4b]' : 'bg-[#fdebed] text-[#a7344a]'"
          >
            <span
              class="h-2.5 w-2.5 rounded-full"
              :class="isConnected ? 'bg-emerald-400' : 'bg-rose-400'"
            ></span>
            {{ isConnected ? '已连接' : '未连接' }}
          </span>
        </div>
        <p class="mt-4 text-xs text-[#9a8b7c]">
          {{ statusDescription }}
        </p>
      </section>

      <section class="mt-6 space-y-4">
        <div class="rounded-2xl border border-[#eadfd3] bg-white/70 p-4">
          <h3 class="text-sm font-semibold text-[#3d3430]">会话概览</h3>
          <dl class="mt-3 space-y-2 text-xs text-[#8d7d6c]">
            <div class="flex items-center justify-between">
              <dt>消息数量</dt>
              <dd class="font-medium text-[#5c4f43]">{{ messageCount }} 条</dd>
            </div>
            <div class="flex items-center justify-between">
              <dt>创建时间</dt>
              <dd class="font-medium text-[#5c4f43]">{{ createdAtText }}</dd>
            </div>
            <div class="flex items-center justify-between">
              <dt>最近更新</dt>
              <dd class="font-medium text-[#5c4f43]">{{ updatedAtText }}</dd>
            </div>
          </dl>
        </div>

        <div class="rounded-2xl border border-dashed border-[#eadfd3] bg-white/50 p-4 text-center text-xs text-[#9a8b7c]">
          <p>未来将在此展示引用资料、知识库链接以及自动化工具的执行记录。</p>
          <p class="mt-2">欢迎设计更多需要的上下文信息。</p>
        </div>
      </section>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { Conversation } from '@/services/api'

const props = defineProps<{
  conversation: Conversation | null
  isConnected: boolean
  messageCount: number
  modal?: boolean
}>()

defineEmits<{
  close: []
}>()

const panelClass = computed(() => [
  'flex h-full flex-col bg-[#fdfaf4] text-[#2f2720]',
  props.modal
    ? 'w-full max-w-md shadow-2xl ring-1 ring-black/10 sm:ml-auto sm:w-[420px] sm:rounded-l-3xl'
    : '',
])

const conversationTitle = computed(() => props.conversation?.title || '未命名会话')

const statusDescription = computed(() => {
  if (props.isConnected) {
    return '系统正在跟随你的输入实时响应，如需断开连接可在上方操作栏中处理。'
  }
  return '当前会话暂未成功连接，请检查网络状态或稍后重试。'
})

function formatTimestamp(value?: string | null) {
  if (!value) return '暂无'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '暂无'
  return date.toLocaleString('zh-CN', {
    month: 'long',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

const createdAtText = computed(() => formatTimestamp(props.conversation?.created_at))
const updatedAtText = computed(() => formatTimestamp(props.conversation?.updated_at))
</script>
