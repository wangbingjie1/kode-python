<!-- Token 成本卡片 - 开发者模式 -->
<template>
  <div v-if="showCost" class="token-cost-card">
    <div class="card-header">
      <h3>💰 真实成本分析</h3>
      <button @click="toggleExpand" class="expand-btn">
        {{ expanded ? '收起' : '展开' }}
      </button>
    </div>

    <div v-if="expanded" class="card-body">
      <!-- Token 统计 -->
      <div class="section">
        <h4>📊 Token 统计</h4>
        <table class="cost-table">
          <thead>
            <tr>
              <th>类型</th>
              <th>数量</th>
              <th>单价</th>
              <th>成本</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>常规输入</td>
              <td>{{ formatNumber(regularInputTokens) }}</td>
              <td>$3.00/MTok</td>
              <td>${{ regularInputCost.toFixed(6) }}</td>
            </tr>
            <tr class="cache-creation">
              <td>缓存创建</td>
              <td>{{ formatNumber(cacheCreationTokens) }}</td>
              <td>$3.75/MTok (1.25×)</td>
              <td>${{ cacheCreationCost.toFixed(6) }}</td>
            </tr>
            <tr class="cache-read">
              <td>缓存读取</td>
              <td>{{ formatNumber(cacheReadTokens) }}</td>
              <td>$0.30/MTok (节省90%)</td>
              <td>${{ cacheReadCost.toFixed(6) }}</td>
            </tr>
            <tr class="output">
              <td>输出生成</td>
              <td>{{ formatNumber(outputTokens) }}</td>
              <td>$15.00/MTok</td>
              <td>${{ outputCost.toFixed(6) }}</td>
            </tr>
            <tr class="total">
              <td><strong>总计</strong></td>
              <td><strong>{{ formatNumber(totalTokens) }}</strong></td>
              <td>-</td>
              <td><strong>${{ actualCost.toFixed(6) }}</strong></td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- 成本对比 -->
      <div class="section cost-comparison">
        <h4>💸 成本对比</h4>
        <div class="comparison-row">
          <span class="label">实际成本:</span>
          <span class="value actual">${{ actualCost.toFixed(6) }}</span>
        </div>
        <div class="comparison-row">
          <span class="label">无缓存成本:</span>
          <span class="value no-cache">${{ noCacheCost.toFixed(6) }}</span>
        </div>
        <div class="comparison-row savings">
          <span class="label">节省:</span>
          <span class="value">
            ${{ costSavings.toFixed(6) }} ({{ savingsPercentage.toFixed(1) }}%)
          </span>
        </div>
      </div>

      <!-- 用户配额 -->
      <div class="section quota-info">
        <h4>📦 用户配额扣除</h4>
        <p class="quota-explanation">
          用户配额按简化模式计算：<strong>{{ formatNumber(billingTokens) }} tokens</strong>
        </p>
        <p class="quota-note">
          （仅计算输入+输出，缓存优化不影响用户配额）
        </p>
      </div>

      <!-- 优化建议 -->
      <div v-if="savingsPercentage > 20" class="section optimization">
        <h4>✨ 优化效果</h4>
        <p class="optimization-message success">
          🎉 缓存优化效果显著！节省了 {{ savingsPercentage.toFixed(1) }}% 的成本。
        </p>
      </div>
      <div v-else-if="cacheCreationTokens > 0" class="section optimization">
        <h4>💡 优化建议</h4>
        <p class="optimization-message warning">
          ⚠️ 首次请求创建了缓存（成本 1.25×），后续请求将显著降低成本。
        </p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import type { ConversationTokenUsage } from '@/stores/chat'

interface Props {
  usage: ConversationTokenUsage
  showCost?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  showCost: true // 开发模式默认显示
})

const expanded = ref(false)

const toggleExpand = () => {
  expanded.value = !expanded.value
}

// Token 数量
const regularInputTokens = computed(() => {
  return props.usage.total_input_tokens - props.usage.cache_creation_input_tokens - props.usage.cache_read_input_tokens
})

const cacheCreationTokens = computed(() => props.usage.cache_creation_input_tokens)
const cacheReadTokens = computed(() => props.usage.cache_read_input_tokens)
const outputTokens = computed(() => props.usage.total_output_tokens)
const totalTokens = computed(() => props.usage.total_tokens)

