# 前端关键问题修复方案

## 1. SSE 服务 - 自动重连机制

**问题**：无重连机制，网络波动导致永久失连

**修复**：在 `web-frontend/src/services/sse.ts` 中添加：
- 指数退避重连（1s, 2s, 4s, 8s, 16s）
- 最大重试次数限制（5次）
- 连接超时检测（30秒）
- 保存待发消息，重连后继续发送

**关键代码**：
- 添加 reconnectAttempts, maxReconnectAttempts, reconnectDelay 属性
- 添加 attemptReconnect() 方法，实现指数退避
- 在 handleConnectionError() 中触发重连
- 在 handleMessage() 中重置 reconnectAttempts

---

## 2. ChatStore 回调内存泄漏修复

**问题**：每次切换对话，新回调会堆积到旧的上面

**修复**：在 `web-frontend/src/stores/chat.ts` 中改进 connectToConversation：

```typescript
async function connectToConversation(conversationId: string) {
  try {
    // ... 其他逻辑 ...
    
    // 重点：完全清理旧的 SSE 服务状态
    if (currentConversation.value?.id !== conversationId) {
      // 切换到新对话时，重置 SSE 服务
      sseService.reset()  // 改用 reset() 而不仅仅是 clearCallbacks()
    }
    
    // 重新创建新的回调
    sseService.onMessage((chunk) => {
      handleStreamingChunk(chunk)
    })
    // ... 其他回调 ...
  }
}
```

关键改动：
- 使用 sseService.reset() 完全重置状态
- 不再使用累积式的回调注册

---

## 3. ChatView 定时器未清理

**问题**：scrollThrottle 在 component 卸载后仍在运行

**修复**：在 `web-frontend/src/views/ChatView.vue` 的 onUnmounted 中添加清理：

```typescript
onUnmounted(() => {
  chatStore.clearConversation()
  
  // 清理定时器
  if (scrollThrottle) {
    clearTimeout(scrollThrottle)
    scrollThrottle = null
  }
  
  // ... 其他清理 ...
})
```

---

## 4. SSE Token 传递改为 POST

**问题**：Token 通过 URL 参数，容易被泄露

**改进方案**（需要后端配合）：
- 当前临时方案：Token 仍在 URL，但后端应通过 HTTPS 和 Strict-Transport-Security 头防止降级
- 长期方案：改为 POST 请求，在请求体中传递 token

**前端改动**（暂时保持兼容）：
```typescript
// 标记待实现：需要后端支持 Authorization header
// sseUrl 中的 token 参数可以后续移除
```

---

## 5. 登录表单客户端验证

**问题**：仅依赖 HTML5 属性，容易被绕过

**修复**：在 `web-frontend/src/views/LoginView.vue` 中添加：

```typescript
async function handleLogin() {
  // 客户端验证
  if (!loginForm.username || !loginForm.password) {
    registerError.value = '用户名和密码不能为空'
    return
  }
  
  if (loginForm.password.length < 6) {
    registerError.value = '密码至少 6 位'
    return
  }
  
  try {
    await authStore.login(loginForm)
    notification.success('登录成功', ...)
    router.push('/')
  } catch (error) {
    notification.error('登录失败', String(error))
  }
}

async function handleRegister() {
  registerError.value = null
  
  // 客户端验证
  if (!registerForm.username || registerForm.username.length < 3) {
    registerError.value = '用户名至少 3 位'
    return
  }
  
  if (!registerForm.email || !isValidEmail(registerForm.email)) {
    registerError.value = '邮箱格式不正确'
    return
  }
  
  if (registerForm.password.length < 8) {
    registerError.value = '密码至少 8 位'
    return
  }
  
  if (registerForm.password !== registerForm.passwordConfirm) {
    registerError.value = '两次输入的密码不一致'
    return
  }
  
  // 检查密码强度
  if (!isStrongPassword(registerForm.password)) {
    registerError.value = '密码必须包含大小写字母、数字和特殊字符'
    return
  }
  
  try {
    await authStore.register({...})
  } catch (error) {
    notification.error('注册失败', String(error))
  }
}

// 辅助函数
function isValidEmail(email: string): boolean {
  const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  return re.test(email)
}

function isStrongPassword(password: string): boolean {
  const hasUpper = /[A-Z]/.test(password)
  const hasLower = /[a-z]/.test(password)
  const hasDigit = /[0-9]/.test(password)
  const hasSpecial = /[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(password)
  return hasUpper && hasLower && (hasDigit || hasSpecial)
}
```

