"use client"

import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { ZoomIn, ZoomOut, Maximize2 } from "lucide-react"

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

interface KnowledgeGraphData {
  projectId: string
  rootNodeId: string
  nodes: GraphNode[]
  edges: GraphEdge[]
}

const knowledgeGraphData: KnowledgeGraphData = {
  projectId: "proj_abc123",
  rootNodeId: "node_gmv",
  nodes: [
    {
      id: "node_gmv",
      level: 0,
      type: "north_star",
      label: "GMV",
      fullName: "Gross Merchandise Volume",
      value: 1245000,
      displayValue: "$1,245,000",
      change: 18.5,
      changeDirection: "up",
      unit: "USD",
      formula: "Total Orders × Average Order Value",
      position: { x: 500, y: 50 },
      size: { width: 200, height: 120 },
      color: "#4F46E5",
      icon: "🌟",
      parentId: null,
      childIds: ["node_orders", "node_aov"],
      isExpanded: true,
      isHighlighted: false,
      healthStatus: "normal",
    },
    {
      id: "node_orders",
      level: 1,
      type: "primary_metric",
      label: "Total Orders",
      value: 45678,
      displayValue: "45,678",
      change: 22.3,
      changeDirection: "up",
      unit: "count",
      position: { x: 300, y: 230 },
      size: { width: 180, height: 100 },
      color: "#10B981",
      icon: "📊",
      parentId: "node_gmv",
      childIds: ["node_new_users", "node_repeat_users"],
      isExpanded: true,
      isHighlighted: false,
      healthStatus: "normal",
    },
    {
      id: "node_aov",
      level: 1,
      type: "primary_metric",
      label: "AOV",
      fullName: "Average Order Value",
      value: 27.25,
      displayValue: "$27.25",
      change: -3.1,
      changeDirection: "down",
      unit: "USD",
      position: { x: 720, y: 230 },
      size: { width: 180, height: 100 },
      color: "#F59E0B",
      icon: "💰",
      parentId: "node_gmv",
      childIds: ["node_unit_price", "node_discount"],
      isExpanded: true,
      isHighlighted: false,
      healthStatus: "warning",
    },
    {
      id: "node_new_users",
      level: 2,
      type: "secondary_metric",
      label: "New User Orders",
      value: 28456,
      displayValue: "28,456",
      change: 35.0,
      changeDirection: "up",
      unit: "count",
      position: { x: 180, y: 400 },
      size: { width: 160, height: 90 },
      color: "#3B82F6",
      icon: "👤",
      parentId: "node_orders",
      childIds: [],
      isExpanded: false,
      isHighlighted: false,
      healthStatus: "normal",
    },
    {
      id: "node_repeat_users",
      level: 2,
      type: "secondary_metric",
      label: "Repeat User Orders",
      value: 17222,
      displayValue: "17,222",
      change: 8.0,
      changeDirection: "up",
      unit: "count",
      position: { x: 380, y: 400 },
      size: { width: 160, height: 90 },
      color: "#3B82F6",
      icon: "🔄",
      parentId: "node_orders",
      childIds: [],
      isExpanded: false,
      isHighlighted: false,
      healthStatus: "normal",
    },
    {
      id: "node_unit_price",
      level: 2,
      type: "secondary_metric",
      label: "Unit Price",
      value: 8.93,
      displayValue: "$8.93",
      change: 2.1,
      changeDirection: "up",
      unit: "USD",
      position: { x: 620, y: 400 },
      size: { width: 160, height: 90 },
      color: "#8B5CF6",
      icon: "🏷️",
      parentId: "node_aov",
      childIds: [],
      isExpanded: false,
      isHighlighted: false,
      healthStatus: "normal",
    },
    {
      id: "node_discount",
      level: 2,
      type: "secondary_metric",
      label: "Discount Rate",
      value: 15.2,
      displayValue: "15.2%",
      change: 3.8,
      changeDirection: "up",
      unit: "percent",
      position: { x: 820, y: 400 },
      size: { width: 160, height: 90 },
      color: "#EC4899",
      icon: "🎁",
      parentId: "node_aov",
      childIds: [],
      isExpanded: false,
      isHighlighted: false,
      healthStatus: "normal",
    },
  ],
  edges: [
    {
      id: "edge_1",
      source: "node_gmv",
      target: "node_orders",
      type: "breakdown",
      strength: 1.0,
      label: "contributes to",
      color: "#6B7280",
      style: "solid",
    },
    {
      id: "edge_2",
      source: "node_gmv",
      target: "node_aov",
      type: "breakdown",
      strength: 1.0,
      label: "contributes to",
      color: "#6B7280",
      style: "solid",
    },
    {
      id: "edge_3",
      source: "node_orders",
      target: "node_new_users",
      type: "breakdown",
      strength: 0.62,
      label: "62%",
      color: "#6B7280",
      style: "solid",
    },
    {
      id: "edge_4",
      source: "node_orders",
      target: "node_repeat_users",
      type: "breakdown",
      strength: 0.38,
      label: "38%",
      color: "#6B7280",
      style: "solid",
    },
    {
      id: "edge_5",
      source: "node_aov",
      target: "node_unit_price",
      type: "breakdown",
      strength: 1.0,
      color: "#6B7280",
      style: "solid",
    },
    {
      id: "edge_6",
      source: "node_aov",
      target: "node_discount",
      type: "breakdown",
      strength: 1.0,
      color: "#6B7280",
      style: "solid",
    },
  ],
}

