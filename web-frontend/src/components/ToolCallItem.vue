<template>
  <div class="tool-call-card" :class="{ 'is-expanded': isExpanded, 'has-error': hasError }">
    <!-- Header -->
    <div class="tool-header" @click="toggleExpand">
      <div class="tool-icon">
        <svg v-if="!hasError" class="icon-tool" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
          <path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
        </svg>
        <svg v-else class="icon-error" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      </div>

      <div class="tool-info">
        <div class="tool-name">{{ toolName }}</div>
        <div class="tool-status">{{ statusText }}</div>
      </div>

      <div class="expand-icon" :class="{ 'is-rotated': isExpanded }">
        <svg class="icon-chevron" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7" />
        </svg>
      </div>
    </div>

    <!-- Expandable content -->
    <transition name="expand">
      <div v-if="isExpanded" class="tool-details">
        <!-- Arguments -->
        <div v-if="toolArgs && Object.keys(toolArgs).length > 0" class="detail-section">
          <div class="section-title">输入参数</div>
          <div class="code-block">
            <pre>{{ formatJSON(toolArgs) }}</pre>
          </div>
        </div>

        <!-- SQL Query Display (for DatabaseExecuteQuery tool) -->
        <div v-if="isDatabaseQueryTool && extractedSQL" class="detail-section">
          <div class="section-title-with-action">
            <span class="section-title">SQL 查询</span>
            <div class="button-group">
              <button
                @click.stop="copySQLToClipboard"
                :disabled="isCopyingSQL"
                class="icon-button"
                title="复制SQL"
              >
                <svg v-if="!isCopyingSQL" class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                </svg>
                <svg v-else class="w-3.5 h-3.5 text-green-600" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" />
                </svg>
                <span>{{ isCopyingSQL ? '已复制' : '复制' }}</span>
              </button>
              <button
                @click.stop="executeQuery"
                :disabled="isQuerying"
                class="query-button"
              >
                <svg v-if="!isQuerying" class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
                <svg v-else class="w-3.5 h-3.5 animate-spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v4m0 8v4m8-8h-4M8 12H4m12.364-7.364l-2.828 2.828M8.464 15.536l-2.828 2.828m0-12.728l2.828 2.828m8.485 8.485l2.828 2.828" />
                </svg>
                <span>{{ isQuerying ? '查询中...' : '立即查询' }}</span>
              </button>
            </div>
          </div>
          <div class="sql-block">
            <pre>{{ extractedSQL }}</pre>
          </div>
        </div>

        <!-- Result or Error -->
        <div v-if="toolResult || toolError" class="detail-section">
          <div class="section-title">{{ hasError ? '错误信息' : '执行结果' }}</div>
          <div class="code-block" :class="{ 'is-error': hasError }">
            <pre>{{ toolResult || toolError }}</pre>
          </div>
        </div>

        <!-- Query results table -->
        <div v-if="showQueryResults" class="detail-section">
          <div class="section-title">查询结果</div>
          <QueryResultTable
            :loading="isQuerying"
            :error="queryError"
            :data="queryResults"
          />
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import QueryResultTable from './QueryResultTable.vue'
import { executeDatabaseQuery } from '@/services/api'
import { notification } from '@/composables/useNotification'

interface ToolCallProps {
  toolName: string
  toolArgs?: Record<string, any>
  toolResult?: string
  toolError?: string
  status?: string
}

const props = defineProps<ToolCallProps>()

const isExpanded = ref(false)
const isQuerying = ref(false)
const isCopyingSQL = ref(false)
const queryResults = ref<any>(null)
const queryError = ref<string>('')
const showQueryResults = ref(false)

const hasError = computed(() => !!props.toolError)

const statusText = computed(() => {
  if (hasError.value || props.status === 'error') return '执行失败'
  if (props.status === 'completed') return '执行成功'
  if (props.status === 'started') return '执行中...'
  return '已完成'
})

const isDatabaseQueryTool = computed(() => {
  return props.toolName === 'DatabaseExecuteQuery'
})

const parsedResult = computed(() => {
  if (!props.toolResult) return null
  try {
    const parsed = JSON.parse(props.toolResult)
    console.log('[ToolCallItem] Parsed result:', parsed)
    return parsed
  } catch (e) {
    console.error('[ToolCallItem] Failed to parse toolResult:', e, 'Raw:', props.toolResult)
    return null
  }
})

