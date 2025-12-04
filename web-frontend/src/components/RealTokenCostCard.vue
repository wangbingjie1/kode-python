<template>
  <div v-if="showCost" class="real-cost-card">
    <div class="card-header">
      <div class="header-left">
        <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <span class="title">真实成本分析</span>
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

    <div v-if="!isCollapsed" class="card-body">
      <!-- 总览统计 -->
      <div class="section summary">
        <div class="stats-grid">
          <div class="stat-item">
            <div class="stat-label">迭代次数</div>
            <div class="stat-value">{{ stats.iterations }}</div>
          </div>
          <div class="stat-item">
            <div class="stat-label">总 Tokens</div>
            <div class="stat-value">{{ formatNumber(stats.total) }}</div>
          </div>
          <div class="stat-item highlight">
            <div class="stat-label">总成本</div>
            <div class="stat-value cost">${{ stats.totalCost.toFixed(6) }}</div>
            <div class="stat-sublabel">¥{{ (stats.totalCost * 7.3).toFixed(4) }}</div>
          </div>
          <div class="stat-item savings" v-if="stats.totalSavings > 0">
            <div class="stat-label">缓存节省</div>
            <div class="stat-value success">${{ stats.totalSavings.toFixed(6) }}</div>
            <div class="stat-sublabel">约 {{ savingsPercentage }}% 成本</div>
          </div>
        </div>
      </div>

      <!-- Token 详细统计 -->
      <div class="section">
        <h4 class="section-title">Token 使用详情</h4>
        <table class="cost-table">
          <thead>
            <tr>
              <th>类型</th>
              <th>数量</th>
              <th>单价</th>
              <th>成本 (USD)</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>常规输入</td>
              <td>{{ formatNumber(stats.regularInput) }}</td>
              <td>$3.00/MTok</td>
              <td>${{ stats.regularInputCost.toFixed(6) }}</td>
            </tr>
            <tr class="cache-creation">
              <td>缓存创建</td>
              <td>{{ formatNumber(stats.cacheCreation) }}</td>
              <td>$3.75/MTok (1.25×)</td>
              <td>${{ stats.cacheCreationCost.toFixed(6) }}</td>
            </tr>
            <tr class="cache-read">
              <td>缓存读取</td>
              <td>{{ formatNumber(stats.cacheRead) }}</td>
              <td>$0.30/MTok (节省90%)</td>
              <td>${{ stats.cacheReadCost.toFixed(6) }}</td>
            </tr>
            <tr class="output">
              <td>输出生成</td>
              <td>{{ formatNumber(stats.output) }}</td>
              <td>$15.00/MTok</td>
              <td>${{ stats.outputCost.toFixed(6) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useChatStore } from '@/stores/chat'

interface Props {
  showDetails?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  showDetails: false
})

const chatStore = useChatStore()

const isCollapsed = ref(false)

// ✅ 直接使用 chat store 的实时数据（来自 SSE 流）
const tokenUsage = computed(() => chatStore.conversationTokenUsage)
const showCost = computed(() =>
  tokenUsage.value.total_tokens > 0 ||
  tokenUsage.value.total_input_tokens > 0
)

// ✅ 使用 SSE 实时数据计算统计
const stats = computed(() => {
  const usage = tokenUsage.value

  // 计算常规输入：从 total_input_tokens 减去缓存部分
  // ⚠️ 注意：后端的 total_input_tokens 已经是完整计数（包含所有输入）
  const regularInput = usage.total_input_tokens -
                      (usage.cache_creation_input_tokens || 0) -
                      (usage.cache_read_input_tokens || 0)
  const cacheCreation = usage.cache_creation_input_tokens || 0
  const cacheRead = usage.cache_read_input_tokens || 0
  const output = usage.total_output_tokens || 0

  // 成本计算（Anthropic 定价）
  const regularInputCost = regularInput * 3 / 1_000_000
  const cacheCreationCost = cacheCreation * 3.75 / 1_000_000
  const cacheReadCost = cacheRead * 0.30 / 1_000_000
  const outputCost = output * 15 / 1_000_000
  const totalCost = regularInputCost + cacheCreationCost + cacheReadCost + outputCost

  // 无缓存成本对比
  const noCacheCost = usage.total_input_tokens * 3 / 1_000_000 + outputCost
  const totalSavings = noCacheCost - totalCost

  return {
    regularInput,
    cacheCreation,
    cacheRead,
    output,
    totalInput: usage.total_input_tokens,
    totalOutput: output,
    total: usage.total_tokens,
    regularInputCost,
    cacheCreationCost,
    cacheReadCost,
    outputCost,
    totalCost,
    totalSavings,
    noCacheCost,
    iterations: usage.iterations || 0
  }
})

