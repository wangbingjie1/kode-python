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

export interface ChartData {
  type: string
  config: any
  metadata?: Record<string, any>
}

export interface Insight {
  type: string
  severity: string
  content: string
  icon?: string
  metadata?: Record<string, any>
}

export interface TokenUsage {
  input_tokens: number
  output_tokens: number
  total_tokens: number
  cache_creation_input_tokens?: number
  cache_read_input_tokens?: number
  iteration?: number
}

export interface ConversationTokenUsage {
  total_input_tokens: number
  total_output_tokens: number
  total_tokens: number
  cache_creation_input_tokens: number
  cache_read_input_tokens: number
  iterations: number
  tool_calls_count: number
}

export interface UserInputQuestion {
  question: string
  question_type: 'text' | 'select' | 'multiselect' | 'confirm'
  options?: string[]
  default_value?: string
  required?: boolean
  context?: string
}

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant' | 'system' | 'tool' | 'chart' | 'insight'
  content: string
  timestamp: Date
  isStreaming?: boolean
  metadata?: Record<string, any>
  toolCall?: ToolCall
  chart?: ChartData
  insights?: Insight[]
  tokenUsage?: TokenUsage  // 每次 API 调用的 token 使用
  userInputQuestion?: UserInputQuestion  // 交互式提问数据
}

