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

        <!-- Result or Error -->
        <div v-if="toolResult || toolError" class="detail-section">
          <div class="section-title">{{ hasError ? '错误信息' : '执行结果' }}</div>
          <div class="code-block" :class="{ 'is-error': hasError }">
            <pre>{{ toolResult || toolError }}</pre>
          </div>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'

interface ToolCallProps {
  toolName: string
  toolArgs?: Record<string, any>
  toolResult?: string
  toolError?: string
  status?: string
}

const props = defineProps<ToolCallProps>()

const isExpanded = ref(false)

const hasError = computed(() => !!props.toolError)

const statusText = computed(() => {
  if (hasError.value || props.status === 'error') return '执行失败'
  if (props.status === 'completed') return '执行成功'
  if (props.status === 'started') return '执行中...'
  return '已完成'
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