const savingsPercentage = computed(() => {
  if (stats.value.noCacheCost === 0) return '0.0'
  const percentage = (stats.value.totalSavings / stats.value.noCacheCost) * 100
  return percentage.toFixed(1)
})

const formatNumber = (num: number): string => {
  return num.toLocaleString('zh-CN')
}
</script>

<style scoped>
.real-cost-card {
  margin: 1rem 0;
  border: 1px solid #e0d4f7;
  border-radius: 0.75rem;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  overflow: hidden;
  color: white;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem 1.25rem;
  background: rgba(0, 0, 0, 0.1);
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.icon {
  width: 1.25rem;
  height: 1.25rem;
}

.title {
  font-size: 0.9375rem;
  font-weight: 600;
}

.collapse-btn {
  padding: 0.25rem;
  color: rgba(255, 255, 255, 0.8);
  border-radius: 0.375rem;
  transition: all 0.15s ease;
  background: transparent;
  border: none;
  cursor: pointer;
}

.collapse-btn:hover {
  color: white;
  background: rgba(255, 255, 255, 0.1);
}

.rotate-180 {
  transform: rotate(180deg);
}

.loading-state,
.error-state {
  padding: 2rem;
  text-align: center;
}

.spinner {
  width: 2rem;
  height: 2rem;
  border: 3px solid rgba(255, 255, 255, 0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
  margin: 0 auto 0.5rem;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.card-body {
  padding: 1.25rem;
}

.section {
  margin-bottom: 1.25rem;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 0.5rem;
  padding: 1rem;
  backdrop-filter: blur(10px);
}

.section:last-child {
  margin-bottom: 0;
}

.section.summary {
  background: rgba(255, 255, 255, 0.15);
}

.section-title {
  font-size: 0.875rem;
  font-weight: 600;
  margin: 0 0 0.75rem 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: 0.75rem;
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 0.875rem;
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: 0.5rem;
  transition: all 0.15s ease;
}

.stat-item:hover {
  background: rgba(255, 255, 255, 0.15);
  transform: translateY(-2px);
}

.stat-item.highlight {
  background: rgba(255, 193, 7, 0.2);
  border-color: rgba(255, 193, 7, 0.4);
}

.stat-item.savings {
  background: rgba(76, 175, 80, 0.2);
  border-color: rgba(76, 175, 80, 0.4);
}

.stat-label {
  font-size: 0.75rem;
  opacity: 0.9;
  margin-bottom: 0.375rem;
}

.stat-value {
  font-size: 1.375rem;
  font-weight: 700;
  margin-bottom: 0.125rem;
}

.stat-value.cost {
  color: #ffd740;
}

.stat-value.success {
  color: #81c784;
}

.stat-sublabel {
  font-size: 0.6875rem;
  opacity: 0.7;
}

.cost-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.8125rem;
}

.cost-table th,
.cost-table td {
  padding: 0.625rem;
  text-align: left;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.cost-table thead th {
  font-weight: 600;
  opacity: 0.8;
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.cost-table tbody tr:last-child td {
  border-bottom: none;
}

.cost-table .cache-creation {
  background: rgba(255, 193, 7, 0.1);
}

.cost-table .cache-read {
  background: rgba(76, 175, 80, 0.1);
}

.cost-table .output {
  background: rgba(33, 150, 243, 0.1);
}

.toggle-details-btn {
  padding: 0.25rem 0.75rem;
  background: rgba(255, 255, 255, 0.15);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 0.375rem;
  color: white;
  font-size: 0.75rem;
  cursor: pointer;
  transition: all 0.15s;
}

.toggle-details-btn:hover {
  background: rgba(255, 255, 255, 0.25);
}

.traces-list {
  margin-top: 0.75rem;
}

.trace-item {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 0.375rem;
  padding: 0.75rem;
  margin-bottom: 0.5rem;
}

.trace-item:last-child {
  margin-bottom: 0;
}

.trace-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.5rem;
  font-size: 0.8125rem;
}

.trace-iteration {
  font-weight: 600;
  color: #ffd740;
}

.trace-model {
  opacity: 0.7;
  font-size: 0.75rem;
}

.trace-cost {
  font-weight: 600;
  font-family: 'Courier New', monospace;
}

.trace-stats {
  display: flex;
  gap: 1rem;
  font-size: 0.75rem;
  opacity: 0.8;
}

@media (max-width: 768px) {
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .cost-table {
    font-size: 0.75rem;
  }

  .cost-table th,
  .cost-table td {
    padding: 0.5rem 0.375rem;
  }
}
</style>
