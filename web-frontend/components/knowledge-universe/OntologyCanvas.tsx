"use client"

import { useState, useMemo } from "react"
import type { OntologyNode, OntologyRelation, ObjectType, RelationType } from "@/types/ontology"
import { NodeLevels, NodeColors, RelationColors } from "@/types/ontology"
import { NodeDetailPanel } from "./NodeDetailPanel"
import { Focus } from "lucide-react"

interface OntologyCanvasProps {
  nodes: OntologyNode[]
  relations: OntologyRelation[]
  selectedNodeTypes: ObjectType[]
  selectedLevels: number[]
  selectedRelationTypes: RelationType[]
}

export function OntologyCanvas({
  nodes,
  relations,
  selectedNodeTypes,
  selectedLevels,
  selectedRelationTypes,
}: OntologyCanvasProps) {
  const [selectedNode, setSelectedNode] = useState<string | null>(null)
  const [hoveredNode, setHoveredNode] = useState<string | null>(null)
  const [focusMode, setFocusMode] = useState(false)

  // 计算筛选后的节点和关系
  const { filteredNodes, nodePositions } = useMemo(() => {
    // 1. 计算累积层级（向上兼容）
    const maxLevel = selectedLevels.length > 0 ? Math.max(...selectedLevels) : 0
    const cumulativeLevels = maxLevel > 0 ? Array.from({ length: maxLevel }, (_, i) => i + 1) : []

    // 2. 先筛选关系（因为需要基于关系筛选节点）
    const filteredRels = relations.filter((rel) => selectedRelationTypes.includes(rel.type))

    // 3. 获取参与筛选关系的所有节点ID
    const nodesInRelations = new Set<string>()
    filteredRels.forEach((rel) => {
      nodesInRelations.add(rel.source)
      nodesInRelations.add(rel.target)
    })

    // 4. 筛选节点（必须同时满足：类型匹配、层级匹配、参与筛选的关系）
    let filtered = nodes.filter((node) => {
      const nodeLevel = NodeLevels[node.type]
      const matchesType = selectedNodeTypes.includes(node.type)
      const matchesLevel = cumulativeLevels.includes(nodeLevel)
      const matchesRelation = selectedRelationTypes.length === 0 || nodesInRelations.has(node.id)

      return matchesType && matchesLevel && matchesRelation
    })

    // 5. 聚焦模式：只显示选中节点及其邻居
    if (focusMode && selectedNode) {
      const relatedNodeIds = new Set<string>([selectedNode])
      filteredRels.forEach((rel) => {
        if (rel.source === selectedNode) relatedNodeIds.add(rel.target)
        if (rel.target === selectedNode) relatedNodeIds.add(rel.source)
      })
      filtered = filtered.filter((node) => relatedNodeIds.has(node.id))
    }

    // 6. 按层级分组
    const nodesByLevel: Record<number, OntologyNode[]> = { 1: [], 2: [], 3: [], 4: [] }
    filtered.forEach((node) => {
      const level = NodeLevels[node.type]
      nodesByLevel[level].push(node)
    })

    // 7. 改进的布局算法 - 基于关系的智能布局
    const positions: Record<string, { x: number; y: number }> = {}
    const levelWidth = 300 // 每层宽度
    const baseNodeHeight = 140 // 基础节点高度
    const minVerticalGap = 20 // 最小垂直间距
    const startX = 80
    const startY = 80

    // 计算每个节点的连接数
    const nodeConnections: Record<string, number> = {}
    filtered.forEach((node) => {
      const connections = filteredRels.filter((rel) => rel.source === node.id || rel.target === node.id).length
      nodeConnections[node.id] = connections
    })

    // 为每个层级计算节点位置
    Object.entries(nodesByLevel).forEach(([level, levelNodes]) => {
      if (levelNodes.length === 0) return

      const levelNum = Number.parseInt(level)
      const x = startX + (levelNum - 1) * levelWidth

      // 按连接数排序（连接多的节点放中间，减少线条交叉）
      const sortedNodes = [...levelNodes].sort((a, b) => {
        const connA = nodeConnections[a.id] || 0
        const connB = nodeConnections[b.id] || 0
        return connB - connA // 降序
      })

      // 动态计算垂直间距
      const totalNodes = sortedNodes.length
      const dynamicGap = totalNodes > 5 ? minVerticalGap : minVerticalGap * 2

      // 将连接数最多的节点放在中间
      const midIndex = Math.floor(totalNodes / 2)
      sortedNodes.forEach((node, index) => {
        const offset = index - midIndex
        const y = startY + midIndex * (baseNodeHeight + dynamicGap) + offset * (baseNodeHeight + dynamicGap)
        positions[node.id] = { x, y: Math.max(startY, y) }
      })
    })

    return { filteredNodes: filtered, nodePositions: positions }
  }, [nodes, selectedNodeTypes, selectedLevels, selectedRelationTypes, focusMode, selectedNode, relations])

  // 筛选关系（只显示可见节点之间的关系）
  const filteredRelations = useMemo(() => {
    const visibleNodeIds = new Set(filteredNodes.map((n) => n.id))
    return relations.filter(
      (rel) =>
        selectedRelationTypes.includes(rel.type) && visibleNodeIds.has(rel.source) && visibleNodeIds.has(rel.target),
    )
  }, [relations, filteredNodes, selectedRelationTypes])

  // 获取选中节点的关系
  const selectedNodeRelations = useMemo(() => {
    if (!selectedNode) return { incoming: [], outgoing: [] }
    return {
      incoming: filteredRelations.filter((rel) => rel.target === selectedNode),
      outgoing: filteredRelations.filter((rel) => rel.source === selectedNode),
    }
  }, [selectedNode, filteredRelations])

  // 计算画布尺寸
  const canvasSize = useMemo(() => {
    const positions = Object.values(nodePositions)
    if (positions.length === 0) return { width: 1200, height: 800 }

    const maxX = Math.max(...positions.map((p) => p.x), 0)
    const maxY = Math.max(...positions.map((p) => p.y), 0)
    return {
      width: maxX + 400,
      height: maxY + 300,
    }
  }, [nodePositions])

  const handleNodeClick = (nodeId: string) => {
    setSelectedNode(nodeId === selectedNode ? null : nodeId)
  }

  return (
    <>
      <div className="relative w-full h-full overflow-auto p-8">
        {/* 背景网格 */}
        <div
          className="absolute inset-0 opacity-20"
          style={{
            backgroundImage: "radial-gradient(circle, #CBD5E0 1px, transparent 1px)",
            backgroundSize: "30px 30px",
          }}
        />

        {/* SVG 层 - 关系线 */}
        <svg
          className="absolute top-0 left-0 pointer-events-none"
          style={{
            width: canvasSize.width,
            height: canvasSize.height,
            zIndex: 1,
          }}
        >
          <defs>
            {Object.entries(RelationColors).map(([type, color]) => (
              <marker
                key={type}
                id={`arrow-${type}`}
                markerWidth="10"
                markerHeight="10"
                refX="9"
                refY="3"
                orient="auto"
                markerUnits="strokeWidth"
              >
                <path d="M0,0 L0,6 L9,3 z" fill={color} />
              </marker>
            ))}
          </defs>

          {filteredRelations.map((rel, idx) => {
            const sourcePos = nodePositions[rel.source]
            const targetPos = nodePositions[rel.target]
            if (!sourcePos || !targetPos) return null

            const x1 = sourcePos.x + 200 // 节点宽度
            const y1 = sourcePos.y + 60 // 节点高度一半
            const x2 = targetPos.x
            const y2 = targetPos.y + 60

            const color = RelationColors[rel.type]

            const isRelated = selectedNode && (rel.source === selectedNode || rel.target === selectedNode)
            const opacity = selectedNode ? (isRelated ? 1 : 0.15) : 0.7
            const strokeWidth = isRelated ? 3 : 2

            return (
              <g key={rel.id || idx}>
                <path
                  d={`M ${x1} ${y1} C ${(x1 + x2) / 2} ${y1}, ${(x1 + x2) / 2} ${y2}, ${x2} ${y2}`}
                  stroke={color}
                  strokeWidth={strokeWidth}
                  fill="none"
                  strokeDasharray="5,5"
                  markerEnd={`url(#arrow-${rel.type})`}
                  opacity={opacity}
                  className="transition-all duration-300"
                />
              </g>
            )
          })}
        </svg>

        {/* 节点层 */}
        <div className="relative" style={{ width: canvasSize.width, height: canvasSize.height, zIndex: 10 }}>
          {filteredNodes.map((node) => {
            const pos = nodePositions[node.id]
            if (!pos) return null

            const colors = NodeColors[node.type]
            const isSelected = selectedNode === node.id
            const isHovered = hoveredNode === node.id

            const isRelated =
              selectedNode &&
              filteredRelations.some(
                (rel) =>
                  (rel.source === selectedNode && rel.target === node.id) ||
                  (rel.target === selectedNode && rel.source === node.id),
              )
            const isDimmed = selectedNode && !isSelected && !isRelated

            return (
              <div
                key={node.id}
                className="absolute w-[200px] rounded-xl p-4 cursor-pointer transition-all duration-300"
                style={{
                  left: pos.x,
                  top: pos.y,
                  backgroundColor: colors.bg,
                  border: `2px solid ${colors.border}`,
                  boxShadow: isSelected || isHovered ? "0 8px 24px rgba(0,0,0,0.15)" : "0 2px 8px rgba(0,0,0,0.06)",
                  opacity: isDimmed ? 0.2 : 1,
                  transform: isSelected || isHovered ? "translateY(-4px) scale(1.02)" : "translateY(0) scale(1)",
                }}
                onClick={() => handleNodeClick(node.id)}
                onMouseEnter={() => setHoveredNode(node.id)}
                onMouseLeave={() => setHoveredNode(null)}
              >
                <div className="flex justify-between items-start mb-2">
                  <div className="flex-1">
                    <div
                      className="text-[10px] font-semibold uppercase tracking-wide mb-1"
                      style={{ color: colors.text, opacity: 0.7 }}
                    >
                      {node.type}
                    </div>
                    <div className="text-sm font-semibold leading-tight" style={{ color: colors.text }}>
                      {node.id.replace(/_/g, " ")}
                    </div>
                  </div>
                </div>

                <div className="mt-3 space-y-1">
                  {Object.entries(node.properties)
                    .slice(0, 2)
                    .map(([key, value]) => (
                      <div key={key} className="flex justify-between text-[11px]">
                        <span className="text-slate-500 truncate mr-2">{key}:</span>
                        <span className="text-slate-700 font-medium truncate">
                          {String(value).substring(0, 20)}
                          {String(value).length > 20 ? "..." : ""}
                        </span>
                      </div>
                    ))}
                </div>

                {isSelected && (
                  <div
                    className="absolute -top-1 -right-1 w-5 h-5 rounded-full flex items-center justify-center text-white text-xs font-bold"
                    style={{ backgroundColor: colors.border }}
                  >
                    ✓
                  </div>
                )}
              </div>
            )
          })}
        </div>

        {/* 层级标签 */}
        <div className="absolute top-4 left-8 flex gap-6 z-20">
          {[
            { level: 1, label: "Data", x: 80 },
            { level: 2, label: "Analysis/Model", x: 380 },
            { level: 3, label: "Report/Cohort", x: 680 },
            { level: 4, label: "Strategy/Campaign", x: 980 },
          ].map(({ level, label, x }) => {
            const maxLevel = selectedLevels.length > 0 ? Math.max(...selectedLevels) : 0
            if (level > maxLevel) return null

            return (
              <div
                key={level}
                className="text-xs font-semibold text-slate-600 uppercase tracking-wide"
                style={{ marginLeft: level === 1 ? 0 : "300px" }}
              >
                {label}
              </div>
            )
          })}
        </div>

        {/* 聚焦模式切换按钮 */}
        {selectedNode && (
          <button
            onClick={() => setFocusMode(!focusMode)}
            className={`absolute left-8 bottom-8 z-20 flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all shadow-md ${
              focusMode ? "bg-[#5A95A8] text-white" : "bg-white/95 text-slate-700 hover:bg-white"
            }`}
          >
            <Focus className="w-4 h-4" />
            <span>{focusMode ? "Exit Focus" : "Focus Mode"}</span>
          </button>
        )}

        {/* 空状态 */}
        {filteredNodes.length === 0 && (
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="text-center">
              <div className="text-4xl mb-4 opacity-30">🔍</div>
              <div className="text-sm font-medium text-slate-600">No nodes match your filters</div>
              <div className="text-xs text-slate-500 mt-1">Try adjusting your filter settings</div>
            </div>
          </div>
        )}

        {/* 统计信息 */}
        <div className="fixed right-[420px] bottom-8 bg-white/95 backdrop-blur-md rounded-lg shadow-md px-4 py-2 text-xs text-slate-600 z-20">
          <div className="flex gap-4">
            <span>
              Nodes: <strong>{filteredNodes.length}</strong>/{nodes.length}
            </span>
            <span>
              Relations: <strong>{filteredRelations.length}</strong>/{relations.length}
            </span>
          </div>
        </div>
      </div>

      {/* 节点详情面板 */}
      {selectedNode && filteredNodes.find((n) => n.id === selectedNode) && (
        <NodeDetailPanel
          node={filteredNodes.find((n) => n.id === selectedNode)!}
          relations={selectedNodeRelations}
          allNodes={nodes}
          onClose={() => setSelectedNode(null)}
          onNodeClick={handleNodeClick}
        />
      )}
    </>
  )
}
