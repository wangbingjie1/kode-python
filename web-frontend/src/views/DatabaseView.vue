<template>
  <div class="database-view">
    <div class="database-header">
      <h1>数据库管理</h1>
      <div class="header-actions">
        <div class="view-tabs">
          <button
            :class="['tab-btn', { active: currentView === 'connections' }]"
            @click="currentView = 'connections'"
          >
            连接管理
          </button>
          <button
            :class="['tab-btn', { active: currentView === 'ontology' }]"
            @click="currentView = 'ontology'"
          >
            本体管理
          </button>
          <button
            :class="['tab-btn', { active: currentView === 'query' }]"
            @click="currentView = 'query'"
          >
            查询测试
          </button>
        </div>
        <button
          v-if="currentView === 'connections'"
          @click="showConnectionForm = true"
          class="btn-primary"
        >
          新建连接
        </button>
      </div>
    </div>

    <div class="database-content" v-if="currentView === 'connections'">
      <!-- Sidebar with connections list -->
      <div class="connections-sidebar">
        <div class="sidebar-header">
          <h2>数据库连接</h2>
        </div>
        <div class="connections-list">
          <div
            v-for="connection in connections"
            :key="connection.name"
            :class="['connection-item', { active: selectedConnection?.name === connection.name }]"
            @click="selectConnection(connection)"
          >
            <div class="connection-icon">
              <span>{{ getDatabaseIcon(connection.db_type) }}</span>
            </div>
            <div class="connection-info">
              <div class="connection-name">{{ connection.name }}</div>
              <div class="connection-details">
                {{ connection.db_type }} - {{ connection.database }}
              </div>
            </div>
            <button
              @click.stop="deleteConnection(connection.name)"
              class="btn-icon"
              title="删除连接"
            >
              ×
            </button>
          </div>
          <div v-if="connections.length === 0" class="empty-state">
            暂无数据库连接
          </div>
        </div>
      </div>

      <!-- Main content area -->
      <div class="main-content">
        <div v-if="!selectedConnection" class="empty-selection">
          <p>请选择一个数据库连接或创建新连接</p>
        </div>

        <div v-else class="connection-details">
          <div class="details-header">
            <h2>{{ selectedConnection.name }}</h2>
            <div class="action-buttons">
              <button @click="editConnection" class="btn-secondary">
                编辑
              </button>
              <button @click="testConnection" class="btn-secondary" :disabled="testing">
                {{ testing ? '测试中...' : '测试连接' }}
              </button>
              <button @click="loadSchema" class="btn-secondary" :disabled="loadingSchema">
                {{ loadingSchema ? '加载中...' : '加载结构' }}
              </button>
            </div>
          </div>

          <div class="connection-info-grid">
            <div class="info-item">
              <label>类型</label>
              <span>{{ selectedConnection.db_type }}</span>
            </div>
            <div class="info-item">
              <label>主机</label>
              <span>{{ selectedConnection.host }}:{{ selectedConnection.port }}</span>
            </div>
            <div class="info-item">
              <label>数据库</label>
              <span>{{ selectedConnection.database }}</span>
            </div>
            <div class="info-item">
              <label>用户名</label>
              <span>{{ selectedConnection.username }}</span>
            </div>
            <div class="info-item" v-if="selectedConnection.schema">
              <label>Schema</label>
              <span>{{ selectedConnection.schema }}</span>
            </div>
            <div class="info-item">
              <label>SSL</label>
              <span>{{ selectedConnection.ssl ? '启用' : '禁用' }}</span>
            </div>
          </div>

          <!-- Schema display -->
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
                  <span class="column-count">({{ table.columns.length }} 列)</span>
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

    <!-- Ontology View -->
    <div class="database-content" v-if="currentView === 'ontology'">
      <OntologyViewer />
    </div>

    <!-- Query Tester View -->
    <div class="database-content" v-if="currentView === 'query'">
      <div class="query-container">
        <QueryTester :connections="connections" />
      </div>
    </div>

    <!-- Connection Form Modal -->
    <div v-if="showConnectionForm" class="modal-overlay" @click="closeConnectionForm">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h2>{{ isEditMode ? '编辑数据库连接' : '新建数据库连接' }}</h2>
          <button @click="closeConnectionForm" class="btn-icon">×</button>
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
import { ref, onMounted } from 'vue'
import {
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

const formData = ref<CreateDatabaseConnectionRequest>({
  name: '',
  db_type: 'postgresql',
  host: 'localhost',
  port: 5432,
  database: '',
  username: '',
  password: '',
  schema: '',
  ssl: false
})

onMounted(async () => {
  await loadConnections()
})

async function loadConnections() {
  try {
    connections.value = await listDatabaseConnections()
  } catch (error: any) {
    notification.error('加载失败', error.message)
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
    password: '', // Don't populate password for security
    db_schema: selectedConnection.value.schema || null,
    ssl: selectedConnection.value.ssl
  }
  showConnectionForm.value = true
}

async function saveConnection() {
  creating.value = true
  try {
    if (isEditMode.value && editingConnectionName.value) {
      // Update existing connection
      const updateData: UpdateDatabaseConnectionRequest = {
        host: formData.value.host,
        port: formData.value.port,
        database: formData.value.database,
        username: formData.value.username,
        db_schema: formData.value.db_schema,
        ssl: formData.value.ssl
      }
      // Only include password if it's been changed
      if (formData.value.password) {
        updateData.password = formData.value.password
      }
      await updateDatabaseConnection(editingConnectionName.value, updateData)
      notification.success('更新成功', `连接 ${editingConnectionName.value} 已更新`)
    } else {
      // Create new connection
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
    db_schema: null,
    ssl: false
  }
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
.database-view {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: #f5f5f5;
}

.database-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.5rem 2rem;
  background: white;
  border-bottom: 1px solid #e0e0e0;
}

.database-header h1 {
  margin: 0;
  font-size: 1.5rem;
  color: #333;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.view-tabs {
  display: flex;
  gap: 0.5rem;
}

.tab-btn {
  padding: 0.5rem 1rem;
  background: white;
  border: 1px solid #e0e0e0;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.875rem;
  color: #666;
  transition: all 0.2s;
}

.tab-btn:hover {
  border-color: #2196f3;
  color: #2196f3;
}

.tab-btn.active {
  background: #2196f3;
  color: white;
  border-color: #2196f3;
}

.query-container {
  padding: 2rem;
  height: 100%;
  overflow-y: auto;
}

.database-content {
  flex: 1;
  display: flex;
  overflow: hidden;
}

.connections-sidebar {
  width: 300px;
  background: white;
  border-right: 1px solid #e0e0e0;
  display: flex;
  flex-direction: column;
}

.sidebar-header {
  padding: 1rem;
  border-bottom: 1px solid #e0e0e0;
}

.sidebar-header h2 {
  margin: 0;
  font-size: 1rem;
  color: #666;
}

.connections-list {
  flex: 1;
  overflow-y: auto;
}

.connection-item {
  display: flex;
  align-items: center;
  padding: 0.75rem 1rem;
  cursor: pointer;
  border-bottom: 1px solid #f0f0f0;
  transition: background 0.2s;
}

.connection-item:hover {
  background: #f8f8f8;
}

.connection-item.active {
  background: #e3f2fd;
  border-left: 3px solid #2196f3;
}

.connection-icon {
  font-size: 1.5rem;
  margin-right: 0.75rem;
}

.connection-info {
  flex: 1;
  min-width: 0;
}

.connection-name {
  font-weight: 500;
  color: #333;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.connection-details {
  font-size: 0.75rem;
  color: #999;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.main-content {
  flex: 1;
  overflow-y: auto;
  padding: 2rem;
}

.empty-selection,
.empty-state {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100%;
  color: #999;
}

.connection-details {
  background: white;
  border-radius: 8px;
  padding: 2rem;
}

.details-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
}

.details-header h2 {
  margin: 0;
  font-size: 1.5rem;
  color: #333;
}

.action-buttons {
  display: flex;
  gap: 0.5rem;
}

.connection-info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 1rem;
  margin-bottom: 2rem;
}

