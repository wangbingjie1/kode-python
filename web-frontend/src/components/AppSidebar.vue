<template>
  <aside class="app-sidebar" :class="{ 'is-collapsed': isCollapsed }">
    <!-- Header: Logo + User Menu -->
    <header class="sidebar-header">
      <button
        class="collapse-btn"
        @click="$emit('toggle-collapse')"
        :aria-label="isCollapsed ? '展开侧边栏' : '折叠侧边栏'"
      >
        <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M4 6h16M4 12h16M4 18h16" />
        </svg>
      </button>

      <div v-if="!isCollapsed" class="logo">
        <span class="logo-text">Kode AI</span>
      </div>

      <div v-if="!isCollapsed" class="user-menu">
        <div class="user-trigger" @click="toggleUserMenu">
          <div class="user-avatar">
            {{ userInitial }}
          </div>
          <svg class="dropdown-icon" :class="{ 'is-open': isUserMenuOpen }" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7" />
          </svg>
        </div>

        <div v-if="isUserMenuOpen" class="user-dropdown">
          <div class="dropdown-item user-info">
            <div class="user-name">{{ authStore.currentUser?.username }}</div>
            <div class="user-email">{{ authStore.currentUser?.email }}</div>
          </div>
          <div class="dropdown-divider"></div>
          <router-link to="/profile" class="dropdown-item" @click="isUserMenuOpen = false">
            <svg class="item-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
            </svg>
            {{ $t('nav.profile') }}
          </router-link>
          <div class="dropdown-divider"></div>
          <button class="dropdown-item logout-btn" @click="handleLogout">
            <svg class="item-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
            </svg>
            {{ $t('nav.logout') }}
          </button>
        </div>
      </div>
    </header>

    <template v-if="!isCollapsed">
      <!-- New Chat Button -->
      <div class="new-chat-section">
        <button class="new-chat-btn" @click="$emit('new-conversation')">
          <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 5v14m7-7H5" />
          </svg>
          <span>新建对话</span>
        </button>
      </div>

      <!-- Tab Navigation -->
      <nav class="sidebar-nav">
        <button
          v-for="tab in tabs"
          :key="tab.id"
          class="nav-tab"
          :class="{ 'is-active': activeTab === tab.id }"
          @click="$emit('change-tab', tab.id)"
        >
          <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
            <path stroke-linecap="round" stroke-linejoin="round" :d="tab.icon" />
          </svg>
          <span>{{ tab.label }}</span>
        </button>
      </nav>

      <!-- Content Area -->
      <div class="sidebar-content">
        <!-- Chats Tab -->
        <div v-if="activeTab === 'chats'" class="content-section">
          <!-- 搜索框 -->
          <div class="search-box">
            <svg class="search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            <input
              v-model="searchKeyword"
              type="text"
              class="search-input"
              placeholder="搜索对话..."
              @input="handleSearch"
              @keydown.enter="handleSearch"
            />
            <button
              v-if="searchKeyword"
              class="clear-search-btn"
              @click="clearSearch"
            >
              <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          <!-- 搜索选项 -->
          <div v-if="searchKeyword" class="search-options">
            <label class="search-option">
              <input
                type="checkbox"
                v-model="searchContent"
                @change="toggleSearchContent"
              />
              <span>搜索消息内容</span>
            </label>
          </div>

          <div class="section-header">
            <h3 class="section-title">{{ searchKeyword ? '搜索结果' : '最近对话' }}</h3>
            <span v-if="totalConversations !== undefined" class="total-count">
              {{ totalConversations }} 个对话
            </span>
          </div>

          <!-- 搜索中提示 -->
          <div v-if="isSearching" class="loading-state">
            <svg class="loading-icon spinning" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
            </svg>
            <span>搜索中...</span>
          </div>

          <div
            v-else-if="conversations.length"
            ref="conversationsListRef"
            class="conversations-list"
            @scroll="handleScroll"
          >
            <div
              v-for="conv in conversations"
              :key="conv.id"
              class="conversation-item"
              :class="{ 'is-active': conv.id === activeConversationId }"
              @click="$emit('select-conversation', conv.id)"
            >
              <svg class="conv-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6">
                <path stroke-linecap="round" stroke-linejoin="round" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V7a2 2 0 012-2h14a2 2 0 012 2v7a2 2 0 01-2 2h-5l-5 5v-4z" />
              </svg>
              <div class="conv-info">
                <div class="conv-title">{{ conv.title }}</div>
                <div v-if="conv.matched_message" class="conv-match">
                  <svg class="match-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M7 8h10M7 12h4m1 8l-4-4H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-3l-4 4z" />
                  </svg>
                  <span>{{ conv.matched_message }}</span>
                </div>
                <div v-else class="conv-time">{{ formatTime(conv.created_at) }}</div>
              </div>
              <button
                class="delete-btn"
                :disabled="deletingIds?.has(conv.id)"
                @click.stop="$emit('delete-conversation', conv.id)"
              >
                <svg v-if="!deletingIds?.has(conv.id)" class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M19 7l-1 12a2 2 0 01-2 2H8a2 2 0 01-2-2L5 7m4 4v6m4-6v6M9 7V5a1 1 0 011-1h4a1 1 0 011 1v2m-9 0h12" />
                </svg>
                <svg v-else class="icon spinning" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
              </button>
            </div>

            <!-- 加载更多指示器 -->
            <div v-if="isLoadingMore" class="load-more-indicator">
              <svg class="loading-icon spinning" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
              <span>加载更多...</span>
            </div>

            <!-- 没有更多数据 -->
            <div v-else-if="!hasMore && conversations.length > 0" class="no-more-indicator">
              <span>没有更多对话了</span>
            </div>
          </div>

          <div v-else class="empty-state">
            <svg class="empty-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6">
              <path stroke-linecap="round" stroke-linejoin="round" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.86 9.86 0 01-4.26-.95L3 20l1.4-3.72A6.96 6.96 0 013 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
            </svg>
            <p>{{ searchKeyword ? '未找到匹配的对话' : '暂无对话' }}</p>
          </div>
        </div>

        <!-- Database Tab -->
        <div v-else-if="activeTab === 'database'" class="content-section">
          <h3 class="section-title">数据库连接</h3>
          <div v-if="databaseConnections.length" class="database-list">
            <div
              v-for="db in databaseConnections"
              :key="db.name"
              class="database-item"
              @click="openDatabase(db)"
            >
              <div class="db-icon">{{ getDatabaseIcon(db.db_type) }}</div>
              <div class="db-info">
                <div class="db-name">{{ db.name }}</div>
                <div class="db-meta">{{ db.db_type }} · {{ db.database }}</div>
              </div>
            </div>
          </div>
          <div v-else class="empty-state">
            <svg class="empty-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6">
              <path stroke-linecap="round" stroke-linejoin="round" d="M4 6c0-1.657 3.582-3 8-3s8 1.343 8 3M4 12c0 1.657 3.582 3 8 3s8-1.343 8-3M4 18c0 1.657 3.582 3 8 3s8-1.343 8-3M4 6v12c0 1.657 3.582 3 8 3s8-1.343 8-3V6" />
            </svg>
            <p>暂无数据库连接</p>
          </div>
          <router-link to="/database" class="manage-db-btn" @click="$emit('close-mobile')">
            <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
            <span>管理数据库</span>
          </router-link>
        </div>

        <!-- Billing Tab -->
        <div v-else-if="activeTab === 'billing'" class="content-section">
          <h3 class="section-title">订阅计划</h3>
          <div class="billing-info">
            <div class="plan-card">
              <div class="plan-name">{{ currentPlan?.display_name || '免费计划' }}</div>
              <div class="plan-price" v-if="currentPlan">
                ${{ currentPlan.price }}/{{ currentPlan.billing_period === 'monthly' ? '月' : '年' }}
              </div>
              <router-link to="/billing" class="upgrade-btn" @click="$emit('close-mobile')">
                <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M13 7l5 5m0 0l-5 5m5-5H6" />
                </svg>
                查看套餐
              </router-link>
            </div>
          </div>
        </div>

        <!-- Settings Tab -->
        <div v-else-if="activeTab === 'settings'" class="content-section">
          <h3 class="section-title">设置</h3>
          <div class="settings-list">
            <div class="setting-item">
              <div class="setting-label">
                <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M3 5h12M9 3v2m1.048 9.5A18.022 18.022 0 016.412 9m6.088 9h7M11 21l5-10 5 10M12.751 5C11.783 10.77 8.07 15.61 3 18.129" />
                </svg>
                <span>语言</span>
              </div>
              <LanguageSwitcher />
            </div>
          </div>
        </div>
      </div>

    </template>
  </aside>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '@/stores/auth'
