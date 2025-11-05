<template>
  <div class="min-h-screen bg-[#fdf7f0] text-[#322d29] antialiased">
    <div class="flex min-h-screen flex-col lg:flex-row">
      <div class="hidden lg:flex lg:w-16 lg:flex-col lg:items-center lg:gap-4 lg:border-r lg:border-[#eadfd3] lg:bg-[#fcf1e4] lg:py-6">
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
        <div class="flex h-10 w-10 items-center justify-center rounded-2xl bg-white/80 text-[#d78b5b] shadow-inner">
          <svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 3l2.09 6.26H20l-5.05 3.67L16.18 19 12 15.77 7.82 19l1.23-6.07L4 9.26h5.91z" />
          </svg>
        </div>
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

      <main class="flex w-full flex-1 flex-col">
        <header class="border-b border-[#eadfd3] bg-white/70 px-5 py-5 lg:px-12">
          <div class="flex items-center justify-between gap-4">
            <div class="flex items-center gap-3">
              <button
                @click="sidebarOpen = true"
                class="flex h-11 w-11 items-center justify-center rounded-full border border-[#eadfd3] bg-white/80 text-[#8a7c6b] shadow-sm transition hover:-translate-y-0.5 hover:text-[#6f6256] hover:shadow-md focus:outline-none focus:ring-2 focus:ring-[#d8c6b4] lg:hidden"
                aria-label="打开导航"
                type="button"
              >
                <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M4 6h16M4 12h16M4 18h16" />
                </svg>
              </button>
              <div>
                <p class="text-xs font-semibold uppercase tracking-[0.32em] text-[#b9aa9a]">Workspace</p>
                <p class="mt-1 text-xl font-semibold text-[#2f2720]">数据库管理</p>
              </div>
            </div>
            <button
              v-if="currentView === 'connections'"
              @click="showConnectionForm = true"
              class="btn-primary"
              type="button"
            >
              新建连接
            </button>
          </div>
        </header>

        <div class="flex flex-1 flex-col lg:flex-row">
          <aside class="module-sidebar">
            <button
              :class="['module-btn', { active: currentView === 'connections' }]"
              @click="currentView = 'connections'"
            >
              连接管理
            </button>
            <button
              :class="['module-btn', { active: currentView === 'ontology' }]"
              @click="currentView = 'ontology'"
            >
              本体管理
            </button>
            <button
              :class="['module-btn', { active: currentView === 'query' }]"
              @click="currentView = 'query'"
            >
              查询测试
            </button>
          </aside>

          <section class="module-content">
            <div v-if="currentView === 'connections'" class="flex min-h-0 flex-1 flex-col gap-6 lg:flex-row">
              <div class="connections-panel">
                <div class="panel-header">
                  <h2>数据库连接</h2>
                  <p class="panel-subtitle">管理与切换数据源，保持工作区一致体验</p>
                </div>
                <div class="connections-scroll">
                  <div
                    v-for="connection in connections"
                    :key="connection.name"
                    :class="['connection-card', { active: selectedConnection?.name === connection.name }]"
                    @click="selectConnection(connection)"
                  >
                    <div class="connection-icon">
                      <span>{{ getDatabaseIcon(connection.db_type) }}</span>
                    </div>
                    <div class="connection-info">
                      <div class="connection-name">{{ connection.name }}</div>
                      <div class="connection-meta">
                        {{ connection.db_type }} · {{ connection.database }}
                      </div>
                    </div>
                    <button
                      @click.stop="deleteConnection(connection.name)"
                      class="btn-icon"
                      title="删除连接"
                      type="button"
                    >
                      ×
                    </button>
                  </div>
                  <div v-if="connections.length === 0" class="empty-panel">
                    <div class="empty-illustration">💡</div>
                    <p class="empty-title">暂无数据库连接</p>
                    <p class="empty-description">点击右上角“新建连接”即可开始配置</p>
                  </div>
                </div>
              </div>

              <div class="details-panel">
                <div v-if="!selectedConnection" class="empty-selection">
                  <div class="empty-illustration">📁</div>
                  <p class="empty-title">请选择一个数据库连接</p>
                  <p class="empty-description">在左侧列表中选择已有连接，或新建一个连接来开始协作</p>
                </div>

                <div v-else class="connection-details-card">
                  <div class="details-header">
                    <div>
                      <h2>{{ selectedConnection.name }}</h2>
                      <p class="details-subtitle">{{ selectedConnection.db_type }} 数据源</p>
                    </div>
                    <div class="action-buttons">
                      <button @click="editConnection" class="btn-secondary" type="button">
                        编辑
                      </button>
                      <button @click="testConnection" class="btn-secondary" :disabled="testing" type="button">
                        {{ testing ? '测试中...' : '测试连接' }}
                      </button>
                        <button @click="loadSchema" class="btn-secondary" :disabled="loadingSchema" type="button">
                        {{ loadingSchema ? '加载中...' : '加载结构' }}
                      </button>
                    </div>
                  </div>

                  <div class="info-grid">
                    <div class="info-item">
                      <span class="info-label">类型</span>
                      <span class="info-value">{{ selectedConnection.db_type }}</span>
                    </div>
                    <div class="info-item">
                      <span class="info-label">主机</span>
                      <span class="info-value">{{ selectedConnection.host }}:{{ selectedConnection.port }}</span>
                    </div>
                    <div class="info-item">
                      <span class="info-label">数据库</span>
                      <span class="info-value">{{ selectedConnection.database }}</span>
                    </div>
                    <div class="info-item">
                      <span class="info-label">用户名</span>
                      <span class="info-value">{{ selectedConnection.username }}</span>
                    </div>
                    <div class="info-item" v-if="selectedConnection.schema">
                      <span class="info-label">Schema</span>
                      <span class="info-value">{{ selectedConnection.schema }}</span>
                    </div>
                    <div class="info-item">
                      <span class="info-label">SSL</span>
                      <span class="info-value">{{ selectedConnection.ssl ? '启用' : '禁用' }}</span>
                    </div>
                  </div>

                  <div v-if="schema" class="schema-section">
                    <h3>数据库结构 ({{ schema.table_count }} 个表)</h3>
                    <div class="tables-list">
                      <div
                        v-for="table in schema.tables"
                        :key="table.name"
                        class="table-item"
                      >
                        <div class="table-header" @click="toggleTable(table.name)">
                          <span class="table-icon">📋</span>
                          <span class="table-name">{{ table.name }}</span>
                          <span class="column-count">共 {{ table.columns.length }} 列</span>
                          <span class="toggle-icon">
                            {{ expandedTables.has(table.name) ? '▼' : '▶' }}
                          </span>
                        </div>
                        <div v-if="expandedTables.has(table.name)" class="table-details">
                          <table class="columns-table">
                            <thead>
                              <tr>
                                <th>列名</th>
                                <th>类型</th>
                                <th>可空</th>
                                <th>主键</th>
                              </tr>
                            </thead>
                            <tbody>
                              <tr v-for="column in table.columns" :key="column.name">
                                <td>{{ column.name }}</td>
                                <td>{{ column.type }}</td>
                                <td>{{ column.nullable ? '是' : '否' }}</td>
                                <td>{{ table.primary_keys.includes(column.name) ? '✓' : '' }}</td>
                              </tr>
                            </tbody>
                          </table>
                          <div v-if="table.foreign_keys.length > 0" class="foreign-keys">
                            <h4>外键关系</h4>
                            <ul>
                              <li v-for="(fk, idx) in table.foreign_keys" :key="idx">
                                {{ fk.columns.join(', ') }} → {{ fk.referred_table }}({{
                                  fk.referred_columns.join(', ')
                                }})
                              </li>
                            </ul>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div v-else-if="currentView === 'ontology'" class="module-card">
              <OntologyViewer />
            </div>

            <div v-else class="module-card">
              <QueryTester :connections="connections" />
            </div>
          </section>
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
          :active-section="activeSidebarSection"
          @new-conversation="handleNewConversation"
          @select-conversation="handleSelectConversation"
          @delete-conversation="handleDeleteConversation"
          @navigate="handleSidebarSectionSelect"
        />
          </div>
        </div>
      </main>
    </div>

    <div v-if="showConnectionForm" class="modal-overlay" @click="closeConnectionForm">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h2>{{ isEditMode ? '编辑数据库连接' : '新建数据库连接' }}</h2>
          <button @click="closeConnectionForm" class="btn-icon" type="button">×</button>
        </div>
        <form @submit.prevent="saveConnection" class="connection-form">
          <div class="form-group">
            <label>连接名称*</label>
            <input v-model="formData.name" type="text" required :disabled="isEditMode" />
          </div>
          <div class="form-group">
            <label>数据库类型*</label>
            <select v-model="formData.db_type" required>
              <option value="postgresql">PostgreSQL</option>
              <option value="mysql">MySQL</option>
              <option value="sqlite">SQLite</option>
              <option value="sqlserver">SQL Server</option>
              <option value="oracle">Oracle</option>
            </select>
          </div>
          <div class="form-group" v-if="formData.db_type !== 'sqlite'">
            <label>主机*</label>
            <input v-model="formData.host" type="text" required />
          </div>
          <div class="form-group" v-if="formData.db_type !== 'sqlite'">
            <label>端口*</label>
            <input v-model.number="formData.port" type="number" required />
          </div>
          <div class="form-group">
            <label>数据库名*</label>
            <input v-model="formData.database" type="text" required />
          </div>
          <div class="form-group" v-if="formData.db_type !== 'sqlite'">
            <label>用户名*</label>
            <input v-model="formData.username" type="text" required />
          </div>
          <div class="form-group" v-if="formData.db_type !== 'sqlite'">
            <label>密码{{ isEditMode ? ' (留空保持不变)' : '*' }}</label>
            <input v-model="formData.password" type="password" :required="!isEditMode" />
          </div>
          <div class="form-group">
            <label>Schema (可选)</label>
            <input v-model="formData.db_schema" type="text" />
          </div>
          <div class="form-group" v-if="formData.db_type !== 'sqlite'">
            <label>
              <input v-model="formData.ssl" type="checkbox" />
              启用 SSL
            </label>
          </div>
          <div class="form-actions">
            <button type="button" @click="closeConnectionForm" class="btn-secondary">
              取消
            </button>
            <button type="submit" class="btn-primary" :disabled="creating">
              {{ creating ? (isEditMode ? '保存中...' : '创建中...') : (isEditMode ? '保存' : '创建') }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api, {
  listDatabaseConnections,
  createDatabaseConnection,
  updateDatabaseConnection,
  deleteDatabaseConnection,
  testDatabaseConnection,
  getDatabaseSchema,
  type DatabaseConnection,
  type CreateDatabaseConnectionRequest,
  type UpdateDatabaseConnectionRequest,
  type DatabaseSchema
} from '@/services/api'
import { notification } from '@/composables/useNotification'
import OntologyViewer from '@/components/OntologyViewer.vue'
import QueryTester from '@/components/QueryTester.vue'
import ConversationSidebar from '@/components/ConversationSidebar.vue'
import { useChatStore } from '@/stores/chat'
import { DEFAULT_PROJECT_ID } from '@/config/constants'

const router = useRouter()
const route = useRoute()
const chatStore = useChatStore()

const currentView = ref<'connections' | 'ontology' | 'query'>('connections')
const connections = ref<DatabaseConnection[]>([])
const selectedConnection = ref<DatabaseConnection | null>(null)
const showConnectionForm = ref(false)
const isEditMode = ref(false)
const editingConnectionName = ref<string | null>(null)
const testing = ref(false)
const loadingSchema = ref(false)
const creating = ref(false)
const schema = ref<DatabaseSchema | null>(null)
const expandedTables = ref<Set<string>>(new Set())

const sidebarOpen = ref(false)
const isSidebarCollapsed = ref(false)
const conversations = ref<any[]>([])
const navBusy = ref(false)

type SidebarSection = 'chats' | 'projects' | 'database' | 'documents'

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

const activeSidebarSection = ref<SidebarSection>('database')

const isConnected = computed(() => chatStore.isConnected)
const currentConversationId = computed(() => route.params.conversationId as string | undefined)

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
    activeSidebarSection.value = 'database'
    isSidebarCollapsed.value = false
  }
})

