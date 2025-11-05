/**
 * SSE (Server-Sent Events) Service
 *
 * Manages SSE connections for real-time chat communication.
 * Replaces WebSocket implementation with simpler SSE approach.
 */

export interface StreamingChunk {
  type: 'thinking' | 'tool_call' | 'tool_result' | 'chunk' | 'complete' | 'error' | 'done'
  content: string
  metadata: Record<string, any>
}

type MessageCallback = (chunk: StreamingChunk) => void
type ErrorCallback = (error: Error) => void
type CloseCallback = () => void

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
