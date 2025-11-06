<template>
  <div class="min-h-screen bg-[#fdf7f0] text-[#322d29] antialiased">
    <!-- Top Navigation Bar -->
    <NavigationBar />

    <div class="flex min-h-screen flex-col lg:flex-row" style="height: calc(100vh - 60px);">
      <!-- Left Navigation Rail (Desktop) -->
      <div class="hidden lg:flex lg:w-16 lg:flex-col lg:items-center lg:gap-4 lg:border-r lg:border-[#eadfd3] lg:bg-[#fcf1e4] lg:py-6">
        <!-- Sidebar toggle -->
        <button
          type="button"
          class="flex h-10 w-10 items-center justify-center rounded-2xl border border-transparent text-[#b9a695] transition hover:border-[#e7d8c9] hover:bg-white/70 hover:text-[#8c7763]"
          :class="isSidebarCollapsed ? 'bg-white/80 text-[#8c7763] shadow-inner' : ''"
          aria-label="切换侧边栏"
          @click="handleSidebarToggle"
        >
          <svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
            <path stroke-linecap="round" stroke-linejoin="round" d="M4 6h16M4 12h16M4 18h16" />
          </svg>
        </button>

        <!-- Logo -->
        <div class="flex h-10 w-10 items-center justify-center rounded-2xl bg-white/80 text-[#d78b5b] shadow-inner">
          <svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 3l2.09 6.26H20l-5.05 3.67L16.18 19 12 15.77 7.82 19l1.23-6.07L4 9.26h5.91z" />
          </svg>
        </div>

        <!-- New conversation -->
        <button
          type="button"
          class="rounded-full p-2 text-[#b9a695] transition hover:bg-white/60 hover:text-[#8c7763]"
          aria-label="新建会话"
          @click="handleNewConversation"
        >
          <svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 5v14m7-7H5" />
          </svg>
        </button>

        <!-- Navigation sections -->
        <div class="mt-2 flex flex-1 flex-col items-center gap-4 text-[#b9a695]">
          <button
            v-for="section in sidebarSections"
            :key="section.id"
            type="button"
            class="rounded-full p-2 transition hover:bg-white/60 hover:text-[#8c7763]"
            :class="activeSidebarSection === section.id
              ? (isSidebarCollapsed ? 'bg-white/40 text-[#a67d62]' : 'bg-white/80 text-[#8c7763] shadow-inner')
              : ''"
            :aria-label="section.label"
            @click="handleSidebarSectionSelect(section.id)"
          >
            <svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7">
              <path stroke-linecap="round" stroke-linejoin="round" :d="section.icon" />
            </svg>
          </button>
        </div>
      </div>

      <!-- Conversation Sidebar (Desktop) -->
      <div
        v-show="!isSidebarCollapsed"
        class="hidden lg:flex lg:w-80 lg:flex-none lg:border-r lg:border-[#eadfd3] lg:bg-[#fefaf4]"
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
      </div>

      <!-- Main Content Area -->
      <main class="flex w-full flex-1 flex-col">
        <slot />
      </main>

      <!-- Mobile Sidebar Overlay -->
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
            :active-section="activeSidebarSection"
            @new-conversation="handleNewConversation"
            @select-conversation="handleSelectConversation"
            @delete-conversation="handleDeleteConversation"
            @navigate="handleSidebarSectionSelect"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, provide, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import NavigationBar from '@/components/NavigationBar.vue'
import ConversationSidebar from '@/components/ConversationSidebar.vue'
import { useChatStore } from '@/stores/chat'
import { notification } from '@/composables/useNotification'
import { DEFAULT_PROJECT_ID } from '@/config/constants'
import api from '@/services/api'

type SidebarSection = 'chats' | 'projects' | 'database' | 'documents'

const router = useRouter()
const route = useRoute()
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

const sidebarOpen = ref(false)
const isSidebarCollapsed = ref(false)
const conversations = ref<any[]>([])
const navBusy = ref(false)
const activeSidebarSection = ref<SidebarSection>('chats')

const isConnected = computed(() => chatStore.isConnected)
const currentConversationId = computed(() => route.params.conversationId as string | undefined)

// Provide sidebar control to child components
provide('openSidebar', () => {
  sidebarOpen.value = true
})

// 根据路由自动设置当前激活的侧边栏区域
watch(
  () => route.name,
  (name) => {
    if (name === 'database') {
      activeSidebarSection.value = 'database'
    } else if (name === 'chat' || name === 'chat-conversation') {
      activeSidebarSection.value = 'chats'
    }
  },
  { immediate: true },
)

watch(sidebarOpen, (open) => {
  if (open) {
    isSidebarCollapsed.value = false
  }
})

onMounted(async () => {
  await loadConversations()
})

async function loadConversations() {
  try {
    const response = await api.get(`/chat/projects/${DEFAULT_PROJECT_ID}/conversations`)
    conversations.value = response.data
  } catch (error) {
    console.error('加载会话列表失败:', error)
  }
}

async function handleNewConversation() {
  if (navBusy.value) return

  activeSidebarSection.value = 'chats'
  isSidebarCollapsed.value = false

  navBusy.value = true
  try {
    const conversation = await chatStore.createNewConversation(DEFAULT_PROJECT_ID, '新对话')
    await loadConversations()
    await router.push(`/chat/${conversation.id}`)
    notification.success('已创建对话', '', 2000, true)
  } catch (error) {
    console.error('创建会话失败:', error)
    notification.error('创建失败', '无法创建新对话，请稍后再试')
  } finally {
    navBusy.value = false
    sidebarOpen.value = false
  }
}

async function handleSelectConversation(conversationId: string) {
  await router.push(`/chat/${conversationId}`)
  activeSidebarSection.value = 'chats'
  isSidebarCollapsed.value = false
  sidebarOpen.value = false
}

async function handleDeleteConversation(conversationId: string) {
  try {
    await api.delete(`/chat/conversations/${conversationId}`)
    await loadConversations()
    notification.success('会话已删除', '', 2000, true)
    if (conversationId === currentConversationId.value) {
      await handleNewConversation()
    }
  } catch (error) {
    console.error('删除会话失败:', error)
    notification.error('删除失败', '无法删除会话')
  }
}

function handleSidebarSectionSelect(section: SidebarSection) {
  activeSidebarSection.value = section

  if (section === 'chats') {
    const targetConversation = currentConversationId.value
      ? `/chat/${currentConversationId.value}`
      : '/chat'
    void loadConversations()
    void router.push(targetConversation)
    isSidebarCollapsed.value = false
    sidebarOpen.value = false
    return
  }

  if (section === 'database') {
    void router.push('/database')
    sidebarOpen.value = false
    return
  }

  // Other sections: 保持侧边栏打开
  isSidebarCollapsed.value = false
  sidebarOpen.value = false
}

function handleSidebarToggle() {
  isSidebarCollapsed.value = !isSidebarCollapsed.value
}
</script>