const formData = ref<CreateDatabaseConnectionRequest>({
  name: '',
  db_type: 'postgresql',
  host: 'localhost',
  port: 5432,
  database: '',
  username: '',
  password: '',
  db_schema: '',
  ssl: false
})

onMounted(async () => {
  await Promise.allSettled([loadConnections(), loadConversations()])
})

async function loadConnections() {
  try {
    connections.value = await listDatabaseConnections()
  } catch (error: any) {
    notification.error('加载失败', error.message)
  }
}

async function loadConversations() {
  try {
    const response = await api.get(`/chat/projects/${DEFAULT_PROJECT_ID}/conversations`)
    conversations.value = response.data
  } catch (error) {
    console.error('加载会话列表失败:', error)
  }
}

async function selectConnection(connection: DatabaseConnection) {
  selectedConnection.value = connection
  schema.value = null
  expandedTables.value.clear()
}

function editConnection() {
  if (!selectedConnection.value) return

  isEditMode.value = true
  editingConnectionName.value = selectedConnection.value.name
  formData.value = {
    name: selectedConnection.value.name,
    db_type: selectedConnection.value.db_type,
    host: selectedConnection.value.host,
    port: selectedConnection.value.port,
    database: selectedConnection.value.database,
    username: selectedConnection.value.username,
    password: '',
    db_schema: selectedConnection.value.schema || '',
    ssl: selectedConnection.value.ssl
  }
  showConnectionForm.value = true
}

