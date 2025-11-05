<template>
  <aside class="flex h-full w-full flex-col bg-[#fdf7f0] text-[#413730]">
    <header class="border-b border-[#eadfd3] px-4 pb-5 pt-5">
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-3">
          <div class="flex h-9 w-9 items-center justify-center rounded-xl bg-[#f3c8a5] text-sm font-semibold text-[#8a4e2f] shadow-inner">
            K
          </div>
          <div class="leading-tight">
            <p class="text-sm font-semibold text-[#362e27]">Kode Copilot</p>
            <p class="text-xs text-[#a09182]">Powered by FutureShare</p>
          </div>
        </div>
        <span class="rounded-full bg-white/60 px-2 py-1 text-[10px] font-medium uppercase tracking-[0.22em] text-[#b29f8c]">
          Beta
        </span>
      </div>

      <div class="mt-5 flex flex-col gap-3">
        <button
          type="button"
          class="flex w-full items-center justify-center gap-2 rounded-xl bg-[#f26b3a] px-4 py-3 text-sm font-semibold text-white shadow-[0_12px_30px_rgba(242,107,58,0.28)] transition hover:-translate-y-0.5 hover:bg-[#e0582a]"
          @click="$emit('new-conversation')"
        >
          <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 5v14m7-7H5" />
          </svg>
          New chat
        </button>

        <div class="flex items-center gap-2 rounded-xl bg-white/80 px-3 py-2 text-xs font-medium text-[#78695c] shadow-[0_16px_28px_rgba(190,160,130,0.14)]">
          <span class="h-2.5 w-2.5 rounded-full" :class="statusIndicatorClass"></span>
          <span>{{ statusText }}</span>
        </div>
      </div>
    </header>

    <nav class="border-b border-[#eadfd3] px-4 py-3.5">
      <p class="px-2 text-[11px] font-semibold uppercase tracking-[0.3em] text-[#b49f8d]">Workspace</p>
      <ul class="mt-4 space-y-1.5">
        <li
          v-for="item in navItems"
          :key="item.id"
        >
          <button
            type="button"
            class="flex w-full items-center gap-3 rounded-xl px-3 py-2 text-sm font-medium transition"
            :class="item.active
              ? 'bg-white text-[#312821] shadow-sm'
              : 'text-[#6d5f52] hover:bg-white/70 hover:text-[#3a312a]'"
            @click="$emit('navigate', item.id)"
          >
            <svg class="h-4 w-4 text-[#c58d63]" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7">
              <path stroke-linecap="round" stroke-linejoin="round" :d="item.icon" />
            </svg>
            <span class="truncate">{{ item.label }}</span>
          </button>
        </li>
      </ul>
    </nav>

    <section class="flex-1 overflow-y-auto px-4 py-4">
      <template v-if="isChatsSection">
        <p class="px-2 text-[11px] font-semibold uppercase tracking-[0.26em] text-[#b49f8d]">Recent</p>

        <div
          v-if="conversations.length"
          class="mt-4 space-y-1.5"
        >
          <div
            v-for="conv in conversations"
            :key="conv.id"
            class="group relative flex cursor-pointer items-center gap-3 rounded-2xl px-3 py-3 pr-10 transition"
            :class="conv.id === activeConversationId
              ? 'bg-white text-[#2f2720] shadow-[0_12px_30px_rgba(149,126,102,0.12)]'
              : 'text-[#5d5146] hover:bg-white/70 hover:shadow-[0_10px_28px_rgba(160,138,115,0.12)]'"
            role="button"
            tabindex="0"
            @click="$emit('select-conversation', conv.id)"
            @keydown.enter="$emit('select-conversation', conv.id)"
          >
            <div class="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-xl bg-white/70 text-[#c58d63] shadow-inner">
              <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7">
                <path stroke-linecap="round" stroke-linejoin="round" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V7a2 2 0 012-2h14a2 2 0 012 2v7a2 2 0 01-2 2h-5l-5 5v-4z" />
              </svg>
            </div>
            <div class="min-w-0 flex-1">
              <p class="truncate text-sm font-semibold">{{ conv.title }}</p>
              <p class="mt-1 text-xs text-[#a09182]">{{ formatDate(conv.created_at) }}</p>
            </div>
            <button
              type="button"
              class="absolute right-2.5 top-1/2 -translate-y-1/2 rounded-full p-1 text-[#b6a393] opacity-0 transition group-hover:opacity-100 hover:bg-white hover:text-[#da6c55]"
              aria-label="Delete conversation"
              @click.stop="$emit('delete-conversation', conv.id)"
            >
              <svg class="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6">
                <path stroke-linecap="round" stroke-linejoin="round" d="M19 7l-1 12a2 2 0 01-2 2H8a2 2 0 01-2-2L5 7m4 4v6m4-6v6M9 7V5a1 1 0 011-1h4a1 1 0 011 1v2m-9 0h12" />
              </svg>
            </button>
          </div>
        </div>

        <div
          v-else
          class="mt-10 rounded-2xl border border-dashed border-[#e7d9ca] bg-white/70 px-6 py-10 text-center text-[#8e8172]"
        >
          <div class="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-[#f3c8a5]/60 text-[#c58d63]">
            <svg class="h-6 w-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6">
              <path stroke-linecap="round" stroke-linejoin="round" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.86 9.86 0 01-4.26-.95L3 20l1.4-3.72A6.96 6.96 0 013 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
            </svg>
          </div>
          <p class="mt-4 text-sm font-medium">No conversations yet</p>
          <p class="mt-2 text-xs text-[#b09f8f]">Use the button above to start a new session.</p>
        </div>
      </template>

      <template v-else>
        <div class="mt-10 rounded-2xl border border-dashed border-[#e7d9ca] bg-white/70 px-6 py-10 text-center text-[#8e8172]">
          <div class="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-[#f3c8a5]/60 text-[#c58d63]">
            <svg class="h-6 w-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6">
              <path stroke-linecap="round" stroke-linejoin="round" d="M12 8v8m-4-4h8" />
            </svg>
          </div>
          <p class="mt-4 text-sm font-medium">Coming soon</p>
          <p class="mt-2 text-xs text-[#b09f8f]">This section is not available yet.</p>
        </div>
      </template>
    </section>
  </aside>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface Conversation {
  id: string
  title: string
  created_at: string
}

