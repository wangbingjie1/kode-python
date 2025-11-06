<template>
  <MainLayout>
    <header class="border-b border-[#eadfd3] bg-white/70 px-5 py-5 lg:px-12">
      <div class="flex items-center justify-between gap-4">
        <div class="flex items-center gap-3">
          <button
            @click="openMobileSidebar"
            class="flex h-11 w-11 items-center justify-center rounded-full border border-[#eadfd3] bg-white/80 text-[#8a7c6b] shadow-sm transition hover:-translate-y-0.5 hover:text-[#6f6256] hover:shadow-md focus:outline-none focus:ring-2 focus:ring-[#d8c6b4] lg:hidden"
            aria-label="打开导航"
            type="button"
          >
            <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>
          <div>
            <p class="text-xs font-semibold uppercase tracking-[0.32em] text-[#b9aa9a]">Settings</p>
            <p class="mt-1 text-xl font-semibold text-[#2f2720]">用户中心</p>
          </div>
        </div>
      </div>
    </header>

    <div class="profile-view">
      <div class="profile-container">

      <!-- Tab 导航 -->
      <div class="tabs">
        <button
          v-for="tab in tabs"
          :key="tab.id"
          class="tab-button"
          :class="{ active: activeTab === tab.id }"
          @click="activeTab = tab.id"
        >
          <svg class="tab-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" :d="tab.icon" />
          </svg>
          <span>{{ tab.label }}</span>
        </button>
      </div>

      <!-- Tab 内容 -->
      <div class="tab-content">
        <!-- 个人信息 -->
        <section v-if="activeTab === 'profile'" class="tab-panel">
          <h2>个人信息</h2>

          <div class="profile-card">
            <div class="avatar-section">
              <div class="avatar-large">
                <img v-if="authStore.currentUser?.avatar_url" :src="authStore.currentUser.avatar_url" alt="Avatar" />
                <span v-else>{{ userInitial }}</span>
              </div>
              <button class="btn-secondary">更换头像</button>
            </div>

            <div class="form-section">
              <div class="form-group">
                <label>用户名</label>
                <input
                  type="text"
                  :value="authStore.currentUser?.username"
                  readonly
                  class="input-readonly"
                />
                <p class="hint">用户名不可修改</p>
              </div>

              <div class="form-group">
                <label>邮箱</label>
                <input
                  type="email"
                  :value="authStore.currentUser?.email"
                  readonly
                  class="input-readonly"
                />
              </div>

              <div class="form-group">
                <label>登录方式</label>
                <div class="auth-provider">
                  <span class="provider-badge" :class="`provider-${authStore.currentUser?.auth_provider}`">
                    {{ getProviderName(authStore.currentUser?.auth_provider) }}
                  </span>
                </div>
              </div>

              <div v-if="authStore.currentUser?.auth_provider === 'local'" class="form-group">
                <button class="btn-secondary" @click="showPasswordChange = true">修改密码</button>
              </div>
            </div>
          </div>
        </section>

        <!-- 订阅管理 -->
        <section v-if="activeTab === 'subscription'" class="tab-panel">
          <h2>订阅管理</h2>

          <!-- 当前订阅 -->
          <div v-if="subscription" class="subscription-card">
            <div class="subscription-header">
              <div>
                <h3>{{ subscription.plan?.display_name }}</h3>
                <span class="status-badge" :class="`status-${subscription.status}`">
                  {{ getStatusText(subscription.status) }}
                </span>
              </div>
              <div class="subscription-price">
                <span class="price">¥{{ subscription.plan?.price }}</span>
                <span class="period">/{{ subscription.plan?.billing_period === 'monthly' ? '月' : '年' }}</span>
              </div>
            </div>

            <div class="subscription-details">
              <div class="detail-item">
                <span class="detail-label">有效期</span>
                <span class="detail-value">{{ formatDate(subscription.start_date) }} - {{ formatDate(subscription.end_date) }}</span>
              </div>
              <div class="detail-item">
                <span class="detail-label">自动续费</span>
                <span class="detail-value">{{ subscription.auto_renew ? '已开启' : '已关闭' }}</span>
              </div>
            </div>

            <div class="subscription-actions">
              <button v-if="subscription.status === 'active'" class="btn-danger" @click="handleCancelSubscription">
                取消订阅
              </button>
            </div>
          </div>

          <!-- 使用量统计 -->
          <div v-if="usageSummary" class="usage-stats">
            <h3>使用量统计</h3>
            <div class="stats-grid">
              <div class="stat-card">
                <div class="stat-icon" style="background: #dbeafe; color: #3b82f6">
                  <svg fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 8h10M7 12h4m1 8l-4-4H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-3l-4 4z" />
                  </svg>
                </div>
                <div class="stat-info">
                  <p class="stat-label">Token 使用</p>
                  <p class="stat-value">{{ formatNumber(usageSummary.token_used) }} / {{ formatNumber(usageSummary.token_quota) }}</p>
                  <div class="stat-bar">
                    <div class="stat-fill" :style="{ width: `${tokenPercentage}%`, backgroundColor: getProgressColor(tokenPercentage) }"></div>
                  </div>
                </div>
              </div>

              <div class="stat-card">
                <div class="stat-icon" style="background: #d1fae5; color: #10b981">
                  <svg fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
                  </svg>
                </div>
                <div class="stat-info">
                  <p class="stat-label">消息数量</p>
                  <p class="stat-value">{{ usageSummary.message_used }} / {{ usageSummary.message_quota }}</p>
                  <div class="stat-bar">
                    <div class="stat-fill" :style="{ width: `${messagePercentage}%`, backgroundColor: getProgressColor(messagePercentage) }"></div>
                  </div>
                </div>
              </div>

              <div class="stat-card">
                <div class="stat-icon" style="background: #fef3c7; color: #f59e0b">
                  <svg fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                  </svg>
                </div>
                <div class="stat-info">
                  <p class="stat-label">对话数</p>
                  <p class="stat-value">{{ usageSummary.conversation_count }} / {{ usageSummary.conversation_quota }}</p>
                </div>
              </div>
            </div>
          </div>

          <!-- 套餐升级 -->
          <div class="upgrade-section">
            <h3>升级套餐</h3>
            <router-link to="/billing" class="btn-primary">查看所有套餐</router-link>
          </div>
        </section>

        <!-- 安全设置 -->
        <section v-if="activeTab === 'security'" class="tab-panel">
          <h2>安全设置</h2>

          <div class="security-card">
            <h3>登录密码</h3>
            <p class="security-description">定期修改密码可以提高账号安全性</p>
            <button v-if="authStore.currentUser?.auth_provider === 'local'" class="btn-secondary" @click="showPasswordChange = true">
              修改密码
            </button>
            <p v-else class="hint">您使用的是 {{ getProviderName(authStore.currentUser?.auth_provider) }} 登录，无需设置密码</p>
          </div>

          <div class="security-card">
            <h3>登录设备</h3>
            <p class="security-description">当前登录设备和会话管理</p>
            <div class="session-list">
              <div class="session-item">
                <div class="session-icon">
                  <svg fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                  </svg>
                </div>
                <div class="session-info">
                  <p class="session-device">当前设备</p>
                  <p class="session-time">最后活跃：刚刚</p>
                </div>
                <span class="session-badge">当前</span>
              </div>
            </div>
          </div>
        </section>

        <!-- 偏好设置 -->
        <section v-if="activeTab === 'preferences'" class="tab-panel">
          <h2>偏好设置</h2>

          <div class="preference-card">
            <div class="preference-item">
              <div class="preference-info">
                <h3>语言</h3>
                <p>选择界面显示语言</p>
              </div>
              <LanguageSwitcher />
            </div>

            <div class="preference-item">
              <div class="preference-info">
                <h3>主题</h3>
                <p>选择浅色或深色主题</p>
              </div>
              <div class="theme-switcher">
                <button class="theme-option active">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
                  </svg>
                  浅色
                </button>
                <button class="theme-option" disabled>
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
                  </svg>
                  深色 (即将推出)
                </button>
              </div>
            </div>
          </div>
        </section>
      </div>
    </div>

    <!-- 修改密码对话框 -->
    <div v-if="showPasswordChange" class="modal-overlay" @click="showPasswordChange = false">
      <div class="modal-content" @click.stop>
        <h2>修改密码</h2>
        <form @submit.prevent="handlePasswordChange">
          <div class="form-group">
            <label>当前密码</label>
            <input type="password" v-model="passwordForm.current" required />
          </div>
          <div class="form-group">
            <label>新密码</label>
            <input type="password" v-model="passwordForm.new" required minlength="6" />
          </div>
          <div class="form-group">
            <label>确认新密码</label>
            <input type="password" v-model="passwordForm.confirm" required />
          </div>
          <div class="modal-actions">
            <button type="button" class="btn-secondary" @click="showPasswordChange = false">取消</button>
            <button type="submit" class="btn-primary">确认修改</button>
          </div>
        </form>
      </div>
    </div>
    </div>
  </MainLayout>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, inject } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useBillingStore } from '@/stores/billing'
