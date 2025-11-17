<template>
  <div v-if="showUsage" class="token-usage-card">
    <div class="usage-header">
      <div class="header-left">
        <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
        </svg>
        <span class="title">Token 使用统计</span>
      </div>
      <button
        type="button"
        class="collapse-btn"
        @click="isCollapsed = !isCollapsed"
        :title="isCollapsed ? '展开' : '收起'"
      >
        <svg
          class="w-4 h-4 transition-transform"
          :class="{ 'rotate-180': !isCollapsed }"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
        >
          <path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7" />
        </svg>
      </button>
    </div>

    <div v-show="!isCollapsed" class="usage-body">
      <!-- 总体统计 -->
      <div class="usage-section">
        <div class="section-title">本次会话</div>
        <div class="stats-grid">
          <div class="stat-item">
            <div class="stat-label">输入</div>
            <div class="stat-value text-blue-600">
              {{ formatNumber(usage.total_input_tokens) }}
            </div>
            <div class="stat-unit">tokens</div>
          </div>
          <div class="stat-item">
            <div class="stat-label">输出</div>
            <div class="stat-value text-green-600">
              {{ formatNumber(usage.total_output_tokens) }}
            </div>
            <div class="stat-unit">tokens</div>
          </div>
          <div class="stat-item highlight">
            <div class="stat-label">总计</div>
            <div class="stat-value text-purple-600">
              {{ formatNumber(usage.total_tokens) }}
            </div>
            <div class="stat-unit">tokens</div>
          </div>
        </div>
      </div>

      <!-- 缓存统计 (如果有) -->
      <div
        v-if="usage.cache_read_input_tokens > 0 || usage.cache_creation_input_tokens > 0"
        class="usage-section"
      >
        <div class="section-title">缓存优化</div>
        <div class="stats-grid">
          <div v-if="usage.cache_read_input_tokens > 0" class="stat-item">
            <div class="stat-label">缓存命中</div>
            <div class="stat-value text-emerald-600">
              {{ formatNumber(usage.cache_read_input_tokens) }}
            </div>
            <div class="stat-unit">tokens</div>
          </div>
          <div v-if="usage.cache_creation_input_tokens > 0" class="stat-item">
            <div class="stat-label">缓存创建</div>
            <div class="stat-value text-amber-600">
              {{ formatNumber(usage.cache_creation_input_tokens) }}
            </div>
            <div class="stat-unit">tokens</div>
          </div>
        </div>
        <div v-if="savingsPercentage > 0" class="savings-info">
          <svg class="w-4 h-4 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
          </svg>
          <span>节省约 {{ savingsPercentage.toFixed(1) }}% 成本</span>
        </div>
      </div>

      <!-- 执行统计 -->
      <div class="usage-section">
        <div class="section-title">执行统计</div>
        <div class="stats-row">
          <div class="stat-pill">
            <span class="pill-label">迭代次数:</span>
            <span class="pill-value">{{ usage.iterations }}</span>
          </div>
          <div class="stat-pill">
            <span class="pill-label">工具调用:</span>
            <span class="pill-value">{{ usage.tool_calls_count }}</span>
          </div>
        </div>
      </div>

      <!-- 成本估算 (可选) -->
      <div v-if="estimatedCost > 0" class="usage-section">
        <div class="section-title">成本估算</div>
        <div class="cost-info">
          <span class="cost-label">本次会话:</span>
          <span class="cost-value">¥{{ estimatedCost.toFixed(4) }}</span>
        </div>
        <div class="cost-note">
          * 基于 Claude Sonnet 定价估算
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import type { ConversationTokenUsage } from '@/stores/chat'

const props = defineProps<{
  usage: ConversationTokenUsage
}>()

const isCollapsed = ref(false)

const showUsage = computed(() => props.usage.total_tokens > 0)

const formatNumber = (num: number): string => {
  return num.toLocaleString('zh-CN')
}

// 计算缓存节省比例
const savingsPercentage = computed(() => {
  const cacheRead = props.usage.cache_read_input_tokens || 0
  const totalInput = props.usage.total_input_tokens || 0
  if (totalInput === 0) return 0
  // 缓存读取通常节省 90% 的成本
  return (cacheRead / totalInput) * 90
})