async function saveConnection() {
  creating.value = true
  try {
    if (isEditMode.value && editingConnectionName.value) {
      const updateData: UpdateDatabaseConnectionRequest = {
        host: formData.value.host,
        port: formData.value.port,
        database: formData.value.database,
        username: formData.value.username,
        db_schema: formData.value.db_schema,
        ssl: formData.value.ssl
      }
      if (formData.value.password) {
        updateData.password = formData.value.password
      }
      await updateDatabaseConnection(editingConnectionName.value, updateData)
      notification.success('更新成功', `连接 ${editingConnectionName.value} 已更新`)
    } else {
      await createDatabaseConnection(formData.value)
      notification.success('创建成功', `连接 ${formData.value.name} 已创建`)
    }
    await loadConnections()
    closeConnectionForm()
  } catch (error: any) {
    const operation = isEditMode.value ? '更新' : '创建'
    notification.error(`${operation}失败`, error.response?.data?.detail || error.message)
  } finally {
    creating.value = false
  }
}

async function deleteConnection(name: string) {
  if (!confirm(`确定要删除连接 "${name}" 吗?`)) {
    return
  }

  try {
    await deleteDatabaseConnection(name)
    notification.success('删除成功', `连接 ${name} 已删除`)
    await loadConnections()
    if (selectedConnection.value?.name === name) {
      selectedConnection.value = null
      schema.value = null
    }
  } catch (error: any) {
    notification.error('删除失败', error.response?.data?.detail || error.message)
  }
}

