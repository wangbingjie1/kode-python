"use client"

import { useState } from "react"
import { Card } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { Send, Bot, User, ZoomIn, ZoomOut, Maximize2, Sparkles, FileText, X } from "lucide-react"
import { cn } from "@/lib/utils"

interface Message {
  role: "user" | "assistant"
  content: string
  time: string
}

interface GraphNode {
  id: string
  level: number
  type: "north_star" | "primary_metric" | "secondary_metric"
  label: string
  fullName?: string
  value: number
  displayValue: string
  change: number
  changeDirection: "up" | "down" | "neutral"
  unit: string
  formula?: string
  position: { x: number; y: number }
  size: { width: number; height: number }
  color: string
  icon: string
  parentId: string | null
  childIds: string[]
  isExpanded: boolean
  isHighlighted: boolean
  healthStatus: "normal" | "warning" | "critical"
}

interface GraphEdge {
  id: string
  source: string
  target: string
  type: "breakdown"
  strength: number
  label?: string
  color: string
  style: "solid" | "dashed"
}

const sampleGraphData = {
  nodes: [
    {
      id: "node_gmv",
      level: 0,
      type: "north_star" as const,
      label: "GMV",
      fullName: "Gross Merchandise Volume",
      value: 1245000,
      displayValue: "$1,245,000",
      change: 18.5,
      changeDirection: "up" as const,
      unit: "USD",
      formula: "Total Orders × Average Order Value",
      position: { x: 500, y: 50 },
      size: { width: 200, height: 120 },
      color: "#5A95A8",
      icon: "🌟",
      parentId: null,
      childIds: ["node_orders", "node_aov"],
      isExpanded: true,
      isHighlighted: false,
      healthStatus: "normal" as const,
    },
    {
      id: "node_orders",
      level: 1,
      type: "primary_metric" as const,
      label: "Total Orders",
      value: 45678,
      displayValue: "45,678",
      change: 22.3,
      changeDirection: "up" as const,
      unit: "count",
      position: { x: 300, y: 230 },
      size: { width: 180, height: 100 },
      color: "#10B981",
      icon: "📊",
      parentId: "node_gmv",
      childIds: ["node_new_users", "node_repeat_users"],
      isExpanded: true,
      isHighlighted: false,
      healthStatus: "normal" as const,
    },
    {
      id: "node_aov",
      level: 1,
      type: "primary_metric" as const,
      label: "AOV",
      fullName: "Average Order Value",
      value: 27.25,
      displayValue: "$27.25",
      change: -3.1,
      changeDirection: "down" as const,
      unit: "USD",
      position: { x: 720, y: 230 },
      size: { width: 180, height: 100 },
      color: "#F59E0B",
      icon: "💰",
      parentId: "node_gmv",
      childIds: ["node_unit_price", "node_discount"],
      isExpanded: true,
      isHighlighted: false,
      healthStatus: "warning" as const,
    },
    {
      id: "node_new_users",
      level: 2,
      type: "secondary_metric" as const,
      label: "New User Orders",
      value: 28456,
      displayValue: "28,456",
      change: 35.0,
      changeDirection: "up" as const,
      unit: "count",
      position: { x: 180, y: 400 },
      size: { width: 160, height: 90 },
      color: "#3B82F6",
      icon: "👤",
      parentId: "node_orders",
      childIds: [],
      isExpanded: false,
      isHighlighted: false,
      healthStatus: "normal" as const,
    },
    {
      id: "node_repeat_users",
      level: 2,
      type: "secondary_metric" as const,
      label: "Repeat User Orders",
      value: 17222,
      displayValue: "17,222",
      change: 8.0,
      changeDirection: "up" as const,
      unit: "count",
      position: { x: 380, y: 400 },
      size: { width: 160, height: 90 },
      color: "#3B82F6",
      icon: "🔄",
      parentId: "node_orders",
      childIds: [],
      isExpanded: false,
      isHighlighted: false,
      healthStatus: "normal" as const,
    },
    {
      id: "node_unit_price",
      level: 2,
      type: "secondary_metric" as const,
      label: "Unit Price",
      value: 8.93,
      displayValue: "$8.93",
      change: 2.1,
      changeDirection: "up" as const,
      unit: "USD",
      position: { x: 620, y: 400 },
      size: { width: 160, height: 90 },
      color: "#8B5CF6",
      icon: "🏷️",
      parentId: "node_aov",
      childIds: [],
      isExpanded: false,
      isHighlighted: false,
      healthStatus: "normal" as const,
    },
    {
      id: "node_discount",
      level: 2,
      type: "secondary_metric" as const,
      label: "Discount Rate",
      value: 15.2,
      displayValue: "15.2%",
      change: 3.8,
      changeDirection: "up" as const,
      unit: "percent",
      position: { x: 820, y: 400 },
      size: { width: 160, height: 90 },
      color: "#EC4899",
      icon: "🎁",
      parentId: "node_aov",
      childIds: [],
      isExpanded: false,
      isHighlighted: false,
      healthStatus: "normal" as const,
    },
  ],
  edges: [
    {
      id: "edge_1",
      source: "node_gmv",
      target: "node_orders",
      type: "breakdown" as const,
      strength: 1.0,
      label: "contributes to",
      color: "#6B7280",
      style: "solid" as const,
    },
    {
      id: "edge_2",
      source: "node_gmv",
      target: "node_aov",
      type: "breakdown" as const,
      strength: 1.0,
      label: "contributes to",
      color: "#6B7280",
      style: "solid" as const,
    },
    {
      id: "edge_3",
      source: "node_orders",
      target: "node_new_users",
      type: "breakdown" as const,
      strength: 0.62,
      label: "62%",
      color: "#6B7280",
      style: "solid" as const,
    },
    {
      id: "edge_4",
      source: "node_orders",
      target: "node_repeat_users",
      type: "breakdown" as const,
      strength: 0.38,
      label: "38%",
      color: "#6B7280",
      style: "solid" as const,
    },
    {
      id: "edge_5",
      source: "node_aov",
      target: "node_unit_price",
      type: "breakdown" as const,
      strength: 1.0,
      color: "#6B7280",
      style: "solid" as const,
    },
    {
      id: "edge_6",
      source: "node_aov",
      target: "node_discount",
      type: "breakdown" as const,
      strength: 1.0,
      color: "#6B7280",
      style: "solid" as const,
    },
  ],
}