import MainLayout from '@/layouts/MainLayout.vue'
import LanguageSwitcher from '@/components/LanguageSwitcher.vue'

const openSidebar = inject<() => void>('openSidebar')

function openMobileSidebar() {
  openSidebar?.()
}

const authStore = useAuthStore()
const billingStore = useBillingStore()

const activeTab = ref('profile')
const showPasswordChange = ref(false)
const passwordForm = ref({
  current: '',
  new: '',
  confirm: ''
})

const tabs = [
  { id: 'profile', label: '个人信息', icon: 'M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z' },
  { id: 'subscription', label: '订阅管理', icon: 'M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z' },
  { id: 'security', label: '安全设置', icon: 'M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z' },
  { id: 'preferences', label: '偏好设置', icon: 'M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z' }
]

const subscription = computed(() => billingStore.subscription)
const usageSummary = computed(() => billingStore.usageSummary)
const tokenPercentage = computed(() => billingStore.tokenUsagePercentage)
const messagePercentage = computed(() => billingStore.messageUsagePercentage)
const userInitial = computed(() => authStore.currentUser?.username?.charAt(0)?.toUpperCase() || 'U')

onMounted(async () => {
  await billingStore.refreshAll()
})

function getProviderName(provider?: string): string {
  const names: Record<string, string> = {
    local: '本地账号',
    google: 'Google',
    github: 'GitHub'
  }
  return names[provider || 'local'] || provider || '未知'
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

function formatDate(dateStr: string): string {
  const date = new Date(dateStr)
  return date.toLocaleDateString('zh-CN', { year: 'numeric', month: 'long', day: 'numeric' })
}

function formatNumber(num: number): string {
  if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`
  if (num >= 1000) return `${(num / 1000).toFixed(1)}K`
  return num.toString()
}

function getProgressColor(percentage: number): string {
  if (percentage >= 90) return '#ef4444'
  if (percentage >= 70) return '#f59e0b'
  return '#10b981'
}

async function handleCancelSubscription() {
  if (!confirm('确定要取消订阅吗？订阅将在当前计费周期结束后停止。')) return

  try {
    await billingStore.cancelSubscription(false)
    alert('订阅已取消')
  } catch (err) {
    console.error('Cancel subscription failed:', err)
    alert('取消订阅失败，请稍后重试')
  }
}

async function handlePasswordChange() {
  if (passwordForm.value.new !== passwordForm.value.confirm) {
    alert('两次输入的新密码不一致')
    return
  }

  // TODO: 实现密码修改 API
  alert('密码修改功能即将推出')
  showPasswordChange.value = false
  passwordForm.value = { current: '', new: '', confirm: '' }
}
</script>

<style scoped>
.profile-view {
  flex: 1;
  overflow-y: auto;
  background: #fdf7f0;
  padding: 2rem;
}

.profile-container {
  max-width: 1200px;
  margin: 0 auto;
}

h2 {
  font-size: 1.5rem;
  font-weight: 600;
  color: #2f2720;
  margin-bottom: 1.5rem;
}

h3 {
  font-size: 1.125rem;
  font-weight: 600;
  color: #2f2720;
  margin: 0;
}

/* Tabs */
.tabs {
  display: flex;
  gap: 0.5rem;
  border-bottom: 2px solid #eadfd3;
  margin-bottom: 2rem;
  overflow-x: auto;
}

.tab-button {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1.5rem;
  border: none;
  background: none;
  color: #78695c;
  font-size: 0.938rem;
  font-weight: 500;
  cursor: pointer;
  border-bottom: 2px solid transparent;
  margin-bottom: -2px;
  transition: all 0.2s;
  white-space: nowrap;
}

.tab-button:hover {
  color: #2f2720;
  background: rgba(255, 255, 255, 0.5);
}

.tab-button.active {
  color: #f26b3a;
  border-bottom-color: #f26b3a;
  background: rgba(255, 255, 255, 0.6);
}

.tab-icon {
  width: 1.25rem;
  height: 1.25rem;
}

/* Tab Content */
.tab-content {
  animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

.tab-panel {
  display: block;
}

/* Profile Card */
.profile-card {
  background: rgba(255, 255, 255, 0.8);
  border: 1px solid #eadfd3;
  border-radius: 0.75rem;
  padding: 2rem;
  margin-bottom: 2rem;
  box-shadow: 0 8px 20px rgba(190, 160, 130, 0.1);
}

.avatar-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
  margin-bottom: 2rem;
  padding-bottom: 2rem;
  border-bottom: 1px solid #e5e7eb;
}

.avatar-large {
  width: 6rem;
  height: 6rem;
  border-radius: 50%;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 2rem;
  font-weight: 600;
  overflow: hidden;
}

.avatar-large img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.form-section {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.form-group label {
  font-size: 0.875rem;
  font-weight: 600;
  color: #374151;
}

.form-group input {
  padding: 0.75rem;
  border: 1px solid #d1d5db;
  border-radius: 0.5rem;
  font-size: 0.938rem;
  color: #1f2937;
}

.input-readonly {
  background: #f9fafb;
  cursor: not-allowed;
}

.hint {
  font-size: 0.813rem;
  color: #6b7280;
  margin: 0;
}

.auth-provider {
  display: flex;
  align-items: center;
}

.provider-badge {
  padding: 0.375rem 0.75rem;
  border-radius: 9999px;
  font-size: 0.813rem;
  font-weight: 600;
}

.provider-local {
  background: #dbeafe;
  color: #1e40af;
}

.provider-google {
  background: #fef3c7;
  color: #92400e;
}

.provider-github {
  background: #f3f4f6;
  color: #1f2937;
}

/* Subscription Card */
.subscription-card {
  background: rgba(255, 255, 255, 0.8);
  border: 1px solid #eadfd3;
  border-radius: 0.75rem;
  padding: 2rem;
  margin-bottom: 2rem;
  box-shadow: 0 8px 20px rgba(190, 160, 130, 0.1);
}

.subscription-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 1.5rem;
  padding-bottom: 1.5rem;
  border-bottom: 1px solid #e5e7eb;
}

.subscription-header h3 {
  margin-bottom: 0.5rem;
}

.status-badge {
  display: inline-block;
  padding: 0.25rem 0.75rem;
  border-radius: 9999px;
  font-size: 0.813rem;
  font-weight: 600;
}

.status-active {
  background: #d1fae5;
  color: #065f46;
}

.status-expired, .status-cancelled {
  background: #fee2e2;
  color: #991b1b;
}

.status-trial {
  background: #dbeafe;
  color: #1e40af;
}

.subscription-price {
  text-align: right;
}

.price {
  font-size: 2rem;
  font-weight: bold;
  color: #1f2937;
}

.period {
  font-size: 0.938rem;
  color: #6b7280;
}

.subscription-details {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.detail-item {
  display: flex;
  justify-content: space-between;
  font-size: 0.938rem;
}

.detail-label {
  color: #6b7280;
}

.detail-value {
  color: #1f2937;
  font-weight: 500;
}

.subscription-actions {
  display: flex;
  justify-content: flex-end;
}

/* Usage Stats */
.usage-stats {
  background: rgba(255, 255, 255, 0.8);
  border: 1px solid #eadfd3;
  border-radius: 0.75rem;
  padding: 2rem;
  margin-bottom: 2rem;
  box-shadow: 0 8px 20px rgba(190, 160, 130, 0.1);
}

.usage-stats h3 {
  margin-bottom: 1.5rem;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1.5rem;
}

.stat-card {
  display: flex;
  gap: 1rem;
  padding: 1.5rem;
  background: #f9fafb;
  border-radius: 0.75rem;
}

.stat-icon {
  width: 3rem;
  height: 3rem;
  border-radius: 0.75rem;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.stat-icon svg {
  width: 1.5rem;
  height: 1.5rem;
}

.stat-info {
  flex: 1;
}

.stat-label {
  font-size: 0.813rem;
  color: #6b7280;
  margin: 0 0 0.5rem;
}

.stat-value {
  font-size: 1.25rem;
  font-weight: bold;
  color: #1f2937;
  margin: 0 0 0.75rem;
}

.stat-bar {
  height: 0.5rem;
  background: #e5e7eb;
  border-radius: 9999px;
  overflow: hidden;
}

.stat-fill {
  height: 100%;
  transition: width 0.3s ease;
}

/* Upgrade Section */
.upgrade-section {
  background: rgba(255, 255, 255, 0.8);
  border: 1px solid #eadfd3;
  border-radius: 0.75rem;
  padding: 2rem;
  text-align: center;
  box-shadow: 0 8px 20px rgba(190, 160, 130, 0.1);
}

.upgrade-section h3 {
  margin-bottom: 1rem;
}

/* Security Card */
.security-card {
  background: rgba(255, 255, 255, 0.8);
  border: 1px solid #eadfd3;
  border-radius: 0.75rem;
  padding: 2rem;
  margin-bottom: 2rem;
  box-shadow: 0 8px 20px rgba(190, 160, 130, 0.1);
}

.security-card h3 {
  margin-bottom: 0.5rem;
}

.security-description {
  font-size: 0.938rem;
  color: #6b7280;
  margin-bottom: 1.5rem;
}

.session-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.session-item {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1rem;
  background: #f9fafb;
  border-radius: 0.5rem;
}

.session-icon {
  width: 2.5rem;
  height: 2.5rem;
  border-radius: 0.5rem;
  background: #dbeafe;
  color: #3b82f6;
  display: flex;
  align-items: center;
  justify-content: center;
}

.session-icon svg {
  width: 1.5rem;
  height: 1.5rem;
}

.session-info {
  flex: 1;
}

.session-device {
  font-size: 0.938rem;
  font-weight: 600;
  color: #1f2937;
  margin: 0 0 0.25rem;
}

.session-time {
  font-size: 0.813rem;
  color: #6b7280;
  margin: 0;
}

.session-badge {
  padding: 0.25rem 0.75rem;
  background: #10b981;
  color: white;
  font-size: 0.75rem;
  font-weight: 600;
  border-radius: 9999px;
}

/* Preference Card */
.preference-card {
  background: rgba(255, 255, 255, 0.8);
  border: 1px solid #eadfd3;
  border-radius: 0.75rem;
  padding: 2rem;
  box-shadow: 0 8px 20px rgba(190, 160, 130, 0.1);
}

.preference-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.5rem 0;
  border-bottom: 1px solid #e5e7eb;
}

.preference-item:last-child {
  border-bottom: none;
}

.preference-info h3 {
  margin-bottom: 0.25rem;
}

.preference-info p {
  font-size: 0.875rem;
  color: #6b7280;
  margin: 0;
}

.theme-switcher {
  display: flex;
  gap: 0.5rem;
}

.theme-option {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1.5rem;
  border: 2px solid #eadfd3;
  background: rgba(255, 255, 255, 0.6);
  border-radius: 0.5rem;
  cursor: pointer;
  transition: all 0.2s;
  font-size: 0.875rem;
}

.theme-option svg {
  width: 1.5rem;
  height: 1.5rem;
}

.theme-option:hover:not(:disabled) {
  border-color: #f26b3a;
}

.theme-option.active {
  border-color: #f26b3a;
  background: rgba(254, 242, 238, 0.9);
}

.theme-option:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Buttons */
.btn-primary {
  padding: 0.75rem 1.5rem;
  background: linear-gradient(135deg, #f26b3a, #e0582a);
  color: white;
  border: none;
  border-radius: 0.5rem;
  font-size: 0.938rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  text-decoration: none;
  display: inline-block;
}

.btn-primary:hover {
  transform: translateY(-2px);
  box-shadow: 0 10px 20px rgba(242, 107, 58, 0.3);
}

.btn-secondary {
  padding: 0.75rem 1.5rem;
  background: rgba(255, 255, 255, 0.8);
  color: #2f2720;
  border: 1px solid #eadfd3;
  border-radius: 0.5rem;
  font-size: 0.938rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-secondary:hover {
  background: rgba(255, 255, 255, 1);
  border-color: #c58d63;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(197, 141, 99, 0.2);
}

.btn-danger {
  padding: 0.75rem 1.5rem;
  background: rgba(255, 255, 255, 0.8);
  color: #ef4444;
  border: 1px solid #fecaca;
  border-radius: 0.5rem;
  font-size: 0.938rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-danger:hover {
  background: #fef2f2;
  border-color: #fca5a5;
  transform: translateY(-1px);
}

/* Modal */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: rgba(255, 255, 255, 0.98);
  border: 1px solid #eadfd3;
  border-radius: 0.75rem;
  padding: 2rem;
  max-width: 500px;
  width: 90%;
  box-shadow: 0 20px 50px rgba(0, 0, 0, 0.3);
}

.modal-content h2 {
  margin-bottom: 1.5rem;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 1rem;
  margin-top: 1.5rem;
}

@media (max-width: 768px) {
  .profile-view {
    padding: 1rem;
  }

  h1 {
    font-size: 1.5rem;
  }

  .tabs {
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
  }

  .tab-button {
    font-size: 0.875rem;
    padding: 0.625rem 1rem;
  }

  .stats-grid {
    grid-template-columns: 1fr;
  }

  .subscription-header {
    flex-direction: column;
    gap: 1rem;
  }

  .subscription-price {
    text-align: left;
  }
}
</style>