export const useChatStore = defineStore('chat', () => {
  // State
  const currentConversation = ref<Conversation | null>(null)
  const messages = ref<ChatMessage[]>([])
  const isConnected = ref(false)
  const isTyping = ref(false)
  const currentStreamingMessage = ref<ChatMessage | null>(null)
  const conversationTokenUsage = ref<ConversationTokenUsage>({
    total_input_tokens: 0,
    total_output_tokens: 0,
    total_tokens: 0,
    cache_creation_input_tokens: 0,
    cache_read_input_tokens: 0,
    iterations: 0,
    tool_calls_count: 0
  })

  // 用户输入状态
  const pendingUserInput = ref<ChatMessage | null>(null)  // 当前等待用户回答的消息

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
      messages.value = history.map(msg => {
        // 兼容后端返回的 message_metadata 字段名
        const metadata = (msg as any).message_metadata || msg.metadata || {}

        const baseMessage = {
          id: msg.id,
          role: msg.role as 'user' | 'assistant' | 'chart' | 'insight',
          content: msg.content,
          timestamp: new Date(msg.created_at),
          metadata
        }

        // 还原 chart 消息的数据结构
        if (msg.role === 'chart' && metadata?.chart_config) {
          console.log('[ChatStore] Restoring chart from history:', {
            chart_type: metadata.chart_type,
            chart_config_type: typeof metadata.chart_config,
            chart_config: metadata.chart_config
          })

          // 如果 chart_config 是字符串,需要解析
          let chartConfig = metadata.chart_config
          if (typeof chartConfig === 'string') {
            try {
              chartConfig = JSON.parse(chartConfig)
              console.log('[ChatStore] Parsed chart config from string:', chartConfig)
            } catch (e) {
              console.error('[ChatStore] Failed to parse chart config:', e)
            }
          }

          return {
            ...baseMessage,
            chart: {
              type: metadata.chart_type || 'unknown',
              config: chartConfig,
              metadata: metadata
            }
          }
        }

        // 还原 insight 消息的数据结构
        if (msg.role === 'insight' && metadata?.insights) {
          return {
            ...baseMessage,
            insights: metadata.insights
          }
        }

        return baseMessage
      })
      console.log('[ChatStore] Loaded', messages.value.length, 'messages')

      // Clear old callbacks before setting up new ones
      sseService.clearCallbacks()
      console.log('[ChatStore] Cleared old SSE callbacks')

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
      case 'thinking': {
        // Create or update thinking message
        isTyping.value = true

        // Check if we already have a thinking message
        if (currentStreamingMessage.value && currentStreamingMessage.value.metadata?.isThinking) {
          // Append to existing thinking message
          currentStreamingMessage.value.content += chunk.content
        } else {
          // Create new thinking message
          currentStreamingMessage.value = {
            id: `thinking-${Date.now()}`,
            role: 'assistant',
            content: chunk.content,
            timestamp: new Date(),
            isStreaming: true,
            metadata: { isThinking: true, iteration: chunk.metadata?.iteration }
          }
          messages.value.push(currentStreamingMessage.value)
        }
        break
      }

      case 'tool_call': {
        isTyping.value = true

        // Finalize any streaming assistant message before tool call
        if (currentStreamingMessage.value) {
          currentStreamingMessage.value.isStreaming = false
          currentStreamingMessage.value = null
        }

        const toolName = chunk.metadata?.tool_name || 'Unknown tool'
        const toolStatus = chunk.metadata?.status || 'executing'
        const toolArgs = chunk.metadata?.args || {}

        console.log('[ChatStore] Processing tool_call:', {
          toolName,
          toolStatus,
          toolArgs,
          fullMetadata: chunk.metadata
        })

        const latestToolMessage = findLatestToolMessage(toolName)
        const shouldCreateNewMessage =
          !latestToolMessage || (toolStatus === 'started' && latestToolMessage.toolCall?.status === 'completed')

        if (shouldCreateNewMessage) {
          // Create new tool message
          const newMessage = {
            id: `tool-${Date.now()}-${Math.random()}`,
            role: 'tool' as const,
            content: '',
            timestamp: new Date(),
            metadata: chunk.metadata,
            isStreaming: false,
            toolCall: {
              toolName,
              toolArgs,
              status: toolStatus
            }
          }
          console.log('[ChatStore] Creating new tool message:', newMessage)
          messages.value.push(newMessage)
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
          console.log('[ChatStore] Updated existing tool message:', latestToolMessage)
        }
        break
      }

      case 'tool_result': {
        const toolName = chunk.metadata?.tool_name || 'Unknown tool'
        const toolResult = chunk.metadata?.result ?? chunk.content
        const toolError = chunk.metadata?.error
        const toolStatus = chunk.metadata?.status || (toolError ? 'error' : 'completed')

        console.log('[ChatStore] Processing tool_result:', {
          toolName,
          toolResult: typeof toolResult === 'string' ? toolResult.substring(0, 100) : toolResult,
          toolError,
          toolStatus,
          fullMetadata: chunk.metadata
        })

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
          console.log('[ChatStore] Updated tool message with result:', toolMessage.toolCall)
        } else {
          // Create new tool result message
          const newMessage = {
            id: `tool-result-${Date.now()}-${Math.random()}`,
            role: 'tool' as const,
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
          }
          console.log('[ChatStore] Creating new tool result message:', newMessage)
          messages.value.push(newMessage)
        }
        break
      }

      case 'text_complete':
        // Text portion complete (before tool calls in same iteration)
        if (currentStreamingMessage.value) {
          currentStreamingMessage.value.isStreaming = false
          currentStreamingMessage.value = null
        }
        break

      case 'chunk':
        // Real LLM output
        if (!currentStreamingMessage.value || currentStreamingMessage.value.metadata?.isThinking) {
          // Finalize thinking message if exists
          if (currentStreamingMessage.value?.metadata?.isThinking) {
            currentStreamingMessage.value.isStreaming = false
          }

          // Create new assistant message for real content
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

      case 'token_usage': {
        // 处理每次 API 调用的 token 统计
        const usage: TokenUsage = {
          input_tokens: chunk.metadata?.input_tokens || 0,
          output_tokens: chunk.metadata?.output_tokens || 0,
          total_tokens: chunk.metadata?.total_tokens || 0,
          cache_creation_input_tokens: chunk.metadata?.cache_creation_input_tokens,
          cache_read_input_tokens: chunk.metadata?.cache_read_input_tokens,
          iteration: chunk.metadata?.iteration
        }

        // 累加到会话总计
        conversationTokenUsage.value.total_input_tokens += usage.input_tokens
        conversationTokenUsage.value.total_output_tokens += usage.output_tokens
        conversationTokenUsage.value.total_tokens += usage.total_tokens
        conversationTokenUsage.value.cache_creation_input_tokens += usage.cache_creation_input_tokens || 0
        conversationTokenUsage.value.cache_read_input_tokens += usage.cache_read_input_tokens || 0
        conversationTokenUsage.value.iterations = usage.iteration || 0

        console.log('[ChatStore] Token usage:', usage)
        console.log('[ChatStore] Conversation total:', conversationTokenUsage.value)
        break
      }

      case 'complete':
        // Finalize message
        if (currentStreamingMessage.value) {
          currentStreamingMessage.value.isStreaming = false
          currentStreamingMessage.value.metadata = chunk.metadata
        }
        currentStreamingMessage.value = null
        isTyping.value = false

        // 从 complete 元数据中获取总计（如果有）
        if (chunk.metadata?.token_usage) {
          const finalUsage = chunk.metadata.token_usage
          conversationTokenUsage.value = {
            total_input_tokens: finalUsage.total_input_tokens || 0,
            total_output_tokens: finalUsage.total_output_tokens || 0,
            total_tokens: finalUsage.total_tokens || 0,
            cache_creation_input_tokens: finalUsage.cache_creation_input_tokens || 0,
            cache_read_input_tokens: finalUsage.cache_read_input_tokens || 0,
            iterations: chunk.metadata.iterations || 0,
            tool_calls_count: chunk.metadata.tool_calls?.length || 0
          }
          console.log('[ChatStore] Final conversation token usage:', conversationTokenUsage.value)
        }

        // 刷新配额信息（异步，不阻塞）
        ;(async () => {
          try {
            const { useBillingStore } = await import('@/stores/billing')
            const billingStore = useBillingStore()
            await billingStore.fetchUsageSummary()
          } catch (err) {
            console.warn('Failed to refresh billing usage:', err)
          }
        })()
        break

      case 'chart': {
        // 处理图表消息
        // chunk.content 应该是 config 对象 (已解析的 JSON)
        const chartConfig = typeof chunk.content === 'string'
          ? JSON.parse(chunk.content)
          : chunk.content

        const chartMessage = {
          id: `chart-${Date.now()}-${Math.random()}`,
          role: 'chart' as const,
          content: '',
          timestamp: new Date(),
          isStreaming: false,
          chart: {
            type: chunk.metadata?.chart_type || 'unknown',
            config: chartConfig,  // 确保是对象而不是字符串
            metadata: chunk.metadata
          }
        }
        console.log('[ChatStore] Adding chart message:', chartMessage)
        console.log('[ChatStore] Chart config:', chartConfig)
        messages.value.push(chartMessage)
        break
      }

      case 'insight': {
        // 处理洞察消息
        const insightMessage = {
          id: `insight-${Date.now()}-${Math.random()}`,
          role: 'insight' as const,
          content: '',
          timestamp: new Date(),
          isStreaming: false,
          insights: chunk.content,
          metadata: chunk.metadata
        }
        console.log('[ChatStore] Adding insight message:', insightMessage)
        messages.value.push(insightMessage)
        break
      }

      case 'user_input_required': {
        // Agent 需要用户输入
        console.log('[ChatStore] User input required:', chunk.metadata?.question_data)

        const questionData: UserInputQuestion = chunk.metadata?.question_data || {
          question: chunk.content,
          question_type: 'text'
        }

        // 创建用户输入消息（带特殊标记）
        const userInputMessage: ChatMessage = {
          id: `user-input-${Date.now()}`,
          role: 'assistant',
          content: questionData.question,
          timestamp: new Date(),
          isStreaming: false,
          metadata: {
            ...chunk.metadata,
            requiresUserInput: true
          },
          userInputQuestion: questionData
        }

        console.log('[ChatStore] Adding user input message:', userInputMessage)
        messages.value.push(userInputMessage)

        // 设置为待回答状态
        pendingUserInput.value = userInputMessage

        // 停止 typing 状态（等待用户输入）
        isTyping.value = false

        // 通知前端渲染问题界面
        notification.info(
          '需要您的输入',
          questionData.context || '请回答问题以继续执行'
        )

        break
      }

      case 'user_input_received': {
        // 用户已回答，清除待回答状态
        console.log('[ChatStore] User input received:', chunk.content)
        pendingUserInput.value = null

        // 恢复 typing 状态（Agent 继续执行）
        isTyping.value = true

        break
      }

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
   * 提交用户对交互式提问的响应
   */
  async function submitUserResponse(answer: any) {
    if (!pendingUserInput.value) {
      console.warn('[ChatStore] No pending user input to submit')
      return
    }

    if (!currentConversation.value) {
      console.error('[ChatStore] No current conversation')
      return
    }

    const questionType = pendingUserInput.value.userInputQuestion?.question_type || 'text'

    try {
      console.log('[ChatStore] Submitting user response:', { answer, questionType })

      // 调用 API 提交响应
      await api.submitUserResponse(currentConversation.value.id, {
        answer,
        question_type: questionType
      })

      console.log('[ChatStore] User response submitted successfully')

      // 添加用户答案到消息列表（作为用户消息）
      const answerText = Array.isArray(answer)
        ? answer.join(', ')
        : String(answer)

      messages.value.push({
        id: `user-answer-${Date.now()}`,
        role: 'user',
        content: `回答: ${answerText}`,
        timestamp: new Date(),
        metadata: {
          isUserAnswer: true,
          questionId: pendingUserInput.value.id
        }
      })

      // 清除待回答状态（等待 user_input_received 事件）
      // pendingUserInput.value = null  // 由 SSE 事件处理
    } catch (error: any) {
      console.error('[ChatStore] Error submitting user response:', error)
      notification.error(
        '提交失败',
        error.response?.data?.detail || '无法提交您的回答，请重试'
      )
      throw error
    }
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

    // Reset token usage
    conversationTokenUsage.value = {
      total_input_tokens: 0,
      total_output_tokens: 0,
      total_tokens: 0,
      cache_creation_input_tokens: 0,
      cache_read_input_tokens: 0,
      iterations: 0,
      tool_calls_count: 0
    }
  }

  return {
    // State
    currentConversation,
    messages,
    isConnected,
    isTyping,
    hasMessages,
    conversationTokenUsage,
    pendingUserInput,  // 新增：待回答的用户输入

    // Actions
    connectToConversation,
    sendMessage,
    createNewConversation,
    clearConversation,
    submitUserResponse  // 新增：提交用户响应
  }
})