async function testConnection() {
  if (!selectedConnection.value) return

  testing.value = true
  try {
    const result = await testDatabaseConnection(selectedConnection.value.name)
    if (result.status === 'success') {
      notification.success('测试成功', result.message)
    } else {
      notification.error('测试失败', result.message)
    }
  } catch (error: any) {
    notification.error('测试失败', error.response?.data?.detail || error.message)
  } finally {
    testing.value = false
  }
}

async function loadSchema() {
  if (!selectedConnection.value) return

  loadingSchema.value = true
  try {
    schema.value = await getDatabaseSchema(selectedConnection.value.name)
    notification.success('加载成功', `已加载 ${schema.value.table_count} 个表的结构`)
  } catch (error: any) {
    notification.error('加载失败', error.response?.data?.detail || error.message)
  } finally {
    loadingSchema.value = false
  }
}

function toggleTable(tableName: string) {
  if (expandedTables.value.has(tableName)) {
    expandedTables.value.delete(tableName)
  } else {
    expandedTables.value.add(tableName)
  }
}

function closeConnectionForm() {
  showConnectionForm.value = false
  isEditMode.value = false
  editingConnectionName.value = null
  formData.value = {
    name: '',
    db_type: 'postgresql',
    host: 'localhost',
    port: 5432,
    database: '',
    username: '',
    password: '',
    db_schema: '',
    ssl: false
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

  isSidebarCollapsed.value = false
  sidebarOpen.value = false
}

function handleSidebarToggle() {
  isSidebarCollapsed.value = !isSidebarCollapsed.value
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
</script>

<style scoped>
.module-sidebar {
  display: flex;
  flex-direction: row;
  gap: 0.75rem;
  padding: 1rem 1.25rem;
  background: rgba(255, 246, 236, 0.9);
  backdrop-filter: blur(18px);
  border-bottom: 1px solid #eadfd3;
  overflow-x: auto;
}

@media (min-width: 1024px) {
  .module-sidebar {
    width: 240px;
    flex-direction: column;
    align-items: stretch;
    border-bottom: none;
    border-right: 1px solid #eadfd3;
    padding: 1.75rem 1.5rem;
  }
}

.module-btn {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  padding: 0.75rem 0.95rem;
  border-radius: 1rem;
  border: 1px solid transparent;
  background: rgba(255, 255, 255, 0.6);
  color: #7b6453;
  font-weight: 600;
  font-size: 0.95rem;
  cursor: pointer;
  transition: all 0.2s ease;
  white-space: nowrap;
}

.module-btn:hover {
  background: rgba(255, 255, 255, 0.85);
  color: #c4713b;
  box-shadow: 0 10px 26px rgba(201, 167, 130, 0.2);
}

.module-btn.active {
  background: #fff4e6;
  color: #c0662b;
  border-color: #f0cfb1;
  box-shadow: 0 14px 32px rgba(207, 168, 130, 0.28);
}

.module-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  padding: 1.75rem 1.25rem 2.5rem;
  overflow-y: auto;
  background: #fefaf4;
}

@media (min-width: 1024px) {
  .module-content {
    padding: 2.5rem 3rem;
  }
}

.connections-panel {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
  width: 100%;
  max-height: 100%;
  border: 1px solid #efe2d0;
  border-radius: 28px;
  background: rgba(255, 255, 255, 0.8);
  box-shadow: 0 25px 50px rgba(197, 167, 132, 0.18);
  padding: 1.5rem;
}

@media (min-width: 1024px) {
  .connections-panel {
    width: 20rem;
  }
}

.panel-header h2 {
  margin: 0;
  font-size: 1.05rem;
  font-weight: 600;
  color: #413428;
}

.panel-subtitle {
  margin-top: 0.5rem;
  font-size: 0.78rem;
  color: #a08c78;
}

.connections-scroll {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  padding-right: 0.25rem;
}

.connection-card {
  display: flex;
  align-items: center;
  gap: 0.85rem;
  padding: 0.85rem 0.95rem;
  border-radius: 1.2rem;
  border: 1px solid transparent;
  background: rgba(255, 255, 255, 0.7);
  cursor: pointer;
  transition: all 0.22s ease;
  position: relative;
  box-shadow: 0 12px 24px rgba(205, 171, 135, 0.12);
}

.connection-card:hover {
  transform: translateY(-2px);
  background: rgba(255, 255, 255, 0.92);
  box-shadow: 0 16px 32px rgba(197, 164, 128, 0.24);
}

.connection-card.active {
  border-color: #f0caa6;
  background: #fff1e3;
  box-shadow: 0 20px 38px rgba(197, 151, 110, 0.32);
}

.connection-card .btn-icon {
  width: 1.75rem;
  height: 1.75rem;
  font-size: 1rem;
}

.connection-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 2.4rem;
  height: 2.4rem;
  border-radius: 0.9rem;
  background: rgba(255, 244, 231, 0.9);
  font-size: 1.35rem;
}

