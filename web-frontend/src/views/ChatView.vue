<template>
  <div class="min-h-screen bg-[#fdf7f0] text-[#322d29] antialiased">
    <div class="flex min-h-screen flex-col lg:flex-row">
      <div class="hidden lg:flex lg:w-16 lg:flex-col lg:items-center lg:gap-8 lg:border-r lg:border-[#eadfd3] lg:bg-[#fcf1e4] lg:py-6">
        <div class="flex h-10 w-10 items-center justify-center rounded-2xl bg-white/80 text-[#d78b5b] shadow-inner">
          <svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 3l2.09 6.26H20l-5.05 3.67L16.18 19 12 15.77 7.82 19l1.23-6.07L4 9.26h5.91z" />
          </svg>
        </div>
        <div class="flex flex-1 flex-col items-center gap-6 text-[#b9a695]">
          <button type="button" class="rounded-full p-2 transition hover:bg-white/60 hover:text-[#8c7763]">
            <svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7">
              <path stroke-linecap="round" stroke-linejoin="round" d="M12 5v14m7-7H5" />
            </svg>
          </button>
          <button type="button" class="rounded-full p-2 transition hover:bg-white/60 hover:text-[#8c7763]">
            <svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7">
              <path stroke-linecap="round" stroke-linejoin="round" d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>
          <button type="button" class="rounded-full p-2 transition hover:bg-white/60 hover:text-[#8c7763]">
            <svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7">
              <path stroke-linecap="round" stroke-linejoin="round" d="M4 7h16M4 12h16M4 17h16" />
            </svg>
          </button>
        </div>
      </div>

      <div class="hidden lg:flex lg:w-80 lg:flex-none lg:border-r lg:border-[#eadfd3] lg:bg-[#fefaf4]">
        <ConversationSidebar
          class="w-full"
          :conversations="conversations"
          :active-conversation-id="currentConversationId"
          :is-connected="isConnected"
          @new-conversation="handleNewConversation"
          @select-conversation="handleSelectConversation"
          @delete-conversation="handleDeleteConversation"
        />
      </div>

      <main class="flex w-full flex-1 flex-col">
        <header class="border-b border-[#eadfd3] px-5 py-5 lg:px-12">
          <div class="flex items-center gap-3">
            <button
              @click="sidebarOpen = true"
              class="flex h-11 w-11 items-center justify-center rounded-full border border-[#eadfd3] bg-white/80 text-[#8a7c6b] shadow-sm transition hover:-translate-y-0.5 hover:text-[#6f6256] hover:shadow-md focus:outline-none focus:ring-2 focus:ring-[#d8c6b4] lg:hidden"
              aria-label="打开对话列表"
              type="button"
            >
              <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>

            <div class="flex flex-col gap-2">
              <p class="text-xs font-semibold uppercase tracking-[0.32em] text-[#b9aa9a]">Kode AI</p>
              <p class="text-lg font-semibold text-[#2f2720]">{{ conversationTitle }}</p>
            </div>
          </div>
        </header>

        <div class="flex flex-1 flex-col items-center px-5 pb-16 pt-10 lg:px-16">
          <div
            v-if="chatStore.hasMessages"
            class="flex w-full flex-1"
          >
            <div class="mx-auto flex w-full max-w-3xl flex-1 flex-col overflow-hidden rounded-[32px] border border-[#efe2d0] bg-white/80 shadow-[0_35px_90px_rgba(185,157,126,0.18)]">
              <div class="conversation-scroll flex-1 overflow-y-auto px-8 py-10">
                <div class="space-y-8">
                  <MessageItem
                    v-for="message in chatStore.messages"
                    :key="message.id"
                    :message="message"
                  />

                  <div
                    v-if="chatStore.isTyping"
                    class="typing-indicator flex items-center gap-3 rounded-2xl bg-[#f9f0e4] px-4 py-3 text-[#6d6256] shadow-sm"
                  >
                    <div class="flex h-8 w-8 items-center justify-center rounded-xl bg-[#f0c9b0] text-xs font-semibold text-[#a46443]">
                      AI
                    </div>
                    <div class="flex items-center gap-1.5">
                      <span class="inline-block h-2 w-2 animate-bounce rounded-full bg-[#e4b292]"></span>
                      <span class="inline-block h-2 w-2 animate-bounce rounded-full bg-[#e4b292]" style="animation-delay: 0.15s"></span>
                      <span class="inline-block h-2 w-2 animate-bounce rounded-full bg-[#e4b292]" style="animation-delay: 0.3s"></span>
                    </div>
                  </div>

                  <div ref="messagesEnd"></div>
                </div>
              </div>
            </div>
          </div>

          <div class="mt-auto w-full max-w-3xl pt-10">
            <ChatInput
              :disabled="!isConnected"
              :is-sending="chatStore.isTyping"
              @send="handleSendMessage"
            />
          </div>
        </div>
      </main>
    </div>

    <div
      v-if="sidebarOpen"
      class="fixed inset-0 z-40 flex bg-black/30 backdrop-blur-sm transition lg:hidden"
      @click="sidebarOpen = false"
    >
      <div
        class="h-full w-72 bg-[#fefaf4] shadow-2xl ring-1 ring-black/5"
        @click.stop
      >
        <ConversationSidebar
          :conversations="conversations"
          :active-conversation-id="currentConversationId"
          :is-connected="isConnected"
          @new-conversation="handleNewConversation"
          @select-conversation="handleSelectConversation"
          @delete-conversation="handleDeleteConversation"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick, watch, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useChatStore } from '@/stores/chat'
