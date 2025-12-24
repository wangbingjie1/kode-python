/**
 * Chat Store
 *
 * Manages chat state with Pinia
 */

import { defineStore } from 'pinia'
import { ref, computed, onUnmounted } from 'vue'
import type { Conversation, Message } from '@/services/api'
import { sseService, heartbeatService } from '@/services/sse'
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
  regular_input_tokens: number
  total_input_tokens: number
  total_output_tokens: number
  total_tokens: number
  cache_creation_input_tokens: number
  cache_read_input_tokens: number
  iterations: number
  tool_calls_count: number
  cost_breakdown?: {
    regular_input_cost?: number
    cache_creation_cost?: number
    cache_read_cost?: number
    output_cost?: number
  }
  total_cost?: number
  cache_savings?: number
  savings_percentage?: number
}

export interface UserInputQuestion {
  question: string
  question_type: 'text' | 'select' | 'multiselect' | 'confirm' | 'batch_form'
  options?: any[]  // For batch_form, this contains the groups array
  default_value?: string
  required?: boolean
  context?: string
}

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant' | 'system' | 'tool' | 'chart' | 'insight' | 'progress'
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
  const tokenStatsStatus = ref<'idle' | 'pending' | 'final'>('idle')
  const conversationTokenUsage = ref<ConversationTokenUsage>({
    regular_input_tokens: 0,
    total_input_tokens: 0,
    total_output_tokens: 0,
    total_tokens: 0,
    cache_creation_input_tokens: 0,
    cache_read_input_tokens: 0,
    iterations: 0,
    tool_calls_count: 0,
    cost_breakdown: {
      regular_input_cost: 0,
      cache_creation_cost: 0,
      cache_read_cost: 0,
      output_cost: 0
    },
    total_cost: 0,
    cache_savings: 0,
    savings_percentage: 0
  })

  // 用户输入状态
  const pendingUserInput = ref<ChatMessage | null>(null)  // 当前等待用户回答的消息

  // Computed
  const hasMessages = computed(() => messages.value.length > 0)

  // ============================================================
  // 心跳连接管理
  // ============================================================

  /**
   * 启动心跳连接（登录后调用）
   */
  function startHeartbeat() {
    // 先清除旧的回调,避免重复注册
    heartbeatService.clearCallbacks()

    // 注册连接状态变化回调
    heartbeatService.onConnectionChange((connected) => {
      isConnected.value = connected
      console.log('[ChatStore] Heartbeat connection status:', connected)
    })

    // 启动心跳（会触发 connected 事件并调用回调）
    heartbeatService.connect()
    console.log('[ChatStore] Heartbeat started')
  }

  /**
   * 停止心跳连接（登出时调用）
   */
  function stopHeartbeat() {
    heartbeatService.disconnect()
    heartbeatService.clearCallbacks()
    isConnected.value = false
    console.log('[ChatStore] Heartbeat stopped')
  }

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

      // 🔥 合并 tool_use 和 tool_result 消息对，并正确插入 chart/insight
      const mergedMessages: ChatMessage[] = []
      const toolUseMap = new Map<string, { msg: any, index: number }>() // tool_use_id -> {msg, index}
      
      // 📊 收集需要插入的 charts 和 insights (来自 final 消息)
      const chartsToInsert: Array<{ chartData: any, afterToolName: string }> = []
      const insightsToInsert: Array<{ insightData: any, afterToolName: string }> = []

      // 第一遍：处理所有消息，收集 charts/insights 但不立即插入
      for (const msg of history) {
        // 🔍 DEBUG: 打印原始消息结构(仅打印前2条tool相关消息)
        if ((msg.role === 'assistant' || msg.role === 'user') && history.indexOf(msg) < 10) {
          console.log('[ChatStore] Raw message from API:', {
            role: msg.role,
            hasMetadata: 'metadata' in msg,
            hasMessageMetadata: 'message_metadata' in (msg as any),
            metadataKeys: msg.metadata ? Object.keys(msg.metadata) : 'N/A',
            messageMetadataKeys: (msg as any).message_metadata ? Object.keys((msg as any).message_metadata) : 'N/A',
            metadataType: msg.metadata ? (msg.metadata as any).type : 'N/A'
          })
        }

        // 兼容后端返回的 message_metadata 字段名
        const metadata = (msg as any).message_metadata || msg.metadata || {}

        const baseMessage = {
          id: msg.id,
          role: msg.role as 'user' | 'assistant' | 'chart' | 'insight' | 'tool',
          content: msg.content,
          timestamp: new Date(msg.created_at),
          metadata
        }

        // 还原 chart 消息的数据结构 (直接保存的独立 chart 消息)
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
              console.error('[ChatStore] Failed to parse chart config from history:', e)
              console.error('[ChatStore] Raw chart config:', chartConfig)
              // 如果解析失败,返回普通消息
              mergedMessages.push(baseMessage)
              continue
            }
          }

          // 验证 chartConfig 是有效对象
          if (!chartConfig || typeof chartConfig !== 'object') {
            console.error('[ChatStore] Invalid chart config in history (not an object):', chartConfig)
            mergedMessages.push(baseMessage)
            continue
          }

          mergedMessages.push({
            ...baseMessage,
            chart: {
              type: metadata.chart_type || 'unknown',
              config: chartConfig,
              metadata: metadata
            }
          })
          continue
        }

        // 还原 insight 消息的数据结构 (直接保存的独立 insight 消息)
        if (msg.role === 'insight' && metadata?.insights) {
          mergedMessages.push({
            ...baseMessage,
            insights: metadata.insights
          })
          continue
        }

        // 🔥 [FIX] 从 final 消息中提取 charts 和 insights，但不立即插入
        if (metadata?.type === 'final') {
          // 1. 提取 charts 到待插入列表
          if (metadata.charts && Array.isArray(metadata.charts)) {
            console.log('[ChatStore] Found charts in final message:', metadata.charts.length)
            for (const chartData of metadata.charts) {
              let chartConfig = chartData.chart_config
              
              // 解析 config 如果是字符串
              if (typeof chartConfig === 'string') {
                try {
                  chartConfig = JSON.parse(chartConfig)
                } catch (e) {
                  console.error('[ChatStore] Failed to parse chart config from final message:', e)
                  continue
                }
              }

              if (chartConfig && typeof chartConfig === 'object') {
                chartsToInsert.push({
                  chartData: {
                    ...baseMessage,
                    id: `chart-${baseMessage.id}-${Math.random()}`,
                    role: 'chart',
                    chart: {
                      type: chartData.chart_type || 'unknown',
                      config: chartConfig,
                      metadata: { data_summary: chartData.data_summary }
                    }
                  },
                  afterToolName: 'ChartGenerator' // 插入到 ChartGenerator 之后
                })
              }
            }
          }

          // 2. 提取 insights 到待插入列表
          if (metadata.insights && Array.isArray(metadata.insights)) {
            console.log('[ChatStore] Found insights in final message:', metadata.insights.length)
            for (const insightData of metadata.insights) {
              if (insightData.insights && Array.isArray(insightData.insights)) {
                insightsToInsert.push({
                  insightData: {
                    ...baseMessage,
                    id: `insight-${baseMessage.id}-${Math.random()}`,
                    role: 'insight',
                    insights: insightData.insights,
                    metadata: { 
                        total_count: insightData.total_count,
                        data_summary: insightData.data_summary
                    }
                  },
                  afterToolName: 'InsightExtractor' // 插入到 InsightExtractor 之后
                })
              }
            }
          }

          // 3. 如果 final 消息本身没有文本内容，就跳过
          if (!msg.content) {
            continue
          }
        }

        // 🔥 处理 tool_use 和 tool_result 消息配对
        if (metadata?.type === 'tool_use') {
          // 这是工具调用，先占位并保存到 map 中
          const toolUseId = metadata.tool_use_id
          if (toolUseId) {
            const index = mergedMessages.length
            const placeholderMsg = {
              ...baseMessage,
              role: 'tool' as const,
              toolCall: {
                toolName: metadata.tool_name || 'Unknown tool',
                toolArgs: metadata.tool_args || {},
                status: 'started'  // 初始状态为 started，等待 result 更新
              }
            }
            // 先占位
            mergedMessages.push(placeholderMsg)
            // 记录位置，等待 tool_result 更新
            toolUseMap.set(toolUseId, { msg: placeholderMsg, index })
            console.log('[ChatStore] Added tool_use placeholder at index', index, ':', toolUseId, metadata.tool_name)
          }
          continue
        }

        if (metadata?.type === 'tool_result') {
          // 这是工具结果，查找对应的 tool_use 并更新
          const toolUseId = metadata.tool_use_id
          const toolUseData = toolUseId ? toolUseMap.get(toolUseId) : null

          console.log('[ChatStore] Processing tool_result:', {
            toolUseId: toolUseId?.substring(0, 20),
            toolName: metadata.tool_name,
            foundMatch: !!toolUseData,
            availableToolUseIds: Array.from(toolUseMap.keys()).map(id => id.substring(0, 20))
          })

          if (toolUseData) {
            // 找到配对，直接更新占位的消息
            const toolUseMsg = toolUseData.msg
            toolUseMsg.toolCall.toolResult = msg.content
            toolUseMsg.toolCall.toolError = metadata.status === 'error' ? metadata.error : undefined
            toolUseMsg.toolCall.status = metadata.status || 'completed'  // 使用 tool_result 的 status
            // 注意：保持 tool_use 的原始时间戳，不要用 tool_result 的

            toolUseMap.delete(toolUseId) // 清理已配对的
            console.log('[ChatStore] ✅ Updated tool_use at index', toolUseData.index, 'with result:', toolUseMsg.toolCall.toolName, 'status:', toolUseMsg.toolCall.status)
          } else {
            // 没找到配对，检查是否是重复的消息（已处理过的 tool_use）
            let isDuplicate = false

            // Case 1: 有 tool_use_id，检查是否已存在于 mergedMessages 中
            if (toolUseId) {
              const existing = mergedMessages.find(m => m.metadata?.tool_use_id === toolUseId)
              if (existing) {
                isDuplicate = true
              }
            }
            // Case 2: 无 tool_use_id，检查最近的消息是否是同名且已完成的工具调用
            else {
              // 向回查找最近的同名工具消息
              for (let i = mergedMessages.length - 1; i >= Math.max(0, mergedMessages.length - 10); i--) {
                const m = mergedMessages[i]
                if (m.role === 'tool' && m.toolCall?.toolName === metadata.tool_name) {
                  // 如果该工具消息已有结果或状态为完成，则当前无 ID 的消息极可能是重复的
                  if (m.toolCall.status === 'completed' || m.toolCall.toolResult) {
                    isDuplicate = true
                  }
                  break // 只检查最近的一个同名工具
                }
              }
            }

            if (isDuplicate) {
              console.log('[ChatStore] Skipping duplicate/redundant tool_result:', { toolName: metadata.tool_name, toolUseId })
              continue
            }

            // 确实没找到配对且不是重复，创建独立的 tool 消息
            console.warn('[ChatStore] ❌ tool_result without tool_use, creating standalone message. tool_use_id:', toolUseId?.substring(0, 20))
            mergedMessages.push({
              ...baseMessage,
              role: 'tool' as const,
              toolCall: {
                toolName: metadata.tool_name || 'Unknown tool',
                toolArgs: metadata.tool_args || {},
                toolResult: msg.content,
                toolError: metadata.status === 'error' ? metadata.error : undefined,
                status: metadata.status || 'completed'
              }
            })
          }
          continue
        }

        // 普通消息（user/assistant）
        mergedMessages.push(baseMessage)
      }

      // 检查未配对的 tool_use（历史数据中可能出现）
      for (const [toolUseId, toolUseData] of toolUseMap.entries()) {
        console.warn('[ChatStore] Orphaned tool_use (no result):', toolUseId, 'at index', toolUseData.index)
        // 🔥 如果是从数据库加载的历史数据，没有 result 说明工具已经执行完成了
        // 将状态改为 'completed'，避免显示"执行中..."
        toolUseData.msg.toolCall.status = 'completed'
        console.log('[ChatStore] Set orphaned tool status to completed')
      }

      // 🎯 第二遍：将收集到的 charts/insights 插入到对应工具调用之后
      const finalMessages: ChatMessage[] = []
      let chartIndex = 0
      let insightIndex = 0

      for (let i = 0; i < mergedMessages.length; i++) {
        const msg = mergedMessages[i]
        finalMessages.push(msg)

        // 如果是工具调用消息，检查是否需要在其后插入 chart/insight
        if (msg.role === 'tool' && msg.toolCall) {
          const toolName = msg.toolCall.toolName

          // 在 ChartGenerator 之后插入 chart
          if (toolName === 'ChartGenerator' && chartIndex < chartsToInsert.length) {
            const chartToInsert = chartsToInsert[chartIndex]
            if (chartToInsert.afterToolName === 'ChartGenerator') {
              console.log(`[ChatStore] ✅ Inserting chart after ChartGenerator at position ${finalMessages.length}`)
              finalMessages.push(chartToInsert.chartData)
              chartIndex++
            }
          }

          // 在 InsightExtractor 之后插入 insight
          if (toolName === 'InsightExtractor' && insightIndex < insightsToInsert.length) {
            const insightToInsert = insightsToInsert[insightIndex]
            if (insightToInsert.afterToolName === 'InsightExtractor') {
              console.log(`[ChatStore] ✅ Inserting insight after InsightExtractor at position ${finalMessages.length}`)
              finalMessages.push(insightToInsert.insightData)
              insightIndex++
            }
          }
        }
      }

      // 如果还有未插入的 charts/insights (没找到对应工具),放在最后
      while (chartIndex < chartsToInsert.length) {
        console.warn('[ChatStore] ⚠️ Chart without matching ChartGenerator tool, appending to end')
        finalMessages.push(chartsToInsert[chartIndex].chartData)
        chartIndex++
      }
      while (insightIndex < insightsToInsert.length) {
        console.warn('[ChatStore] ⚠️ Insight without matching InsightExtractor tool, appending to end')
        finalMessages.push(insightsToInsert[insightIndex].insightData)
        insightIndex++
      }

      messages.value = finalMessages
      console.log('[ChatStore] Loaded', messages.value.length, 'messages (merged tool messages)')

      // 🔍 DEBUG: 打印最终的消息顺序
      console.log('[ChatStore] Final message order:')
      finalMessages.forEach((m, i) => {
        const toolName = m.toolCall?.toolName || 'N/A'
        const roleInfo = m.role === 'chart' ? `chart(${m.chart?.type})` : m.role === 'insight' ? 'insight' : m.role
        const preview = m.content?.substring(0, 30) || 'N/A'
        console.log(`  ${i}: ${roleInfo} | ${toolName} | ${preview}`)
      })

      // Clear old callbacks before setting up new ones
      sseService.clearCallbacks()
      console.log('[ChatStore] Cleared old SSE callbacks')

      // Connect SSE (设置 conversation ID，不再设置假的 isConnected)
      sseService.connect(conversationId)
      // 注意: isConnected 现在由 heartbeatService 管理，不在这里设置
      console.log('[ChatStore] SSE ready for conversation. isConnected (from heartbeat):', isConnected.value)

      // Setup message handler
      sseService.onMessage((chunk) => {
        console.log('[ChatStore] SSE message received:', chunk.type)
        handleStreamingChunk(chunk)
      })

      sseService.onClose(() => {
        console.log('[ChatStore] SSE stream closed (message complete)')
        // isConnected 由 heartbeat 管理，这里不需要修改
      })

      sseService.onError((error) => {
        console.error('[ChatStore] SSE error:', error)
        notification.error('连接错误', 'SSE 连接失败: ' + error.message)
        // isConnected 由 heartbeat 管理，这里不需要修改
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
    // 检查心跳连接状态
    if (!isConnected.value) {
      notification.error('连接断开', '与服务器的连接已断开，请刷新页面重试')
      throw new Error('Not connected to server (heartbeat disconnected)')
    }

    // 检查是否有活跃的对话
    if (!sseService.isConnected()) {
      throw new Error('No active conversation')
    }

    // 标记 Token 统计生成中，避免 UI 闪跳
    tokenStatsStatus.value = 'pending'

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

  function findToolMessageByUseId(toolUseId: string): ChatMessage | undefined {
    // 精确匹配 tool_use_id（最可靠）
    for (let index = messages.value.length - 1; index >= 0; index -= 1) {
      const message = messages.value[index]
      if (message.role === 'tool' && message.metadata?.tool_use_id === toolUseId) {
        return message
      }
    }
    return undefined
  }

  function findLatestToolMessage(toolName: string): ChatMessage | undefined {
    // 兜底：按工具名查找最新的（用于没有 tool_use_id 的场景）
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
        const toolUseId = chunk.metadata?.tool_use_id  // 🔥 获取 tool_use_id

        console.log('[ChatStore] Processing tool_call:', {
          toolName,
          toolStatus,
          toolArgs,
          toolUseId,
          fullMetadata: chunk.metadata
        })

        // 🔥 优先使用 tool_use_id 精确匹配
        const existingToolMessage = toolUseId ? findToolMessageByUseId(toolUseId) : findLatestToolMessage(toolName)
        const shouldCreateNewMessage = !existingToolMessage || (toolStatus === 'started' && existingToolMessage.toolCall?.status === 'completed')

        if (shouldCreateNewMessage) {
          // Create new tool message
          const newMessage = {
            id: `tool-${Date.now()}-${Math.random()}`,
            role: 'tool' as const,
            content: '',
            timestamp: new Date(),
            metadata: { ...chunk.metadata, tool_use_id: toolUseId },  // 保存 tool_use_id
            isStreaming: false,
            toolCall: {
              toolName,
              toolArgs,
              status: toolStatus
            }
          }
          console.log('[ChatStore] Creating new tool message:', newMessage)
          messages.value.push(newMessage)
        } else if (existingToolMessage?.toolCall) {
          // Update existing tool message
          const previousToolCall = existingToolMessage.toolCall
          existingToolMessage.metadata = { ...existingToolMessage.metadata, ...chunk.metadata }
          existingToolMessage.timestamp = new Date()
          existingToolMessage.toolCall = {
            toolName,
            toolArgs: Object.keys(toolArgs).length > 0 ? toolArgs : previousToolCall.toolArgs,
            toolResult: previousToolCall.toolResult,
            toolError: previousToolCall.toolError,
            status: toolStatus
          }
          console.log('[ChatStore] Updated existing tool message:', existingToolMessage)
        }
        break
      }

      case 'tool_result': {
        const toolName = chunk.metadata?.tool_name || 'Unknown tool'
        const toolResult = chunk.metadata?.result ?? chunk.content
        const toolError = chunk.metadata?.error
        const toolStatus = chunk.metadata?.status || (toolError ? 'error' : 'completed')
        const toolUseId = chunk.metadata?.tool_use_id  // 🔥 获取 tool_use_id

        console.log('[ChatStore] Processing tool_result:', {
          toolName,
          toolResult: typeof toolResult === 'string' ? toolResult.substring(0, 100) : toolResult,
          toolError,
          toolStatus,
          toolUseId,
          fullMetadata: chunk.metadata
        })

        // 🔥 优先使用 tool_use_id 精确匹配
        const toolMessage = toolUseId ? findToolMessageByUseId(toolUseId) : findLatestToolMessage(toolName)

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
          // Create new tool result message（兜底，理论上不应该走到这里）
          console.warn('[ChatStore] tool_result without matching tool_use, creating standalone message')
          const newMessage = {
            id: `tool-result-${Date.now()}-${Math.random()}`,
            role: 'tool' as const,
            content: '',
            timestamp: new Date(),
            metadata: { ...chunk.metadata, tool_use_id: toolUseId },
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
        // 每次 API 调用的 token 统计，前端累积，最终会被 final_token_stats 覆盖
        const usage: TokenUsage = {
          input_tokens: chunk.metadata?.input_tokens || 0,
          output_tokens: chunk.metadata?.output_tokens || 0,
          total_tokens: chunk.metadata?.total_tokens || 0,
          cache_creation_input_tokens: chunk.metadata?.cache_creation_input_tokens,
          cache_read_input_tokens: chunk.metadata?.cache_read_input_tokens,
          iteration: chunk.metadata?.iteration
        }

        // 不实时灌入 UI，等待 final_token_stats 统一覆盖，避免突变
        console.log('[ChatStore] Token usage (streaming, not applied to UI):', usage)
        break
      }

      case 'complete': {
        // Finalize message
        if (currentStreamingMessage.value) {
          currentStreamingMessage.value.isStreaming = false
          currentStreamingMessage.value.metadata = chunk.metadata
        }
        currentStreamingMessage.value = null
        isTyping.value = false

        // 从 complete 元数据里获取总计（兜底校验）
        if (chunk.metadata?.token_usage) {
          const finalUsage = chunk.metadata.token_usage
          const cacheCreation = finalUsage.cache_creation_input_tokens || 0
          const cacheRead = finalUsage.cache_read_input_tokens || 0
          const regularInput = finalUsage.regular_input_tokens ??
            finalUsage.input_tokens ??
            Math.max((finalUsage.total_input_tokens || 0) - cacheCreation - cacheRead, 0)
          const totalInput = finalUsage.total_input_tokens ||
            regularInput + cacheCreation + cacheRead
          const outputTokens = finalUsage.total_output_tokens || finalUsage.output_tokens || 0
          const totalTokens = finalUsage.total_tokens || totalInput + outputTokens

          conversationTokenUsage.value = {
            regular_input_tokens: regularInput,
            total_input_tokens: totalInput,
            total_output_tokens: outputTokens,
            total_tokens: totalTokens,
            cache_creation_input_tokens: cacheCreation,
            cache_read_input_tokens: cacheRead,
            iterations: chunk.metadata.iterations || 0,
            tool_calls_count: chunk.metadata.tool_calls?.length || 0
          }
          console.log('[ChatStore] Final conversation token usage:', conversationTokenUsage.value)
          tokenStatsStatus.value = 'final'
        }

        // 刷新计费信息（异步，不阻塞 UI）
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
      }

      case 'chart': {
        // 处理图表消息
        // chunk.content 可能是对象或字符串,需要统一处理
        let chartConfig = chunk.content

        // 如果是字符串,尝试解析
        if (typeof chartConfig === 'string') {
          try {
            chartConfig = JSON.parse(chartConfig)
            console.log('[ChatStore] Parsed chart config from string')
          } catch (e) {
            console.error('[ChatStore] Failed to parse chart config:', e)
            console.error('[ChatStore] Raw content:', chartConfig)
            // 如果解析失败,跳过此图表
            break
          }
        }

        // 验证 chartConfig 是有效对象
        if (!chartConfig || typeof chartConfig !== 'object') {
          console.error('[ChatStore] Invalid chart config (not an object):', chartConfig)
          break
        }

        const chartMessage = {
          id: `chart-${Date.now()}-${Math.random()}`,
          role: 'chart' as const,
          content: '',
          timestamp: new Date(),
          isStreaming: false,
          chart: {
            type: chunk.metadata?.chart_type || 'unknown',
            config: chartConfig,  // 确保是对象
            metadata: chunk.metadata
          }
        }
        console.log('[ChatStore] Adding chart message:', chartMessage)
        console.log('[ChatStore] Chart config type:', typeof chartConfig)
        console.log('[ChatStore] Chart config keys:', Object.keys(chartConfig))
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

      case 'progress': {
        // 处理进度消息（如本体构建进度）
        // 进度消息是临时的，用于实时显示进度，不保存到数据库
        // 我们可以选择：1) 显示在消息列表中（临时） 2) 显示在独立的进度条中
        // 这里选择显示在消息列表中，但每次新进度会替换旧的相同阶段的进度
        const stage = chunk.metadata?.stage || 'default'

        // 查找相同 stage 的现有进度消息并移除
        const existingProgressIndex = messages.value.findIndex(
          msg => msg.role === 'progress' && msg.metadata?.stage === stage
        )
        if (existingProgressIndex !== -1) {
          messages.value.splice(existingProgressIndex, 1)
        }

        // 添加新的进度消息
        const progressMessage = {
          id: `progress-${Date.now()}-${Math.random()}`,
          role: 'progress' as const,
          content: chunk.content,
          timestamp: new Date(),
          isStreaming: false,
          metadata: chunk.metadata
        }
        console.log('[ChatStore] Adding/updating progress message:', progressMessage)
        messages.value.push(progressMessage)
        break
      }

      case 'user_input_required': {
        // Agent 需要用户输入
        console.log('[ChatStore] User input required:', chunk.metadata?.question_data)

        const questionData: UserInputQuestion = chunk.metadata?.question_data || {
          question: chunk.content,
          question_type: 'text'
        }

        // 🔥 特殊处理:如果是 batch_form 类型,需要更新对应工具调用的 toolResult
        // 这样 ToolCallItem 组件才能从 parsedToolResult 中读取到 groups 数据
        if (questionData.question_type === 'batch_form' && questionData.options) {
          const toolUseId = chunk.metadata?.tool_use_id
          if (toolUseId) {
            const toolMessage = findToolMessageByUseId(toolUseId)
            if (toolMessage?.toolCall) {
              // 将 options 格式化为 groups 结构并保存到 toolResult
              const batchData = {
                status: 'success',
                total_loaded: questionData.options.reduce((sum: number, group: any) => sum + (group.question_count || 0), 0),
                groups: questionData.options,
                message: questionData.question,
                connection_name: chunk.metadata?.connection_name || toolMessage.toolCall.toolArgs?.connection_name
              }
              toolMessage.toolCall.toolResult = JSON.stringify(batchData, null, 2)
              console.log('[ChatStore] Updated tool message with batch data:', toolMessage)
              
              // 设置为待回答状态
              // 构造一个包含 userInputQuestion 的对象，以便 submitUserResponse 能正确识别类型
              pendingUserInput.value = {
                ...toolMessage,
                userInputQuestion: questionData
              }
              
              // 停止 typing 状态(等待用户输入)
              isTyping.value = false
              
              // 对于 batch_form,不创建新的 userInputMessage
              // ToolCallItem 组件会自动显示对话框
              console.log('[ChatStore] batch_form will be handled by ToolCallItem component')
              break
            }
          }
        }

        // 创建用户输入消息(带特殊标记) - 仅用于非 batch_form 类型
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

        // 停止 typing 状态(等待用户输入)
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

      case 'final_token_stats': {
        // ⚠ 收到后端最终 token / 成本统计
        const finalStats = chunk.metadata
        console.log('[ChatStore] Final token stats received:', finalStats)

        const cacheCreation = finalStats.cache_creation_tokens || 0
        const cacheRead = finalStats.cache_read_tokens || 0
        const totalInput = finalStats.total_input_tokens || (cacheCreation + cacheRead)
        const regularInput = finalStats.regular_input_tokens ??
          Math.max(totalInput - cacheCreation - cacheRead, 0)
        const outputTokens = finalStats.total_output_tokens || 0
        const totalTokens = finalStats.total_tokens || (totalInput + outputTokens)

        const costBreakdown = finalStats.cost_breakdown || {}
        const regularInputCost = costBreakdown.regular_input_cost ?? (regularInput * 3 / 1_000_000)
        const cacheCreationCost = costBreakdown.cache_creation_cost ?? (cacheCreation * 3.75 / 1_000_000)
        const cacheReadCost = costBreakdown.cache_read_cost ?? (cacheRead * 0.30 / 1_000_000)
        const outputCost = costBreakdown.output_cost ?? (outputTokens * 15 / 1_000_000)
        const totalCost = finalStats.total_cost ?? (regularInputCost + cacheCreationCost + cacheReadCost + outputCost)

        const noCacheCost = totalInput * 3 / 1_000_000 + outputCost
        const cacheSavings = finalStats.cache_savings ?? (noCacheCost - totalCost)
        const savingsPct = finalStats.savings_percentage ?? (noCacheCost > 0 ? (cacheSavings / noCacheCost * 100) : 0)

        conversationTokenUsage.value = {
          regular_input_tokens: regularInput,
          total_input_tokens: totalInput,
          total_output_tokens: outputTokens,
          total_tokens: totalTokens,
          cache_creation_input_tokens: cacheCreation,
          cache_read_input_tokens: cacheRead,
          iterations: finalStats.iteration_count || 0,
          tool_calls_count: conversationTokenUsage.value.tool_calls_count, // 保持之前的工具调用计数
          cost_breakdown: {
            regular_input_cost: regularInputCost,
            cache_creation_cost: cacheCreationCost,
            cache_read_cost: cacheReadCost,
            output_cost: outputCost
          },
          total_cost: totalCost,
          cache_savings: cacheSavings,
          savings_percentage: savingsPct
        }

        console.log('[ChatStore] Updated conversation token usage:', conversationTokenUsage.value)
        break
      }

      case 'title_updated': {
        // 会话标题已更新
        console.log('[ChatStore] Title updated:', chunk.content)
        if (currentConversation.value) {
          currentConversation.value.title = chunk.content
          console.log('[ChatStore] Updated conversation title to:', chunk.content)

          // 通知用户
          notification.success('标题已生成', `会话标题: ${chunk.content}`)
        }
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
        tokenStatsStatus.value = 'idle'
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
    // 保存引用，防止在 await 期间被 SSE 事件清空
    const currentPendingInput = pendingUserInput.value
    
    if (!currentPendingInput) {
      console.warn('[ChatStore] No pending user input to submit')
      return
    }

    if (!currentConversation.value) {
      console.error('[ChatStore] No current conversation')
      return
    }

    const questionType = currentPendingInput.userInputQuestion?.question_type || 'text'

    try {
      console.log('[ChatStore] Submitting user response:', { answer, questionType })

      // 调用 API 提交响应
      await api.submitUserResponse(currentConversation.value.id, {
        answer,
        question_type: questionType
      })

      console.log('[ChatStore] User response submitted successfully')

      // 立即添加用户答案到消息列表（UX：用户需要看到自己的回答）
      let answerText = ''
      if (questionType === 'batch_form') {
        // 批量问答特殊展示
        const count = answer.answers ? Object.keys(answer.answers).length : 0
        answerText = `已提交 ${count} 个问题的回答`
      } else {
        answerText = Array.isArray(answer)
          ? answer.join(', ')
          : String(answer)
      }

      messages.value.push({
        id: `user-answer-${Date.now()}`,
        role: 'user',
        content: `回答: ${answerText}`,
        timestamp: new Date(),
        metadata: {
          isUserAnswer: true,
          questionId: currentPendingInput.id
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
   * Cancel ongoing streaming response
   */
  async function cancelStreaming() {
    if (!currentConversation.value) {
      console.warn('[ChatStore] No active conversation to cancel')
      return
    }

    try {
      console.log('[ChatStore] Cancelling streaming for conversation:', currentConversation.value.id)

      await api.cancelStreaming(currentConversation.value.id)

      // 立即停止 typing 状态
      isTyping.value = false
      tokenStatsStatus.value = 'idle'
      tokenStatsStatus.value = 'idle'

      // 如果有正在流式输出的消息,标记为已完成
      if (currentStreamingMessage.value) {
        currentStreamingMessage.value.isStreaming = false
        currentStreamingMessage.value = null
      }

      console.log('[ChatStore] Streaming cancelled successfully')
      notification.info('已停止', 'AI 响应已终止', 2000)
    } catch (error: any) {
      console.error('[ChatStore] Error cancelling streaming:', error)

      // 即使 API 调用失败,也尝试本地清理状态
      isTyping.value = false
      if (currentStreamingMessage.value) {
        currentStreamingMessage.value.isStreaming = false
        currentStreamingMessage.value = null
      }

      notification.error(
        '停止失败',
        error.response?.data?.detail || '无法停止 AI 响应'
      )
    }
  }

  /**
   * Clear current conversation (不影响心跳连接)
   */
  function clearConversation() {
    // 断开 SSE 聊天连接（不是心跳连接）
    sseService.disconnect()
    sseService.clearCallbacks()
    sseService.reset()

    currentConversation.value = null
    messages.value = []
    // 注意: isConnected 由 heartbeat 管理，不在这里设置
    isTyping.value = false
    currentStreamingMessage.value = null
    tokenStatsStatus.value = 'idle'

    // Reset token usage
    conversationTokenUsage.value = {
      regular_input_tokens: 0,
      total_input_tokens: 0,
      total_output_tokens: 0,
      total_tokens: 0,
      cache_creation_input_tokens: 0,
      cache_read_input_tokens: 0,
      iterations: 0,
      tool_calls_count: 0,
      cost_breakdown: {
        regular_input_cost: 0,
        cache_creation_cost: 0,
        cache_read_cost: 0,
        output_cost: 0
      },
      total_cost: 0,
      cache_savings: 0,
      savings_percentage: 0
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
    tokenStatsStatus,
    pendingUserInput,  // 待回答的用户输入

    // Actions
    connectToConversation,
    sendMessage,
    createNewConversation,
    clearConversation,
    submitUserResponse,  // 提交用户响应
    cancelStreaming,  // 终止 streaming

    // 心跳连接管理
    startHeartbeat,  // 启动心跳（登录后调用）
    stopHeartbeat    // 停止心跳（登出时调用）
  }
})
