<template>
  <div class="chat-view">
    <!-- App Sidebar -->
    <AppSidebar
      :is-collapsed="isSidebarCollapsed"
      :active-tab="activeSidebarTab"
      :conversations="conversations"
      :active-conversation-id="currentConversationId"
      :deleting-ids="deletingConversationIds"
      :has-more="hasMoreConversations"
      :is-loading-more="isLoadingMore"
      :is-searching="isSearching"
      :total-conversations="totalConversations"
      @toggle-collapse="handleSidebarToggle"
      @change-tab="handleTabChange"
      @new-conversation="handleNewConversation"
      @select-conversation="handleSelectConversation"
      @delete-conversation="handleDeleteConversation"
      @load-more="handleLoadMoreConversations"
      @search="handleSearchConversations"
      @clear-search="handleClearSearch"
    />

    <!-- Main Chat Area -->
    <main class="chat-main">
      <!-- Chat Header -->
      <header class="chat-header">
        <div class="header-left">
          <button
            v-if="isSidebarCollapsed"
            @click="handleSidebarToggle"
            class="sidebar-toggle-btn"
            aria-label="展开侧边栏"
          >
            <svg class="icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>

          <div class="conversation-info">
            <p class="conversation-title">{{ conversationTitle }}</p>
            <div class="conversation-meta">
              <span class="connection-status" :class="{ 'is-connected': isConnected }">
                <span class="status-dot"></span>
                {{ isConnected ? '已连接' : '已断开' }}
              </span>
              <span v-if="lastUpdatedText">{{ lastUpdatedText }}</span>
            </div>
          </div>
        </div>

        <div class="header-right">
          <button
            type="button"
            class="header-btn"
            @click="scrollToBottom(true)"
          >
            <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M12 5v14m0 0l-5-5m5 5l5-5" />
            </svg>
            <span>最新</span>
          </button>

          <button
            type="button"
            class="header-btn"
            @click="handleContextPanelToggle"
          >
            <span>不确定性</span>
            <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M5 12h14M12 5l7 7-7 7" />
            </svg>
          </button>
        </div>
      </header>

      <!-- Messages Area -->
      <section ref="messageContainer" class="messages-container">
        <div class="messages-wrapper">
          <template v-if="timelineMessages.length">
            <MessageItem
              v-for="item in timelineMessages"
              :key="item.message.id"
              :message="item.message"
              :group-behavior="item.groupBehavior"
            />

            <!-- 真实成本分析 (显示在消息底部) -->
            <RealTokenCostCard
              v-if="!isTyping && currentConversationId"
              :conversation-id="currentConversationId"
              :show-details="true"
            />
          </template>

          <div v-else class="empty-state">
            <div class="empty-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V7a2 2 0 012-2h14a2 2 0 012 2v7a2 2 0 01-2 2h-5l-5 5v-4z" />
              </svg>
            </div>
            <div class="empty-content">
              <h3>开始新的对话</h3>
              <p>在下方输入框中输入消息开始聊天</p>
            </div>
            <button
              type="button"
              class="new-conversation-btn"
              @click="handleNewConversation"
            >
              <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M12 5v14m7-7H5" />
              </svg>
              新建会话
            </button>
          </div>
        </div>

        <button
          v-if="showScrollToLatest"
          type="button"
          class="scroll-to-latest-btn"
          @click="scrollToBottom(true)"
        >
          <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 5v14m0 0l-5-5m5 5l5-5" />
          </svg>
          回到最新
        </button>
      </section>

      <!-- Chat Input -->
      <!-- 不再根据心跳状态禁用输入框，心跳只用于 UI 显示 -->
      <footer class="chat-footer" :class="{ 'sidebar-collapsed': isSidebarCollapsed }">
        <div class="input-wrapper">
          <ChatInput
            :disabled="false"
            :is-sending="chatStore.isTyping"
            @send="handleSendMessage"
            @stop="handleStopGeneration"
            @database-change="handleDatabaseChange"
          />
        </div>
      </footer>
    </main>

    <!-- Uncertainty Sidebar (Desktop) -->
    <UncertaintySidebar
      v-if="contextPanelOpen && isDesktopViewport"
      class="context-panel"
      :connection-name="currentDatabaseName"
      @close="handleContextPanelClose"
    />

    <!-- User Input Dialog -->
    <UserInputDialog
      :question="pendingUserInputQuestion"
      @submit="handleUserInputSubmit"
      @cancel="handleUserInputCancel"
    />

    <!-- Uncertainty Sidebar (Mobile Sheet) -->
    <div
      v-if="contextPanelSheet && !isDesktopViewport"
      class="mobile-overlay"
      @click="handleContextPanelClose"
    >
      <div class="mobile-sheet" @click.stop>
        <UncertaintySidebar
          modal
          :connection-name="currentDatabaseName"
          @close="handleContextPanelClose"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppSidebar from '@/components/AppSidebar.vue'
