/**
 * Chat Store
 *
 * Manages chat state with Pinia
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { Conversation, Message } from '@/services/api'
import { sseService } from '@/services/sse'
import * as api from '@/services/api'
import { notification } from '@/composables/useNotification'

export interface ToolCall {
  toolName: string
  toolArgs: Record<string, any>
  toolResult?: string
  toolError?: string
  status: string
}

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant' | 'system' | 'tool'
  content: string
  timestamp: Date
  isStreaming?: boolean
  metadata?: Record<string, any>
  toolCall?: ToolCall
}

export const useChatStore = defineStore('chat', () => {
  // State
  const currentConversation = ref<Conversation | null>(null)
  const messages = ref<ChatMessage[]>([])
  const isConnected = ref(false)
  const isTyping = ref(false)
  const currentStreamingMessage = ref<ChatMessage | null>(null)

  // Computed
  const hasMessages = computed(() => messages.value.length > 0)

  // Actions

  /**
   * Connect to conversation
   */
  async function connectToConversation(conversationId: string) {
    try {
      console.log('[ChatStore] Connecting to conversation:', conversationId)

      // Clear previous state
      isTyping.value = false
      currentStreamingMessage.value = null
      console.log('[ChatStore] State cleared. isTyping:', isTyping.value)

      // Get conversation details
      currentConversation.value = await api.getConversation(conversationId)
      console.log('[ChatStore] Conversation loaded:', currentConversation.value.title)

      // Load message history
      const history = await api.getConversationMessages(conversationId)
      messages.value = history.map(msg => ({
        id: msg.id,
        role: msg.role as 'user' | 'assistant',
        content: msg.content,
        timestamp: new Date(msg.created_at),
        metadata: msg.metadata
      }))
      console.log('[ChatStore] Loaded', messages.value.length, 'messages')

      // Connect SSE
      sseService.connect(conversationId)
      isConnected.value = true
      console.log('[ChatStore] SSE connected. isConnected:', isConnected.value)

      // Setup message handler
      sseService.onMessage((chunk) => {
        console.log('[ChatStore] SSE message received:', chunk.type)
        handleStreamingChunk(chunk)
      })

      sseService.onClose(() => {
        console.log('[ChatStore] SSE stream closed (message complete)')
        // Don't set isConnected to false - we're still connected to the conversation
        // SSE closes after each message completion, but we remain ready to send new messages
      })

      sseService.onError((error) => {
        console.error('[ChatStore] SSE error:', error)
        notification.error('连接错误', 'SSE 连接失败: ' + error.message)
        isConnected.value = false // Only disconnect on error
      })

      console.log('[ChatStore] Connection setup complete')
    } catch (error) {
      console.error('[ChatStore] Error connecting to conversation:', error)
      throw error
    }
  }

  /**
   * Send message
  */
  async function sendMessage(content: string, databaseName?: string) {
    if (!isConnected.value) {
      throw new Error('Not connected to conversation')
    }

    // Add user message to UI
    const userMessage: ChatMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content,
      timestamp: new Date(),
      metadata: databaseName ? { database_name: databaseName } : undefined
    }
    messages.value.push(userMessage)

    // Send via SSE
    try {
      sseService.sendMessage(content, databaseName)
      isTyping.value = true
    } catch (error) {
      console.error('Error sending message:', error)
      throw error
    }
  }

  function findLatestToolMessage(toolName: string): ChatMessage | undefined {
    for (let index = messages.value.length - 1; index >= 0; index -= 1) {
      const message = messages.value[index]
      if (message.role === 'tool' && message.toolCall?.toolName === toolName) {
        return message
      }
    }
    return undefined
  }

  /**
   * Handle streaming chunk from SSE
   */
  function handleStreamingChunk(chunk: any) {
    console.log('[ChatStore] Received chunk:', chunk.type, chunk)

    switch (chunk.type) {
      case 'thinking':
        // Just set typing indicator, don't create message
        isTyping.value = true
        break

      case 'tool_call': {
        isTyping.value = true
        const toolName = chunk.metadata?.tool_name || 'Unknown tool'
        const toolStatus = chunk.metadata?.status || 'executing'
        const toolArgs = chunk.metadata?.args || {}
        const latestToolMessage = findLatestToolMessage(toolName)
        const shouldCreateNewMessage =
          !latestToolMessage || (toolStatus === 'started' && latestToolMessage.toolCall?.status === 'completed')

        if (shouldCreateNewMessage) {
          // Create new tool message
          messages.value.push({
            id: `tool-${Date.now()}-${Math.random()}`,
            role: 'tool',
            content: '',
            timestamp: new Date(),
            metadata: chunk.metadata,
            isStreaming: false,
            toolCall: {
              toolName,
              toolArgs,
              status: toolStatus
            }
          })
        } else if (latestToolMessage?.toolCall) {
          // Update existing tool message
          const previousToolCall = latestToolMessage.toolCall
          latestToolMessage.metadata = { ...latestToolMessage.metadata, ...chunk.metadata }
          latestToolMessage.timestamp = new Date()
          latestToolMessage.toolCall = {
            toolName,
            toolArgs: Object.keys(toolArgs).length > 0 ? toolArgs : previousToolCall.toolArgs,
            toolResult: previousToolCall.toolResult,
            toolError: previousToolCall.toolError,
            status: toolStatus
          }
        }
        break
      }

      case 'tool_result': {
        const toolName = chunk.metadata?.tool_name || 'Unknown tool'
        const toolResult = chunk.metadata?.result ?? chunk.content
        const toolError = chunk.metadata?.error
        const toolStatus = chunk.metadata?.status || (toolError ? 'error' : 'completed')
        const toolMessage = findLatestToolMessage(toolName)

        if (toolMessage?.toolCall) {
          // Update existing tool message with result
          const previousToolArgs = toolMessage.toolCall.toolArgs
          toolMessage.metadata = { ...toolMessage.metadata, ...chunk.metadata }
          toolMessage.timestamp = new Date()
          toolMessage.toolCall = {
            toolName,
            toolArgs: chunk.metadata?.tool_args || previousToolArgs,
            toolResult,
            toolError,
            status: toolStatus
          }
        } else {
          // Create new tool result message
          messages.value.push({
            id: `tool-result-${Date.now()}-${Math.random()}`,
            role: 'tool',
            content: '',
            timestamp: new Date(),
            metadata: chunk.metadata,
            isStreaming: false,
            toolCall: {
              toolName,
              toolArgs: chunk.metadata?.tool_args || {},
              toolResult,
              toolError,
              status: toolStatus
            }
          })
        }
        break
      }

      case 'chunk':
        // Real LLM output
        if (!currentStreamingMessage.value) {
          // Create new assistant message
          currentStreamingMessage.value = {
            id: `assistant-${Date.now()}`,
            role: 'assistant',
            content: chunk.content,
            timestamp: new Date(),
            isStreaming: true,
            metadata: chunk.metadata
          }
          messages.value.push(currentStreamingMessage.value)
        } else {
          // Append to existing message
          currentStreamingMessage.value.content += chunk.content
        }
        break

      case 'complete':
        // Finalize message
        if (currentStreamingMessage.value) {
          currentStreamingMessage.value.isStreaming = false
          currentStreamingMessage.value.metadata = chunk.metadata
        }
        currentStreamingMessage.value = null
        isTyping.value = false
        break

      case 'error':
        // Handle error
        if (currentStreamingMessage.value) {
          currentStreamingMessage.value.content = `错误: ${chunk.content}`
          currentStreamingMessage.value.isStreaming = false
        } else {
          messages.value.push({
            id: `error-${Date.now()}`,
            role: 'system',
            content: `错误: ${chunk.content}`,
            timestamp: new Date(),
            metadata: chunk.metadata
          })
        }
        currentStreamingMessage.value = null
        isTyping.value = false
        break
    }
  }

  /**
   * Create new conversation
   */
  async function createNewConversation(projectId: string, title?: string) {
    const conversation = await api.createConversation({
      project_id: projectId,
      title
    })
    return conversation
  }

  /**
   * Clear current conversation
   */
  function clearConversation() {
    if (isConnected.value) {
      sseService.disconnect()
    }
    sseService.clearCallbacks()
    currentConversation.value = null
    messages.value = []
    isConnected.value = false
    isTyping.value = false
    currentStreamingMessage.value = null
  }

  return {
    // State
    currentConversation,
    messages,
    isConnected,
    isTyping,
    hasMessages,

    // Actions
    connectToConversation,
    sendMessage,
    createNewConversation,
    clearConversation
  }
})
