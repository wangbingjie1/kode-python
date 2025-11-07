# 前端代码安全审查报告

## 严重等级问题（必须修复）

### 1. SSE 连接无自动重连机制 【高风险】
**文件**: `web-frontend/src/services/sse.ts`
**问题描述**: 
- EventSource 无重连配置，当网络波动导致连接断开时，用户无法自动恢复连接
- SSE 消息完成后调用 disconnect()，再发送新消息时才重新建立连接
- 期间如果网络故障不会自动恢复

**影响**: 用户在弱网环境下会永久失连，必须刷新页面
**修复方案**: 实现重连机制，记录连接失败次数并指数退避

---

### 2. 内存泄漏 - ChatStore 事件监听器累积 【高风险】
**文件**: `web-frontend/src/stores/chat.ts` (第72-97行)
**问题描述**:
```typescript
// 每次 connectToConversation 都会注册新回调，旧回调不会真正被清除
sseService.onMessage((chunk) => { ... })
sseService.onError((error) => { ... })
sseService.onClose(() => { ... })
```
- clearCallbacks() 虽然清除了数组，但如果短时间内多次切换对话，新回调会附加到旧的引用上
- SSE service 是单例，导致回调重复累积

**影响**: 长期使用会内存泄漏，消息处理速度逐渐变慢

**修复方案**: 创建单次绑定的回调，或者改用事件监听器模式

---

### 3. 内存泄漏 - ChatView 定时器未清理 【中等风险】
**文件**: `web-frontend/src/views/ChatView.vue` (第229-250行)
**问题描述**:
```typescript
let scrollThrottle: ReturnType<typeof setTimeout> | null = null

watch(() => timelineMessages.value.map(m => m.message.content).join(''), async () => {
  if (scrollThrottle) {
    clearTimeout(scrollThrottle)  // ✓ 清理了
  }
  scrollThrottle = setTimeout(...)  // 但没有在 onUnmounted 中清理
})
```

**影响**: component 卸载后定时器仍在运行，导致内存占用不释放

**修复方案**: 在 onUnmounted 中清理 scrollThrottle

---

### 4. SSE 通过 URL 参数传递 Token 【安全风险】
**文件**: `web-frontend/src/services/sse.ts` (第58-64行)
**问题描述**:
```typescript
let sseUrl = `/api/sse/chat/${this.conversationId}/stream?task=${encodedTask}`
if (token) {
  sseUrl += `&token=${encodeURIComponent(token)}`  // ❌ Token 在 URL 中
}
```

**安全风险**:
- Token 可能被浏览器历史记录保存
- 可能被代理/防火墙日志记录
- 可能通过 Referer 头泄露
- 浏览器扩展可能访问

**影响**: Token 泄露导致账户被攫取

**修复方案**: 后端应支持使用 Authorization header，或者使用 POST 替代 GET

---

### 5. 缺少登录路由守卫验证 【中等风险】
**文件**: `web-frontend/src/router/index.ts` (第63-77行)
**问题描述**:
- 路由守卫依赖 authStore.isAuthenticated
- 但如果 token 过期，isAuthenticated 仍返回 true（仅检查 token 是否存在）
- API 401 时会触发自动跳转到登录，但这是被动的

**影响**: 用户可能短暂进入需要认证的页面后被踢出

**修复方案**: 添加 token 有效期验证，或在路由守卫中验证 token

---

### 6. EventSource 自动重连不可靠 【高风险】
**文件**: `web-frontend/src/services/sse.ts` (第67行)
**问题描述**:
- EventSource 是浏览器API，会自动尝试重连（默认3秒）
- 但重连是无限的，会持续尝试
- 没有 max retry 控制，可能导致浏览器持续发送大量请求

**影响**: 当后端 SSE 端点有问题时，会形成DOS攻击

**修复方案**: 添加 max retry 限制，超过限制后主动断开

---

