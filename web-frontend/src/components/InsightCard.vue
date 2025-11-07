<template>
  <div class="insight-card-container">
    <div
      v-for="(insight, index) in insights"
      :key="index"
      class="insight-card"
      :class="getSeverityClass(insight.severity)"
    >
      <div class="insight-header">
        <span class="insight-icon">{{ insight.icon || getDefaultIcon(insight.type) }}</span>
        <span class="insight-type">{{ getTypeName(insight.type) }}</span>
        <span class="insight-severity" :class="`severity-${insight.severity || 'low'}`">
          {{ getSeverityName(insight.severity) }}
        </span>
      </div>
      <div class="insight-content">
        {{ insight.content }}
      </div>
      <div v-if="insight.metadata && showMetadata" class="insight-metadata">
        <details>
          <summary class="metadata-summary">详细数据</summary>
          <pre class="metadata-content">{{ JSON.stringify(insight.metadata, null, 2) }}</pre>
        </details>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
interface Insight {
  type: string
  severity: string
  content: string
  icon?: string
  metadata?: any
}

interface Props {
  insights: Insight[]
  showMetadata?: boolean
}

withDefaults(defineProps<Props>(), {
  showMetadata: false
})

function getTypeName(type: string): string {
  const typeNames: Record<string, string> = {
    trend: '趋势',
    anomaly: '异常',
    comparison: '对比',
    proportion: '占比'
  }
  return typeNames[type] || '洞察'
}

function getSeverityName(severity: string): string {
  const severityNames: Record<string, string> = {
    high: '高',
    medium: '中',
    low: '低'
  }
  return severityNames[severity] || ''
}

function getDefaultIcon(type: string): string {
  const icons: Record<string, string> = {
    trend: '📈',
    anomaly: '⚠️',
    comparison: '📊',
    proportion: '🎯'
  }
  return icons[type] || '💡'
}

function getSeverityClass(severity: string): string {
  return `severity-${severity || 'low'}`
}
</script>

<style scoped>
.insight-card-container {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  margin: 1rem 0;
}

.insight-card {
  padding: 1rem;
  border-radius: 8px;
  border-left: 4px solid;
  background: white;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  transition: all 0.2s;
}

.insight-card:hover {
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.15);
  transform: translateY(-1px);
}

.insight-card.severity-high {
  border-left-color: #ef4444;
  background: #fef2f2;
}

.insight-card.severity-medium {
  border-left-color: #f59e0b;
  background: #fffbeb;
}

.insight-card.severity-low {
  border-left-color: #3b82f6;
  background: #eff6ff;
}

.insight-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
  font-size: 0.875rem;
  font-weight: 600;
}

.insight-icon {
  font-size: 1.25rem;
}

.insight-type {
  color: #374151;
}

.insight-severity {
  margin-left: auto;
  padding: 0.125rem 0.5rem;
  border-radius: 9999px;
  font-size: 0.75rem;
  font-weight: 500;
}

.insight-severity.severity-high {
  background: #fee2e2;
  color: #b91c1c;
}

.insight-severity.severity-medium {
  background: #fef3c7;
  color: #b45309;
}

.insight-severity.severity-low {
  background: #dbeafe;
  color: #1e40af;
}

.insight-content {
  color: #1f2937;
  line-height: 1.5;
  font-size: 0.9375rem;
}

.insight-metadata {
  margin-top: 0.75rem;
  padding-top: 0.75rem;
  border-top: 1px solid #e5e7eb;
}

.metadata-summary {
  cursor: pointer;
  font-size: 0.875rem;
  color: #6b7280;
  user-select: none;
}

.metadata-summary:hover {
  color: #374151;
}

.metadata-content {
  margin-top: 0.5rem;
  padding: 0.75rem;
  background: #f9fafb;
  border-radius: 4px;
  font-size: 0.8125rem;
  color: #4b5563;
  overflow-x: auto;
}
</style>