import ChatInput from '@/components/ChatInput.vue'
import UncertaintySidebar from '@/components/UncertaintySidebar.vue'
import MessageItem from '@/components/MessageItem.vue'
import RealTokenCostCard from '@/components/RealTokenCostCard.vue'
import UserInputDialog from '@/components/UserInputDialog.vue'
import { notification } from '@/composables/useNotification'
import { useChatStore } from '@/stores/chat'
import type { ChatMessage } from '@/stores/chat'
import api, { getOrCreateDefaultProject, listProjectConversations, type Conversation } from '@/services/api'

type TabId = 'chats' | 'database' | 'billing' | 'settings'

interface TimelineMessage {
  message: ChatMessage
  groupBehavior: 'standalone' | 'compact-start' | 'compact-middle' | 'compact-end'
}

const route = useRoute()
const router = useRouter()
const chatStore = useChatStore()

const isLoading = ref(false)
const conversations = ref<Conversation[]>([])
const isSidebarCollapsed = ref(false)
const activeSidebarTab = ref<TabId>('chats')
const contextPanelOpen = ref(false)
const contextPanelSheet = ref(false)
const isDesktopViewport = ref(false)
const showScrollToLatest = ref(false)
const messageContainer = ref<HTMLElement | null>(null)
const currentProjectId = ref<string | null>(null)
const currentDatabaseName = ref<string>('')

// 分页和搜索状态
const conversationOffset = ref(0)
const conversationLimit = ref(20)
const hasMoreConversations = ref(true)
const isLoadingMore = ref(false)
const isSearching = ref(false)
const totalConversations = ref(0)
const currentSearchKeyword = ref('')
const currentSearchContent = ref(false)

const isConnected = computed(() => chatStore.isConnected)
const isTyping = computed(() => chatStore.isTyping)
const pendingUserInputQuestion = computed(() => chatStore.pendingUserInput?.userInputQuestion || null)
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

// 监听 currentConversation.title 变化，同步更新侧边栏列表
watch(
  () => chatStore.currentConversation?.title,
  (newTitle) => {
    if (newTitle && currentConversationId.value) {
      const conv = conversations.value.find(c => c.id === currentConversationId.value)
      if (conv && conv.title !== newTitle) {
        conv.title = newTitle
        console.log('[ChatView] Synced sidebar title:', newTitle)
      }
    }
  },
)

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
  if (currentRole === 'system') {
    return 'standalone'
  }

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

function handleContextPanelToggle() {
  if (isDesktopViewport.value) {
    contextPanelOpen.value = !contextPanelOpen.value
  } else {
    contextPanelSheet.value = true
  }
}

function handleContextPanelClose() {
  if (isDesktopViewport.value) {
    contextPanelOpen.value = false
  } else {
    contextPanelSheet.value = false
  }
}

function handleDatabaseChange(databaseName: string) {
  currentDatabaseName.value = databaseName
}

