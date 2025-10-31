/**
 * WebSocket Service
 *
 * Manages WebSocket connection for real-time chat communication
 */

export interface StreamingChunk {
  type: 'thinking' | 'tool_call' | 'chunk' | 'complete' | 'error'
  content: string
  metadata: Record<string, any>
}

export interface WebSocketMessage {
  type: 'task' | 'ping'
  content: string
  metadata?: Record<string, any>
}

type MessageCallback = (chunk: StreamingChunk) => void
type ErrorCallback = (error: Event) => void
type CloseCallback = () => void
type ReconnectCallback = (attempt: number) => void

export class WebSocketService {
  private ws: WebSocket | null = null
  private conversationId: string | null = null
  private messageCallbacks: MessageCallback[] = []
  private errorCallbacks: ErrorCallback[] = []
  private closeCallbacks: CloseCallback[] = []
  private reconnectCallbacks: ReconnectCallback[] = []
  private reconnectAttempts = 0
  private maxReconnectAttempts = 5
  private reconnectDelay = 1000
  private shouldReconnect = true

  constructor() {}

  /**
   * Connect to WebSocket server
   */
  connect(conversationId: string): Promise<void> {
    return new Promise((resolve, reject) => {
      this.conversationId = conversationId

      // Determine WebSocket URL
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      const host = window.location.host
      const wsUrl = `${protocol}//${host}/ws/chat/${conversationId}`

      this.ws = new WebSocket(wsUrl)

      this.ws.onopen = () => {
        console.log('WebSocket connected')
        this.reconnectAttempts = 0
        resolve()
      }

      this.ws.onmessage = (event) => {
        try {
          const chunk: StreamingChunk = JSON.parse(event.data)
          this.messageCallbacks.forEach(callback => callback(chunk))
        } catch (error) {
          console.error('Error parsing WebSocket message:', error)
        }
      }

      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error)
        this.errorCallbacks.forEach(callback => callback(error))
        reject(error)
      }

      this.ws.onclose = () => {
        console.log('WebSocket closed')
        this.closeCallbacks.forEach(callback => callback())

        // Attempt reconnection
        if (this.shouldReconnect && this.reconnectAttempts < this.maxReconnectAttempts) {
          this.reconnectAttempts++
          console.log(`Reconnecting... Attempt ${this.reconnectAttempts}`)
          this.reconnectCallbacks.forEach(callback => callback(this.reconnectAttempts))

          setTimeout(() => {
            if (this.conversationId && this.shouldReconnect) {
              this.connect(this.conversationId).catch(err => {
                console.error('Reconnection failed:', err)
              })
            }
          }, this.reconnectDelay * this.reconnectAttempts)
        }
      }
    })
  }

  /**
   * Send message to server
   */
  sendMessage(content: string) {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      throw new Error('WebSocket is not connected')
    }

    const message: WebSocketMessage = {
      type: 'task',
      content,
      metadata: {}
    }

    this.ws.send(JSON.stringify(message))
  }

  /**
   * Send ping to keep connection alive
   */
  sendPing() {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      return
    }

    const message: WebSocketMessage = {
      type: 'ping',
      content: '',
    }

    this.ws.send(JSON.stringify(message))
  }

  /**
   * Register message callback
   */
  onMessage(callback: MessageCallback) {
    this.messageCallbacks.push(callback)
  }

  /**
   * Register error callback
   */
  onError(callback: ErrorCallback) {
    this.errorCallbacks.push(callback)
  }

  /**
   * Register close callback
   */
  onClose(callback: CloseCallback) {
    this.closeCallbacks.push(callback)
  }

  /**
   * Register reconnect callback
   */
  onReconnect(callback: ReconnectCallback) {
    this.reconnectCallbacks.push(callback)
  }

  /**
   * Disconnect WebSocket
   */
  disconnect() {
    this.shouldReconnect = false
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
    this.conversationId = null
    this.messageCallbacks = []
    this.errorCallbacks = []
    this.closeCallbacks = []
    this.reconnectCallbacks = []
    this.reconnectAttempts = 0
  }

  /**
   * Check if WebSocket is connected
   */
  isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN
  }
}

// Singleton instance
export const websocketService = new WebSocketService()
