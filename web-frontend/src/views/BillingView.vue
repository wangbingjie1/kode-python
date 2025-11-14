<template>
  <div class="billing-view">
    <div class="billing-container">
      <h1>订阅管理</h1>

      <!-- 当前订阅状态 -->
      <div v-if="subscription" class="subscription-section">
        <h2>当前订阅</h2>
        <div class="subscription-card">
          <div class="subscription-info">
            <div class="subscription-plan">
              <h3>{{ subscription.plan?.display_name }}</h3>
              <span class="status-badge" :class="`status-${subscription.status}`">
                {{ getStatusText(subscription.status) }}
              </span>
            </div>
            <p class="subscription-period">
              有效期：{{ formatDate(subscription.start_date) }} - {{ formatDate(subscription.end_date) }}
            </p>
            <p v-if="subscription.auto_renew" class="auto-renew">
              ✓ 已开启自动续费
            </p>
          </div>
          <div class="subscription-actions">
            <button
              v-if="subscription.status === 'active'"
              class="btn-cancel"
              @click="handleCancelSubscription"
              :disabled="canceling"
            >
              {{ canceling ? '处理中...' : '取消订阅' }}
            </button>
          </div>
        </div>
      </div>

      <!-- 使用量统计 -->
      <div v-if="usageSummary" class="usage-section">
        <h2>使用量统计</h2>
        <div class="usage-cards">
          <div class="usage-card">
            <div class="usage-icon" style="background: #dbeafe; color: #3b82f6">
              <svg fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 8h10M7 12h4m1 8l-4-4H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-3l-4 4z" />
              </svg>
            </div>
            <div class="usage-details">
              <h4>Token 使用</h4>
              <p class="usage-value">{{ formatNumber(usageSummary.token_used) }} / {{ formatNumber(usageSummary.token_quota) }}</p>
              <div class="usage-bar">
                <div class="usage-fill" :style="{ width: `${tokenPercentage}%`, backgroundColor: getProgressColor(tokenPercentage) }"></div>
              </div>
            </div>
          </div>

          <!-- 纯 Token 计费，移除消息和对话统计 -->
        </div>
      </div>

      <!-- 套餐选择 -->
      <div class="plans-section">
        <h2>升级套餐</h2>
        <PricingPlans />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, computed, ref } from 'vue'
import { useBillingStore } from '@/stores/billing'
import PricingPlans from '@/components/PricingPlans.vue'

const billingStore = useBillingStore()

const subscription = computed(() => billingStore.subscription)
const usageSummary = computed(() => billingStore.usageSummary)
const tokenPercentage = computed(() => billingStore.tokenUsagePercentage)

const canceling = ref(false)

onMounted(async () => {
  await billingStore.refreshAll()
})

function formatDate(dateStr: string): string {
  const date = new Date(dateStr)
  return date.toLocaleDateString('zh-CN', { year: 'numeric', month: 'long', day: 'numeric' })
}

function formatNumber(num: number): string {
  if (num >= 1000000) {
    return `${(num / 1000000).toFixed(1)}M`
  }
  if (num >= 1000) {
    return `${(num / 1000).toFixed(1)}K`
  }
  return num.toString()
}

function getStatusText(status: string): string {
  const statusMap: Record<string, string> = {
    active: '激活',
    expired: '已过期',
    cancelled: '已取消',
    trial: '试用中'
  }
  return statusMap[status] || status
}

function getProgressColor(percentage: number): string {
  if (percentage >= 90) return '#ef4444'
  if (percentage >= 70) return '#f59e0b'
  return '#10b981'
}

async function handleCancelSubscription() {
  if (!confirm('确定要取消订阅吗？订阅将在当前计费周期结束后停止。')) {
    return
  }

  canceling.value = true
  try {
    await billingStore.cancelSubscription(false)
    alert('订阅已取消')
  } catch (err) {
    console.error('Cancel subscription failed:', err)
    alert('取消订阅失败，请稍后重试')
  } finally {
    canceling.value = false
  }
}
</script>

<style scoped>
.billing-view {
  height: 100vh;
  background: #f9fafb;
  overflow-y: auto;
  overflow-x: hidden;
}

.billing-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem;
}

h1 {
  font-size: 2rem;
  font-weight: bold;
  color: #1f2937;
  margin-bottom: 2rem;
}

h2 {
  font-size: 1.5rem;
  font-weight: 600;
  color: #374151;
  margin-bottom: 1rem;
}

.subscription-section,
.usage-section,
.plans-section {
  margin-bottom: 3rem;
}

.subscription-card {
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 0.75rem;
  padding: 2rem;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.subscription-info {
  flex: 1;
}

.subscription-plan {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 0.5rem;
}

.subscription-plan h3 {
  font-size: 1.25rem;
  font-weight: 600;
  color: #1f2937;
  margin: 0;
}

.status-badge {
  padding: 0.25rem 0.75rem;
  border-radius: 9999px;
  font-size: 0.875rem;
  font-weight: 600;
}

.status-active {
  background: #d1fae5;
  color: #065f46;
}

.status-expired,
.status-cancelled {
  background: #fee2e2;
  color: #991b1b;
}

.status-trial {
  background: #dbeafe;
  color: #1e40af;
}

.subscription-period,
.auto-renew {
  font-size: 0.875rem;
  color: #6b7280;
  margin: 0.25rem 0;
}

.auto-renew {
  color: #10b981;
  font-weight: 500;
}

.btn-cancel {
  padding: 0.5rem 1.5rem;
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 0.375rem;
  color: #ef4444;
  font-size: 0.875rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-cancel:hover:not(:disabled) {
  background: #fef2f2;
  border-color: #fecaca;
}

.btn-cancel:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.usage-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 1.5rem;
}

.usage-card {
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 0.75rem;
  padding: 1.5rem;
  display: flex;
  gap: 1rem;
}

.usage-icon {
  width: 3rem;
  height: 3rem;
  border-radius: 0.75rem;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.usage-icon svg {
  width: 1.5rem;
  height: 1.5rem;
}

.usage-details {
  flex: 1;
}

.usage-details h4 {
  font-size: 0.875rem;
  font-weight: 500;
  color: #6b7280;
  margin: 0 0 0.5rem;
}

.usage-value {
  font-size: 1.5rem;
  font-weight: bold;
  color: #1f2937;
  margin: 0 0 0.75rem;
}

.usage-bar {
  height: 0.5rem;
  background: #f3f4f6;
  border-radius: 9999px;
  overflow: hidden;
}

.usage-fill {
  height: 100%;
  transition: width 0.3s ease;
}
</style>