// 成本估算 (Claude Sonnet 4.5 官方定价: 输入 $3/M tokens, 输出 $15/M tokens)
const estimatedCost = computed(() => {
  const exchangeRate = 7.3 // 美元转人民币汇率

  // 计算常规输入 tokens (排除缓存)
  const regularInputTokens = props.usage.total_input_tokens -
    (props.usage.cache_creation_input_tokens || 0) -
    (props.usage.cache_read_input_tokens || 0)

  // 常规输入成本 ($3/M)
  const regularInputCost = (regularInputTokens / 1_000_000) * 3 * exchangeRate

  // 输出成本 ($15/M)
  const outputCost = (props.usage.total_output_tokens / 1_000_000) * 15 * exchangeRate

  // 缓存读取成本 ($0.30/M - 节省90%)
  const cacheReadCost = ((props.usage.cache_read_input_tokens || 0) / 1_000_000) * 0.30 * exchangeRate

  // 缓存创建成本 ($3.75/M - 标准价格的125%)
  const cacheCreationCost = ((props.usage.cache_creation_input_tokens || 0) / 1_000_000) * 3.75 * exchangeRate

  return regularInputCost + outputCost + cacheReadCost + cacheCreationCost
})
</script>

<style scoped>
.token-usage-card {
  margin: 1rem 0;
  border: 1px solid #e5e7eb;
  border-radius: 0.75rem;
  background: linear-gradient(to bottom, #fafbfc, #ffffff);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  overflow: hidden;
}

.usage-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.875rem 1rem;
  background: #f9fafb;
  border-bottom: 1px solid #e5e7eb;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.icon {
  width: 1.125rem;
  height: 1.125rem;
  color: #6b7280;
}

.title {
  font-size: 0.875rem;
  font-weight: 600;
  color: #374151;
}

.collapse-btn {
  padding: 0.25rem;
  color: #6b7280;
  border-radius: 0.375rem;
  transition: all 0.15s ease;
  background: transparent;
  border: none;
  cursor: pointer;
}

.collapse-btn:hover {
  color: #374151;
  background: #e5e7eb;
}

.usage-body {
  padding: 1rem;
}

.usage-section {
  margin-bottom: 1rem;
}

.usage-section:last-child {
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

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(100px, 1fr));
  gap: 0.75rem;
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 0.75rem;
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 0.5rem;
  transition: all 0.15s ease;
}

.stat-item:hover {
  border-color: #d1d5db;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.stat-item.highlight {
  background: linear-gradient(135deg, #faf5ff 0%, #f3e8ff 100%);
  border-color: #e9d5ff;
}

.stat-label {
  font-size: 0.75rem;
  color: #6b7280;
  margin-bottom: 0.25rem;
}

.stat-value {
  font-size: 1.25rem;
  font-weight: 700;
  margin-bottom: 0.125rem;
}

.stat-unit {
  font-size: 0.625rem;
  color: #9ca3af;
  text-transform: uppercase;
}

.stats-row {
  display: flex;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.stat-pill {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
  padding: 0.5rem 0.75rem;
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 9999px;
  font-size: 0.8125rem;
}

.pill-label {
  color: #6b7280;
}

.pill-value {
  font-weight: 600;
  color: #374151;
}

.savings-info {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  margin-top: 0.5rem;
  padding: 0.5rem 0.75rem;
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  border-radius: 0.5rem;
  font-size: 0.8125rem;
  color: #166534;
  font-weight: 500;
}

.cost-info {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.75rem;
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 0.5rem;
}

.cost-label {
  font-size: 0.875rem;
  color: #6b7280;
}

.cost-value {
  font-size: 1.125rem;
  font-weight: 700;
  color: #7c3aed;
}

.cost-note {
  margin-top: 0.5rem;
  font-size: 0.75rem;
  color: #9ca3af;
  text-align: right;
}

.rotate-180 {
  transform: rotate(180deg);
}
</style>
