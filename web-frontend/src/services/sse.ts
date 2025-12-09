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

      this.eventSource.onerror = (error) => {
        console.error('[Heartbeat] Connection error:', error)
        this._isConnected = false
        this.notifyConnectionChange(false)
        this.eventSource?.close()
        this.eventSource = null

        // 尝试重连
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
   */
  sendMessage(content: string, databaseName?: string): void {
    if (!this.conversationId) {
      throw new Error('No conversation ID set')
    }

    // Close existing connection if any
    this.disconnect()

    // Encode task parameter
    const encodedTask = encodeURIComponent(content)

    // Get access token for authentication
    const token = localStorage.getItem('access_token')
    if (!token) {
      console.error('No access token found, SSE authentication will fail')
    }

    // Build SSE URL with token parameter (EventSource doesn't support custom headers)
    let sseUrl = `/api/sse/chat/${this.conversationId}/stream?task=${encodedTask}`
    if (token) {
      sseUrl += `&token=${encodeURIComponent(token)}`
    }
    if (databaseName) {
      sseUrl += `&database_name=${encodeURIComponent(databaseName)}`
    }

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
          return
        }

        // Notify callbacks
        this.messageCallbacks.forEach(callback => callback(chunk))
      } catch (error) {
        console.error('Error parsing SSE message:', error)
      }
    }

    // Handle errors
    this.eventSource.onerror = (error) => {
      console.error('SSE error:', error)
      const errorObj = new Error('SSE connection error')
      this.errorCallbacks.forEach(callback => callback(errorObj))
      this.disconnect()
    }
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