// 成本计算（Anthropic 定价，< 200K tokens）
const regularInputCost = computed(() => regularInputTokens.value * 3 / 1_000_000)
const cacheCreationCost = computed(() => cacheCreationTokens.value * 3.75 / 1_000_000)
const cacheReadCost = computed(() => cacheReadTokens.value * 0.30 / 1_000_000)
const outputCost = computed(() => outputTokens.value * 15 / 1_000_000)

const actualCost = computed(() => {
  return regularInputCost.value + cacheCreationCost.value + cacheReadCost.value + outputCost.value
})

// 无缓存的成本（对比）
const noCacheCost = computed(() => {
  const inputCost = (regularInputTokens.value + cacheCreationTokens.value + cacheReadTokens.value) * 3 / 1_000_000
  return inputCost + outputCost.value
})

// 节省的成本和百分比
const costSavings = computed(() => noCacheCost.value - actualCost.value)
const savingsPercentage = computed(() => {
  if (noCacheCost.value === 0) return 0
  return (costSavings.value / noCacheCost.value) * 100
})

// 用户配额扣除（简化计费）
const billingTokens = computed(() => props.usage.total_input_tokens + props.usage.total_output_tokens)

const formatNumber = (num: number) => {
  return num.toLocaleString('zh-CN')
}
</script>

<style scoped>
.token-cost-card {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 12px;
  padding: 20px;
  color: white;
  margin: 20px 0;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.card-header h3 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
}

.expand-btn {
  background: rgba(255, 255, 255, 0.2);
  border: 1px solid rgba(255, 255, 255, 0.3);
  color: white;
  padding: 6px 16px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.2s;
}

.expand-btn:hover {
  background: rgba(255, 255, 255, 0.3);
  transform: translateY(-1px);
}

.card-body {
  animation: slideDown 0.3s ease-out;
}

@keyframes slideDown {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.section {
  margin-bottom: 24px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  padding: 16px;
  backdrop-filter: blur(10px);
}

.section h4 {
  margin: 0 0 12px 0;
  font-size: 16px;
  font-weight: 600;
  opacity: 0.9;
}

.cost-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;
}

.cost-table th,
.cost-table td {
  padding: 8px 12px;
  text-align: left;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.cost-table thead th {
  font-weight: 600;
  opacity: 0.8;
  font-size: 13px;
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

.cost-table .total {
  font-weight: 600;
  background: rgba(255, 255, 255, 0.15);
}

.cost-comparison {
  font-size: 15px;
}

.comparison-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.comparison-row:last-child {
  border-bottom: none;
}

.comparison-row.savings {
  font-weight: 600;
  font-size: 16px;
  margin-top: 8px;
  background: rgba(76, 175, 80, 0.2);
  padding: 12px;
  border-radius: 6px;
  border: 1px solid rgba(76, 175, 80, 0.3);
}

.comparison-row .label {
  opacity: 0.9;
}

.comparison-row .value {
  font-weight: 600;
  font-family: 'Courier New', monospace;
}

.comparison-row .value.actual {
  color: #81c784;
}

.comparison-row .value.no-cache {
  color: #ffb74d;
  text-decoration: line-through;
  opacity: 0.7;
}

.quota-info p {
  margin: 8px 0;
  font-size: 14px;
  line-height: 1.6;
}

.quota-explanation {
  font-weight: 500;
}

.quota-note {
  opacity: 0.7;
  font-size: 13px;
}

.optimization {
  background: linear-gradient(135deg, rgba(76, 175, 80, 0.2) 0%, rgba(56, 142, 60, 0.2) 100%);
  border: 1px solid rgba(76, 175, 80, 0.3);
}

.optimization-message {
  margin: 0;
  font-size: 14px;
  line-height: 1.6;
}

.optimization-message.success {
  color: #c8e6c9;
}

.optimization-message.warning {
  color: #fff9c4;
}

/* 响应式 */
@media (max-width: 768px) {
  .token-cost-card {
    padding: 16px;
  }

  .cost-table {
    font-size: 12px;
  }

  .cost-table th,
  .cost-table td {
    padding: 6px 8px;
  }
}
</style>