import { useBillingStore } from '@/stores/billing'
import { notification } from '@/composables/useNotification'
import LanguageSwitcher from './LanguageSwitcher.vue'
import { listDatabaseConnections, type DatabaseConnection, type Conversation } from '@/services/api'

type TabId = 'chats' | 'database' | 'billing' | 'settings'

const props = defineProps<{
  isCollapsed: boolean
  activeTab: TabId
  conversations: Conversation[]
  activeConversationId?: string
  deletingIds?: Set<string>
  // 分页相关
  hasMore?: boolean
  isLoadingMore?: boolean
  isSearching?: boolean
  totalConversations?: number
}>()

const emit = defineEmits<{
  'toggle-collapse': []
  'change-tab': [id: TabId]
  'new-conversation': []
  'select-conversation': [id: string]
  'delete-conversation': [id: string]
  'close-mobile': []
  'load-more': []
  'search': [keyword: string, searchContent: boolean]
  'clear-search': []
}>()

const router = useRouter()
const { t } = useI18n()
const authStore = useAuthStore()
const billingStore = useBillingStore()

const isUserMenuOpen = ref(false)
const databaseConnections = ref<DatabaseConnection[]>([])
const searchKeyword = ref('')
const searchContent = ref(false)  // 是否搜索消息内容
const conversationsListRef = ref<HTMLElement | null>(null)
let searchDebounceTimer: ReturnType<typeof setTimeout> | null = null

