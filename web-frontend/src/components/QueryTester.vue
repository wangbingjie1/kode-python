<template>
  <div class="query-tester">
    <div class="query-header">
      <h3>SQL 查询测试</h3>
      <select v-model="selectedConnection" class="connection-select">
        <option value="">选择数据库连接</option>
        <option v-for="conn in connections" :key="conn.name" :value="conn.name">
          {{ conn.name }} ({{ conn.db_type }})
        </option>
      </select>
    </div>

    <div class="query-editor">
      <div class="editor-toolbar">
        <button @click="executeQuery" :disabled="!canExecute" class="btn-execute">
          {{ executing ? '执行中...' : '执行查询' }}
        </button>
        <button @click="clearQuery" class="btn-clear">清空</button>
        <button @click="formatQuery" class="btn-format">格式化</button>
      </div>

      <textarea
        v-model="queryText"
        class="query-textarea"
        placeholder="在此输入 SQL 查询语句..."
        spellcheck="false"
      ></textarea>
    </div>

    <div v-if="queryResult" class="query-result">
      <div class="result-header">
        <h4>查询结果</h4>
        <div class="result-meta">
          <span v-if="queryResult.success">
            {{ queryResult.rowCount }} 行 · 执行时间: {{ queryResult.executionTime }}ms
          </span>
          <span v-else class="error-badge">执行失败</span>
        </div>
      </div>

      <div v-if="queryResult.success" class="result-table-container">
        <table class="result-table">
          <thead>
            <tr>
              <th v-for="col in queryResult.columns" :key="col">{{ col }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, idx) in queryResult.rows" :key="idx">
              <td v-for="col in queryResult.columns" :key="col">
                {{ formatCellValue(row[col]) }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-else class="error-message">
        <pre>{{ queryResult.error }}</pre>
      </div>
    </div>

    <div class="query-history">
      <h4>查询历史</h4>
      <div
        v-for="(item, idx) in queryHistory"
        :key="idx"
        class="history-item"
        @click="loadHistoryQuery(item)"
      >
        <div class="history-query">{{ truncateQuery(item.query) }}</div>
        <div class="history-meta">
          <span>{{ item.connection }}</span>
          <span>{{ formatDate(item.timestamp) }}</span>
          <span
            :class="['history-status', item.success ? 'success' : 'error']"
          >
            {{ item.success ? '成功' : '失败' }}
          </span>
        </div>
      </div>
      <div v-if="queryHistory.length === 0" class="empty-history">
        暂无查询历史
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import type { DatabaseConnection } from '@/services/api'
import { notification } from '@/composables/useNotification'

interface QueryResult {
  success: boolean
  columns?: string[]
  rows?: any[]
  rowCount?: number
  executionTime?: number
  error?: string
}

interface QueryHistoryItem {
  query: string
  connection: string
  timestamp: Date
  success: boolean
}

const props = defineProps<{
  connections: DatabaseConnection[]
}>()

const selectedConnection = ref('')
const queryText = ref('')
const executing = ref(false)
const queryResult = ref<QueryResult | null>(null)
const queryHistory = ref<QueryHistoryItem[]>([])

const canExecute = computed(() => {
  return selectedConnection.value && queryText.value.trim() && !executing.value
})

onMounted(() => {
  loadQueryHistory()
})

async function executeQuery() {
  if (!canExecute.value) return

  executing.value = true
  const startTime = Date.now()

  try {
    // Mock query execution - in real implementation, this would call the backend
    // For now, we'll simulate it
    await new Promise((resolve) => setTimeout(resolve, 500))

    // Simulate result
    const executionTime = Date.now() - startTime
    const mockResult: QueryResult = {
      success: true,
      columns: ['id', 'name', 'created_at'],
      rows: [
        { id: 1, name: 'Test 1', created_at: new Date().toISOString() },
        { id: 2, name: 'Test 2', created_at: new Date().toISOString() }
      ],
      rowCount: 2,
      executionTime
    }

    queryResult.value = mockResult

    // Add to history
    addToHistory({
      query: queryText.value,
      connection: selectedConnection.value,
      timestamp: new Date(),
      success: true
    })

    notification.success('查询成功', `返回 ${mockResult.rowCount} 行结果`)
  } catch (error: any) {
    queryResult.value = {
      success: false,
      error: error.message || '查询执行失败'
    }

    addToHistory({
      query: queryText.value,
      connection: selectedConnection.value,
      timestamp: new Date(),
      success: false
    })

    notification.error('查询失败', error.message)
  } finally {
    executing.value = false
  }
}

function clearQuery() {
  queryText.value = ''
  queryResult.value = null
}

function formatQuery() {
  // Basic SQL formatting
  let formatted = queryText.value
    .replace(/\s+/g, ' ')
    .replace(/\s*,\s*/g, ',\n  ')
    .replace(/\bSELECT\b/gi, 'SELECT\n  ')
    .replace(/\bFROM\b/gi, '\nFROM\n  ')
    .replace(/\bWHERE\b/gi, '\nWHERE\n  ')
    .replace(/\bAND\b/gi, '\n  AND ')
    .replace(/\bOR\b/gi, '\n  OR ')
    .replace(/\bORDER BY\b/gi, '\nORDER BY\n  ')
    .replace(/\bGROUP BY\b/gi, '\nGROUP BY\n  ')
    .replace(/\bJOIN\b/gi, '\nJOIN\n  ')
    .trim()

  queryText.value = formatted
}

function loadHistoryQuery(item: QueryHistoryItem) {
  queryText.value = item.query
  selectedConnection.value = item.connection
  queryResult.value = null
}

function addToHistory(item: QueryHistoryItem) {
  queryHistory.value.unshift(item)
  if (queryHistory.value.length > 20) {
    queryHistory.value = queryHistory.value.slice(0, 20)
  }
  saveQueryHistory()
}

function loadQueryHistory() {
  const saved = localStorage.getItem('query_history')
  if (saved) {
    try {
      const parsed = JSON.parse(saved)
      queryHistory.value = parsed.map((item: any) => ({
        ...item,
        timestamp: new Date(item.timestamp)
      }))
    } catch (e) {
      console.error('Failed to load query history:', e)
    }
  }
}

function saveQueryHistory() {
  localStorage.setItem('query_history', JSON.stringify(queryHistory.value))
}

function formatCellValue(value: any): string {
  if (value === null || value === undefined) return 'NULL'
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}

function truncateQuery(query: string): string {
  const maxLength = 60
  if (query.length <= maxLength) return query
  return query.substring(0, maxLength) + '...'
}

function formatDate(date: Date): string {
  return new Date(date).toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}
</script>

<style scoped>
.query-tester {
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.query-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.query-header h3 {
  margin: 0;
  color: #333;
}

.connection-select {
  padding: 0.5rem;
  border: 1px solid #e0e0e0;
  border-radius: 4px;
  font-size: 0.875rem;
  min-width: 200px;
}

.query-editor {
  display: flex;
  flex-direction: column;
  background: white;
  border: 1px solid #e0e0e0;
  border-radius: 4px;
  overflow: hidden;
}

.editor-toolbar {
  display: flex;
  gap: 0.5rem;
  padding: 0.5rem;
  background: #f8f8f8;
  border-bottom: 1px solid #e0e0e0;
}

.btn-execute,
.btn-clear,
.btn-format {
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.875rem;
  transition: all 0.2s;
}

.btn-execute {
  background: #4caf50;
  color: white;
}

.btn-execute:hover:not(:disabled) {
  background: #45a049;
}

.btn-execute:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-clear,
.btn-format {
  background: #f5f5f5;
  color: #333;
}

.btn-clear:hover,
.btn-format:hover {
  background: #e0e0e0;
}

.query-textarea {
  flex: 1;
  min-height: 150px;
  padding: 1rem;
  border: none;
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 0.875rem;
  resize: vertical;
}

.query-textarea:focus {
  outline: none;
}

.query-result {
  background: white;
  border: 1px solid #e0e0e0;
  border-radius: 4px;
  padding: 1rem;
}

.result-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.result-header h4 {
  margin: 0;
  color: #333;
}

.result-meta {
  font-size: 0.875rem;
  color: #666;
}

.error-badge {
  color: #f44336;
  font-weight: 500;
}

.result-table-container {
  overflow-x: auto;
}

.result-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.875rem;
}

.result-table th,
.result-table td {
  padding: 0.5rem;
  text-align: left;
  border-bottom: 1px solid #f0f0f0;
}

.result-table th {
  background: #f8f8f8;
  font-weight: 600;
  color: #666;
}

.result-table td {
  color: #333;
}

.result-table tbody tr:hover {
  background: #f8f8f8;
}

.error-message {
  padding: 1rem;
  background: #ffebee;
  border-radius: 4px;
  color: #c62828;
}

.error-message pre {
  margin: 0;
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 0.875rem;
  white-space: pre-wrap;
  word-wrap: break-word;
}

.query-history {
  background: white;
  border: 1px solid #e0e0e0;
  border-radius: 4px;
  padding: 1rem;
  max-height: 300px;
  overflow-y: auto;
}

.query-history h4 {
  margin: 0 0 1rem 0;
  color: #333;
  font-size: 1rem;
}

.history-item {
  padding: 0.75rem;
  border: 1px solid #f0f0f0;
  border-radius: 4px;
  margin-bottom: 0.5rem;
  cursor: pointer;
  transition: all 0.2s;
}

.history-item:hover {
  background: #f8f8f8;
  border-color: #2196f3;
}

.history-query {
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 0.875rem;
  color: #333;
  margin-bottom: 0.5rem;
}

.history-meta {
  display: flex;
  gap: 1rem;
  font-size: 0.75rem;
  color: #999;
}

.history-status {
  font-weight: 500;
}

.history-status.success {
  color: #4caf50;
}

.history-status.error {
  color: #f44336;
}

.empty-history {
  text-align: center;
  color: #999;
  padding: 1rem;
}
</style>
