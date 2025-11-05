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
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { notification } from '@/composables/useNotification'

const router = useRouter()
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
</style>
