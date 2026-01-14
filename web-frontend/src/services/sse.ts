/**
 * SSE (Server-Sent Events) Service
 *
 * Manages SSE connections for real-time chat communication.
 * Includes heartbeat connection for maintaining connection status.
 */

export interface StreamingChunk {
  type: 'thinking' | 'tool_call' | 'tool_result' | 'chunk' | 'complete' | 'error' | 'done' | 'heartbeat' | 'connected' | 'disconnected'
  content: string
  metadata: Record<string, any>
}

type MessageCallback = (chunk: StreamingChunk) => void
type ErrorCallback = (error: Error) => void
type CloseCallback = () => void
type ConnectionCallback = (connected: boolean) => void

/**
 * SSE Heartbeat Service
 *
 * 维护一个长连接用于：
 * 1. 检测真实的网络连接状态
 * 2. 每 30 秒接收心跳保持连接
 * 3. 自动重连
 */
export class SSEHeartbeatService {
  private eventSource: EventSource | null = null
  private connectionCallbacks: ConnectionCallback[] = []
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null
  private lastHeartbeat: number = 0
  private _isConnected: boolean = false
  private reconnectAttempts: number = 0
  private maxReconnectAttempts: number = 10
  private baseReconnectDelay: number = 1000 // 1 秒

  constructor() {}

  /**
   * 启动心跳连接
   */
  connect(): void {
    // 如果已连接，先断开
    if (this.eventSource) {
      this.disconnect()
    }

    const token = localStorage.getItem('access_token')
    if (!token) {
      console.warn('[Heartbeat] No access token, skipping heartbeat connection')
      this._isConnected = false
      this.notifyConnectionChange(false)
      return
    }

    const sseUrl = `/api/sse/heartbeat?token=${encodeURIComponent(token)}`

    try {
      this.eventSource = new EventSource(sseUrl)

      this.eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)

          if (data.type === 'connected') {
            console.log('[Heartbeat] Connected')
            this._isConnected = true
            this.reconnectAttempts = 0 // 重置重连计数
            this.notifyConnectionChange(true)
          } else if (data.type === 'heartbeat') {
            this.lastHeartbeat = data.metadata?.timestamp || Date.now() / 1000

            // 🔥 关键修复：如果服务器返回新 token，更新本地存储
            if (data.metadata?.new_token) {
              const newToken = data.metadata.new_token
              localStorage.setItem('access_token', newToken)
              console.log('[Heartbeat] Token refreshed automatically')
            }

            // console.log('[Heartbeat] Received at', new Date(this.lastHeartbeat * 1000).toLocaleTimeString())
          } else if (data.type === 'disconnected') {
            console.log('[Heartbeat] Server disconnected')
            this._isConnected = false
            this.notifyConnectionChange(false)
          }
        } catch (error) {
          console.error('[Heartbeat] Error parsing message:', error)
        }
      }

      this.eventSource.onerror = async (error) => {
        console.error('[Heartbeat] Connection error:', error)

        this._isConnected = false
        this.notifyConnectionChange(false)
        this.eventSource?.close()
        this.eventSource = null

        // 心跳断开可能是网络波动、后端重启等正常情况
        // 尝试刷新 token 后重连（可能是 token 过期）
        if (this.reconnectAttempts === 0) {
          try {
            const { useAuthStore } = await import('@/stores/auth')
            const authStore = useAuthStore()
            const refreshed = await authStore.refreshAccessToken()
            if (refreshed) {
              console.log('[Heartbeat] Token refreshed, reconnecting immediately...')
              this.connect() // 立即重连，不等待
              return
            }
          } catch (refreshError) {
            console.warn('[Heartbeat] Token refresh failed, will retry connection:', refreshError)
          }
        }

        this.scheduleReconnect()
      }

      this.eventSource.onopen = () => {
        console.log('[Heartbeat] Connection opened')
      }

    } catch (error) {
      console.error('[Heartbeat] Failed to create EventSource:', error)
      this._isConnected = false
      this.notifyConnectionChange(false)
    }
  }

  /**
   * 计划重连
   */
  private scheduleReconnect(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
    }

    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('[Heartbeat] Max reconnect attempts reached')
      return
    }

    // 指数退避：1s, 2s, 4s, 8s, 16s, 30s (max)
    const delay = Math.min(
      this.baseReconnectDelay * Math.pow(2, this.reconnectAttempts),
      30000
    )

    console.log(`[Heartbeat] Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts + 1})`)

    this.reconnectTimer = setTimeout(() => {
      this.reconnectAttempts++
      this.connect()
    }, delay)
  }

  /**
   * 断开心跳连接
   */
  disconnect(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }

    if (this.eventSource) {
      this.eventSource.close()
      this.eventSource = null
    }

    this._isConnected = false
    this.notifyConnectionChange(false)
  }

  /**
   * 注册连接状态变化回调
   */
  onConnectionChange(callback: ConnectionCallback): void {
    this.connectionCallbacks.push(callback)
    // 立即通知当前状态
    callback(this._isConnected)
  }

  /**
   * 清除回调
   */
  clearCallbacks(): void {
    this.connectionCallbacks = []
  }

  /**
   * 通知连接状态变化
   */
  private notifyConnectionChange(connected: boolean): void {
    this.connectionCallbacks.forEach(callback => callback(connected))
  }

  /**
   * 获取连接状态
   */
  get isConnected(): boolean {
    return this._isConnected
  }

  /**
   * 获取最后心跳时间
   */
  get lastHeartbeatTime(): number {
    return this.lastHeartbeat
  }
}

// 心跳服务单例
export const heartbeatService = new SSEHeartbeatService()


