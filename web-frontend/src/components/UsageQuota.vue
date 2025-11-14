<template>
  <div class="usage-quota" v-if="usageSummary">
    <div class="quota-header">
      <h4>Token 用量（按 Token 计费）</h4>
      <span class="plan-badge">{{ currentPlan?.display_name || '未订阅' }}</span>
    </div>

    <div class="quota-items">
      <!-- Token 使用量（主要计费指标）-->
      <div class="quota-item">
        <div class="quota-label">
          <span><strong>Token 额度</strong></span>
          <span class="quota-text">{{ formatNumber(usageSummary.token_used) }} / {{ formatNumber(usageSummary.token_quota) }}</span>
        </div>
        <div class="progress-bar">
          <div class="progress-fill" :style="{ width: `${tokenPercentage}%`, backgroundColor: getProgressColor(tokenPercentage) }"></div>
        </div>
        <div class="quota-hint">本周期剩余：{{ formatNumber(usageSummary.token_remaining) }} tokens</div>
      </div>

      <!-- 消息使用量（仅统计）-->
      <div class="quota-item stats-only">
        <div class="quota-label">
          <span class="stats-label">消息数（仅统计）</span>
          <span class="quota-text-secondary">{{ usageSummary.message_used }} 条</span>
        </div>
      </div>
    </div>

    <div v-if="isQuotaExceeded" class="quota-warning">
      <svg class="warning-icon" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
      </svg>
      <span>Token 配额已用尽，请升级套餐</span>
      <router-link to="/billing" class="upgrade-link">立即升级</router-link>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useBillingStore } from '@/stores/billing'

const billingStore = useBillingStore()

const usageSummary = computed(() => billingStore.usageSummary)
const currentPlan = computed(() => billingStore.currentPlan)
const isQuotaExceeded = computed(() => billingStore.isQuotaExceeded)
const tokenPercentage = computed(() => billingStore.tokenUsagePercentage)

function formatNumber(num: number): string {
  if (num >= 1000000) {
    return `${(num / 1000000).toFixed(1)}M`
  }
  if (num >= 1000) {
    return `${(num / 1000).toFixed(1)}K`
  }
  return num.toString()
}

function getProgressColor(percentage: number): string {
  if (percentage >= 90) return '#ef4444'
  if (percentage >= 70) return '#f59e0b'
  return '#10b981'
}
</script>

<style scoped>
.usage-quota {
  background: rgba(255, 255, 255, 0.8);
  border: 1px solid #eadfd3;
  border-radius: 0.75rem;
  padding: 1rem;
  box-shadow: 0 8px 20px rgba(190, 160, 130, 0.1);
}

.quota-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.quota-header h4 {
  font-size: 0.813rem;
  font-weight: 600;
  color: #362e27;
  margin: 0;
}

.plan-badge {
  background: linear-gradient(135deg, #f26b3a, #e0582a);
  color: white;
  padding: 0.25rem 0.75rem;
  border-radius: 9999px;
  font-size: 0.688rem;
  font-weight: 600;
  box-shadow: 0 4px 12px rgba(242, 107, 58, 0.2);
}

.quota-items {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.quota-item {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.quota-label {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.813rem;
  color: #78695c;
}

.quota-text {
  font-weight: 600;
  color: #362e27;
}

.progress-bar {
  height: 0.5rem;
  background: rgba(234, 223, 211, 0.5);
  border-radius: 9999px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  transition: width 0.3s ease, background-color 0.3s ease;
}

.quota-warning {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: 0.75rem;
  padding: 0.75rem;
  margin-top: 1rem;
  font-size: 0.813rem;
  color: #991b1b;
}

.warning-icon {
  width: 1.25rem;
  height: 1.25rem;
  flex-shrink: 0;
}

.upgrade-link {
  margin-left: auto;
  color: #2563eb;
  font-weight: 600;
  text-decoration: none;
}

.upgrade-link:hover {
  text-decoration: underline;
}

/* 新增样式 */
.quota-hint {
  font-size: 0.75rem;
  color: #78695c;
  margin-top: 0.25rem;
}

.stats-only {
  opacity: 0.7;
  border-top: 1px dashed #eadfd3;
  padding-top: 0.75rem;
}

.stats-label {
  font-size: 0.75rem;
  color: #78695c;
}

.quota-text-secondary {
  font-size: 0.75rem;
  color: #78695c;
}
</style>