const tabs = [
  {
    id: 'chats' as TabId,
    label: '对话',
    icon: 'M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V7a2 2 0 012-2h14a2 2 0 012 2v7a2 2 0 01-2 2h-5l-5 5v-4z'
  },
  {
    id: 'database' as TabId,
    label: '数据库本体',
    icon: 'M4 6c0-1.657 3.582-3 8-3s8 1.343 8 3M4 12c0 1.657 3.582 3 8 3s8-1.343 8-3M4 18c0 1.657 3.582 3 8 3s8-1.343 8-3M4 6v12c0 1.657 3.582 3 8 3s8-1.343 8-3V6'
  },
  {
    id: 'billing' as TabId,
    label: '订阅',
    icon: 'M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z'
  },
  {
    id: 'settings' as TabId,
    label: '设置',
    icon: 'M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z M15 12a3 3 0 11-6 0 3 3 0 016 0z'
  }
]

const userInitial = computed(() => {
  const username = authStore.currentUser?.username || 'U'
  return username.charAt(0).toUpperCase()
})

const currentPlan = computed(() => billingStore.currentPlan)

function toggleUserMenu() {
  isUserMenuOpen.value = !isUserMenuOpen.value
}

function handleSearch() {
  // 搜索时防抖处理
  if (searchDebounceTimer) {
    clearTimeout(searchDebounceTimer)
  }
  searchDebounceTimer = setTimeout(() => {
    emit('search', searchKeyword.value.trim(), searchContent.value)
  }, 300)
}

function toggleSearchContent() {
  // v-model 已经更新了 searchContent，不需要手动反转
  if (searchKeyword.value.trim()) {
    emit('search', searchKeyword.value.trim(), searchContent.value)
  }
}

function clearSearch() {
  searchKeyword.value = ''
  searchContent.value = false
  emit('clear-search')
}

// 无限滚动：监测滚动到底部
function handleScroll(e: Event) {
  const target = e.target as HTMLElement
  if (!target) return

  const { scrollTop, scrollHeight, clientHeight } = target
  // 距离底部 100px 时触发加载
  if (scrollHeight - scrollTop - clientHeight < 100) {
    if (props.hasMore && !props.isLoadingMore && !props.isSearching) {
      emit('load-more')
    }
  }
}

async function handleLogout() {
  authStore.logout()
  notification.success(t('auth.logoutSuccess'), t('auth.logoutSuccessMsg'))
  router.push('/login')
}

