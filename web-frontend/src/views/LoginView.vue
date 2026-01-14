<template>
  <div class="login-container">
    <div class="login-card">
      <!-- 关闭按钮 -->
      <button class="close-btn" @click="handleClose">&times;</button>

      <div class="login-header">
        <h1>Welcome to DataMind AI</h1>
        <p>Sign in to continue</p>
      </div>

      <!-- Google 登录 -->
      <button @click.prevent="handleGoogleLogin" class="btn-google" :disabled="authStore.isLoading">
        <svg class="google-icon" viewBox="0 0 24 24">
          <path
            fill="#4285F4"
            d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
          />
          <path
            fill="#34A853"
            d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
          />
          <path
            fill="#FBBC05"
            d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
          />
          <path
            fill="#EA4335"
            d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
          />
        </svg>
        Continue with Google
      </button>

      <!-- 分隔线 -->
      <div class="divider">
        <span>OR CONTINUE WITH EMAIL</span>
      </div>

      <!-- 邮箱验证码登录 -->
      <div class="email-login-form">
        <!-- 邮箱输入 -->
        <div class="form-group">
          <input
            v-model="emailForm.email"
            type="email"
            placeholder="Enter your email"
            class="email-input"
            :class="{ 'has-value': emailForm.email }"
            :disabled="codeSent"
          />
        </div>

        <!-- 验证码输入（发送后显示） -->
        <div v-if="codeSent" class="form-group">
          <div class="code-input-wrapper">
            <input
              v-model="emailForm.code"
              type="text"
              maxlength="6"
              placeholder="Enter 6-digit code"
              class="code-input"
              @keyup.enter="handleVerifyCode"
            />
            <button
              class="resend-btn"
              :disabled="countdown > 0 || authStore.isLoading"
              @click="handleSendCode"
            >
              {{ countdown > 0 ? `${countdown}s` : 'Resend' }}
            </button>
          </div>
        </div>

        <!-- 错误提示 -->
        <div v-if="errorMessage" class="error-message">
          {{ errorMessage }}
        </div>

        <!-- 成功提示 -->
        <div v-if="successMessage" class="success-message">
          {{ successMessage }}
        </div>

        <!-- 发送验证码 / 验证按钮 -->
        <button
          v-if="!codeSent"
          class="btn-primary"
          :disabled="!isValidEmail || authStore.isLoading"
          @click="handleSendCode"
        >
          {{ authStore.isLoading ? 'Sending...' : 'Send Verification Code' }}
        </button>

        <button
          v-else
          class="btn-primary"
          :disabled="emailForm.code.length !== 6 || authStore.isLoading"
          @click="handleVerifyCode"
        >
          {{ authStore.isLoading ? 'Verifying...' : 'Sign In' }}
        </button>
      </div>

      <!-- 服务条款 -->
      <p class="terms">
        By signing in, you agree to our
        <a href="#" @click.prevent>Terms of Service</a> and
        <a href="#" @click.prevent>Privacy Policy</a>
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { notification } from '@/composables/useNotification'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const emailForm = reactive({
  email: '',
  code: ''
})

const codeSent = ref(false)
const countdown = ref(0)
const errorMessage = ref('')
const successMessage = ref('')
let countdownTimer: number | null = null

const isValidEmail = computed(() => {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  return emailRegex.test(emailForm.email)
})

function startCountdown() {
  countdown.value = 60
  countdownTimer = window.setInterval(() => {
    countdown.value--
    if (countdown.value <= 0) {
      if (countdownTimer) {
        clearInterval(countdownTimer)
        countdownTimer = null
      }
    }
  }, 1000)
}

async function handleSendCode() {
  if (!isValidEmail.value) return

  errorMessage.value = ''
  successMessage.value = ''

  const result = await authStore.sendEmailCode(emailForm.email)

  if (result.success) {
    codeSent.value = true
    successMessage.value = result.message
    startCountdown()
  } else {
    errorMessage.value = result.message
  }
}

async function handleVerifyCode() {
  if (emailForm.code.length !== 6) return

  errorMessage.value = ''
  successMessage.value = ''

  try {
    await authStore.verifyEmailCode(emailForm.email, emailForm.code)
    notification.success('Login Successful', `Welcome, ${authStore.currentUser?.username}!`)
    router.push('/')
  } catch (error) {
    errorMessage.value = String(error)
  }
}

async function handleGoogleLogin() {
  try {
    const authUrl = await authStore.getGoogleAuthUrl()
    window.location.href = authUrl
  } catch (error) {
    notification.error('Google Login Failed', String(error))
  }
}

function handleClose() {
  router.push('/')
}

