<template>
  <div class="h-full flex flex-col bg-gray-900 text-gray-100 border-r border-gray-700">
    <!-- Header -->
    <div class="p-4 border-b border-gray-700">
      <button
        @click="$emit('new-conversation')"
        class="w-full px-4 py-3 bg-blue-600 hover:bg-blue-700 rounded-lg font-medium transition-colors flex items-center justify-center gap-2"
      >
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
        </svg>
        新建对话
      </button>
    </div>

    <!-- Conversations List -->
    <div class="flex-1 overflow-y-auto p-3 space-y-1">
      <div
        v-for="conv in conversations"
        :key="conv.id"
        @click="$emit('select-conversation', conv.id)"
        class="group px-3 py-3 rounded-lg cursor-pointer transition-all relative"
        :class="conv.id === activeConversationId
          ? 'bg-gray-700'
          : 'hover:bg-gray-800'"
      >
        <div class="flex items-start gap-2">
          <svg class="w-5 h-5 text-gray-400 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
          </svg>
          <div class="flex-1 min-w-0">
            <p class="text-sm font-medium truncate">{{ conv.title }}</p>
            <p class="text-xs text-gray-400 mt-0.5">{{ formatDate(conv.created_at) }}</p>
          </div>
          <button
            @click.stop="$emit('delete-conversation', conv.id)"
            class="opacity-0 group-hover:opacity-100 p-1 hover:bg-gray-600 rounded transition-opacity"
          >
            <svg class="w-4 h-4 text-gray-400 hover:text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
          </button>
        </div>
      </div>

      <!-- Empty State -->
      <div v-if="conversations.length === 0" class="text-center py-12 text-gray-500">
        <svg class="w-12 h-12 mx-auto mb-3 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
        </svg>
        <p class="text-sm">暂无对话</p>
      </div>
    </div>

    <!-- Footer -->
    <div class="p-4 border-t border-gray-700">
      <div class="flex items-center gap-3 px-3 py-2 rounded-lg bg-gray-800">
        <div class="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center text-sm font-bold">
          K
        </div>
        <div class="flex-1 min-w-0">
          <p class="text-sm font-medium">Kode AI</p>
          <p class="text-xs text-gray-400">{{ statusText }}</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface Conversation {
  id: string
  title: string
  created_at: string
}

const props = defineProps<{
  conversations: Conversation[]
  activeConversationId?: string
  isConnected: boolean
}>()

defineEmits<{
  'new-conversation': []
  'select-conversation': [id: string]
  'delete-conversation': [id: string]
}>()

const statusText = computed(() => props.isConnected ? '在线' : '离线')

function formatDate(dateString: string): string {
  const date = new Date(dateString)
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  const days = Math.floor(diff / (1000 * 60 * 60 * 24))

  if (days === 0) return '今天'
  if (days === 1) return '昨天'
  if (days < 7) return `${days} 天前`

  return date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
}
</script>