.connection-info {
  flex: 1;
  min-width: 0;
}

.connection-name {
  margin: 0;
  font-weight: 600;
  color: #3b3026;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.connection-meta {
  margin-top: 0.2rem;
  font-size: 0.78rem;
  color: #9a8674;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.empty-panel,
.empty-selection {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  gap: 0.5rem;
  color: #9f8d7c;
  background: rgba(255, 255, 255, 0.7);
  border-radius: 28px;
  border: 1px dashed #eddcc8;
  padding: 2.5rem 1.5rem;
}

.empty-illustration {
  font-size: 2rem;
}

.empty-title {
  margin: 0;
  font-size: 1rem;
  font-weight: 600;
  color: #4c3f34;
}

.empty-description {
  margin: 0;
  font-size: 0.85rem;
  color: #a89582;
}

.details-panel {
  flex: 1;
  min-height: 0;
}

.connection-details-card {
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 2rem;
  border-radius: 32px;
  border: 1px solid #efe0cc;
  background: rgba(255, 255, 255, 0.92);
  box-shadow: 0 40px 90px rgba(197, 164, 126, 0.24);
  padding: 2.25rem;
}

.details-header {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
}

.details-header h2 {
  margin: 0;
  font-size: 1.6rem;
  font-weight: 700;
  color: #2f2720;
}

.details-subtitle {
  margin: 0.35rem 0 0;
  font-size: 0.82rem;
  color: #a99585;
}

.action-buttons {
  display: flex;
  gap: 0.6rem;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 1.25rem;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.info-label {
  font-size: 0.75rem;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: #b29f8d;
}

.info-value {
  font-size: 1rem;
  font-weight: 600;
  color: #3a3027;
}

.schema-section {
  border-top: 1px solid #f0e2d4;
  padding-top: 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.schema-section h3 {
  margin: 0;
  font-size: 1rem;
  font-weight: 600;
  color: #3a2f26;
}

.tables-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.table-item {
  border: 1px solid #efe0cd;
  border-radius: 20px;
  overflow: hidden;
  background: rgba(255, 255, 255, 0.9);
  box-shadow: 0 12px 30px rgba(214, 183, 147, 0.18);
}

.table-header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.9rem 1.2rem;
  cursor: pointer;
  color: #463a2f;
  background: linear-gradient(90deg, rgba(255, 244, 231, 0.95), rgba(254, 241, 222, 0.85));
  transition: background 0.2s ease;
}

.table-header:hover {
  background: linear-gradient(90deg, rgba(255, 248, 238, 0.95), rgba(254, 245, 229, 0.85));
}

.table-icon {
  font-size: 1.1rem;
}

.table-name {
  font-weight: 600;
  flex: 1;
}

.column-count {
  font-size: 0.8rem;
  color: #a38974;
}

.toggle-icon {
  font-size: 0.9rem;
  color: #a38974;
}

.table-details {
  padding: 1.25rem;
  background: rgba(255, 255, 255, 0.96);
}

.columns-table {
  width: 100%;
  border-collapse: collapse;
  border-radius: 12px;
  overflow: hidden;
}

.columns-table th {
  text-align: left;
  font-size: 0.78rem;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: #b39e8a;
  padding: 0.6rem 0.75rem;
  border-bottom: 1px solid #f0e5d7;
}

.columns-table td {
  padding: 0.65rem 0.75rem;
  font-size: 0.88rem;
  color: #584a3f;
  border-bottom: 1px solid #f5ebde;
}

.columns-table tr:last-child td {
  border-bottom: none;
}

.foreign-keys {
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid #f0e5d7;
}

.foreign-keys h4 {
  margin: 0 0 0.5rem 0;
  font-size: 0.88rem;
  color: #6d5a4a;
}

.foreign-keys ul {
  margin: 0;
  padding-left: 1.2rem;
  color: #8b7663;
}

.foreign-keys li {
  margin-bottom: 0.35rem;
  font-size: 0.85rem;
}

.module-card {
  flex: 1;
  min-height: 0;
  border-radius: 32px;
  border: 1px solid #efe0cc;
  background: rgba(255, 255, 255, 0.9);
  box-shadow: 0 30px 70px rgba(197, 164, 126, 0.24);
  padding: 2rem;
}

.btn-primary {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.4rem;
  padding: 0.7rem 1.6rem;
  border: none;
  border-radius: 9999px;
  background: linear-gradient(135deg, #f26b3a, #ec915f);
  color: #fff;
  font-size: 0.95rem;
  font-weight: 600;
  box-shadow: 0 16px 32px rgba(233, 124, 72, 0.28);
  cursor: pointer;
  transition: transform 0.16s ease, box-shadow 0.24s ease, filter 0.24s ease;
}

.btn-primary:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 18px 38px rgba(225, 110, 58, 0.32);
  filter: brightness(1.03);
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  box-shadow: none;
}

.btn-secondary {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0.55rem 1.2rem;
  border-radius: 9999px;
  border: 1px solid #efdbc7;
  background: rgba(255, 247, 238, 0.85);
  color: #6d5a4a;
  font-size: 0.9rem;
  font-weight: 600;
  transition: all 0.2s ease;
  cursor: pointer;
}

.btn-secondary:hover:not(:disabled) {
  background: rgba(255, 242, 229, 0.95);
  border-color: #e8c7a5;
  box-shadow: 0 12px 26px rgba(205, 169, 130, 0.18);
}

.btn-secondary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  box-shadow: none;
}

.btn-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 2rem;
  height: 2rem;
  border-radius: 9999px;
  border: none;
  background: rgba(0, 0, 0, 0.04);
  color: #a48871;
  font-size: 1.2rem;
  transition: all 0.2s ease;
  cursor: pointer;
}