// 处理谷歌OAuth2回调
onMounted(async () => {
  const googleSuccess = route.query.google_success as string
  const accessToken = route.query.access_token as string
  const refreshToken = route.query.refresh_token as string

  if (googleSuccess === 'true' && accessToken && refreshToken) {
    try {
      authStore.accessToken = accessToken
      authStore.refreshToken = refreshToken
      localStorage.setItem('access_token', accessToken)
      localStorage.setItem('refresh_token', refreshToken)

      await authStore.fetchUserProfile()

      notification.success('Login Successful', 'Welcome!')
      router.push('/')
    } catch (error) {
      notification.error('Google Login Failed', String(error))
    }
  }
})

onUnmounted(() => {
  if (countdownTimer) {
    clearInterval(countdownTimer)
  }
})
</script>

<style scoped>
.login-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
  padding: 20px;
}

.login-card {
  background: white;
  border-radius: 16px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  padding: 40px;
  width: 100%;
  max-width: 420px;
  position: relative;
}

.close-btn {
  position: absolute;
  top: 16px;
  right: 16px;
  width: 32px;
  height: 32px;
  border: none;
  background: transparent;
  font-size: 24px;
  color: #999;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  transition: all 0.2s;
}

.close-btn:hover {
  background: #f0f0f0;
  color: #333;
}

.login-header {
  text-align: center;
  margin-bottom: 32px;
}

.login-header h1 {
  font-size: 24px;
  font-weight: 600;
  color: #1a1a2e;
  margin: 0 0 8px 0;
}

.login-header p {
  color: #666;
  font-size: 14px;
  margin: 0;
}

.btn-google {
  width: 100%;
  padding: 14px;
  font-size: 14px;
  font-weight: 500;
  color: #333;
  background: white;
  border: 1px solid #ddd;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
}

.btn-google:hover:not(:disabled) {
  background: #f8f8f8;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.btn-google:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.google-icon {
  width: 20px;
  height: 20px;
}

.divider {
  position: relative;
  text-align: center;
  margin: 28px 0;
}

.divider::before {
  content: '';
  position: absolute;
  left: 0;
  top: 50%;
  width: 100%;
  height: 1px;
  background: #e0e0e0;
}

.divider span {
  position: relative;
  background: white;
  padding: 0 16px;
  color: #888;
  font-size: 12px;
  font-weight: 500;
  letter-spacing: 0.5px;
}

.email-login-form {
  margin-bottom: 24px;
}

.form-group {
  margin-bottom: 16px;
}

.email-input {
  width: 100%;
  padding: 16px;
  font-size: 15px;
  border: 2px solid #e8f4f8;
  border-radius: 8px;
  background: #e8f4f8;
  transition: all 0.3s;
  box-sizing: border-box;
}

.email-input:focus {
  outline: none;
  border-color: #4a7c8a;
  background: white;
}

.email-input:disabled {
  background: #f5f5f5;
  color: #666;
}

.email-input.has-value {
  background: #e8f4f8;
}

.code-input-wrapper {
  display: flex;
  gap: 12px;
}

.code-input {
  flex: 1;
  padding: 16px;
  font-size: 18px;
  font-weight: 600;
  letter-spacing: 8px;
  text-align: center;
  border: 2px solid #e0e0e0;
  border-radius: 8px;
  transition: all 0.3s;
  box-sizing: border-box;
}

.code-input:focus {
  outline: none;
  border-color: #4a7c8a;
}

.resend-btn {
  padding: 16px 20px;
  font-size: 14px;
  font-weight: 500;
  color: #4a7c8a;
  background: white;
  border: 2px solid #4a7c8a;
  border-radius: 8px;
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.2s;
}

.resend-btn:hover:not(:disabled) {
  background: #4a7c8a;
  color: white;
}

.resend-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.error-message {
  background: #fef2f2;
  color: #dc2626;
  padding: 12px 16px;
  border-radius: 8px;
  font-size: 14px;
  margin-bottom: 16px;
  border: 1px solid #fecaca;
}

.success-message {
  background: #f0fdf4;
  color: #16a34a;
  padding: 12px 16px;
  border-radius: 8px;
  font-size: 14px;
  margin-bottom: 16px;
  border: 1px solid #bbf7d0;
}

.btn-primary {
  width: 100%;
  padding: 16px;
  font-size: 16px;
  font-weight: 600;
  color: white;
  background: #4a7c8a;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s;
}

.btn-primary:hover:not(:disabled) {
  background: #3d6873;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(74, 124, 138, 0.3);
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.terms {
  text-align: center;
  font-size: 12px;
  color: #888;
  line-height: 1.6;
  margin: 0;
}

.terms a {
  color: #4a7c8a;
  text-decoration: none;
}

.terms a:hover {
  text-decoration: underline;
}
</style>
