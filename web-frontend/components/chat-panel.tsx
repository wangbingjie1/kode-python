"use client"

import { useState, useEffect, useRef, useCallback } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { X, Send, Bot, User, Paperclip, Loader2 } from "lucide-react"
import { cn } from "@/lib/utils"
import { chatApi, getErrorMessage, Message as ApiMessage } from "@/lib/api"
import {
  sendChatMessage,
  createMessageAccumulator,
  SSEClient,
  ChunkMessage,
  CompleteMessage,
  ErrorMessage,
  ToolCallMessage,
  ThinkingMessage,
  DoneMessage,
} from "@/lib/sse"

interface Message {
  role: "user" | "assistant"
  content: string
  time: string
  isStreaming?: boolean
  toolCalls?: { name: string; status: string }[]
}

interface ChatPanelProps {
  onClose: () => void
  conversationId?: string
  projectId?: string
}

export function ChatPanel({ onClose, conversationId: propConversationId, projectId }: ChatPanelProps) {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const [isStreaming, setIsStreaming] = useState(false)
  const [conversationId, setConversationId] = useState<string | undefined>(propConversationId)
  const [error, setError] = useState<string | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const sseClientRef = useRef<SSEClient | null>(null)
  const accumulatorRef = useRef(createMessageAccumulator())

  // 滚动到底部
  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [])

  // 加载历史消息
  useEffect(() => {
    const loadMessages = async () => {
      if (!conversationId) return

      try {
        setIsLoading(true)
        const historyMessages = await chatApi.getMessages(conversationId)
        const formattedMessages: Message[] = historyMessages
          .filter((msg: ApiMessage) => msg.role !== "system")
          .map((msg: ApiMessage) => ({
            role: msg.role as "user" | "assistant",
            content: msg.content,
            time: new Date(msg.created_at).toLocaleTimeString("en-US", {
              hour: "numeric",
              minute: "2-digit",
            }),
          }))
        setMessages(formattedMessages)
      } catch (err) {
        console.error("Failed to load messages:", err)
        setError(getErrorMessage(err))
      } finally {
        setIsLoading(false)
      }
    }

    loadMessages()
  }, [conversationId])

  // 滚动到底部
  useEffect(() => {
    scrollToBottom()
  }, [messages, scrollToBottom])

  // 清理 SSE 连接
  useEffect(() => {
    return () => {
      sseClientRef.current?.close()
    }
  }, [])

  // 创建对话（如果没有 conversationId）
  const ensureConversation = async (): Promise<string | null> => {
    if (conversationId) return conversationId

    if (!projectId) {
      setError("缺少项目 ID，无法创建对话")
      return null
    }

    try {
      const conversation = await chatApi.createConversation({ project_id: projectId })
      setConversationId(conversation.id)
      return conversation.id
    } catch (err) {
      console.error("Failed to create conversation:", err)
      setError(getErrorMessage(err))
      return null
    }
  }

  const handleSend = async () => {
    if (!input.trim() || isStreaming) return

    const userInput = input.trim()
    setInput("")
    setError(null)

    // 确保有对话 ID
    const activeConversationId = await ensureConversation()
    if (!activeConversationId) return

    // 添加用户消息
    const userMessage: Message = {
      role: "user",
      content: userInput,
      time: new Date().toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" }),
    }
    setMessages((prev) => [...prev, userMessage])

    // 添加 AI 消息占位（流式显示）
    const aiMessageIndex = messages.length + 1
    setMessages((prev) => [
      ...prev,
      {
        role: "assistant",
        content: "",
        time: "",
        isStreaming: true,
      },
    ])

    setIsStreaming(true)
    accumulatorRef.current.reset()

    // 关闭之前的连接
    sseClientRef.current?.close()

    // 发送 SSE 请求
    sseClientRef.current = sendChatMessage(activeConversationId, userInput, {
      onThinking: (msg: ThinkingMessage) => {
        // 可选：显示思考过程
        console.log("Thinking:", msg.content)
      },
      onChunk: (msg: ChunkMessage) => {
        accumulatorRef.current.handlers.onChunk(msg)
        setMessages((prev) => {
          const updated = [...prev]
          if (updated[aiMessageIndex]) {
            updated[aiMessageIndex] = {
              ...updated[aiMessageIndex],
              content: accumulatorRef.current.getContent(),
            }
          }
          return updated
        })
      },
      onToolCall: (msg: ToolCallMessage) => {
        accumulatorRef.current.handlers.onToolCall(msg)
        setMessages((prev) => {
          const updated = [...prev]
          if (updated[aiMessageIndex]) {
            const toolCalls = accumulatorRef.current.getToolCalls().map((tc) => ({
              name: tc.tool_name,
              status: tc.status,
            }))
            updated[aiMessageIndex] = {
              ...updated[aiMessageIndex],
              toolCalls,
            }
          }
          return updated
        })
      },
      onComplete: (msg: CompleteMessage) => {
        setMessages((prev) => {
          const updated = [...prev]
          if (updated[aiMessageIndex]) {
            updated[aiMessageIndex] = {
              ...updated[aiMessageIndex],
              content: msg.content,
              time: new Date().toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" }),
              isStreaming: false,
              toolCalls: undefined,
            }
          }
          return updated
        })
        setIsStreaming(false)
      },
      onError: (msg: ErrorMessage) => {
        console.error("SSE error:", msg)
        setError(msg.content)
        setMessages((prev) => {
          const updated = [...prev]
          if (updated[aiMessageIndex]) {
            updated[aiMessageIndex] = {
              ...updated[aiMessageIndex],
              content: `错误: ${msg.content}`,
              time: new Date().toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" }),
              isStreaming: false,
            }
          }
          return updated
        })
        setIsStreaming(false)
      },
      onDone: (_msg: DoneMessage) => {
        setIsStreaming(false)
      },
      onConnectionError: (event: Event) => {
        console.error("Connection error:", event)
        setError("连接失败，请检查网络后重试")
        setIsStreaming(false)
      },
    })
  }

  return (
    <Card className="w-96 h-[calc(100vh-8rem)] flex flex-col bg-card border-border">
      <CardHeader className="flex-shrink-0 border-b border-border">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg flex items-center gap-2">
            <Bot className="h-5 w-5 text-primary" />
            Chat Analysis
          </CardTitle>
          <Button variant="ghost" size="icon" className="h-8 w-8" onClick={onClose}>
            <X className="h-4 w-4" />
          </Button>
        </div>
      </CardHeader>

      <CardContent className="flex-1 overflow-y-auto p-4 space-y-4">
        {/* 加载历史消息状态 */}
        {isLoading && (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            <span className="ml-2 text-sm text-muted-foreground">Loading messages...</span>
          </div>
        )}

        {/* 错误提示 */}
        {error && (
          <div className="bg-destructive/10 text-destructive text-sm px-3 py-2 rounded-lg">
            {error}
          </div>
        )}

        {/* 空状态提示 */}
        {!isLoading && messages.length === 0 && !error && (
          <div className="flex flex-col items-center justify-center py-8 text-center">
            <Bot className="h-12 w-12 text-muted-foreground/50 mb-4" />
            <p className="text-sm text-muted-foreground">
              Start a conversation by sending a message below.
            </p>
          </div>
        )}

        {/* 消息列表 */}
        {messages.map((message, index) => (
          <div key={index} className={cn("flex gap-3", message.role === "user" ? "justify-end" : "justify-start")}>
            {message.role === "assistant" && (
              <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0">
                {message.isStreaming ? (
                  <Loader2 className="h-4 w-4 text-primary animate-spin" />
                ) : (
                  <Bot className="h-4 w-4 text-primary" />
                )}
              </div>
            )}
            <div className={cn("flex flex-col gap-1", message.role === "user" ? "items-end" : "items-start")}>
              <div
                className={cn(
                  "rounded-lg px-3 py-2 max-w-[280px]",
                  message.role === "user" ? "bg-primary text-primary-foreground" : "bg-secondary",
                )}
              >
                {/* 工具调用指示器 */}
                {message.toolCalls && message.toolCalls.length > 0 && (
                  <div className="mb-2 space-y-1">
                    {message.toolCalls.map((tc, i) => (
                      <div key={i} className="flex items-center gap-2 text-xs text-muted-foreground bg-background/50 px-2 py-1 rounded">
                        <Loader2 className="h-3 w-3 animate-spin" />
                        <span>{tc.name}</span>
                      </div>
                    ))}
                  </div>
                )}
                <p className="text-sm whitespace-pre-line">
                  {message.content || (message.isStreaming ? "" : "")}
                  {/* 流式光标 */}
                  {message.isStreaming && <span className="animate-pulse">|</span>}
                </p>
              </div>
              {message.time && (
                <span className="text-xs text-muted-foreground">{message.time}</span>
              )}
            </div>
            {message.role === "user" && (
              <div className="h-8 w-8 rounded-full bg-secondary flex items-center justify-center flex-shrink-0">
                <User className="h-4 w-4" />
              </div>
            )}
          </div>
        ))}
        {/* 滚动锚点 */}
        <div ref={messagesEndRef} />
      </CardContent>

      <div className="flex-shrink-0 p-4 border-t border-border">
        <div className="flex gap-2">
          <Button variant="ghost" size="icon" className="h-9 w-9 flex-shrink-0" disabled={isStreaming}>
            <Paperclip className="h-4 w-4" />
          </Button>
          <Input
            placeholder="Ask me anything..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && !isStreaming && handleSend()}
            className="bg-secondary border-border"
            disabled={isStreaming}
          />
          <Button
            size="icon"
            className="h-9 w-9 flex-shrink-0"
            onClick={handleSend}
            disabled={isStreaming || !input.trim()}
          >
            {isStreaming ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Send className="h-4 w-4" />
            )}
          </Button>
        </div>
        <div className="flex gap-2 mt-2">
          <Button variant="outline" size="sm" className="text-xs bg-transparent" disabled={isStreaming}>
            Save Chat
          </Button>
          <Button
            variant="outline"
            size="sm"
            className="text-xs bg-transparent"
            disabled={isStreaming || messages.length === 0}
            onClick={() => setMessages([])}
          >
            Clear
          </Button>
          <Button variant="outline" size="sm" className="text-xs bg-transparent" disabled={isStreaming}>
            Export
          </Button>
        </div>
      </div>
    </Card>
  )
}
