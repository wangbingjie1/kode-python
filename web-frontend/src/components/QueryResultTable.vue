<template>
  <div class="query-result-container">
    <!-- Loading state -->
    <div v-if="loading" class="loading-state">
      <svg class="animate-spin h-5 w-5 text-blue-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v4m0 8v4m8-8h-4M8 12H4m12.364-7.364l-2.828 2.828M8.464 15.536l-2.828 2.828m0-12.728l2.828 2.828m8.485 8.485l2.828 2.828" />
      </svg>
      <span class="ml-2 text-sm text-gray-600">执行查询中...</span>
    </div>

    <!-- Error state -->
    <div v-else-if="error" class="error-state">
      <svg class="h-5 w-5 text-red-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path stroke-linecap="round" stroke-linejoin="round" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
      <span class="ml-2 text-sm text-red-600">{{ error }}</span>
    </div>

    <!-- Results table -->
    <div v-else-if="data && data.data && data.data.length > 0" class="result-wrapper">
      <div class="result-header">
        <div class="result-info">
          <span class="text-sm font-medium text-gray-700">
            共 {{ data.row_count }} 行
            <span v-if="data.has_more" class="text-gray-500">(可能有更多)</span>
          </span>
        </div>
      </div>

      <div class="table-container">
        <table class="result-table">
          <thead>
            <tr>
              <th v-for="column in data.columns" :key="column" class="table-header">
                {{ column }}
              </th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, index) in data.data" :key="index" class="table-row">
              <td v-for="column in data.columns" :key="column" class="table-cell">
                <div class="cell-content">
                  {{ formatValue(row[column]) }}
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Empty state -->
    <div v-else-if="data && data.row_count === 0" class="empty-state">
      <svg class="h-5 w-5 text-gray-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path stroke-linecap="round" stroke-linejoin="round" d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
      </svg>
      <span class="ml-2 text-sm text-gray-500">查询未返回任何数据</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

interface QueryResultData {
  status: string
  query_type: string
  row_count: number
  has_more: boolean
  columns: string[]
  data: Record<string, any>[]
  message: string
}

interface Props {
  loading?: boolean
  error?: string
  data?: QueryResultData | null
}

const props = withDefaults(defineProps<Props>(), {
  loading: false,
  error: '',
  data: null
})

function formatValue(value: any): string {
  if (value === null || value === undefined) {
    return 'NULL'
  }
  if (typeof value === 'boolean') {
    return value ? 'true' : 'false'
  }
  if (typeof value === 'object') {
    return JSON.stringify(value)
  }
  return String(value)
}
</script>

<style scoped>
.query-result-container {
  margin-top: 0.75rem;
  border-radius: 0.5rem;
  border: 1px solid #e5e7eb;
  background: white;
  overflow: hidden;
}

.loading-state,
.error-state,
.empty-state {
  display: flex;
  align-items: center;
  padding: 1rem;
  justify-content: center;
}

.result-wrapper {
  display: flex;
  flex-direction: column;
}

.result-header {
  padding: 0.75rem 1rem;
  background: #f9fafb;
  border-bottom: 1px solid #e5e7eb;
}

.result-info {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.table-container {
  overflow-x: auto;
  max-height: 400px;
  overflow-y: auto;
}

.result-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.875rem;
}

.table-header {
  position: sticky;
  top: 0;
  background: #f3f4f6;
  padding: 0.5rem 0.75rem;
  text-align: left;
  font-weight: 600;
  color: #374151;
  border-bottom: 1px solid #d1d5db;
  white-space: nowrap;
  z-index: 1;
}

.table-row {
  border-bottom: 1px solid #e5e7eb;
  transition: background-color 0.15s ease;
}

.table-row:hover {
  background: #f9fafb;
}

.table-row:last-child {
  border-bottom: none;
}

.table-cell {
  padding: 0.5rem 0.75rem;
  color: #4b5563;
  max-width: 300px;
}

.cell-content {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.table-cell:hover .cell-content {
  white-space: normal;
  word-break: break-all;
}

@keyframes spin {
  0% {
    transform: rotate(0deg);
  }
  100% {
    transform: rotate(360deg);
  }
}

.animate-spin {
  animation: spin 1s linear infinite;
}
</style>