type SidebarSection = 'chats' | 'projects' | 'database' | 'documents'

const props = defineProps<{
  conversations: Conversation[]
  activeConversationId?: string
  isConnected: boolean
  activeSection: SidebarSection
}>()

defineEmits<{
  'new-conversation': []
  'select-conversation': [id: string]
  'delete-conversation': [id: string]
  navigate: [id: SidebarSection]
}>()

const NAV_ITEMS: ReadonlyArray<{ id: SidebarSection; label: string; icon: string }> = [
  {
    id: 'chats',
    label: 'Chat',
    icon: 'M4 5h16a1 1 0 011 1v12a1 1 0 01-1 1H7l-3 3v-3H4a1 1 0 01-1-1V6a1 1 0 011-1z',
  },
  {
    id: 'projects',
    label: 'Projects',
    icon: 'M4 6a2 2 0 012-2h12a2 2 0 012 2v12H4z',
  },
  {
    id: 'database',
    label: 'Database',
    icon: 'M4 6c0-1.657 3.582-3 8-3s8 1.343 8 3M4 12c0 1.657 3.582 3 8 3s8-1.343 8-3M4 18c0 1.657 3.582 3 8 3s8-1.343 8-3M4 6v12c0 1.657 3.582 3 8 3s8-1.343 8-3V6',
  },
  {
    id: 'documents',
    label: 'Documents',
    icon: 'M7 3h8l4 4v14a1 1 0 01-1 1H7a2 2 0 01-2-2V5a2 2 0 012-2zm8 0v6h6',
  },
]

const navItems = computed(() =>
  NAV_ITEMS.map((item) => ({
    ...item,
    active: item.id === props.activeSection,
  })),
)

const statusText = computed(() => (props.isConnected ? 'Connected' : 'Disconnected'))
const statusIndicatorClass = computed(() =>
  props.isConnected
    ? 'bg-emerald-400 shadow-[0_0_0_3px_rgba(16,166,104,0.12)]'
    : 'bg-rose-300 shadow-[0_0_0_3px_rgba(234,120,138,0.16)]',
)
const isChatsSection = computed(() => props.activeSection === 'chats')

function formatDate(dateString: string): string {
  const date = new Date(dateString)
  if (Number.isNaN(date.getTime())) {
    return ''
  }

  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMinutes = Math.floor(diffMs / (1000 * 60))
  const diffHours = Math.floor(diffMinutes / 60)
  const diffDays = Math.floor(diffHours / 24)

  if (diffMinutes < 0) {
    return date.toLocaleDateString('en-US')
  }

  if (diffDays === 0) {
    if (diffHours === 0) {
      const minutes = Math.max(diffMinutes, 1)
      return `${minutes} minute${minutes === 1 ? '' : 's'} ago`
    }
    return `${diffHours} hour${diffHours === 1 ? '' : 's'} ago`
  }

  if (diffDays === 1) {
    return 'Yesterday'
  }

  if (diffDays < 7) {
    return `${diffDays} days ago`
  }

  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}
</script>
