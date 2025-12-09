/**
 * 认证状态管理 Store
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import axios from 'axios'
import { API_BASE_URL } from '@/config/constants'
import { heartbeatService } from '@/services/sse'

interface User {
  id: string
  username: string
  email: string
  is_active: boolean
  created_at: string
  auth_provider?: string
  avatar_url?: string
}

interface LoginCredentials {
  username: string
  password: string
}

interface RegisterData {
  username: string
  email: string
  password: string
}

export const useAuthStore = defineStore('auth', () => {
  // State
  const user = ref<User | null>(null)
  const accessToken = ref<string | null>(localStorage.getItem('access_token'))
  const refreshToken = ref<string | null>(localStorage.getItem('refresh_token'))
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  // Getters
  const isAuthenticated = computed(() => !!accessToken.value)
  const currentUser = computed(() => user.value)

  // Actions
  async function login(credentials: LoginCredentials) {
    isLoading.value = true
    error.value = null

    try {
      const response = await axios.post(`${API_BASE_URL}/auth/login`, credentials)
      const { access_token, refresh_token } = response.data

      // 存储令牌
      accessToken.value = access_token
      refreshToken.value = refresh_token
      localStorage.setItem('access_token', access_token)
      localStorage.setItem('refresh_token', refresh_token)

      // 获取用户信息
      await fetchUserProfile()

      // 启动心跳连接
      heartbeatService.connect()
      console.log('[Auth] Heartbeat started after login')

      return true
    } catch (err: any) {
      error.value = err.response?.data?.detail || '登录失败'
      throw error.value
    } finally {
      isLoading.value = false
    }
  }

  async function register(data: RegisterData) {
    isLoading.value = true
    error.value = null

    try {
      await axios.post(`${API_BASE_URL}/auth/register`, data)
      // 注册成功后自动登录
      await login({ username: data.username, password: data.password })
      return true
    } catch (err: any) {
      error.value = err.response?.data?.detail || '注册失败'
      throw error.value
    } finally {
      isLoading.value = false
    }
  }

  async function fetchUserProfile() {
    if (!accessToken.value) return

    try {
      const response = await axios.get(`${API_BASE_URL}/auth/profile`, {
        headers: {
          Authorization: `Bearer ${accessToken.value}`
        }
      })
      user.value = response.data
    } catch (err) {
      console.error('获取用户信息失败:', err)
    }
  }

  async function refreshAccessToken() {
    if (!refreshToken.value) {
      logout()
      return false
    }

    try {
      const response = await axios.post(`${API_BASE_URL}/auth/refresh`, {
        refresh_token: refreshToken.value
      })

      const { access_token, refresh_token: new_refresh_token } = response.data

      accessToken.value = access_token
      refreshToken.value = new_refresh_token
      localStorage.setItem('access_token', access_token)
      localStorage.setItem('refresh_token', new_refresh_token)

      return true
    } catch (err) {
      console.error('刷新Token失败:', err)
      logout()
      return false
    }
  }

  async function loginWithGoogle(code: string) {
    isLoading.value = true
    error.value = null

    try {
      const response = await axios.post(`${API_BASE_URL}/auth/google/callback`, { code })
      const { access_token, refresh_token } = response.data

      // 存储令牌
      accessToken.value = access_token
      refreshToken.value = refresh_token
      localStorage.setItem('access_token', access_token)
      localStorage.setItem('refresh_token', refresh_token)

      // 获取用户信息
      await fetchUserProfile()

      // 启动心跳连接
      heartbeatService.connect()
      console.log('[Auth] Heartbeat started after Google login')

      return true
    } catch (err: any) {
      error.value = err.response?.data?.detail || '谷歌登录失败'
      throw error.value
    } finally {
      isLoading.value = false
    }
  }

  async function getGoogleAuthUrl(): Promise<string> {
    try {
      const response = await axios.get(`${API_BASE_URL}/auth/google/login`)
      return response.data.auth_url
    } catch (err: any) {
      error.value = err.response?.data?.detail || '获取谷歌登录URL失败'
      throw error.value
    }
  }

  function logout() {
    // 停止心跳连接
    heartbeatService.disconnect()
    console.log('[Auth] Heartbeat stopped on logout')

    user.value = null
    accessToken.value = null
    refreshToken.value = null
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
  }

  // 初始化时尝试获取用户信息并启动心跳
  if (accessToken.value) {
    fetchUserProfile()
    // 页面刷新后重新启动心跳
    heartbeatService.connect()
    console.log('[Auth] Heartbeat started on page load (token exists)')
  }

  return {
    // State
    user,
    accessToken,
    refreshToken,
    isLoading,
    error,

    // Getters
    isAuthenticated,
    currentUser,

    // Actions
    login,
    register,
    loginWithGoogle,
    getGoogleAuthUrl,
    fetchUserProfile,
    refreshAccessToken,
    logout
  }
})
