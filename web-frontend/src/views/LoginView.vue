<template>
  <div class="login-container">
    <div class="login-card">
      <div class="login-header">
        <h1>Kode AI</h1>
        <p>AI原生ERP开发平台</p>
      </div>

      <!-- 登录表单 -->
      <div v-if="isLoginMode" class="login-form">
        <h2>登录</h2>
        <form @submit.prevent="handleLogin">
          <div class="form-group">
            <label for="username">用户名</label>
            <input
              id="username"
              v-model="loginForm.username"
              type="text"
              placeholder="请输入用户名"
              required
              autofocus
            />
          </div>

          <div class="form-group">
            <label for="password">密码</label>
            <input
              id="password"
              v-model="loginForm.password"
              type="password"
              placeholder="请输入密码"
              required
            />
          </div>

          <div v-if="authStore.error" class="error-message">
            {{ authStore.error }}
          </div>

          <button type="submit" class="btn-primary" :disabled="authStore.isLoading">
            {{ authStore.isLoading ? '登录中...' : '登录' }}
          </button>
        </form>

        <div class="form-footer">
          <span>还没有账号？</span>
          <a href="#" @click.prevent="isLoginMode = false">立即注册</a>
        </div>

        <!-- 分隔线 -->
        <div class="divider">
          <span>或</span>
        </div>

        <!-- 谷歌登录 -->
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
          使用谷歌账号登录
        </button>
      </div>

      <!-- 注册表单 -->
      <div v-else class="login-form">
        <h2>注册</h2>
        <form @submit.prevent="handleRegister">
          <div class="form-group">
            <label for="reg-username">用户名</label>
            <input
              id="reg-username"
              v-model="registerForm.username"
              type="text"
              placeholder="请输入用户名（3-50字符）"
              required
              minlength="3"
              maxlength="50"
              autofocus
            />
          </div>

          <div class="form-group">
            <label for="reg-email">邮箱</label>
            <input
              id="reg-email"
              v-model="registerForm.email"
              type="email"
              placeholder="请输入邮箱"
              required
            />
          </div>

          <div class="form-group">
            <label for="reg-password">密码</label>
            <input
              id="reg-password"
              v-model="registerForm.password"
              type="password"
              placeholder="请输入密码（至少6位）"
              required
              minlength="6"
            />
          </div>

          <div class="form-group">
            <label for="reg-password-confirm">确认密码</label>
            <input
              id="reg-password-confirm"
              v-model="registerForm.passwordConfirm"
              type="password"
              placeholder="请再次输入密码"
              required
            />
          </div>

          <div v-if="authStore.error || registerError" class="error-message">
            {{ authStore.error || registerError }}
          </div>

          <button type="submit" class="btn-primary" :disabled="authStore.isLoading">
            {{ authStore.isLoading ? '注册中...' : '注册' }}
          </button>
        </form>

        <div class="form-footer">
          <span>已有账号？</span>
          <a href="#" @click.prevent="isLoginMode = true">立即登录</a>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { notification } from '@/composables/useNotification'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const isLoginMode = ref(true)
const registerError = ref<string | null>(null)

const loginForm = reactive({
  username: '',
  password: ''
})

const registerForm = reactive({
  username: '',
  email: '',
  password: '',
  passwordConfirm: ''
})

async function handleLogin() {
  try {
    await authStore.login(loginForm)
    notification.success('登录成功', `欢迎回来，${authStore.currentUser?.username}！`)
    router.push('/')
  } catch (error) {
    notification.error('登录失败', String(error))
  }
}

async function handleRegister() {
  registerError.value = null

  // 验证密码
  if (registerForm.password !== registerForm.passwordConfirm) {
    registerError.value = '两次输入的密码不一致'
    return
  }

  try {
    await authStore.register({
      username: registerForm.username,
      email: registerForm.email,
      password: registerForm.password
    })
    notification.success('注册成功', '欢迎加入Kode AI！')
    router.push('/')
  } catch (error) {
    notification.error('注册失败', String(error))
  }
}

async function handleGoogleLogin() {
  try {
    const authUrl = await authStore.getGoogleAuthUrl()
    window.location.href = authUrl
  } catch (error) {
    notification.error('谷歌登录失败', String(error))
  }
}

// 处理谷歌OAuth2回调
onMounted(async () => {
  const code = route.query.code as string
  if (code) {
    try {
      await authStore.loginWithGoogle(code)
      notification.success('登录成功', '欢迎使用谷歌账号登录！')
      router.push('/')
    } catch (error) {
      notification.error('谷歌登录失败', String(error))
    }
  }
})
</script>

<style scoped>
.login-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 20px;
}

.login-card {
  background: white;
  border-radius: 16px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  padding: 40px;
  width: 100%;
  max-width: 420px;
}

.login-header {
  text-align: center;
  margin-bottom: 32px;
}

.login-header h1 {
  font-size: 32px;
  font-weight: bold;
  color: #667eea;
  margin: 0 0 8px 0;
}

.login-header p {
  color: #666;
  font-size: 14px;
  margin: 0;
}

.login-form h2 {
  font-size: 24px;
  font-weight: 600;
  color: #333;
  margin-bottom: 24px;
}

.form-group {
  margin-bottom: 20px;
}

.form-group label {
  display: block;
  font-size: 14px;
  font-weight: 500;
  color: #333;
  margin-bottom: 8px;
}

.form-group input {
  width: 100%;
  padding: 12px 16px;
  font-size: 14px;
  border: 1px solid #ddd;
  border-radius: 8px;
  transition: all 0.3s;
  box-sizing: border-box;
}

.form-group input:focus {
  outline: none;
  border-color: #667eea;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

.error-message {
  background: #fee;
  color: #c33;
  padding: 12px;
  border-radius: 8px;
  font-size: 14px;
  margin-bottom: 16px;
  border: 1px solid #fcc;
}

.btn-primary {
  width: 100%;
  padding: 14px;
  font-size: 16px;
  font-weight: 600;
  color: white;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border: none;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s;
}

.btn-primary:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 8px 16px rgba(102, 126, 234, 0.3);
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.form-footer {
  margin-top: 24px;
  text-align: center;
  font-size: 14px;
  color: #666;
}

.form-footer a {
  color: #667eea;
  text-decoration: none;
  font-weight: 500;
  margin-left: 4px;
}

.form-footer a:hover {
  text-decoration: underline;
}

.divider {
  position: relative;
  text-align: center;
  margin: 24px 0;
}

.divider::before {
  content: '';
  position: absolute;
  left: 0;
  top: 50%;
  width: 100%;
  height: 1px;
  background: #ddd;
}

.divider span {
  position: relative;
  background: white;
  padding: 0 12px;
  color: #999;
  font-size: 14px;
}

.btn-google {
  width: 100%;
  padding: 12px;
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
</style>