async function handleSendMessage(message: string, databaseName?: string) {
  // 保存当前选择的数据库名，用于问卷侧边栏
  if (databaseName) {
    currentDatabaseName.value = databaseName
  }

  try {
    await chatStore.sendMessage(message, databaseName)
    await nextTick()
    scrollToBottom(true)
  } catch (error: any) {
    console.error('Error sending message:', error)

    // 根据错误类型显示不同提示
    if (error.message?.includes('No active conversation')) {
      notification.error('未选择对话', '请先选择或创建一个对话。')
    } else if (error.message?.includes('Authentication failed')) {
      // 认证失败会自动跳转登录页，这里不需要额外处理
      notification.error('登录已过期', '正在跳转到登录页...')
    } else {
      notification.error('发送失败', '无法发送消息，请稍后重试。')
    }
  }
}

async function handleNewConversation() {
  if (isLoading.value) return

  activeSidebarTab.value = 'chats'

  isLoading.value = true
  try {
    // 确保有项目 ID
    if (!currentProjectId.value) {
      await ensureProjectId()
    }

    // 🚀 优化：创建会话后立即跳转，列表刷新异步进行
    const conversation = await chatStore.createNewConversation(currentProjectId.value!, 'New chat')

    // 乐观更新：立即添加到列表顶部
    conversations.value.unshift(conversation)
    totalConversations.value += 1

    // 立即跳转，不等待列表刷新
    await router.push(`/chat/${conversation.id}`)
    notification.success('已创建新会话', '', 2000, true)

    // 后台刷新列表（不阻塞）
    loadConversations().catch(console.error)
  } catch (error) {
    console.error('Error creating conversation:', error)
    notification.error('创建失败', '暂时无法创建新对话，请稍后再试。')
  } finally {
    isLoading.value = false
  }
}

async function handleSelectConversation(conversationId: string) {
  await router.push(`/chat/${conversationId}`)
  activeSidebarTab.value = 'chats'
}

const deletingConversationIds = ref<Set<string>>(new Set())

async function handleDeleteConversation(conversationId: string) {
  // 防止重复删除
  if (deletingConversationIds.value.has(conversationId)) {
    return
  }
  deletingConversationIds.value.add(conversationId)

  // 乐观更新：立即从列表移除
  const originalConversations = [...conversations.value]
  const originalTotal = totalConversations.value
  conversations.value = conversations.value.filter(c => c.id !== conversationId)
  totalConversations.value = Math.max(0, totalConversations.value - 1)

  // 如果删除的是当前对话，立即跳转
  if (conversationId === currentConversationId.value) {
    chatStore.clearConversation()
    router.push('/chat')
  }

  try {
    await api.delete(`/chat/conversations/${conversationId}`)
    // 删除成功，更新 offset 以保持分页正确
    conversationOffset.value = Math.max(0, conversationOffset.value - 1)
  } catch (error: any) {
    // 404 说明已被删除，无需回滚
    if (error?.response?.status === 404) {
      conversationOffset.value = Math.max(0, conversationOffset.value - 1)
      return
    }
    // 其他错误：回滚列表
    console.error('Error deleting conversation:', error)
    conversations.value = originalConversations
    totalConversations.value = originalTotal
    notification.error('删除失败', '暂时无法删除该对话。')
  } finally {
    deletingConversationIds.value.delete(conversationId)
  }
}

async function loadConversations(reset = true) {
  try {
    // 确保有项目 ID
    if (!currentProjectId.value) {
      await ensureProjectId()
    }

    if (reset) {
      conversationOffset.value = 0
      conversations.value = []
      isSearching.value = !!currentSearchKeyword.value
    }

    const response = await listProjectConversations(currentProjectId.value!, {
      limit: conversationLimit.value,
      offset: conversationOffset.value,
      search: currentSearchKeyword.value || undefined,
      search_content: currentSearchContent.value || undefined
    })

    if (reset) {
      conversations.value = response.items
    } else {
      conversations.value = [...conversations.value, ...response.items]
    }

    totalConversations.value = response.total
    hasMoreConversations.value = response.has_more
    conversationOffset.value += response.items.length
  } catch (error) {
    console.error('Error loading conversations:', error)
  } finally {
    isSearching.value = false
    isLoadingMore.value = false
  }
}

