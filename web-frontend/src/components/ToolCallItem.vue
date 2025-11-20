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
        <!-- Arguments (数据库工具默认隐藏) -->
        <div v-if="toolArgs && Object.keys(toolArgs).length > 0 && !isDatabaseQueryTool" class="detail-section">
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

        <!-- Batch Uncertainty Q&A Summary (compact view) -->
        <div v-if="isUncertaintyBatchLoad && uncertaintyData" class="detail-section">
          <div class="section-title-with-action">
            <span class="section-title">批量问答表单</span>
            <span class="text-xs text-gray-500">
              共 {{ uncertaintyData.total_loaded }} 个高优先级问题
            </span>
          </div>

          <div class="uncertainty-summary">
            <div class="summary-info">
              <svg class="summary-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              <div class="summary-text">
                <p class="summary-main">AI 已为你准备好 {{ uncertaintyData.total_loaded }} 个业务问题</p>
                <p class="summary-sub">涵盖 {{ uncertaintyData.groups?.length || 0 }} 个业务域，点击下方按钮在对话框中批量回答</p>
              </div>
            </div>
            <button @click.stop="openBatchDialog" class="open-dialog-button">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                <path stroke-linecap="round" stroke-linejoin="round" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
              </svg>
              <span>查看并回答</span>
            </button>
          </div>
        </div>

        <!-- Result or Error -->
        <div v-if="toolResult || toolError" class="detail-section">
          <div class="section-title">{{ hasError ? '错误信息' : '执行结果' }}</div>

          <!-- 批量问答工具：只显示简洁统计 -->
          <div v-if="isUncertaintyBatchLoad && parsedToolResult" class="result-summary">
            <div class="summary-item">
              <span class="summary-label">加载状态：</span>
              <span class="summary-value success">✓ 成功</span>
            </div>
            <div class="summary-item">
              <span class="summary-label">问题总数：</span>
              <span class="summary-value">{{ parsedToolResult.total_loaded || 0 }} 个</span>
            </div>
            <div class="summary-item">
              <span class="summary-label">业务域：</span>
              <span class="summary-value">{{ parsedToolResult.groups?.length || 0 }} 个</span>
            </div>
          </div>

          <!-- 如果结果是表格数据，用表格展示 -->
          <QueryResultTable
            v-else-if="!hasError && parsedToolResult && isTableData(parsedToolResult)"
            :loading="false"
            :error="''"
            :data="parsedToolResult"
          />

          <!-- 如果是图表，用图表展示 -->
          <div v-else-if="isChartTool && parsedToolResult && parsedToolResult.success && parsedToolResult.config" class="chart-container" style="height: 400px; width: 100%;">
            <ChartRenderer :option="parsedToolResult.config" />
          </div>

          <!-- 否则用代码块展示 -->
          <div v-else class="code-block" :class="{ 'is-error': hasError }">
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

    <!-- Batch Uncertainty Dialog -->
    <UncertaintyBatchDialog
      v-model:visible="showBatchDialog"
      :data="uncertaintyData"
      :connection-name="toolArgs?.connection_name"
      @submit="handleDialogSubmit"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, defineAsyncComponent } from 'vue'
import QueryResultTable from './QueryResultTable.vue'
import UncertaintyBatchDialog from './UncertaintyBatchDialog.vue'
// Use defineAsyncComponent to avoid circular dependencies if any, and for better performance
const ChartRenderer = defineAsyncComponent(() => import('./ChartRenderer.vue'))
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
  // 如果有 toolResult，即使没有 status，也认为是已完成
  if (props.toolResult && !props.status) return '执行成功'
  return '已完成'
})

const isDatabaseQueryTool = computed(() => {
  return props.toolName === 'DatabaseExecuteQuery'
})

const isChartTool = computed(() => {
  return props.toolName === 'ChartGenerator'
})

// 先定义 parsedResult 和 parsedToolResult，因为后面的 computed 会用到
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

// 解析 toolResult 用于表格渲染
const parsedToolResult = computed(() => {
  if (!props.toolResult || hasError.value) return null
  try {
    const parsed = JSON.parse(props.toolResult)
    return parsed
  } catch (e) {
    return null
  }
})

const isUncertaintyBatchLoad = computed(() => {
  // 支持两种 action: 'load' 和 'batch_load'
  const result = props.toolName === 'UncertaintyQAManager' &&
         (props.toolArgs?.action === 'batch_load' || props.toolArgs?.action === 'load')

  // 调试日志
  if (props.toolName === 'UncertaintyQAManager') {
    console.log('[ToolCallItem] UncertaintyQAManager detected:', {
      toolName: props.toolName,
      action: props.toolArgs?.action,
      isMatch: result,
      toolArgs: props.toolArgs,
      toolResult: props.toolResult,
      hasError: hasError.value
    })
  }

  return result
})

