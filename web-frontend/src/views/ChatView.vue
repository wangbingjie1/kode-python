<template>
  <div class="h-screen flex overflow-hidden bg-gray-50">
    <!-- Sidebar -->
    <div class="w-64 flex-shrink-0 hidden md:block">
      <ConversationSidebar
        :conversations="conversations"
        :active-conversation-id="currentConversationId"
        :is-connected="isConnected"
        @new-conversation="handleNewConversation"
        @select-conversation="handleSelectConversation"
        @delete-conversation="handleDeleteConversation"
      />
    </div>

    <!-- Main Content Area -->
    <div class="flex-1 flex flex-col min-w-0">
      <!-- Header -->
      <div class="bg-white border-b border-gray-200 py-3 px-6 flex-shrink-0">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-3">
            <button
              @click="sidebarOpen = !sidebarOpen"
              class="md:hidden p-2 hover:bg-gray-100 rounded-lg"
            >
              <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>
            <div>
              <h1 class="text-lg font-bold text-gray-900">Kode AI 编程助手</h1>
              <div class="flex items-center gap-2 text-xs">
                <div
                  class="w-2 h-2 rounded-full"
                  :class="isConnected ? 'bg-green-500' : 'bg-red-500'"
                ></div>
                <span class="text-gray-500">{{ isConnected ? '在线' : '离线' }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Messages Area -->
      <div class="flex-1 overflow-y-auto">
        <div class="max-w-4xl mx-auto p-6">
          <!-- Welcome Screen -->
          <div v-if="!chatStore.hasMessages" class="text-center py-20">
            <div class="w-20 h-20 bg-gradient-to-br from-blue-600 to-purple-600 rounded-2xl flex items-center justify-center mx-auto mb-6 text-white font-bold text-3xl shadow-lg">
              K
            </div>
            <h2 class="text-3xl font-bold text-gray-900 mb-3">欢迎使用 Kode AI</h2>
            <p class="text-gray-600 mb-12 text-lg">您的智能编程助手，随时为您服务</p>

            <div class="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-3xl mx-auto">
              <div class="bg-white p-6 rounded-xl shadow-sm hover:shadow-md transition-shadow border border-gray-100">
                <div class="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center mx-auto mb-4">
                  <svg class="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
                  </svg>
                </div>
                <h3 class="font-semibold mb-2 text-gray-900">代码生成</h3>
                <p class="text-sm text-gray-600">快速生成高质量代码</p>
              </div>
              <div class="bg-white p-6 rounded-xl shadow-sm hover:shadow-md transition-shadow border border-gray-100">
                <div class="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center mx-auto mb-4">
                  <svg class="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
                <h3 class="font-semibold mb-2 text-gray-900">Bug 修复</h3>
                <p class="text-sm text-gray-600">智能诊断并修复问题</p>
              </div>
              <div class="bg-white p-6 rounded-xl shadow-sm hover:shadow-md transition-shadow border border-gray-100">
                <div class="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center mx-auto mb-4">
                  <svg class="w-6 h-6 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
                  </svg>
                </div>
                <h3 class="font-semibold mb-2 text-gray-900">代码解释</h3>
                <p class="text-sm text-gray-600">深入理解代码逻辑</p>
              </div>
            </div>
          </div>

          <!-- Messages -->
          <div v-else class="space-y-6">
            <MessageItem
              v-for="message in chatStore.messages"
              :key="message.id"
              :message="message"
            />

            <!-- Typing Indicator -->
            <div v-if="chatStore.isTyping" class="flex items-start gap-3">
              <div class="w-8 h-8 bg-gradient-to-br from-purple-500 to-purple-600 rounded-lg flex items-center justify-center text-white text-xs font-bold flex-shrink-0">
                AI
              </div>
              <div class="bg-white rounded-xl px-4 py-3 shadow-sm border border-gray-200">
                <div class="flex gap-1.5">
                  <div class="w-2 h-2 bg-purple-500 rounded-full animate-bounce"></div>
                  <div class="w-2 h-2 bg-purple-500 rounded-full animate-bounce" style="animation-delay: 0.15s"></div>
                  <div class="w-2 h-2 bg-purple-500 rounded-full animate-bounce" style="animation-delay: 0.3s"></div>
                </div>
              </div>
            </div>

            <div ref="messagesEnd"></div>
          </div>
        </div>
      </div>

      <!-- Input Area -->
      <div class="flex-shrink-0">
        <ChatInput
          :disabled="!isConnected"
          :is-sending="chatStore.isTyping"
          @send="handleSendMessage"
        />
      </div>
    </div>

    <!-- Mobile Sidebar Overlay -->
    <div
      v-if="sidebarOpen"
      class="md:hidden fixed inset-0 bg-black bg-opacity-50 z-40"
      @click="sidebarOpen = false"
    >
      <div class="w-64 h-full" @click.stop>
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

// Watch for messages to auto-scroll
watch(() => chatStore.messages.length, async () => {
  await nextTick()
  messagesEnd.value?.scrollIntoView({ behavior: 'smooth' })
})

// Watch for route changes to reinitialize conversation
watch(() => route.params.conversationId, async (newId, oldId) => {
  if (newId && newId !== oldId) {
    await initializeConversation()
  }
})

async function handleSendMessage(message: string) {
  if (!isConnected.value) return

  try {
    await chatStore.sendMessage(message)
  } catch (error) {
    console.error('Error sending message:', error)
    notification.error('发送失败', '无法发送消息，请检查连接状态后重试')
  }
}

async function handleNewConversation() {
  if (isLoading.value) return

  isLoading.value = true
  try {
    const conversation = await chatStore.createNewConversation(DEFAULT_PROJECT_ID, '新对话')
    await loadConversations()
    // Don't call initializeConversation here, let router navigation trigger it
    await router.push(`/chat/${conversation.id}`)
    notification.success('对话已创建', '', 2000, true) // Silent notification
  } catch (error) {
    console.error('Error creating conversation:', error)
    notification.error('创建失败', '无法创建新对话，请稍后重试')
  } finally {
    isLoading.value = false
    sidebarOpen.value = false
  }
}

async function handleSelectConversation(conversationId: string) {
  // Router push will trigger the watcher which calls initializeConversation
  await router.push(`/chat/${conversationId}`)
  sidebarOpen.value = false
}

async function handleDeleteConversation(conversationId: string) {
  try {
    await api.delete(`/chat/conversations/${conversationId}`)
    await loadConversations()

    // If we deleted the current conversation, create a new one
    if (conversationId === currentConversationId.value) {
      await handleNewConversation()
    }

    notification.success('对话已删除', '', 2000, true)
  } catch (error) {
    console.error('Error deleting conversation:', error)
    notification.error('删除失败', '无法删除对话')
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
      notification.success('已连接', '', 1500, true) // Silent notification
    } catch (error) {
      console.error('[ChatView] Error connecting to conversation:', error)
      notification.error('连接失败', '无法连接到对话，请检查后端服务是否运