async function handleLoadMoreConversations() {
  if (isLoadingMore.value || !hasMoreConversations.value) return
  isLoadingMore.value = true
  await loadConversations(false)
}

async function handleSearchConversations(keyword: string, searchContent: boolean) {
  currentSearchKeyword.value = keyword
  currentSearchContent.value = searchContent
  isSearching.value = true
  await loadConversations(true)
}

function handleClearSearch() {
  currentSearchKeyword.value = ''
  currentSearchContent.value = false
  loadConversations(true)
}

async function ensureProjectId() {
  if (!currentProjectId.value) {
    try {
      const project = await getOrCreateDefaultProject()
      currentProjectId.value = project.id
      console.log('Loaded default project:', project.id)
    } catch (error) {
      console.error('Error loading default project:', error)
      notification.error('加载项目失败', '无法获取默认项目，请刷新页面重试。')
      throw error
    }
  }
}

function handleTabChange(tab: TabId) {
  activeSidebarTab.value = tab
}

function handleSidebarToggle() {
  isSidebarCollapsed.value = !isSidebarCollapsed.value
}

/**
 * 处理用户提交交互式问题的答案
 */
async function handleUserInputSubmit(answer: any) {
  try {
    await chatStore.submitUserResponse(answer)
  } catch (error: any) {
    console.error('[ChatView] Error submitting user response:', error)
    // notification 已经在 chatStore 中处理
  }
}

/**
 * 处理用户取消回答
 */
function handleUserInputCancel() {
  // 目前仅清除状态，不发送取消请求
  // 如果需要发送取消信号给后端，可以在这里添加
  notification.info('已取消', '您取消了回答问题', 2000)
}

/**
 * 处理停止生成
 */
async function handleStopGeneration() {
  try {
    await chatStore.cancelStreaming()
  } catch (error: any) {
    console.error('[ChatView] Error stopping generation:', error)
    // notification 已在 chatStore 中处理
  }
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
    } catch (error: any) {
      console.error('[ChatView] Error connecting to conversation:', error)
      // 如果对话不存在或无权限，跳转到聊天首页（不自动创建）
      if (error.response?.status === 403 || error.response?.status === 404) {
        notification.warning('对话不存在', '该对话已被删除或无权访问')
        await router.push('/chat')
      } else {
        notification.error('连接失败', '无法连接到对话，请稍后再试。')
      }
    } finally {
      isLoading.value = false
    }
  }
  // 移除自动创建：当没有 conversationId 时不自动创建对话
  // 用户需要手动点击"新建会话"按钮
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
}

onMounted(async () => {
  // 启动心跳连接
  chatStore.startHeartbeat()

  setupViewportWatcher()
  await ensureProjectId()
  await loadConversations()
  await initializeConversation()
  await nextTick()
  scrollToBottom(true)
})

onUnmounted(() => {
  // 停止心跳连接
  chatStore.stopHeartbeat()

  chatStore.clearConversation()
  if (mediaQueryCleanup) {
    mediaQueryCleanup()
    mediaQueryCleanup = null
  }
  const container = messageContainer.value
  if (container) {
    container.removeEventListener('scroll', handleScroll)
  }
})
</script>

<style scoped>
.chat-view {
  display: flex;
  height: 100vh;
  background: #fdf7f0;
}

.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  background: white;
}

.chat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.75rem 1.5rem;
  border-bottom: 1px solid #eadfd3;
  min-height: 64px;
  background: white;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex: 1;
  min-width: 0;
}

.sidebar-toggle-btn {
  width: 2.25rem;
  height: 2.25rem;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid #eadfd3;
  background: white;
  border-radius: 0.5rem;
  color: #8c7763;
  cursor: pointer;
  transition: all 0.2s;
}

.sidebar-toggle-btn:hover {
  background: rgba(0, 0, 0, 0.05);
  color: #322d29;
}