function getBezierPath(source: GraphNode, target: GraphNode): string {
  const x1 = source.position.x + source.size.width / 2
  const y1 = source.position.y + source.size.height
  const x2 = target.position.x + target.size.width / 2
  const y2 = target.position.y

  const cy = y1 + (y2 - y1) / 2

  return `M ${x1},${y1} C ${x1},${cy} ${x2},${cy} ${x2},${y2}`
}

export function KnowledgeGraphView() {
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null)
  const [hoveredNode, setHoveredNode] = useState<string | null>(null)
  const [zoomLevel, setZoomLevel] = useState(1)
  const [panOffset, setPanOffset] = useState({ x: 0, y: 0 })

  const handleZoomIn = () => {
    setZoomLevel((prev) => Math.min(prev * 1.3, 2))
  }

  const handleZoomOut = () => {
    setZoomLevel((prev) => Math.max(prev * 0.7, 0.5))
  }

  const handleResetZoom = () => {
    setZoomLevel(1)
    setPanOffset({ x: 0, y: 0 })
  }

  const getRelatedNodeIds = (nodeId: string): string[] => {
    const node = knowledgeGraphData.nodes.find((n) => n.id === nodeId)
    if (!node) return []
    return [nodeId, node.parentId, ...node.childIds].filter(Boolean) as string[]
  }

  const getRelatedEdgeIds = (nodeId: string): string[] => {
    return knowledgeGraphData.edges.filter((e) => e.source === nodeId || e.target === nodeId).map((e) => e.id)
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
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="text-sm text-muted-foreground">
          Hover over nodes to see relationships • Click to view details
        </div>
        <div className="flex items-center gap-2">
          <span className="text-sm text-muted-foreground">Zoom: {Math.round(zoomLevel * 100)}%</span>
          <Button variant="outline" size="icon" onClick={handleZoomOut}>
            <ZoomOut className="h-4 w-4" />
          </Button>
          <Button variant="outline" size="icon" onClick={handleZoomIn}>
            <ZoomIn className="h-4 w-4" />
          </Button>
          <Button variant="outline" size="icon" onClick={handleResetZoom}>
            <Maximize2 className="h-4 w-4" />
          </Button>
        </div>
      </div>

      <Card className="glass-card border-white/10 overflow-hidden">
        <CardContent className="p-0">
          <div className="w-full h-[600px] bg-gradient-to-br from-slate-900/50 to-slate-800/50 relative overflow-hidden">
            <div className="absolute inset-0 bg-gradient-to-br from-indigo-500/5 to-purple-500/5 animate-pulse-slow" />

            <svg
              viewBox="0 0 1200 600"
              className="w-full h-full"
              style={{
                transform: `scale(${zoomLevel}) translate(${panOffset.x}px, ${panOffset.y}px)`,
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

                <filter id="glow">
                  <feGaussianBlur stdDeviation="3" result="coloredBlur" />
                  <feMerge>
                    <feMergeNode in="coloredBlur" />
                    <feMergeNode in="SourceGraphic" />
                  </feMerge>
                </filter>
              </defs>

              {/* Edges */}
              <g className="edges">
                {knowledgeGraphData.edges.map((edge) => {
                  const source = knowledgeGraphData.nodes.find((n) => n.id === edge.source)!
                  const target = knowledgeGraphData.nodes.find((n) => n.id === edge.target)!
                  const isHighlighted = isEdgeHighlighted(edge.id)

                  return (
                    <g key={edge.id}>
                      <path
                        d={getBezierPath(source, target)}
                        stroke={isHighlighted ? "#6366F1" : edge.color}
                        strokeWidth={isHighlighted ? 3 : 2}
                        fill="none"
                        markerEnd="url(#arrowhead)"
                        opacity={isHighlighted ? 1 : 0.3}
                        style={{
                          transition: "all 0.2s ease",
                          filter: isHighlighted ? "url(#glow)" : "none",
                        }}
                      />
                      {edge.label && (
                        <text
                          x={
                            (source.position.x + source.size.width / 2 + target.position.x + target.size.width / 2) / 2
                          }
                          y={(source.position.y + source.size.height + target.position.y) / 2}
                          fill="#9CA3AF"
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
                {knowledgeGraphData.nodes.map((node) => {
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
                        rx={12}
                        fill="rgba(255, 255, 255, 0.05)"
                        stroke={isHovered ? "#6366F1" : "rgba(255, 255, 255, 0.1)"}
                        strokeWidth={isHovered ? 3 : 2}
                        style={{
                          transition: "all 0.2s ease",
                          filter: isHovered
                            ? "url(#glow) drop-shadow(0 4px 12px rgba(99, 102, 241, 0.3))"
                            : "drop-shadow(0 2px 4px rgba(0, 0, 0, 0.3))",
                        }}
                        className={node.level === 0 ? "animate-breathe" : ""}
                      />

                      {/* Icon */}
                      <text x={20} y={40} fontSize={24}>
                        {node.icon}
                      </text>

                      {/* Label */}
                      <text x={20} y={65} fontSize={14} fontWeight={600} fill="rgba(255, 255, 255, 0.9)">
                        {node.label}
                      </text>

                      {/* Value */}
                      <text x={20} y={88} fontSize={18} fontWeight={700} fill="white">
                        {node.displayValue}
                      </text>

                      {/* Trend */}
                      <text
                        x={20}
                        y={node.level === 0 ? 110 : 105}
                        fontSize={13}
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
                        r={6}
                        fill={
                          node.healthStatus === "normal"
                            ? "#10B981"
                            : node.healthStatus === "warning"
                              ? "#F59E0B"
                              : "#EF4444"
                        }
                        className="animate-pulse-slow"
                      />
                    </g>
                  )
                })}
              </g>
            </svg>
          </div>
        </CardContent>
      </Card>

      {selectedNode && (
        <>
          <Card className="fixed inset-x-4 top-1/2 -translate-y-1/2 max-w-2xl mx-auto z-50 glass-card border-white/10 shadow-2xl">
            <CardHeader>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <span className="text-3xl">{selectedNode.icon}</span>
                  <div>
                    <CardTitle className="text-white">{selectedNode.fullName || selectedNode.label}</CardTitle>
                    <p className="text-sm text-white/60 mt-1">{selectedNode.formula}</p>
                  </div>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setSelectedNode(null)}
                  className="text-white/80 hover:text-white"
                >
                  Close
                </Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-3 gap-4">
                <div className="space-y-1">
                  <div className="text-sm text-white/60">Current Value</div>
                  <div className="text-2xl font-bold text-white">{selectedNode.displayValue}</div>
                </div>
                <div className="space-y-1">
                  <div className="text-sm text-white/60">Change</div>
                  <div
                    className={`text-2xl font-bold ${selectedNode.changeDirection === "up" ? "text-emerald-400" : "text-red-400"}`}
                  >
                    {selectedNode.change > 0 ? "+" : ""}
                    {selectedNode.change}%
                  </div>
                </div>
                <div className="space-y-1">
                  <div className="text-sm text-white/60">Status</div>
                  <Badge
                    className={
                      selectedNode.healthStatus === "normal"
                        ? "bg-emerald-500/20 text-emerald-400 border-emerald-500/30"
                        : selectedNode.healthStatus === "warning"
                          ? "bg-amber-500/20 text-amber-400 border-amber-500/30"
                          : "bg-red-500/20 text-red-400 border-red-500/30"
                    }
                  >
                    {selectedNode.healthStatus}
                  </Badge>
                </div>
              </div>

              <div className="space-y-2">
                <div className="text-sm font-semibold text-white">Breakdown</div>
                {selectedNode.childIds.length > 0 ? (
                  <div className="space-y-2">
                    {selectedNode.childIds.map((childId) => {
                      const child = knowledgeGraphData.nodes.find((n) => n.id === childId)
                      if (!child) return null
                      return (
                        <div
                          key={childId}
                          className="flex items-center justify-between p-3 rounded-lg bg-white/5 hover:bg-white/10 transition-colors cursor-pointer border border-white/10"
                          onClick={() => setSelectedNode(child)}
                        >
                          <div className="flex items-center gap-2">
                            <span className="text-xl">{child.icon}</span>
                            <span className="text-sm font-medium text-white">{child.label}</span>
                          </div>
                          <div className="flex items-center gap-3">
                            <span className="text-sm font-bold text-white">{child.displayValue}</span>
                            <span
                              className={`text-xs font-medium ${child.changeDirection === "up" ? "text-emerald-400" : "text-red-400"}`}
                            >
                              {child.changeDirection === "up" ? "↗" : "↘"} {child.change}%
                            </span>
                          </div>
                        </div>
                      )
                    })}
                  </div>
                ) : (
                  <p className="text-sm text-white/60">This is a leaf metric with no sub-metrics.</p>
                )}
              </div>

              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  className="border-white/10 text-white hover:bg-white/10 bg-transparent"
                >
                  View Trend
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  className="border-white/10 text-white hover:bg-white/10 bg-transparent"
                >
                  Drill Down
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  className="border-white/10 text-white hover:bg-white/10 bg-transparent"
                >
                  Export Data
                </Button>
              </div>
            </CardContent>
          </Card>
          <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40" onClick={() => setSelectedNode(null)} />
        </>
      )}
    </div>
  )
}