.info-item {
  display: flex;
  flex-direction: column;
}

.info-item label {
  font-size: 0.75rem;
  color: #999;
  margin-bottom: 0.25rem;
}

.info-item span {
  color: #333;
  font-weight: 500;
}

.schema-section {
  margin-top: 2rem;
  padding-top: 2rem;
  border-top: 1px solid #e0e0e0;
}

.schema-section h3 {
  margin-bottom: 1rem;
  color: #333;
}

.tables-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.table-item {
  border: 1px solid #e0e0e0;
  border-radius: 4px;
  overflow: hidden;
}

.table-header {
  display: flex;
  align-items: center;
  padding: 0.75rem 1rem;
  background: #f8f8f8;
  cursor: pointer;
  transition: background 0.2s;
}

.table-header:hover {
  background: #f0f0f0;
}

.table-icon {
  margin-right: 0.5rem;
}

.table-name {
  font-weight: 500;
  color: #333;
}

.column-count {
  margin-left: 0.5rem;
  font-size: 0.875rem;
  color: #999;
}

.toggle-icon {
  margin-left: auto;
  color: #999;
}

.table-details {
  padding: 1rem;
  background: white;
}

.columns-table {
  width: 100%;
  border-collapse: collapse;
}

.columns-table th,
.columns-table td {
  padding: 0.5rem;
  text-align: left;
  border-bottom: 1px solid #f0f0f0;
}

.columns-table th {
  font-weight: 600;
  color: #666;
  font-size: 0.875rem;
}

.columns-table td {
  color: #333;
  font-size: 0.875rem;
}

.foreign-keys {
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid #f0f0f0;
}

.foreign-keys h4 {
  margin: 0 0 0.5rem 0;
  font-size: 0.875rem;
  color: #666;
}

.foreign-keys ul {
  margin: 0;
  padding-left: 1.5rem;
}

.foreign-keys li {
  font-size: 0.875rem;
  color: #333;
  margin-bottom: 0.25rem;
}

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.modal-content {
  background: white;
  border-radius: 8px;
  padding: 2rem;
  max-width: 500px;
  width: 90%;
  max-height: 90vh;
  overflow-y: auto;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
}

.modal-header h2 {
  margin: 0;
  font-size: 1.25rem;
  color: #333;
}

.connection-form {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.form-group {
  display: flex;
  flex-direction: column;
}

.form-group label {
  margin-bottom: 0.5rem;
  font-weight: 500;
  color: #333;
}

.form-group input,
.form-group select {
  padding: 0.5rem;
  border: 1px solid #e0e0e0;
  border-radius: 4px;
  font-size: 1rem;
}

.form-group input[type='checkbox'] {
  width: auto;
  margin-right: 0.5rem;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
  margin-top: 1rem;
}

.btn-primary,
.btn-secondary,
.btn-icon {
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 1rem;
  transition: all 0.2s;
}

.btn-primary {
  background: #2196f3;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: #1976d2;
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-secondary {
  background: #f5f5f5;
  color: #333;
}

.btn-secondary:hover:not(:disabled) {
  background: #e0e0e0;
}

.btn-secondary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-icon {
  padding: 0.25rem 0.5rem;
  background: transparent;
  color: #999;
  font-size: 1.5rem;
}

.btn-icon:hover {
  color: #333;
}
</style>