.btn-icon:hover {
  background: rgba(0, 0, 0, 0.07);
  color: #d6654a;
}

.modal-header .btn-icon {
  width: 2.2rem;
  height: 2.2rem;
  background: rgba(255, 244, 231, 0.85);
  color: #a57a5a;
  font-size: 1.1rem;
}

.modal-header .btn-icon:hover {
  background: rgba(255, 236, 218, 0.95);
  color: #d76544;
}

.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(49, 35, 19, 0.35);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  backdrop-filter: blur(6px);
  padding: 1.5rem;
}

.modal-content {
  width: 100%;
  max-width: 520px;
  background: linear-gradient(150deg, rgba(255, 255, 255, 0.98), rgba(255, 246, 234, 0.96));
  border-radius: 28px;
  border: 1px solid rgba(233, 210, 188, 0.8);
  box-shadow: 0 40px 80px rgba(162, 131, 103, 0.3);
  padding: 2rem;
  max-height: 90vh;
  overflow-y: auto;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1.5rem;
}

.modal-header h2 {
  margin: 0;
  font-size: 1.25rem;
  font-weight: 700;
  color: #32291f;
}

.connection-form {
  display: flex;
  flex-direction: column;
  gap: 1.1rem;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.form-group label {
  font-size: 0.85rem;
  font-weight: 600;
  color: #5d4a3b;
}

.form-group input,
.form-group select {
  border-radius: 14px;
  border: 1px solid #e9d7c4;
  padding: 0.6rem 0.75rem;
  font-size: 0.95rem;
  color: #403329;
  background: rgba(255, 255, 255, 0.92);
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.form-group input:focus,
.form-group select:focus {
  outline: none;
  border-color: #f0c9a2;
  box-shadow: 0 0 0 3px rgba(240, 201, 162, 0.25);
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
  margin-top: 0.5rem;
}
</style>
