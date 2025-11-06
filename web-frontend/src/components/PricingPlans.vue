<template>
  <div class="pricing-plans">
    <div class="pricing-header">
      <h2>选择适合您的套餐</h2>
      <p>灵活的定价方案，满足不同规模团队需求</p>
    </div>

    <div v-if="loading" class="loading">加载中...</div>
    <div v-else-if="error" class="error">{{ error }}</div>

    <div v-else class="plans-grid">
      <div
        v-for="plan in plans"
        :key="plan.id"
        class="plan-card"
        :class="{ 'current-plan': isCurrentPlan(plan), 'popular': plan.name === 'pro' }"
      >
        <div v-if="plan.name === 'pro'" class="popular-badge">最受欢迎</div>

        <div class="plan-header">
          <h3>{{ plan.display_name }}</h3>
          <p class="plan-description">{{ plan.description }}</p>
        </div>

        <div class="plan-price">
          <span class="currency">¥</span>
          <span class="amount">{{ plan.price }}</span>
          <span class="period">/月</span>
        </div>

        <ul class="plan-features">
          <li>
            <svg class="icon" viewBox="0 0 20 20" fill="currentColor">
              <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd" />
            </svg>
            {{ formatNumber(plan.token_quota) }} Tokens/月
          </li>
          <li>
            <svg class="icon" viewBox="0 0 20 20" fill="currentColor">
              <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd" />
            </svg>
            {{ plan.message_quota }} 条消息/月
          </li>
          <li>
            <svg class="icon" viewBox="0 0 20 20" fill="currentColor">
              <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd" />
            </svg>
            {{ plan.conversation_quota }} 个同时对话
          </li>
          <li v-if="plan.database_access">
            <svg class="icon" viewBox="0 0 20 20" fill="currentColor">
              <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd" />
            </svg>
            {{ plan.database_connection_quota }} 个数据库连接
          </li>
          <li v-if="plan.advanced_analysis">
            <svg class="icon" viewBox="0 0 20 20" fill="currentColor">
              <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd" />
            </svg>
            高级数据分析
          </li>
          <li v-if="plan.ontology_building">
            <svg class="icon" viewBox="0 0 20 20" fill="currentColor">
              <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd" />
            </svg>
            业务本体构建
          </li>
          <li v-if="plan.priority_support">
            <svg class="icon" viewBox="0 0 20 20" fill="currentColor">
              <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd" />
            </svg>
            优先技术支持
          </li>
        </ul>

        <button
          class="plan-button"
          :class="{ 'current': isCurrentPlan(plan) }"
          :disabled="isCurrentPlan(plan) || upgrading"
          @click="handleUpgrade(plan)"
        >
          <span v-if="isCurrentPlan(plan)">当前套餐</span>
          <span v-else-if="upgrading">处理中...</span>
          <span v-else>{{ plan.price === 0 ? '开始使用' : '立即升级' }}</span>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useBillingStore } from '@/stores/billing'
import type { Plan } from '@/services/api'

const billingStore = useBillingStore()

const loading = computed(() => billingStore.loading)
const error = computed(() => billingStore.error)
const plans = computed(() => billingStore.plans)
const currentPlan = computed(() => billingStore.currentPlan)

const upgrading = ref(false)

function isCurrentPlan(plan: Plan): boolean {
  return currentPlan.value?.id === plan.id
}

function formatNumber(num: number): string {
  if (num >= 10000000) {
    return `${(num / 10000000).toFixed(0)}千万`
  }
  if (num >= 1000000) {
    return `${(num / 1000000).toFixed(0)}百万`
  }
  if (num >= 10000) {
    return `${(num / 10000).toFixed(0)}万`
  }
  return num.toString()
}

async function handleUpgrade(plan: Plan) {
  if (isCurrentPlan(plan) || upgrading.value) return

  upgrading.value = true
  try {
    await billingStore.upgradeToPlan(plan.id)
  } catch (err) {
    console.error('Upgrade failed:', err)
  } finally {
    upgrading.value = false
  }
}
</script>

<style scoped>
.pricing-plans {
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem;
}

.pricing-header {
  text-align: center;
  margin-bottom: 3rem;
}

.pricing-header h2 {
  font-size: 2rem;
  font-weight: bold;
  margin-bottom: 0.5rem;
  color: #1f2937;
}

.pricing-header p {
  font-size: 1.125rem;
  color: #6b7280;
}

.loading,
.error {
  text-align: center;
  padding: 2rem;
  color: #6b7280;
}

.error {
  color: #ef4444;
}

.plans-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 2rem;
  margin-top: 2rem;
}

.plan-card {
  position: relative;
  background: white;
  border: 2px solid #e5e7eb;
  border-radius: 1rem;
  padding: 2rem;
  transition: all 0.3s;
}

.plan-card:hover {
  border-color: #3b82f6;
  box-shadow: 0 10px 25px rgba(59, 130, 246, 0.1);
  transform: translateY(-4px);
}

.plan-card.popular {
  border-color: #3b82f6;
  box-shadow: 0 10px 25px rgba(59, 130, 246, 0.15);
}

.plan-card.current-plan {
  border-color: #10b981;
  background: #f0fdf4;
}

.popular-badge {
  position: absolute;
  top: -12px;
  left: 50%;
  transform: translateX(-50%);
  background: linear-gradient(135deg, #3b82f6, #2563eb);
  color: white;
  padding: 0.25rem 1rem;
  border-radius: 9999px;
  font-size: 0.875rem;
  font-weight: 600;
}

.plan-header h3 {
  font-size: 1.5rem;
  font-weight: bold;
  margin-bottom: 0.5rem;
  color: #1f2937;
}

.plan-description {
  font-size: 0.875rem;
  color: #6b7280;
  margin-bottom: 1.5rem;
}

.plan-price {
  display: flex;
  align-items: baseline;
  margin-bottom: 2rem;
}

.currency {
  font-size: 1.5rem;
  font-weight: 600;
  color: #1f2937;
}

.amount {
  font-size: 3rem;
  font-weight: bold;
  color: #1f2937;
  margin: 0 0.25rem;
}

.period {
  font-size: 1rem;
  color: #6b7280;
}

.plan-features {
  list-style: none;
  padding: 0;
  margin-bottom: 2rem;
}

.plan-features li {
  display: flex;
  align-items: center;
  padding: 0.75rem 0;
  font-size: 0.875rem;
  color: #374151;
}

.plan-features .icon {
  width: 1.25rem;
  height: 1.25rem;
  margin-right: 0.75rem;
  color: #10b981;
  flex-shrink: 0;
}

.plan-button {
  width: 100%;
  padding: 0.75rem 1.5rem;
  background: linear-gradient(135deg, #3b82f6, #2563eb);
  color: white;
  border: none;
  border-radius: 0.5rem;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s;
}

.plan-button:hover:not(:disabled) {
  background: linear-gradient(135deg, #2563eb, #1d4ed8);
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3);
}

.plan-button:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

.plan-button.current {
  background: #10b981;
}

.plan-button.current:hover {
  background: #10b981;
  transform: none;
}
</style>