import MessageItem from '@/components/MessageItem.vue'
import ConversationSidebar from '@/components/ConversationSidebar.vue'
import ChatInput from '@/components/ChatInput.vue'
import { notification } from '@/composables/useNotification'
import { DEFAULT_PROJECT_ID } from '@/config/constants'
import api from '@/services/api'

const route = useRoute()
const router = useRouter()
const chatStore = useChatStore()

const messagesEnd = ref<HTMLElement>()
const isLoading = ref(false)
const sidebarOpen = ref(false)
const conversations = ref<any[]>([])

const isConnected = computed(() => chatStore.isConnected)
const currentConversationId = computed(() => route.params.conversationId as string)
const conversationTitle = computed(() => chatStore.currentConversation?.title || '未命名会话')

watch(
  () => chatStore.messages.length,
  async () => {
    await nextTick()
    messagesEnd.value?.scrollIntoView({ behavior: 'smooth' })
  },
)

watch(
  () => route.params.conversationId,
  async (newId, oldId) => {
    if (newId && newId !== oldId) {
      await initializeConversation()
    }
  },
)

async function handleSendMessage(message: string, databaseName?: string) {
  if (!isConnected.value) return

  try {
    await chatStore.sendMessage(message, databaseName)
  } catch (error) {
    console.error('Error sending message:', error)
    notification.error('发送失败', '无法发送消息，请检查连接状态或稍后再试')
  }
}

async function handleNewConversation() {
  if (isLoading.value) return

  isLoading.value = true
  try {
    const conversation = await chatStore.createNewConversation(DEFAULT_PROJECT_ID, '新对话')
    await loadConversations()
    await router.push(`/chat/${conversation.id}`)
    notification.success('已创建对话', '', 2000, true)
  } catch (error) {
    console.error('Error creating conversation:', error)
    notification.error('创建失败', '无法创建新对话，请稍后再试')
  } finally {
    isLoading.value = false
    sidebarOpen.value = false
  }
}

async function handleSelectConversation(conversationId: string) {
  await router.push(`/chat/${conversationId}`)
  sidebarOpen.value = false
}

async function handleDeleteConversation(conversationId: string) {
  try {
    await api.delete(`/chat/conversations/${conversationId}`)
    await loadConversations()

    if (conversationId === currentConversationId.value) {
      await handleNewConversation()
    }

    notification.success('会话已删除', '', 2000, true)
  } catch (error) {
    console.error('Error deleting conversation:', error)
    notification.error('删除失败', '无法删除会话')
  }
}

async function loadConversations() {
  try {
    const response = await api.get(`/chat/projects/${DEFAULT_PROJECT_ID}/conversations`)
    conversations.value = response.data
  } catch (error) {
    console.error('Error loading conversations:', error)
  }
}

async function initializeConversation() {
  const conversationId = route.params.conversationId as string
  console.log('[ChatView] initializeConversation called with ID:', conversationId)

  if (conversationId) {
    isLoading.value = true
    console.log('[ChatView] Connecting to conversation...')
    try {
      await chatStore.connectToConversation(conversationId)
      console.log('[ChatView] Connected successfully. isTyping:', chatStore.isTyping, 'hasMessages:', chatStore.hasMessages)
      notification.success('连接成功', '', 1500, true)
    } catch (error) {
      console.error('[ChatView] Error connecting to conversation:', error)
      notification.error('连接失败', '无法连接到会话，请稍后再试')
    } finally {
      isLoading.value = false
      console.log('[ChatView] isLoading set to false')
    }
  } else {
    console.log('[ChatView] No conversation ID, creating new conversation')
    await handleNewConversation()
  }
}

onMounted(async () => {
  await loadConversations()
  await initializeConversation()
})

onUnmounted(() => {
  chatStore.clearConversation()
})
</script>
