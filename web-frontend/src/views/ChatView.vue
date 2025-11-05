<template>
  <div class="h-screen bg-white text-gray-900 antialiased">
    <div
      class="relative flex h-full flex-col overflow-hidden lg:grid min-h-0"
      :class="layoutClass"
    >
      <!-- Navigation rail -->
      <aside class="hidden h-full flex-col items-center gap-3 border-r border-gray-200 bg-white px-2 py-4 lg:flex">
        <button
          type="button"
          class="flex h-9 w-9 items-center justify-center rounded-lg text-gray-600 transition hover:bg-gray-100"
          :class="isSidebarCollapsed ? 'bg-gray-100' : ''"
          aria-label="切换侧边栏"
          @click="handleSidebarToggle"
        >
          <svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M4 6h16M4 12h16M4 18h16" />
          </svg>
        </button>

        <button
          type="button"
          class="flex h-9 w-9 items-center justify-center rounded-lg bg-gray-900 text-white transition hover:bg-gray-800"
          aria-label="新建对话"
          @click="handleNewConversation"
        >
          <svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 5v14m7-7H5" />
          </svg>
        </button>

        <div class="mt-2 flex flex-1 flex-col items-center gap-2">
          <button
            v-for="section in sidebarSections"
            :key="section.id"
            type="button"
            class="rounded-lg p-2 transition hover:bg-gray-100"
            :class="activeSidebarSection === section.id ? 'bg-gray-100 text-gray-900' : 'text-gray-500'"
            :aria-label="section.label"
            @click="handleSidebarSectionSelect(section.id)"
          >
            <svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" :d="section.icon" />
            </svg>
          </button>
        </div>
      </aside>

      <!-- Conversation list (desktop) -->
      <aside
        v-show="!isSidebarCollapsed"
        class="hidden h-full border-r border-gray-200 bg-white lg:flex lg:w-[240px]"
      >
        <ConversationSidebar
          class="w-full"
          :conversations="conversations"
          :active-conversation-id="currentConversationId"
          :is-connected="isConnected"
          :active-section="activeSidebarSection"
          @new-conversation="handleNewConversation"
          @select-conversation="handleSelectConversation"
          @delete-conversation="handleDeleteConversation"
          @navigate="handleSidebarSectionSelect"
        />
      </aside>

      <!-- Main conversation area -->
      <main class="relative grid h-full min-w-0 grid-rows-[auto,1fr,auto] overflow-visible min-h-0">
        <header class="border-b border-gray-200 px-4 py-3 sm:px-6">
          <div class="flex flex-wrap items-center justify-between gap-3">
            <div class="flex items-center gap-3">
              <button
                @click="sidebarOpen = true"
                class="flex h-9 w-9 items-center justify-center rounded-lg border border-gray-200 text-gray-600 transition hover:bg-gray-50 lg:hidden"
                aria-label="打开对话列表"
                type="button"
              >
                <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16" />
                </svg>
              </button>

              <div class="flex flex-col">
                <p class="text-sm font-medium text-gray-900">{{ conversationTitle }}</p>
                <div class="flex items-center gap-2 text-xs text-gray-500">
                  <span class="inline-flex items-center gap-1">
                    <span class="inline-block h-1.5 w-1.5 rounded-full" :class="isConnected ? 'bg-green-500' : 'bg-red-400'"></span>
                    {{ isConnected ? '已连接' : '已断开' }}
                  </span>
                  <span v-if="lastUpdatedText">{{ lastUpdatedText }}</span>
                </div>
              </div>
            </div>

            <div class="flex items-center gap-2">
              <button
                type="button"
                class="hidden items-center gap-1.5 rounded-lg border border-gray-200 bg-white px-3 py-1.5 text-xs font-medium text-gray-700 transition hover:bg-gray-50 sm:flex"
                @click="scrollToBottom(true)"
              >
                <svg class="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M12 5v14m0 0l-5-5m5 5l5-5" />
                </svg>
                最新
              </button>

              <button
                type="button"
                class="flex items-center gap-1.5 rounded-lg border border-gray-200 bg-white px-3 py-1.5 text-xs font-medium text-gray-700 transition hover:bg-gray-50"
                @click="handleContextPanelToggle"
              >
                <span>上下文</span>
                <svg class="h-3.5 w-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M5 12h14M12 5l7 7-7 7" />
                </svg>
              </button>
            </div>
          </div>
        </header>

        <section ref="messageContainer" class="relative min-w-0 overflow-y-auto px-4 pb-32 pt-6 sm:px-8 min-h-0 bg-white">
          <div class="mx-auto w-full max-w-3xl min-w-0 pb-12">
            <template v-if="timelineMessages.length">
              <MessageItem
                v-for="item in timelineMessages"
                :key="item.message.id"
                class="w-full"
                :message="item.message"
                :group-behavior="item.groupBehavior"
              />
            </template>

            <div v-else class="flex h-full flex-col items-center justify-center gap-4 py-20 text-center">
              <div class="flex h-12 w-12 items-center justify-center rounded-xl bg-gray-900 text-white">
                <svg class="h-6 w-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V7a2 2 0 012-2h14a2 2 0 012 2v7a2 2 0 01-2 2h-5l-5 5v-4z" />
                </svg>
              </div>
              <div>
                <h3 class="text-base font-semibold text-gray-900">开始新的对话</h3>
                <p class="mt-1 text-sm text-gray-500">在下方输入框中输入消息开始聊天</p>
              </div>
              <button
                type="button"
                class="inline-flex items-center gap-2 rounded-lg bg-gray-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-gray-800"
                @click="handleNewConversation"
              >
                <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M12 5v14m7-7H5" />
                </svg>
                新建会话
              </button>
            </div>
          </div>

          <button
            v-if="showScrollToLatest"
            type="button"
            class="fixed bottom-32 right-6 z-30 flex items-center gap-2 rounded-lg border border-gray-200 bg-white px-3 py-2 text-xs font-medium text-gray-700 shadow-lg transition hover:bg-gray-50"
            @click="scrollToBottom(true)"
          >
            <svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M12 5v14m0 0l-5-5m5 5l5-5" />
            </svg>
            回到最新
          </button>
        </section>

        <footer class="px-4 pb-6 pt-4 sm:px-6">
          <div class="mx-auto w-full max-w-3xl min-w-0">
            <ChatInput
              :disabled="!isConnected"
              :is-sending="chatStore.isTyping"
              @send="handleSendMessage"
            />
          </div>
        </footer>
      </main>

      <!-- Desktop context panel -->
      <ContextPanel
        v-if="contextPanelOpen && isDesktopViewport"
        class="hidden h-full border-l border-gray-200 bg-white lg:flex lg:w-[300px]"
        :conversation="chatStore.currentConversation"
        :is-connected="isConnected"
        :message-count="chatStore.messages.length"
        @close="handleContextPanelClose"
      />

      <!-- Mobile overlays -->
      <div
        v-if="sidebarOpen"
        class="fixed inset-0 z-40 flex bg-black/20 backdrop-blur-sm transition lg:hidden"
        @click="sidebarOpen = false"
      >
        <div
          class="h-full w-72 bg-white shadow-xl"
          @click.stop
        >
          <ConversationSidebar
            :conversations="conversations"
            :active-conversation-id="currentConversationId"
            :is-connected="isConnected"
            :active-section="activeSidebarSection"
            @new-conversation="handleNewConversation"
            @select-conversation="handleSelectConversation"
            @delete-conversation="handleDeleteConversation"
            @navigate="handleSidebarSectionSelect"
          />
        </div>
      </div>

      <div
        v-if="contextPanelSheet && !isDesktopViewport"
        class="fixed inset-0 z-40 flex bg-black/20 backdrop-blur-sm lg:hidden"
        @click="handleContextPanelClose"
      >
        <div class="ml-auto flex h-full w-full max-w-md" @click.stop>
          <ContextPanel
            modal
            :conversation="chatStore.currentConversation"
            :is-connected="isConnected"
            :message-count="chatStore.messages.length"
            @close="handleContextPanelClose"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import ConversationSidebar from '@/components/ConversationSidebar.vue'