function formatTime(dateString: string): string {
  const date = new Date(dateString)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMinutes = Math.floor(diffMs / (1000 * 60))
  const diffHours = Math.floor(diffMinutes / 60)
  const diffDays = Math.floor(diffHours / 24)

  if (diffDays === 0) {
    if (diffHours === 0) {
      return diffMinutes <= 1 ? '刚刚' : `${diffMinutes}分钟前`
    }
    return `${diffHours}小时前`
  }
  if (diffDays === 1) return '昨天'
  if (diffDays < 7) return `${diffDays}天前`
  return date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
}

function getDatabaseIcon(dbType: string): string {
  const icons: Record<string, string> = {
    postgresql: '🐘',
    mysql: '🐬',
    sqlite: '📁',
    sqlserver: '🔷',
    oracle: '🔴'
  }
  return icons[dbType] || '💾'
}

function openDatabase(db: DatabaseConnection) {
  router.push('/database')
}

async function loadDatabaseConnections() {
  try {
    databaseConnections.value = await listDatabaseConnections()
  } catch (error) {
    console.error('Failed to load database connections:', error)
  }
}

onMounted(() => {
  loadDatabaseConnections()
  billingStore.fetchSubscription()
})

// Close menu when clicking outside
if (typeof document !== 'undefined') {
  document.addEventListener('click', (e) => {
    const target = e.target as HTMLElement
    if (!target.closest('.user-menu')) {
      isUserMenuOpen.value = false
    }
  })
}
</script>

<style scoped>
.app-sidebar {
  width: 280px;
  height: 100vh;
  background: linear-gradient(to bottom, #fefaf7, #fdf7f0);
  border-right: 1px solid #eadfd3;
  display: flex;
  flex-direction: column;
  transition: width 0.3s ease;
  position: relative;
}

.app-sidebar.is-collapsed {
  width: 0;
  overflow: hidden;
}

/* Header */
.sidebar-header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.5rem 1rem;
  border-bottom: 1px solid #eadfd3;
  min-height: 48px;
}

.collapse-btn {
  flex-shrink: 0;
  width: 2rem;
  height: 2rem;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  background: none;
  color: #8c7763;
  cursor: pointer;
  border-radius: 0.5rem;
  transition: all 0.2s;
}

.collapse-btn:hover {
  background: rgba(0, 0, 0, 0.05);
  color: #322d29;
}

.logo {
  flex: 1;
}