.sidebar-toggle-btn .icon {
  width: 1.25rem;
  height: 1.25rem;
}

.conversation-info {
  flex: 1;
  min-width: 0;
}

.conversation-title {
  font-size: 0.875rem;
  font-weight: 600;
  color: #322d29;
  margin: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.conversation-meta {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.75rem;
  color: #8c7763;
  margin-top: 0.25rem;
}

.connection-status {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
}

.status-dot {
  width: 0.5rem;
  height: 0.5rem;
  border-radius: 50%;
  background: #dc2626;
}

.connection-status.is-connected .status-dot {
  background: #10b981;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.header-btn {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.5rem 0.75rem;
  border: 1px solid #eadfd3;
  background: white;
  border-radius: 0.5rem;
  font-size: 0.75rem;
  font-weight: 500;
  color: #6d5f52;
  cursor: pointer;
  transition: all 0.2s;
}

.header-btn:hover {
  background: rgba(244, 229, 213, 0.4);
  color: #322d29;
}

.header-btn .icon {
  width: 1rem;
  height: 1rem;
}

.messages-container {
  flex: 1;
  overflow-y: auto;
  padding: 1.5rem 1rem 9rem 1rem;
  position: relative;
}

.messages-wrapper {
  max-width: 48rem;
  margin: 0 auto;
  width: 100%;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 5rem 1rem;
  text-align: center;
}

.empty-icon {
  width: 3rem;
  height: 3rem;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #2b6cb0, #3b82f6);
  color: white;
  border-radius: 0.75rem;
  margin-bottom: 1rem;
}

.empty-icon svg {
  width: 1.5rem;
  height: 1.5rem;
}

.empty-content h3 {
  font-size: 1rem;
  font-weight: 600;
  color: #322d29;
  margin: 0 0 0.5rem 0;
}

.empty-content p {
  font-size: 0.875rem;
  color: #8c7763;
  margin: 0 0 1.5rem 0;
}

.new-conversation-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1.5rem;
  background: linear-gradient(135deg, #2b6cb0, #3b82f6);
  color: white;
  border: none;
  border-radius: 0.5rem;
  font-weight: 600;
  font-size: 0.875rem;
  cursor: pointer;
  transition: transform 0.2s;
}

.new-conversation-btn:hover {
  transform: translateY(-2px);
}

.new-conversation-btn .icon {
  width: 1rem;
  height: 1rem;
}

.scroll-to-latest-btn {
  position: fixed;
  bottom: 7.5rem;
  right: 2rem;
  z-index: 30;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1rem;
  background: white;
  border: 1px solid #eadfd3;
  border-radius: 0.5rem;
  font-size: 0.75rem;
  font-weight: 500;
  color: #6d5f52;
  cursor: pointer;
  transition: all 0.2s;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.scroll-to-latest-btn:hover {
  background: rgba(244, 229, 213, 0.4);
}

.scroll-to-latest-btn .icon {
  width: 1rem;
  height: 1rem;
}

.chat-footer {
  position: fixed;
  bottom: 1rem;
  left: 280px;
  right: 0;
  padding: 0 1.5rem;
  background: transparent;
  pointer-events: none;
  z-index: 20;
  transition: left 0.3s ease;
}

.chat-footer.sidebar-collapsed {
  left: 0;
}

.input-wrapper {
  max-width: 48rem;
  margin: 0 auto;
  width: 100%;
  pointer-events: all;
}

.context-panel {
  width: 300px;
  height: 100vh;
  border-left: 1px solid #eadfd3;
  background: white;
}

.mobile-overlay {
  position: fixed;
  inset: 0;
  z-index: 40;
  display: flex;
  background: rgba(0, 0, 0, 0.3);
  backdrop-filter: blur(4px);
}

.mobile-sheet {
  margin-left: auto;
  width: 100%;
  max-width: 28rem;
  height: 100%;
}

@media (max-width: 1023px) {
  .context-panel {
    display: none;
  }

  .chat-footer {
    left: 0;
  }
}
</style>
