<template>
  <div class="tool-call-card" :class="{ 'is-expanded': isExpanded, 'has-error': hasError }">
    <!-- Header -->
    <div class="tool-header" @click="toggleExpand">
      <div class="tool-icon">
        <svg v-if="!hasError" class="icon-tool" viewBox="0 0 24 24" fill="none" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
        </svg>
        <svg v-else class="icon-error" viewBox="0 0 24 24" fill="none" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      </div>

      <div class="tool-info">
        <div class="tool-name">{{ toolName }}</div>
        <div class="tool-status">{{ statusText }}</div>
      </div>

      <div class="expand-icon" :class="{ 'is-rotated': isExpanded }">
        <svg class="icon-chevron" viewBox="0 0 24 24" fill="none" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
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
  if (hasError.value) return '执行失败'
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
  border: 1px solid #e3d5c3;
  border-radius: 12px;
  background: #fefbf7;
  overflow: hidden;
  transition: all 0.2s ease;
}

.tool-call-card:hover {
  border-color: #d4c4b0;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

.tool-call-card.has-error {
  border-color: #f5c2c7;
  background: #fef5f6;
}

.tool-header {
  display: flex;
  align-items: center;
  padding: 12px 16px;
  cursor: pointer;
  user-select: none;
  gap: 12px;
}

.tool-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: 8px;
  background: linear-gradient(135deg, #e8dccb 0%, #f0e4d7 100%);
  flex-shrink: 0;
}

.has-error .tool-icon {
  background: linear-gradient(135deg, #f5c2c7 0%, #f8d7da 100%);
}

.icon-tool,
.icon-error {
  width: 18px;
  height: 18px;
  color: #8b7355;
}

.has-error .icon-error {
  color: #c23934;
}

.tool-info {
  flex: 1;
  min-width: 0;
}

.tool-name {
  font-size: 14px;
  font-weight: 600;
  color: #3d3430;
  margin-bottom: 2px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.tool-status {
  font-size: 12px;
  color: #8b7355;
}

.has-error .tool-status {
  color: #c23934;
}

.expand-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  transition: transform 0.2s ease;
}

.expand-icon.is-rotated {
  transform: rotate(180deg);
}

.icon-chevron {
  width: 16px;
  height: 16px;
  color: #998875;
}

.tool-details {
  border-top: 1px solid #f0e4d7;
  padding: 16px;
  background: #fcf9f5;
}

.detail-section {
  margin-bottom: 16px;
}

.detail-section:last-child {
  margin-bottom: 0;
}

.section-title {
  font-size: 12px;
  font-weight: 600;
  color: #6d5d4f;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 8px;
}

.code-block {
  border: 1px solid #e8dccb;
  border-radius: 8px;
  background: white;
  padding: 12px;
  overflow-x: auto;
}

.code-block.is-error {
  border-color: #f5c2c7;
  background: #fefefe;
}

.code-block pre {
  margin: 0;
  font-family: 'Monaco', 'Menlo', 'Courier New', monospace;
  font-size: 12px;
  line-height: 1.5;
  color: #2d2520;
  white-space: pre-wrap;
  word-break: break-word;
}

.code-block.is-error pre {
  color: #c23934;
}

/* Expand transition */
.expand-enter-active,
.expand-leave-active {
  transition: all 0.3s ease;
  max-height: 1000px;
  overflow: hidden;
}

.expand-enter-from,
.expand-leave-to {
  max-height: 0;
  opacity: 0;
}
</style>