---

## 6. ChatInput 错误提示

**问题**：数据库加载失败没有用户提示

**修复**：在 `web-frontend/src/components/ChatInput.vue` 中：

```typescript
async function loadDatabases() {
  loadingDatabases.value = true
  try {
    const response = await api.get('/database/connections')
    databases.value = Array.isArray(response.data) ? response.data : []
  } catch (error) {
    console.error('[ChatInput] Failed to load databases:', error)
    notification.error('加载数据库失败', '无法获取数据库列表，请稍后重试')
  } finally {
    loadingDatabases.value = false
  }
}
```

需要导入：
```typescript
import { notification } from '@/composables/useNotification'
```

---

## 7. API 401 错误处理优化

**问题**：可能导致循环导入，错误处理不够优雅

**修复**：在 `web-frontend/src/services/api.ts` 中改进：

```typescript
// 缓存 authStore 导入，避免重复导入
let cachedAuthStore: any = null

async function getAuthStore() {
  if (!cachedAuthStore) {
    const { useAuthStore } = await import('@/stores/auth')
    cachedAuthStore = useAuthStore()
  }
  return cachedAuthStore
}

// Response 拦截器改进
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config as any

    if (
      error.response?.status === 401 &&
      !originalRequest._retry &&
      !originalRequest.url.includes('/auth/refresh') &&
      !originalRequest.url.includes('/auth/login')
    ) {
      originalRequest._retry = true

      try {
        const authStore = await getAuthStore()
        const refreshed = await authStore.refreshAccessToken()

        if (refreshed) {
          const newToken = localStorage.getItem('access_token')
          originalRequest.headers.Authorization = `Bearer ${newToken}`
          return apiClient(originalRequest)
        }
      } catch (refreshError) {
        console.error('Token refresh failed:', refreshError)
        const authStore = await getAuthStore()
        authStore.logout()

        if (typeof window !== 'undefined') {
          window.location.href = '/login'
        }
      }
    }

    console.error('API Error:', error.response?.data || error.message)
    return Promise.reject(error)
  }
)
```

---

## 8. 消息 XSS 防护加强

**问题**：虽然当前安全，但容易被后续修改破坏

**改进**：在 `web-frontend/src/components/MessageItem.vue` 中添加 DOMPurify：

```bash
npm install dompurify
npm install --save-dev @types/dompurify
```

```typescript
import DOMPurify from 'dompurify'

const renderedContent = computed(() => {
  const html = md.render(props.message.content)
  // 二次净化，确保安全
  return DOMPurify.sanitize(html, { 
    ALLOWED_TAGS: ['p', 'br', 'em', 'strong', 'code', 'pre', 'a', 'ul', 'ol', 'li', 'blockquote', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'],
    ALLOWED_ATTR: ['href', 'title', 'target', 'rel']
  })
})
```

---

## 部署前检查清单

- [ ] SSE 重连机制已实现
- [ ] ChatStore 回调内存泄漏已修复
- [ ] ChatView 定时器已清理
- [ ] 登录表单验证已增强
- [ ] 错误提示已完善
- [ ] 所有 console.error 都有对应的用户提示
- [ ] 已测试弱网环境下的连接稳定性
- [ ] 已测试长时间使用的内存占用情况
- [ ] 已验证 XSS 防护