.logo-text {
  font-size: 1.25rem;
  font-weight: 700;
  background: linear-gradient(135deg, #2b6cb0, #3b82f6);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.user-menu {
  position: relative;
}

.user-trigger {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.25rem 0.5rem;
  border-radius: 9999px;
  cursor: pointer;
  transition: background 0.2s;
}

.user-trigger:hover {
  background: rgba(0, 0, 0, 0.05);
}

.user-avatar {
  width: 2rem;
  height: 2rem;
  border-radius: 50%;
  background: linear-gradient(135deg, #667eea, #764ba2);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  font-size: 0.875rem;
}

.dropdown-icon {
  width: 1rem;
  height: 1rem;
  color: #8c7763;
  transition: transform 0.2s;
}

.dropdown-icon.is-open {
  transform: rotate(180deg);
}

.user-dropdown {
  position: absolute;
  top: calc(100% + 0.5rem);
  right: 0;
  min-width: 220px;
  background: white;
  border-radius: 12px;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.15);
  border: 1px solid #eadfd3;
  overflow: hidden;
  z-index: 1000;
  animation: slideDown 0.2s ease;
}

@keyframes slideDown {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.dropdown-item {
  padding: 0.75rem 1rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  width: 100%;
  border: none;
  background: none;
  cursor: pointer;
  transition: background 0.2s;
  font-size: 0.875rem;
  color: #322d29;
  text-decoration: none;
  text-align: left;
}

.dropdown-item:hover {
  background: rgba(244, 229, 213, 0.4);
}

.dropdown-item.user-info {
  cursor: default;
  flex-direction: column;
  align-items: flex-start;
  gap: 0.25rem;
}

.dropdown-item.user-info:hover {
  background: none;
}

.user-name {
  font-weight: 600;
  color: #322d29;
}

.user-email {
  font-size: 0.75rem;
  color: #8c7763;
}

.dropdown-divider {
  height: 1px;
  background: #eadfd3;
}

.logout-btn {
  color: #dc2626;
  font-weight: 500;
}

.logout-btn:hover {
  background: rgba(220, 38, 38, 0.1);
}

.item-icon {
  width: 1.125rem;
  height: 1.125rem;
}

/* New Chat Button */
.new-chat-section {
  padding: 1rem;
  border-bottom: 1px solid #eadfd3;
}

.new-chat-btn {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  padding: 0.75rem;
  background: linear-gradient(135deg, #f26b3a, #e0582a);
  color: white;
  border: none;
  border-radius: 0.75rem;
  font-weight: 600;
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
  box-shadow: 0 4px 12px rgba(242, 107, 58, 0.3);
}

.new-chat-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(242, 107, 58, 0.4);
}

.new-chat-btn .icon {
  width: 1.25rem;
  height: 1.25rem;
}

/* Navigation Tabs */
.sidebar-nav {
  padding: 0.5rem;
  border-bottom: 1px solid #eadfd3;
}

.nav-tab {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem;
  border: none;
  background: none;
  color: #6d5f52;
  border-radius: 0.75rem;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  text-align: left;
}

.nav-tab:hover {
  background: rgba(255, 255, 255, 0.7);
  color: #322d29;
}

.nav-tab.is-active {
  background: white;
  color: #322d29;
  font-weight: 600;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.nav-tab .icon {
  width: 1.25rem;
  height: 1.25rem;
  color: #c58d63;
}

/* Content Area */
.sidebar-content {
  flex: 1;
  overflow-y: auto;
  padding: 1rem;
}

.content-section {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

/* Search Box */
.search-box {
  position: relative;
  display: flex;
  align-items: center;
  margin-bottom: 0.75rem;
}

.search-icon {
  position: absolute;
  left: 0.75rem;
  width: 1rem;
  height: 1rem;
  color: #8c7763;
  pointer-events: none;
}

.search-input {
  width: 100%;
  padding: 0.625rem 2rem 0.625rem 2.25rem;
  border: 1px solid #eadfd3;
  border-radius: 0.5rem;
  background: white;
  font-size: 0.875rem;
  color: #322d29;
  transition: border-color 0.2s, box-shadow 0.2s;
}

.search-input::placeholder {
  color: #b49f8d;
}

.search-input:focus {
  outline: none;
  border-color: #c58d63;
  box-shadow: 0 0 0 3px rgba(197, 141, 99, 0.1);
}

.clear-search-btn {
  position: absolute;
  right: 0.5rem;
  width: 1.25rem;
  height: 1.25rem;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  background: none;
  color: #8c7763;
  cursor: pointer;
  border-radius: 0.25rem;
  transition: color 0.2s;
}

.clear-search-btn:hover {
  color: #322d29;
}

.clear-search-btn .icon {
  width: 0.875rem;
  height: 0.875rem;
}

/* Section Header */
.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
}

.section-title {
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: #b49f8d;
  margin: 0;
}

.total-count {
  font-size: 0.75rem;
  color: #8c7763;
}

/* Search Options */
.search-options {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}

.search-option {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  font-size: 0.75rem;
  color: #6d5f52;
  cursor: pointer;
}

.search-option input[type="checkbox"] {
  width: 0.875rem;
  height: 0.875rem;
  accent-color: #c58d63;
  cursor: pointer;
}

/* Loading State */
.loading-state {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  padding: 2rem 1rem;
  color: #8c7763;
  font-size: 0.875rem;
}

.loading-icon {
  width: 1.25rem;
  height: 1.25rem;
}

/* Conversations List */
.conversations-list {
  display: flex;
  max-height: calc(100vh - 380px);
  overflow-y: auto;
  flex-direction: column;
  gap: 0.5rem;
}

.conversation-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem;
  border-radius: 0.75rem;
  background: white;
  cursor: pointer;
  transition: all 0.2s;
  position: relative;
}

.conversation-item:hover {
  background: rgba(255, 255, 255, 0.9);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.conversation-item.is-active {
  background: linear-gradient(135deg, rgba(242, 107, 58, 0.1), rgba(224, 88, 42, 0.1));
  box-shadow: 0 2px 12px rgba(242, 107, 58, 0.2);
}

.conv-icon {
  width: 1.25rem;
  height: 1.25rem;
  color: #c58d63;
  flex-shrink: 0;
}

.conv-info {
  flex: 1;
  min-width: 0;
}

.conv-title {
  font-size: 0.875rem;
  font-weight: 600;
  color: #322d29;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.conv-time {
  font-size: 0.75rem;
  color: #8c7763;
  margin-top: 0.25rem;
}

.conv-match {
  display: flex;
  align-items: flex-start;
  gap: 0.25rem;
  margin-top: 0.25rem;
  font-size: 0.75rem;
  color: #6d5f52;
  line-height: 1.4;
}

.conv-match .match-icon {
  width: 0.875rem;
  height: 0.875rem;
  flex-shrink: 0;
  color: #c58d63;
  margin-top: 0.1rem;
}

.conv-match span {
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.delete-btn {
  width: 1.5rem;
  height: 1.5rem;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  background: none;
  color: #b6a393;
  cursor: pointer;
  border-radius: 0.375rem;
  opacity: 0;
  transition: all 0.2s;
}

.conversation-item:hover .delete-btn {
  opacity: 1;
}

.delete-btn:hover {
  background: rgba(220, 38, 38, 0.1);
  color: #dc2626;
}

.delete-btn .icon {
  width: 1rem;
  height: 1rem;
}

.delete-btn:disabled {
  cursor: not-allowed;
  opacity: 1;
}

.delete-btn .icon.spinning {
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* Load More Indicator */
.load-more-indicator,
.no-more-indicator {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  padding: 0.75rem;
  font-size: 0.75rem;
  color: #8c7763;
}

.load-more-indicator .loading-icon {
  width: 1rem;
  height: 1rem;
}

.no-more-indicator {
  color: #b49f8d;
  font-style: italic;
}

/* Database List */
.database-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.database-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem;
  border-radius: 0.75rem;
  background: white;
  cursor: pointer;
  transition: all 0.2s;
}

.database-item:hover {
  background: rgba(255, 255, 255, 0.9);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.db-icon {
  font-size: 1.25rem;
  flex-shrink: 0;
}

.db-info {
  flex: 1;
  min-width: 0;
}

.db-name {
  font-size: 0.875rem;
  font-weight: 600;
  color: #322d29;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.db-meta {
  font-size: 0.75rem;
  color: #8c7763;
  margin-top: 0.25rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.manage-db-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  padding: 0.625rem;
  background: rgba(255, 255, 255, 0.7);
  color: #6d5f52;
  border: 1px solid #eadfd3;
  border-radius: 0.75rem;
  font-weight: 600;
  font-size: 0.875rem;
  cursor: pointer;
  text-decoration: none;
  transition: all 0.2s;
  margin-top: 0.5rem;
}

.manage-db-btn:hover {
  background: white;
  color: #322d29;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.manage-db-btn .icon {
  width: 1rem;
  height: 1rem;
}

/* Empty State */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 2rem 1rem;
  text-align: center;
  color: #8c7763;
}

.empty-icon {
  width: 3rem;
  height: 3rem;
  margin-bottom: 1rem;
  color: #c58d63;
}

.empty-state p {
  font-size: 0.875rem;
  margin: 0;
}

/* Billing Info */
.billing-info {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.plan-card {
  background: white;
  border: 1px solid #eadfd3;
  border-radius: 0.75rem;
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.plan-name {
  font-size: 1rem;
  font-weight: 600;
  color: #322d29;
}

.plan-price {
  font-size: 1.25rem;
  font-weight: 700;
  color: #2b6cb0;
}

.upgrade-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  padding: 0.625rem;
  background: linear-gradient(135deg, #2b6cb0, #3b82f6);
  color: white;
  border: none;
  border-radius: 0.5rem;
  font-weight: 600;
  font-size: 0.875rem;
  cursor: pointer;
  text-decoration: none;
  transition: transform 0.2s;
}

.upgrade-btn:hover {
  transform: translateY(-2px);
}

.upgrade-btn .icon {
  width: 1rem;
  height: 1rem;
}

/* Settings */
.settings-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.setting-item {
  background: white;
  border: 1px solid #eadfd3;
  border-radius: 0.75rem;
  padding: 1rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.setting-label {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  font-size: 0.875rem;
  font-weight: 500;
  color: #322d29;
}

.setting-label .icon {
  width: 1.25rem;
  height: 1.25rem;
  color: #c58d63;
}

.icon {
  flex-shrink: 0;
}
</style>