import ChatInput from '@/components/ChatInput.vue'
import ContextPanel from '@/components/ContextPanel.vue'
import MessageItem from '@/components/MessageItem.vue'
import { notification } from '@/composables/useNotification'
import { DEFAULT_PROJECT_ID } from '@/config/constants'
import { useChatStore } from '@/stores/chat'
import type { ChatMessage } from '@/stores/chat'
import api from '@/services/api'

type SidebarSection = 'chats' | 'projects' | 'database' | 'documents'

interface TimelineMessage {
  message: ChatMessage
  groupBehavior: 'standalone' | 'compact-start' | 'compact-middle' | 'compact-end'
}

const route = useRoute()
const router = useRouter()
const chatStore = useChatStore()

const sidebarSections: ReadonlyArray<{ id: SidebarSection; label: string; icon: string }> = [
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

const isLoading = ref(false)
const sidebarOpen = ref(false)
const conversations = ref<any[]>([])
const isSidebarCollapsed = ref(false)
const activeSidebarSection = ref<SidebarSection>('chats')
const contextPanelOpen = ref(false)
const contextPanelSheet = ref(false)
const isDesktopViewport = ref(false)
const showScrollToLatest = ref(false)
const messageContainer = ref<HTMLElement | null>(null)
const hasUserToggledSidebar = ref(false)
const hasUserToggledContext = ref(false)

const isConnected = computed(() => chatStore.isConnected)
const currentConversationId = computed(() => route.params.conversationId as string)
const conversationTitle = computed(() => chatStore.currentConversation?.title || '未命名会话')
const lastUpdatedText = computed(() => {
  const updatedAt = chatStore.currentConversation?.updated_at
  if (!updatedAt) return ''
  const date = new Date(updatedAt)
  if (Number.isNaN(date.getTime())) return ''
  const diffMinutes = Math.floor((Date.now() - date.getTime()) / (1000 * 60))
  if (diffMinutes < 1) return '刚刚更新'
  if (diffMinutes < 60) return `${diffMinutes} 分钟前更新`
  const diffHours = Math.floor(diffMinutes / 60)
  if (diffHours < 24) return `${diffHours} 小时前更新`
  const diffDays = Math.floor(diffHours / 24)
  if (diffDays === 1) return '昨天更新'
  return `${diffDays} 天前更新`
})

const layoutClass = computed(() => {
  const hasSidebar = !isSidebarCollapsed.value
  const hasContext = contextPanelOpen.value && isDesktopViewport.value

  if (hasSidebar && hasContext) {
    return 'lg:grid-cols-[48px_240px_minmax(0,1fr)_300px]'
  }
  if (hasSidebar) {
    return 'lg:grid-cols-[48px_240px_minmax(0,1fr)]'
  }
  if (hasContext) {
    return 'lg:grid-cols-[48px_minmax(0,1fr)_300px]'
  }
  return 'lg:grid-cols-[48px_minmax(0,1fr)]'
})

const timelineMessages = computed<TimelineMessage[]>(() => {
  const items: TimelineMessage[] = []
  let previousRole: string | null = null

  chatStore.messages.forEach((message, index) => {
    const nextMessage = chatStore.messages[index + 1]
    const nextRole = nextMessage?.role ?? null
    const groupBehavior = resolveGroupBehavior(previousRole, message.role, nextRole)

    items.push({
      message,
      groupBehavior,
    })
    previousRole = message.role
  })

  return items
})

let scrollThrottle: ReturnType<typeof setTimeout> | null = null
let mediaQueryCleanup: (() => void) | null = null
let resizeCleanup: (() => void) | null = null

watch(
  () => timelineMessages.value.length,
  async () => {
    await nextTick()
    scrollToBottom()
  },
)

watch(
  () => timelineMessages.value.map(m => m.message.content).join(''),
  async () => {
    if (scrollThrottle) {
      clearTimeout(scrollThrottle)
    }
    scrollThrottle = setTimeout(async () => {
      await nextTick()
      scrollToBottom()
    }, 120)
  },
)

watch(
  () => chatStore.isTyping,
  async (typing) => {
    if (typing) {
      await nextTick()
      scrollToBottom(true)
    }
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

watch(sidebarOpen, (open) => {
  if (open) {
    activeSidebarSection.value = 'chats'
    isSidebarCollapsed.value = false
  }
})

watch(messageContainer, (element, previous) => {
  if (previous) {
    previous.removeEventListener('scroll', handleScroll)
  }
  if (element) {
    element.addEventListener('scroll', handleScroll)
  }
})

function handleScroll() {
  const container = messageContainer.value
  if (!container) return
  const distanceToBottom = container.scrollHeight - (container.scrollTop + container.clientHeight)
  showScrollToLatest.value = distanceToBottom > 220
}

function scrollToBottom(force = false) {
  const container = messageContainer.value
  if (!container) return

  const distanceToBottom = container.scrollHeight - (container.scrollTop + container.clientHeight)
  const shouldScroll = force || distanceToBottom < 200

  if (shouldScroll) {
    container.scrollTo({
      top: container.scrollHeight,
      behavior: force ? 'smooth' : 'auto',
    })
    showScrollToLatest.value = false
  }
}

function resolveGroupBehavior(
  previousRole: string | null,
  currentRole: string,
  nextRole: string | null,
): TimelineMessage['groupBehavior'] {
  // 系统消息独立显示
  if (currentRole === 'system') {
    return 'standalone'
  }

  // 工具调用和 assistant/user 消息都参与紧凑分组
  const isSameAsPrevious = previousRole === currentRole
  const isSameAsNext = nextRole === currentRole

  if (!isSameAsPrevious && !isSameAsNext) {
    return 'standalone'
  }
  if (!isSameAsPrevious && isSameAsNext) {
    return 'compact-start'
  }
  if (isSameAsPrevious && isSameAsNext) {
    return 'compact-middle'
  }
  return 'compact-end'
}

const SIDEBAR_COLLAPSE_BREAKPOINT = 1200
const CONTEXT_OPEN_BREAKPOINT = 1500

function applyResponsiveLayout(width: number) {
  if (!width) return

  if (width < 1024) {
    contextPanelOpen.value = false
    if (!hasUserToggledSidebar.value) {
      isSidebarCollapsed.value = true
    }
    return
  }

  if (width < SIDEBAR_COLLAPSE_BREAKPOINT) {
    if (!hasUserToggledSidebar.value) {
      isSidebarCollapsed.value = true
    }
  } else if (!hasUserToggledSidebar.value) {
    isSidebarCollapsed.value = false
  }

  if (width >= CONTEXT_OPEN_BREAKPOINT) {
    if (!hasUserToggledContext.value) {
      contextPanelOpen.value = true
    }
  } else if (!hasUserToggledContext.value) {
    contextPanelOpen.value = false
  }
}

function handleContextPanelToggle() {
  hasUserToggledContext.value = true
  if (isDesktopViewport.value) {
    contextPanelOpen.value = !contextPanelOpen.value
  } else {
    contextPanelSheet.value = true
  }
}

function handleContextPanelClose() {
  hasUserToggledContext.value = true
  if (isDesktopViewport.value) {
    contextPanelOpen.value = false
  } else {
    contextPanelSheet.value = false
  }
}

async function handleSendMessage(message: string, databaseName?: string) {
  if (!isConnected.value) return

  try {
    await chatStore.sendMessage(message, databaseName)
    await nextTick()
    scrollToBottom(true)
  } catch (error) {
    console.error('Error sending message:', error)
    notification.error('发送失败', '暂时无法发送消息，请检查网络后重试。')
  }
}

async function handleNewConversation() {
  if (isLoading.value) return

  activeSidebarSection.value = 'chats'

  isLoading.value = true
  try {
    const conversation = await chatStore.createNewConversation(DEFAULT_PROJECT_ID, 'New chat')
    await loadConversations()
    await router.push(`/chat/${conversation.id}`)
    notification.success('已创建新会话', '', 2000, true)
  } catch (error) {
    console.error('Error creating conversation:', error)
    notification.error('创建失败', '暂时无法创建新对话，请稍后再试。')
  } finally {
    isLoading.value = false
    sidebarOpen.value = false
  }
}

async function handleSelectConversation(conversationId: string) {
  await router.push(`/chat/${conversationId}`)
  activeSidebarSection.value = 'chats'
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
    notification.error('删除失败', '暂时无法删除该对话。')
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

function handleSidebarSectionSelect(section: SidebarSection) {
  activeSidebarSection.value = section

  if (section === 'chats') {
    void loadConversations()
  } else if (section === 'database') {
    void router.push('/database')
  }
}

function handleSidebarToggle() {
  hasUserToggledSidebar.value = true
  isSidebarCollapsed.value = !isSidebarCollapsed.value
}

async function initializeConversation() {
  const conversationId = route.params.conversationId as string

  if (conversationId) {
    isLoading.value = true
    try {
      await chatStore.connectToConversation(conversationId)
      notification.success('连接成功', '', 1500, true)
      await nextTick()
      setTimeout(() => scrollToBottom(true), 200)
    } catch (error) {
      console.error('[ChatView] Error connecting to conversation:', error)
      notification.error('连接失败', '无法连接到对话，请稍后再试。')
    } finally {
      isLoading.value = false
    }
  } else {
    await handleNewConversation()
  }
}

function setupViewportWatcher() {
  if (typeof window === 'undefined') return
  const query = window.matchMedia('(min-width: 1024px)')

  const updateViewportState = (event: MediaQueryList | MediaQueryListEvent) => {
    const matches = (event as MediaQueryList).matches
    isDesktopViewport.value = matches
    if (matches) {
      contextPanelSheet.value = false
    } else {
      contextPanelOpen.value = false
    }
    applyResponsiveLayout(window.innerWidth)
  }

  updateViewportState(query)

  const listener = (event: MediaQueryListEvent) => updateViewportState(event)

  if (typeof query.addEventListener === 'function') {
    query.addEventListener('change', listener)
    mediaQueryCleanup = () => query.removeEventListener('change', listener)
  } else {
    query.addListener(listener)
    mediaQueryCleanup = () => query.removeListener(listener)
  }

  const handleResize = () => applyResponsiveLayout(window.innerWidth)
  window.addEventListener('resize', handleResize)
  resizeCleanup = () => window.removeEventListener('resize', handleResize)
}

onMounted(async () => {
  setupViewportWatcher()
  if (typeof window !== 'undefined') {
    applyResponsiveLayout(window.innerWidth)
  }
  await loadConversations()
  await initializeConversation()
  await nextTick()
  scrollToBottom(true)
})

onUnmounted(() => {
  chatStore.clearConversation()
  if (mediaQueryCleanup) {
    mediaQueryCleanup()
    mediaQueryCleanup = null
  }
  if (resizeCleanup) {
    resizeCleanup()
    resizeCleanup = null
  }
  const container = messageContainer.value
  if (container) {
    container.removeEventListener('scroll', handleScroll)
  }
})
</script>