/**
 * SSE Chat Service
 *
 * 用于发送消息和接收流式响应
 */
export class SSEService {
  private eventSource: EventSource | null = null
  private conversationId: string | null = null
  private messageCallbacks: MessageCallback[] = []
  private errorCallbacks: ErrorCallback[] = []
  private closeCallbacks: CloseCallback[] = []
  private isReady: boolean = false

  constructor() {}

  /**
   * Connect to SSE stream for a conversation
   */
  connect(conversationId: string): void {
    this.conversationId = conversationId
    this.isReady = true // Mark as ready to send messages
    // Actual SSE connection will be established when sending message
  }

  /**
   * Send message and start receiving SSE stream
   *
   * 如果遇到 401 错误，会尝试刷新 token 并重试一次
   */
  async sendMessage(content: string, databaseName?: string): Promise<void> {
    if (!this.conversationId) {
      throw new Error('No conversation ID set')
    }

    // Close existing connection if any
    this.disconnect()

    // 尝试发送，如果 401 则刷新 token 重试
    const tryConnect = async (isRetry = false): Promise<void> => {
      // Get access token for authentication
      const token = localStorage.getItem('access_token')
      if (!token) {
        console.error('No access token found, redirecting to login')
        window.location.href = '/login'
        return
      }

      // Encode task parameter
      const encodedTask = encodeURIComponent(content)

      // Build SSE URL with token parameter (EventSource doesn't support custom headers)
      let sseUrl = `/api/sse/chat/${this.conversationId}/stream?task=${encodedTask}`
      sseUrl += `&token=${encodeURIComponent(token)}`
      if (databaseName) {
        sseUrl += `&database_name=${encodeURIComponent(databaseName)}`
      }

      return new Promise<void>((resolve, reject) => {
        // Create SSE connection
        this.eventSource = new EventSource(sseUrl)

        // Handle incoming messages
        this.eventSource.onmessage = (event) => {
          try {
            const chunk: StreamingChunk = JSON.parse(event.data)

            // Check for done signal
            if (chunk.type === 'done') {
              this.disconnect()
              this.closeCallbacks.forEach(callback => callback())
              resolve()
              return
            }

            // Notify callbacks
            this.messageCallbacks.forEach(callback => callback(chunk))
          } catch (error) {
            console.error('Error parsing SSE message:', error)
          }
        }

        // Handle errors - 🔥 修复：不要因为 SSE 连接失败就 logout
        // SSE 失败可能是：401 认证失败、429 配额不足、网络问题等
        // EventSource API 不暴露 HTTP 状态码，所以我们不能确定具体原因
        this.eventSource.onerror = async (error) => {
          console.error('SSE error:', error)

          // EventSource 不直接暴露 HTTP 状态码
          // 检查 readyState: 0=CONNECTING, 1=OPEN, 2=CLOSED
          const readyState = this.eventSource?.readyState
          this.disconnect()

          // 如果连接从未打开过（立即失败），尝试刷新 token 重试一次
          if (readyState === EventSource.CLOSED && !isRetry) {
            console.log('[SSE] Connection failed immediately, trying to refresh token...')

            try {
              // 动态导入避免循环依赖
              const { useAuthStore } = await import('@/stores/auth')
              const authStore = useAuthStore()
              const refreshed = await authStore.refreshAccessToken()

              if (refreshed) {
                console.log('[SSE] Token refreshed, retrying connection...')
                // 重试连接
                await tryConnect(true)
                resolve()
                return
              }
            } catch (refreshError) {
              console.error('[SSE] Token refresh failed:', refreshError)
            }

            // 🔥 关键修复：即使 token 刷新失败，也不要自动 logout
            // 可能是 429 配额不足或其他非认证错误
            // 让调用方（chat store）处理错误，显示友好提示
            console.warn('[SSE] Connection failed after retry, NOT logging out automatically')
            const errorObj = new Error('SSE connection failed - please check your quota or try again')
            ;(errorObj as any).mayBeQuotaExceeded = true  // 标记可能是配额问题
            this.errorCallbacks.forEach(callback => callback(errorObj))
            reject(errorObj)
            return
          }

          const errorObj = new Error('SSE connection error')
          this.errorCallbacks.forEach(callback => callback(errorObj))
          reject(errorObj)
        }

        // 连接成功打开时 resolve（可选，因为 SSE 是持续连接）
        this.eventSource.onopen = () => {
          console.log('[SSE] Connection opened successfully')
        }
      })
    }

    await tryConnect()
  }

  /**
   * Register message callback
   */
  onMessage(callback: MessageCallback): void {
    this.messageCallbacks.push(callback)
  }

  /**
   * Register error callback
   */
  onError(callback: ErrorCallback): void {
    this.errorCallbacks.push(callback)
  }

  /**
   * Register close callback
   */
  onClose(callback: CloseCallback): void {
    this.closeCallbacks.push(callback)
  }

  /**
   * Disconnect SSE stream
   */
  disconnect(): void {
    if (this.eventSource) {
      this.eventSource.close()
      this.eventSource = null
    }
  }

  /**
   * Check if SSE is connected or ready to connect
   * Returns true if we have a conversation ID set (ready to send messages)
   */
  isConnected(): boolean {
    return this.isReady && this.conversationId !== null
  }

  /**
   * Clear all callbacks
   */
  clearCallbacks(): void {
    this.messageCallbacks = []
    this.errorCallbacks = []
    this.closeCallbacks = []
  }

  /**
   * Reset service state
   */
  reset(): void {
    this.disconnect()
    this.clearCallbacks()
    this.conversationId = null
    this.isReady = false
  }
}

// Singleton instance
export const sseService = new SSEService()
