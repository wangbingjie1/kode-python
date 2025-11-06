/**
 * Billing Store
 *
 * Manages subscription, plans, and usage state
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type {
  Plan,
  Subscription,
  UsageSummary
} from '@/services/api'
import {
  listPlans,
  getMySubscription,
  getMyUsageSummary,
  createStripeCheckout,
  cancelSubscription as cancelSubscriptionAPI
} from '@/services/api'

export const useBillingStore = defineStore('billing', () => {
  // State
  const plans = ref<Plan[]>([])
  const subscription = ref<Subscription | null>(null)
  const usageSummary = ref<UsageSummary | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  // Computed
  const currentPlan = computed(() => {
    if (!subscription.value || !subscription.value.plan) {
      return null
    }
    return subscription.value.plan
  })

  const isSubscriptionActive = computed(() => {
    return subscription.value?.status === 'active'
  })

  const isQuotaExceeded = computed(() => {
    return usageSummary.value?.is_quota_exceeded || false
  })

  const tokenUsagePercentage = computed(() => {
    if (!usageSummary.value) return 0
    const { token_used, token_quota } = usageSummary.value
    if (token_quota === 0) return 0
    return Math.min(100, (token_used / token_quota) * 100)
  })

  const messageUsagePercentage = computed(() => {
    if (!usageSummary.value) return 0
    const { message_used, message_quota } = usageSummary.value
    if (message_quota === 0) return 0
    return Math.min(100, (message_used / message_quota) * 100)
  })

  // Actions
  async function fetchPlans() {
    loading.value = true
    error.value = null

    try {
      plans.value = await listPlans()
    } catch (err: any) {
      error.value = err.response?.data?.detail || '获取套餐失败'
      console.error('Failed to fetch plans:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  async function fetchSubscription() {
    loading.value = true
    error.value = null

    try {
      subscription.value = await getMySubscription()
    } catch (err: any) {
      // 如果是404，说明用户没有订阅（这是正常情况）
      if (err.response?.status === 404) {
        subscription.value = null
      } else {
        error.value = err.response?.data?.detail || '获取订阅失败'
        console.error('Failed to fetch subscription:', err)
        throw err
      }
    } finally {
      loading.value = false
    }
  }

  async function fetchUsageSummary() {
    loading.value = true
    error.value = null

    try {
      usageSummary.value = await getMyUsageSummary()
    } catch (err: any) {
      error.value = err.response?.data?.detail || '获取使用量失败'
      console.error('Failed to fetch usage summary:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  async function upgradeToPlan(planId: string) {
    loading.value = true
    error.value = null

    try {
      // 获取当前页面URL，用于支付成功/取消后跳转
      const baseURL = window.location.origin
      const successURL = `${baseURL}/billing/success`
      const cancelURL = `${baseURL}/billing`

      const result = await createStripeCheckout({
        plan_id: planId,
        success_url: successURL,
        cancel_url: cancelURL
      })

      // 跳转到 Stripe Checkout 页面
      window.location.href = result.checkout_url
    } catch (err: any) {
      error.value = err.response?.data?.detail || '创建支付会话失败'
      console.error('Failed to create checkout session:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  async function cancelSubscription(immediate = false) {
    if (!subscription.value) {
      throw new Error('没有活跃的订阅')
    }

    loading.value = true
    error.value = null

    try {
      subscription.value = await cancelSubscriptionAPI(subscription.value.id, immediate)
    } catch (err: any) {
      error.value = err.response?.data?.detail || '取消订阅失败'
      console.error('Failed to cancel subscription:', err)
      throw err
    } finally {
      loading.value = false
    }
  }

  async function refreshAll() {
    await Promise.all([
      fetchPlans(),
      fetchSubscription(),
      fetchUsageSummary()
    ])
  }

  return {
    // State
    plans,
    subscription,
    usageSummary,
    loading,
    error,

    // Computed
    currentPlan,
    isSubscriptionActive,
    isQuotaExceeded,
    tokenUsagePercentage,
    messageUsagePercentage,

    // Actions
    fetchPlans,
    fetchSubscription,
    fetchUsageSummary,
    upgradeToPlan,
    cancelSubscription,
    refreshAll
  }
})
