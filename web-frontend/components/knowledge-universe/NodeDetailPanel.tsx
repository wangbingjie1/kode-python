"use client"

import { X, Link2, Database } from "lucide-react"
import type { OntologyNode, OntologyRelation, ObjectType } from "@/types/ontology"
import { NodeColors, RelationColors } from "@/types/ontology"

interface NodeDetailPanelProps {
  node: OntologyNode
  relations: {
    incoming: OntologyRelation[]
    outgoing: OntologyRelation[]
  }
  allNodes: OntologyNode[]
  onClose: () => void
  onNodeClick: (nodeId: string) => void
}

export function NodeDetailPanel({ 
  node, 
  relations, 
  allNodes, 
  onClose, 
  onNodeClick 
}: NodeDetailPanelProps) {
  const colors = NodeColors[node.type]
  const totalRelations = relations.incoming.length + relations.outgoing.length

  const getNodeName = (nodeId: string) => {
    const n = allNodes.find(node => node.id === nodeId)
    return n ? n.id.replace(/_/g, ' ') : nodeId
  }

  return (
    <div className="fixed top-16 right-[420px] bottom-0 w-[350px] bg-white border-l border-slate-200 z-30 flex flex-col shadow-lg">
      {/* Header */}
      <div 
        className="px-5 py-4 border-b border-slate-200"
        style={{ backgroundColor: colors.bg }}
      >
        <div className="flex justify-between items-start mb-2">
          <div 
            className="text-[10px] font-semibold uppercase tracking-wider"
            style={{ color: colors.text, opacity: 0.7 }}
          >
            {node.type}
          </div>
          <button
            onClick={onClose}
            className="w-7 h-7 rounded-lg flex items-center justify-center transition-all hover:bg-white/50"
          >
            <X className="w-4 h-4" style={{ color: colors.text }} />
          </button>
        </div>
        <h3 
          className="text-base font-semibold leading-tight"
          style={{ color: colors.text }}
        >
          {node.id.replace(/_/g, ' ').toUpperCase()}
        </h3>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto px-5 py-4">
        {/* Properties */}
        <div className="mb-6">
          <div className="flex items-center gap-2 mb-3">
            <Database className="w-4 h-4 text-[#5A95A8]" />
            <h4 className="text-xs font-semibold text-[#4A5568] uppercase tracking-wider">
              Properties
            </h4>
          </div>
          <div className="space-y-2">
            {Object.entries(node.properties).map(([key, value]) => (
              <div key={key} className="bg-[#F8F9FB] rounded-lg px-3 py-2">
                <div className="text-[10px] text-[#6B7280] uppercase tracking-wide mb-0.5">
                  {key}
                </div>
                <div className="text-sm text-[#2D3748] font-medium break-words">
                  {String(value)}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Relations */}
        <div>
          <div className="flex items-center gap-2 mb-3">
            <Link2 className="w-4 h-4 text-[#5A95A8]" />
            <h4 className="text-xs font-semibold text-[#4A5568] uppercase tracking-wider">
              Relations ({totalRelations})
            </h4>
          </div>

          {/* Outgoing Relations */}
          {relations.outgoing.length > 0 && (
            <div className="mb-4">
              <div className="text-[10px] text-[#6B7280] uppercase tracking-wide mb-2 px-1">
                Outgoing ({relations.outgoing.length})
              </div>
              <div className="space-y-1.5">
                {relations.outgoing.map((rel, idx) => (
                  <button
                    key={idx}
                    onClick={() => onNodeClick(rel.target)}
                    className="w-full text-left px-3 py-2 bg-[#F8F9FB] rounded-lg hover:bg-[#E5E7EB] transition-all group"
                  >
                    <div className="flex items-center gap-2 mb-1">
                      <div 
                        className="w-2 h-2 rounded-full"
                        style={{ backgroundColor: RelationColors[rel.type] }}
                      />
                      <span className="text-[10px] text-[#6B7280] font-medium">
                        {rel.type.replace(/_/g, ' ')}
                      </span>
                    </div>
                    <div className="text-sm text-[#2D3748] font-medium group-hover:text-[#5A95A8] transition-colors flex items-center gap-1">
                      <span className="truncate">{getNodeName(rel.target)}</span>
                      <span className="text-xs opacity-0 group-hover:opacity-100">→</span>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Incoming Relations */}
          {relations.incoming.length > 0 && (
            <div>
              <div className="text-[10px] text-[#6B7280] uppercase tracking-wide mb-2 px-1">
                Incoming ({relations.incoming.length})
              </div>
              <div className="space-y-1.5">
                {relations.incoming.map((rel, idx) => (
                  <button
                    key={idx}
                    onClick={() => onNodeClick(rel.source)}
                    className="w-full text-left px-3 py-2 bg-[#F8F9FB] rounded-lg hover:bg-[#E5E7EB] transition-all group"
                  >
                    <div className="flex items-center gap-2 mb-1">
                      <div 
                        className="w-2 h-2 rounded-full"
                        style={{ backgroundColor: RelationColors[rel.type] }}
                      />
                      <span className="text-[10px] text-[#6B7280] font-medium">
                        {rel.type.replace(/_/g, ' ')}
                      </span>
                    </div>
                    <div className="text-sm text-[#2D3748] font-medium group-hover:text-[#5A95A8] transition-colors flex items-center gap-1">
                      <span className="text-xs opacity-0 group-hover:opacity-100">←</span>
                      <span className="truncate">{getNodeName(rel.source)}</span>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          )}

          {totalRelations === 0 && (
            <div className="text-center py-8">
              <div className="text-3xl mb-2 opacity-30">🔗</div>
              <div className="text-xs text-[#6B7280]">No relations found</div>
            </div>
          )}
        </div>
      </div>

      {/* Footer Stats */}
      <div className="px-5 py-3 border-t border-slate-200 bg-[#F8F9FB]">
        <div className="flex justify-between text-xs text-[#6B7280]">
          <span>Incoming: <strong className="text-[#2D3748]">{relations.incoming.length}</strong></span>
          <span>Outgoing: <strong className="text-[#2D3748]">{relations.outgoing.length}</strong></span>
          <span>Total: <strong className="text-[#2D3748]">{totalRelations}</strong></span>
        </div>
      </div>
    </div>
  )
}