### 7. 消息内容 XSS 防护不足 【中等风险】
**文件**: `web-frontend/src/components/MessageItem.vue` (第187-213行)
**问题描述**:
```typescript
const md: MarkdownIt = new MarkdownIt({
  html: false,  // ✓ 禁用 HTML
  linkify: true,  // ✓ 自动链接
  typographer: true,  // 可能有问题
})
```

虽然设置了 `html: false`，但是：
- 代码块中使用 `onclick="window.copyCode(this)"` 直接注入
- 如果后端返回恶意的 markdown，可能绕过防护
- 没有 DOMPurify 等额外的净化

**风险**: 虽然当前代码安全，但容易被后续修改破坏

---

### 8. 登录表单验证不足 【中等风险】
**文件**: `web-frontend/src/views/LoginView.vue` (第15-34行)
**问题描述**:
```html
<input
  id="password"
  v-model="loginForm.password"
  type="password"
  placeholder="请输入密码"
  required
/>
```
- 仅依赖 HTML5 的 required 属性
- 浏览器开发者工具可轻易绕过：修改 DOM 移除 required，或直接调用 API
- 注册时没有密码强度验证

**影响**: 弱密码被接受

---

### 9. 登录成功后 Token 处理问题 【中等风险】
**文件**: `web-frontend/src/views/LoginView.vue` (第216-238行)
**问题描述**:
```typescript
// Google OAuth 回调处理
if (googleSuccess === 'true' && accessToken && refreshToken) {
  authStore.accessToken = accessToken  // ❌ 直接赋值
  authStore.refreshToken = refreshToken
  localStorage.setItem('access_token', accessToken)
  localStorage.setItem('refresh_token', refreshToken)
}
```
- Token 通过 URL query 参数传递
- 虽然代码中处理了，但存在短暂的安全窗口
- 没有检查 Token 格式的有效性

---

### 10. API 401 错误处理导致循环导入 【中等风险】
**文件**: `web-frontend/src/services/api.ts` (第39-78行)
**问题描述**:
```typescript
if (error.response?.status === 401 && !originalRequest._retry) {
  try {
    const { useAuthStore } = await import('@/stores/auth')
    const authStore = useAuthStore()
    // 刷新 token...
  } catch (refreshError) {
    console.error('Token refresh failed:', refreshError)
    const { useAuthStore } = await import('@/stores/auth')  // ❌ 第二次导入
    const authStore = useAuthStore()
    authStore.logout()
  }
}
```
- 动态导入两次可能导致循环依赖
- 没有防止无限重试的机制

---

### 11. ChatInput 数据库加载错误没有用户提示 【低风险】
**文件**: `web-frontend/src/components/ChatInput.vue` (第146-156行)
**问题描述**:
```typescript
async function loadDatabases() {
  try {
    const response = await api.get('/database/connections')
    databases.value = Array.isArray(response.data) ? response.data : []
  } catch (error) {
    console.error('[ChatInput] Failed to load databases:', error)  // ❌ 无用户提示
  }
}
```
- 如果 API 失败，用户不知道发生了什么
- 数据库下拉菜单会显示为空，用户会困惑

---

### 12. 消息不会自动保存到后端 【中等风险】
**文件**: `web-frontend/src/stores/chat.ts`
**问题描述**:
- 用户发送的消息添加到本地 UI，但等待 SSE 响应保存
- 如果 SSE 因任何原因失败，消息可能丢失
- 没有离线缓存机制

---

## 总结

### 必须修复（上线前）：
1. ✗ SSE 自动重连机制
2. ✗ ChatStore 回调内存泄漏
3. ✗ ChatView 定时器未清理
4. ✗ SSE Token 安全传递
5. ✗ EventSource 重试限制
6. ✗ API 401 错误处理优化

### 应该修复（高优先级）：
7. ✓ 消息 XSS 防护加强
8. ✓ 登录表单客户端验证
9. ✓ Token 格式验证
10. ✓ ChatInput 错误提示

### 可以后续优化：
11. ✓ 消息离线缓存
12. ✓ Token 有效期检查