// 提取并反转义SQL语句
const extractedSQL = computed(() => {
  if (!parsedResult.value || !parsedResult.value.sql) return null

  // 反转义SQL字符串：\n → 换行, \t → 制表符
  const sql = parsedResult.value.sql
  const unescaped = sql
    .replace(/\\n/g, '\n')
    .replace(/\\t/g, '\t')
    .replace(/\\r/g, '\r')
    .replace(/\\"/g, '"')
    .replace(/\\'/g, "'")

  console.log('[ToolCallItem] Extracted SQL (unescaped):', unescaped)
  return unescaped
})

function toggleExpand() {
  isExpanded.value = !isExpanded.value
}

function formatJSON(obj: any): string {
  try {
    return JSON.stringify(obj, null, 2)
  } catch (e) {
    return String(obj)
  }
}

async function copySQLToClipboard() {
  if (!extractedSQL.value) {
    notification.error('错误', '无法复制SQL')
    return
  }

  try {
    await navigator.clipboard.writeText(extractedSQL.value)
    isCopyingSQL.value = true
    notification.success('已复制', 'SQL已复制到剪贴板')
    setTimeout(() => {
      isCopyingSQL.value = false
    }, 2000)
  } catch (error) {
    console.error('Failed to copy SQL:', error)
    notification.error('复制失败', '无法访问剪贴板')
  }
}

async function executeQuery() {
  if (!extractedSQL.value) {
    notification.error('错误', '无法提取SQL查询')
    return
  }

  const connectionName = parsedResult.value?.connection_name || props.toolArgs?.connection_name

  if (!connectionName) {
    notification.error('错误', '无法确定数据库连接名称')
    console.error('[ToolCallItem] Missing connection_name. parsedResult:', parsedResult.value, 'toolArgs:', props.toolArgs)
    return
  }

  isQuerying.value = true
  queryError.value = ''
  queryResults.value = null
  showQueryResults.value = true

  try {
    console.log('[ToolCallItem] Executing query:', { connectionName, sql: extractedSQL.value })
    const result = await executeDatabaseQuery(connectionName, extractedSQL.value)

    if (result.status === 'success') {
      queryResults.value = result
      notification.success('查询成功', result.message || '查询执行完成')
    } else {
      queryError.value = result.message || '查询执行失败'
      notification.error('查询失败', queryError.value)
    }
  } catch (error: any) {
    queryError.value = error.response?.data?.detail || error.message || '查询执行失败'
    console.error('[ToolCallItem] Query execution error:', error)
    notification.error('查询失败', queryError.value)
  } finally {
    isQuerying.value = false
  }
}
</script>

<style scoped>
.tool-call-card {
  margin: 0.75rem 0;
  border: 1px solid #e5e7eb;
  border-radius: 0.5rem;
  background: #fafafa;
  overflow: hidden;
  transition: all 0.15s ease;
}

.tool-call-card:hover {
  border-color: #d1d5db;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.tool-call-card.has-error {
  border-color: #fca5a5;
  background: #fef2f2;
}

.tool-header {
  display: flex;
  align-items: center;
  padding: 0.75rem 1rem;
  cursor: pointer;
  user-select: none;
  gap: 0.75rem;
}

.tool-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 0.375rem;
  background: #f3f4f6;
  flex-shrink: 0;
}

.has-error .tool-icon {
  background: #fee2e2;
}

.icon-tool,
.icon-error {
  width: 16px;
  height: 16px;
  color: #6b7280;
}

.has-error .icon-error {
  color: #dc2626;
}

.tool-info {
  flex: 1;
  min-width: 0;
}

.tool-name {
  font-size: 0.875rem;
  font-weight: 600;
  color: #111827;
  margin-bottom: 0.125rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.tool-status {
  font-size: 0.75rem;
  color: #6b7280;
}

.has-error .tool-status {
  color: #dc2626;
}

.expand-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  transition: transform 0.2s ease;
}

.expand-icon.is-rotated {
  transform: rotate(180deg);
}

.icon-chevron {
  width: 16px;
  height: 16px;
  color: #9ca3af;
}

.tool-details {
  border-top: 1px solid #e5e7eb;
  padding: 1rem;
  background: white;
}

.detail-section {
  margin-bottom: 1rem;
}

.detail-section:last-child {
  margin-bottom: 0;
}

.section-title {
  font-size: 0.75rem;
  font-weight: 600;
  color: #6b7280;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 0.5rem;
}

.section-title-with-action {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.5rem;
}

.button-group {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}

.icon-button {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.375rem 0.75rem;
  border-radius: 0.375rem;
  border: 1px solid #d1d5db;
  background: white;
  color: #6b7280;
  cursor: pointer;
  transition: all 0.15s ease;
  font-weight: 500;
  font-size: 0.75rem;
}

.icon-button:hover:not(:disabled) {
  border-color: #9ca3af;
  background: #f9fafb;
  color: #374151;
}

.icon-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.query-button {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.375rem 0.75rem;
  border-radius: 0.375rem;
  border: 1px solid #3b82f6;
  background: white;
  color: #3b82f6;
  cursor: pointer;
  transition: all 0.15s ease;
  font-weight: 500;
  font-size: 0.75rem;
}

.query-button:hover:not(:disabled) {
  background: #3b82f6;
  color: white;
  box-shadow: 0 1px 2px rgba(59, 130, 246, 0.2);
}

.query-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.query-button svg,
.icon-button svg {
  width: 0.875rem;
  height: 0.875rem;
}

.sql-block {
  border: 1px solid #d1d5db;
  border-radius: 0.375rem;
  background: #1f2937;
  padding: 0.75rem;
  overflow-x: auto;
  font-family: 'Monaco', 'Menlo', 'Courier New', monospace;
  font-size: 0.8rem;
  line-height: 1.6;
}

.sql-block pre {
  margin: 0;
  color: #f3f4f6;
  white-space: pre;
  word-break: normal;
}

.code-block {
  border: 1px solid #e5e7eb;
  border-radius: 0.375rem;
  background: #f9fafb;
  padding: 0.75rem;
  overflow-x: auto;
}

.code-block.is-error {
  border-color: #fca5a5;
  background: #fef2f2;
}

.code-block pre {
  margin: 0;
  font-family: 'Monaco', 'Menlo', 'Courier New', monospace;
  font-size: 0.75rem;
  line-height: 1.5;
  color: #374151;
  white-space: pre-wrap;
  word-break: break-word;
}

.code-block.is-error pre {
  color: #991b1b;
}

/* Expand transition */
.expand-enter-active,
.expand-leave-active {
  transition: all 0.2s ease;
  max-height: 800px;
  overflow: hidden;
}

.expand-enter-from,
.expand-leave-to {
  max-height: 0;
  opacity: 0;
}
</style>