// 解析批量问答数据
const uncertaintyData = computed(() => {
  if (!isUncertaintyBatchLoad.value || !parsedToolResult.value) {
    if (isUncertaintyBatchLoad.value) {
      console.log('[ToolCallItem] uncertaintyData is null because:', {
        isUncertaintyBatchLoad: isUncertaintyBatchLoad.value,
        parsedToolResult: parsedToolResult.value,
        hasError: hasError.value
      })
    }
    return null
  }

  const result = parsedToolResult.value

  // 如果是 'load' 格式（questions 数组），转换为 'batch_load' 格式（groups 数组）
  if (result.questions && !result.groups) {
    console.log('[ToolCallItem] Converting "load" format to "batch_load" format')

    // 按 domain 分组
    const groupsMap: Record<string, any[]> = {}
    result.questions.forEach((q: any) => {
      const domain = q.domain || 'unknown'
      if (!groupsMap[domain]) {
        groupsMap[domain] = []
      }
      groupsMap[domain].push(q)
    })

    // 转换为 groups 数组
    const groups = Object.entries(groupsMap).map(([domain, questions]) => ({
      domain,
      question_count: questions.length,
      questions
    }))

    return {
      ...result,
      total_loaded: result.questions.length,
      groups
    }
  }

  console.log('[ToolCallItem] uncertaintyData loaded:', result)
  return result
})

// 批量问答对话框状态
const showBatchDialog = ref(false)

// 调试：监听对话框显示状态
watch(showBatchDialog, (newVal) => {
  console.log('[ToolCallItem] showBatchDialog changed to:', newVal)
})

// 监听 uncertaintyData 变化，自动打开对话框
watch(
  () => uncertaintyData.value,
  (newData) => {
    console.log('[ToolCallItem] uncertaintyData changed:', newData)
    if (newData && newData.total_loaded > 0) {
      console.log('[ToolCallItem] Auto-opening batch dialog for', newData.total_loaded, 'questions')
      // 延迟一点时间自动打开，让用户看到工具卡片的动画
      setTimeout(() => {
        console.log('[ToolCallItem] Setting showBatchDialog to true')
        showBatchDialog.value = true
      }, 500)
    } else {
      console.log('[ToolCallItem] Not opening dialog:', {
        hasData: !!newData,
        totalLoaded: newData?.total_loaded
      })
    }
  }
  // 不使用 immediate: true，避免初始化时的错误
)

// 判断是否为表格数据
function isTableData(data: any): boolean {
  return (
    data &&
    typeof data === 'object' &&
    Array.isArray(data.columns) &&
    Array.isArray(data.data) &&
    data.columns.length > 0
  )
}

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

function openBatchDialog() {
  showBatchDialog.value = true
}

function handleDialogSubmit(answers: Record<string, string>) {
  console.log('[ToolCallItem] Batch answers submitted:', answers)
  // 对话框组件已经处理提交逻辑并显示了通知，这里不需要重复显示
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
  max-height: 400px;
  overflow: auto;
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

/* 自定义滚动条样式 */
.code-block::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}

.code-block::-webkit-scrollbar-track {
  background: #f3f4f6;
  border-radius: 3px;
}

.code-block::-webkit-scrollbar-thumb {
  background: #d1d5db;
  border-radius: 3px;
}

.code-block::-webkit-scrollbar-thumb:hover {
  background: #9ca3af;
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

/* Batch Uncertainty Summary Styles (compact) */
.uncertainty-summary {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 1rem;
  background: linear-gradient(135deg, #eff6ff 0%, #f0f9ff 100%);
  border: 1px solid #bfdbfe;
  border-radius: 0.5rem;
  transition: all 0.15s ease;
}

.uncertainty-summary:hover {
  border-color: #93c5fd;
  box-shadow: 0 2px 4px rgba(59, 130, 246, 0.1);
}

.summary-info {
  display: flex;
  align-items: flex-start;
  gap: 0.875rem;
  flex: 1;
}

.summary-icon {
  width: 40px;
  height: 40px;
  color: #3b82f6;
  flex-shrink: 0;
  padding: 0.5rem;
  background: white;
  border-radius: 0.5rem;
  box-shadow: 0 1px 2px rgba(59, 130, 246, 0.1);
}

.summary-text {
  flex: 1;
}

.summary-main {
  font-size: 0.9375rem;
  font-weight: 600;
  color: #1e40af;
  margin: 0 0 0.25rem 0;
  line-height: 1.4;
}

.summary-sub {
  font-size: 0.8125rem;
  color: #6b7280;
  margin: 0;
  line-height: 1.4;
}

.open-dialog-button {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.625rem 1.25rem;
  border-radius: 0.4375rem;
  border: none;
  background: #3b82f6;
  color: white;
  cursor: pointer;
  transition: all 0.15s ease;
  font-weight: 600;
  font-size: 0.875rem;
  box-shadow: 0 2px 4px rgba(59, 130, 246, 0.2);
  flex-shrink: 0;
}

.open-dialog-button:hover {
  background: #2563eb;
  box-shadow: 0 4px 6px rgba(59, 130, 246, 0.3);
  transform: translateY(-1px);
}

.open-dialog-button:active {
  transform: translateY(0);
}

.open-dialog-button svg {
  width: 1.125rem;
  height: 1.125rem;
}

/* Result Summary Styles */
.result-summary {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  padding: 1rem;
  background: #f9fafb;
  border-radius: 0.5rem;
  border: 1px solid #e5e7eb;
}

.summary-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.875rem;
}

.summary-label {
  font-weight: 500;
  color: #6b7280;
}

.summary-value {
  font-weight: 600;
  color: #111827;
}

.summary-value.success {
  color: #059669;
}
</style>