const initialMessages: Message[] = [
  {
    role: "assistant",
    content:
      "Hi! I've analyzed your uploaded data and built a knowledge graph. You can ask me anything like:\n• What are the key drivers of GMV growth?\n• How do different metrics relate to each other?\n• What insights can you provide about the data?",
    time: new Date().toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" }),
  },
]

function getBezierPath(source: GraphNode, target: GraphNode): string {
  const x1 = source.position.x + source.size.width / 2
  const y1 = source.position.y + source.size.height
  const x2 = target.position.x + target.size.width / 2
  const y2 = target.position.y

  const cy = y1 + (y2 - y1) / 2

  return `M ${x1},${y1} C ${x1},${cy} ${x2},${cy} ${x2},${y2}`
}

interface AppWorkspaceProps {
  uploadedFiles: File[]
  onBack: () => void
}

export function AppWorkspace({ uploadedFiles, onBack }: AppWorkspaceProps) {
  const [messages, setMessages] = useState<Message[]>(initialMessages)
  const [input, setInput] = useState("")
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null)
  const [hoveredNode, setHoveredNode] = useState<string | null>(null)
  const [zoomLevel, setZoomLevel] = useState(1)
  const [isGeneratingGraph, setIsGeneratingGraph] = useState(true)

  useState(() => {
    setTimeout(() => {
      setIsGeneratingGraph(false)
    }, 2000)
  })

  const handleSend = () => {
    if (!input.trim()) return

    const newMessage: Message = {
      role: "user",
      content: input,
      time: new Date().toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" }),
    }

    setMessages([...messages, newMessage])
    setInput("")

    setTimeout(() => {
      const aiResponse: Message = {
        role: "assistant",
        content:
          "Based on the knowledge graph analysis, I can see that GMV growth is primarily driven by increased order volume (+22.3%), particularly from new users (+35%). However, AOV has decreased slightly (-3.1%), which suggests an opportunity to focus on upselling strategies.",
        time: new Date().toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" }),
      }
      setMessages((prev) => [...prev, aiResponse])
    }, 1000)
  }

  const handleZoomIn = () => {
    setZoomLevel((prev) => Math.min(prev * 1.3, 2))
  }

  const handleZoomOut = () => {
    setZoomLevel((prev) => Math.max(prev * 0.7, 0.5))
  }

  const handleResetZoom = () => {
    setZoomLevel(1)
  }

  const getRelatedNodeIds = (nodeId: string): string[] => {
    const node = sampleGraphData.nodes.find((n) => n.id === nodeId)
    if (!node) return []
    return [nodeId, node.parentId, ...node.childIds].filter(Boolean) as string[]
  }

  const getRelatedEdgeIds = (nodeId: string): string[] => {
    return sampleGraphData.edges.filter((e) => e.source === nodeId || e.target === nodeId).map((e) => e.id)
  }

  const isNodeHighlighted = (nodeId: string): boolean => {
    if (!hoveredNode) return true
    return getRelatedNodeIds(hoveredNode).includes(nodeId)
  }

  const isEdgeHighlighted = (edgeId: string): boolean => {
    if (!hoveredNode) return true
    return getRelatedEdgeIds(hoveredNode).includes(edgeId)
  }

  return (
    <div className="min-h-screen bg-[#F8F9FB]">
      <div className="border-b border-[#E5E7EB] bg-white">
        <div className="container max-w-[1400px] mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Button variant="ghost" size="sm" onClick={onBack} className="text-[#6B7280]">
                ← Back
              </Button>
              <div className="flex items-center gap-2">
                <FileText className="h-5 w-5 text-[#5A95A8]" />
                <span className="font-semibold text-[#1A202C]">
                  {uploadedFiles.length} file{uploadedFiles.length > 1 ? "s" : ""} uploaded
                </span>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Badge className="bg-[#10B981]/10 text-[#10B981] border-[#10B981]/20">
                {isGeneratingGraph ? "Generating..." : "Ready"}
              </Badge>
            </div>
          </div>
        </div>
      </div>

      <div className="container max-w-[1400px] mx-auto px-6 py-6">
        <div className="grid grid-cols-1 lg:grid-cols-[1fr_400px] gap-6">
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-2xl font-semibold text-[#1A202C]">Knowledge Graph</h2>
              <div className="flex items-center gap-2">
                <span className="text-sm text-[#6B7280]">Zoom: {Math.round(zoomLevel * 100)}%</span>
                <Button variant="outline" size="icon" onClick={handleZoomOut} className="h-8 w-8 bg-transparent">
                  <ZoomOut className="h-4 w-4" />
                </Button>
                <Button variant="outline" size="icon" onClick={handleZoomIn} className="h-8 w-8 bg-transparent">
                  <ZoomIn className="h-4 w-4" />
                </Button>
                <Button variant="outline" size="icon" onClick={handleResetZoom} className="h-8 w-8 bg-transparent">
                  <Maximize2 className="h-4 w-4" />
                </Button>
              </div>
            </div>

            <Card className="overflow-hidden shadow-sm border-[#E5E7EB]">
              <div className="w-full h-[600px] bg-white relative overflow-hidden">
                {isGeneratingGraph ? (
                  <div className="absolute inset-0 flex flex-col items-center justify-center gap-4">
                    <Sparkles className="h-12 w-12 text-[#5A95A8] animate-pulse" />
                    <p className="text-[#6B7280] font-medium">Building knowledge graph...</p>
                  </div>
                ) : (
                  <svg
                    viewBox="0 0 1200 600"
                    className="w-full h-full"
                    style={{
                      transform: `scale(${zoomLevel})`,
                      transition: "transform 0.3s ease-out",
                    }}
                  >
                    <defs>
                      <marker
                        id="arrowhead"
                        viewBox="0 -5 10 10"
                        refX={8}
                        refY={0}
                        markerWidth={6}
                        markerHeight={6}
                        orient="auto"
                      >
                        <path d="M0,-5L10,0L0,5" fill="#6B7280" />
                      </marker>
                    </defs>

                    {/* Edges */}
                    <g className="edges">
                      {sampleGraphData.edges.map((edge) => {
                        const source = sampleGraphData.nodes.find((n) => n.id === edge.source)!
                        const target = sampleGraphData.nodes.find((n) => n.id === edge.target)!
                        const isHighlighted = isEdgeHighlighted(edge.id)

                        return (
                          <g key={edge.id}>
                            <path
                              d={getBezierPath(source, target)}
                              stroke={isHighlighted ? "#5A95A8" : edge.color}
                              strokeWidth={isHighlighted ? 3 : 2}
                              fill="none"
                              markerEnd="url(#arrowhead)"
                              opacity={isHighlighted ? 1 : 0.3}
                              style={{ transition: "all 0.2s ease" }}
                            />
                            {edge.label && (
                              <text
                                x={
                                  (source.position.x +
                                    source.size.width / 2 +
                                    target.position.x +
                                    target.size.width / 2) /
                                  2
                                }
                                y={(source.position.y + source.size.height + target.position.y) / 2}
                                fill="#6B7280"
                                fontSize={11}
                                textAnchor="middle"
                                opacity={isHighlighted ? 1 : 0.3}
                                style={{ transition: "opacity 0.2s ease" }}
                              >
                                {edge.label}
                              </text>
                            )}
                          </g>
                        )
                      })}
                    </g>

                    {/* Nodes */}
                    <g className="nodes">
                      {sampleGraphData.nodes.map((node) => {
                        const isHighlighted = isNodeHighlighted(node.id)
                        const isHovered = hoveredNode === node.id

                        return (
                          <g
                            key={node.id}
                            transform={`translate(${node.position.x}, ${node.position.y})`}
                            style={{ cursor: "pointer" }}
                            opacity={isHighlighted ? 1 : 0.3}
                            onMouseEnter={() => setHoveredNode(node.id)}
                            onMouseLeave={() => setHoveredNode(null)}
                            onClick={() => setSelectedNode(node)}
                          >
                            <rect
                              width={node.size.width}
                              height={node.size.height}
                              rx={10}
                              fill="#FFFFFF"
                              stroke={isHovered ? "#5A95A8" : "#E5E7EB"}
                              strokeWidth={isHovered ? 2 : 1}
                              style={{
                                transition: "all 0.2s ease",
                                filter: isHovered
                                  ? "drop-shadow(0 8px 24px rgba(90, 149, 168, 0.2))"
                                  : "drop-shadow(0 2px 8px rgba(0, 0, 0, 0.06))",
                              }}
                            />

                            {/* Icon */}
                            <text x={20} y={40} fontSize={24}>
                              {node.icon}
                            </text>

                            {/* Label */}
                            <text x={20} y={65} fontSize={14} fontWeight={600} fill="#1A202C">
                              {node.label}
                            </text>

                            {/* Value */}
                            <text x={20} y={88} fontSize={16} fontWeight={700} fill="#2D3748">
                              {node.displayValue}
                            </text>

                            {/* Trend */}
                            <text
                              x={20}
                              y={node.level === 0 ? 110 : 105}
                              fontSize={12}
                              fontWeight={600}
                              fill={node.changeDirection === "up" ? "#10B981" : "#EF4444"}
                            >
                              {node.changeDirection === "up" ? "↗" : "↘"} {node.change > 0 ? "+" : ""}
                              {node.change}%
                            </text>

                            {/* Status indicator */}
                            <circle
                              cx={node.size.width - 15}
                              cy={15}
                              r={5}
                              fill={
                                node.healthStatus === "normal"
                                  ? "#10B981"
                                  : node.healthStatus === "warning"
                                    ? "#F59E0B"
                                    : "#EF4444"
                              }
                            />
                          </g>
                        )
                      })}
                    </g>
                  </svg>
                )}
              </div>
            </Card>

            <p className="text-sm text-[#6B7280] leading-relaxed">
              Hover over nodes to see relationships • Click to view details
            </p>
          </div>

          <div className="flex flex-col h-[calc(100vh-180px)] lg:sticky lg:top-6">
            <Card className="flex flex-col h-full shadow-sm border-[#E5E7EB]">
              {/* Chat Header */}
              <div className="flex-shrink-0 border-b border-[#E5E7EB] p-4">
                <div className="flex items-center gap-2">
                  <div className="h-8 w-8 rounded-full bg-[#5A95A8]/10 flex items-center justify-center">
                    <Bot className="h-4 w-4 text-[#5A95A8]" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-[#1A202C]">AI Assistant</h3>
                    <p className="text-xs text-[#6B7280]">Ask me anything about your data</p>
                  </div>
                </div>
              </div>

              {/* Messages */}
              <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-[#F5F6F7]">
                {messages.map((message, index) => (
                  <div
                    key={index}
                    className={cn("flex gap-3", message.role === "user" ? "justify-end" : "justify-start")}
                  >
                    {message.role === "assistant" && (
                      <div className="h-8 w-8 rounded-full bg-[#5A95A8]/10 flex items-center justify-center flex-shrink-0">
                        <Bot className="h-4 w-4 text-[#5A95A8]" />
                      </div>
                    )}
                    <div className={cn("flex flex-col gap-1", message.role === "user" ? "items-end" : "items-start")}>
                      <div
                        className={cn(
                          "rounded-2xl px-4 py-3 max-w-[280px]",
                          message.role === "user"
                            ? "bg-[#5A95A8] text-white"
                            : "bg-white border border-[#E5E7EB] text-[#2D3748]",
                        )}
                      >
                        <p className="text-sm leading-relaxed whitespace-pre-line">{message.content}</p>
                      </div>
                      <span className="text-xs text-[#6B7280]">{message.time}</span>
                    </div>
                    {message.role === "user" && (
                      <div className="h-8 w-8 rounded-full bg-[#E5E7EB] flex items-center justify-center flex-shrink-0">
                        <User className="h-4 w-4 text-[#6B7280]" />
                      </div>
                    )}
                  </div>
                ))}
              </div>

              {/* Input */}
              <div className="flex-shrink-0 p-4 border-t border-[#E5E7EB] bg-white">
                <div className="flex gap-2">
                  <Input
                    placeholder="Ask me anything..."
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && handleSend()}
                    className="bg-[#F8F9FB] border-[#E5E7EB] text-[#2D3748] placeholder:text-[#6B7280]"
                  />
                  <Button
                    size="icon"
                    className="h-10 w-10 flex-shrink-0 bg-[#5A95A8] hover:bg-[#7AB8CC]"
                    onClick={handleSend}
                  >
                    <Send className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            </Card>
          </div>
        </div>
      </div>

      {selectedNode && (
        <>
          <div className="fixed inset-0 bg-black/40 backdrop-blur-sm z-40" onClick={() => setSelectedNode(null)} />
          <Card className="fixed inset-x-4 top-1/2 -translate-y-1/2 max-w-2xl mx-auto z-50 shadow-2xl border-[#E5E7EB]">
            <div className="p-6">
              <div className="flex items-center justify-between mb-6">
                <div className="flex items-center gap-3">
                  <span className="text-3xl">{selectedNode.icon}</span>
                  <div>
                    <h3 className="text-xl font-semibold text-[#1A202C]">
                      {selectedNode.fullName || selectedNode.label}
                    </h3>
                    {selectedNode.formula && <p className="text-sm text-[#6B7280] mt-1">{selectedNode.formula}</p>}
                  </div>
                </div>
                <Button variant="ghost" size="icon" onClick={() => setSelectedNode(null)}>
                  <X className="h-4 w-4" />
                </Button>
              </div>

              <div className="grid grid-cols-3 gap-4 mb-6">
                <div className="space-y-1">
                  <div className="text-sm text-[#6B7280]">Current Value</div>
                  <div className="text-2xl font-bold text-[#1A202C]">{selectedNode.displayValue}</div>
                </div>
                <div className="space-y-1">
                  <div className="text-sm text-[#6B7280]">Change</div>
                  <div
                    className={`text-2xl font-bold ${selectedNode.changeDirection === "up" ? "text-[#10B981]" : "text-[#EF4444]"}`}
                  >
                    {selectedNode.change > 0 ? "+" : ""}
                    {selectedNode.change}%
                  </div>
                </div>
                <div className="space-y-1">
                  <div className="text-sm text-[#6B7280]">Status</div>
                  <Badge
                    className={
                      selectedNode.healthStatus === "normal"
                        ? "bg-[#10B981]/10 text-[#10B981] border-[#10B981]/20"
                        : selectedNode.healthStatus === "warning"
                          ? "bg-[#F59E0B]/10 text-[#F59E0B] border-[#F59E0B]/20"
                          : "bg-[#EF4444]/10 text-[#EF4444] border-[#EF4444]/20"
                    }
                  >
                    {selectedNode.healthStatus}
                  </Badge>
                </div>
              </div>

              {selectedNode.childIds.length > 0 && (
                <div className="space-y-3">
                  <div className="text-sm font-semibold text-[#1A202C]">Breakdown</div>
                  <div className="space-y-2">
                    {selectedNode.childIds.map((childId) => {
                      const child = sampleGraphData.nodes.find((n) => n.id === childId)
                      if (!child) return null
                      return (
                        <div
                          key={childId}
                          className="flex items-center justify-between p-3 rounded-lg bg-[#F8F9FB] hover:bg-[#F5F6F7] transition-colors cursor-pointer border border-[#E5E7EB]"
                          onClick={() => setSelectedNode(child)}
                        >
                          <div className="flex items-center gap-2">
                            <span className="text-xl">{child.icon}</span>
                            <span className="text-sm font-medium text-[#2D3748]">{child.label}</span>
                          </div>
                          <div className="flex items-center gap-3">
                            <span className="text-sm font-bold text-[#1A202C]">{child.displayValue}</span>
                            <span
                              className={`text-xs font-medium ${child.changeDirection === "up" ? "text-[#10B981]" : "text-[#EF4444]"}`}
                            >
                              {child.changeDirection === "up" ? "↗" : "↘"} {child.change}%
                            </span>
                          </div>
                        </div>
                      )
                    })}
                  </div>
                </div>
              )}
            </div>
          </Card>
        </>
      )}
    </div>
  )
}
