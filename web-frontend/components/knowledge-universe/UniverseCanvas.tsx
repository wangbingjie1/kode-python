"use client"

import { useRef, useState } from "react"
import type { Card, Connection } from "@/types/knowledge-universe"

interface UniverseCanvasProps {
  cards: Card[]
  connections: Connection[]
  onCardSelect: (cardId: string) => void
  onCardEdit: (cardId: string) => void
  onCardDelete: (cardId: string) => void
  selectedCard: string | null
}

export default function UniverseCanvas({
  cards,
  connections,
  onCardSelect,
  onCardEdit,
  onCardDelete,
  selectedCard,
}: UniverseCanvasProps) {
  const canvasRef = useRef<HTMLDivElement>(null)
  const [hoveredCard, setHoveredCard] = useState<string | null>(null)

  return (
    <div ref={canvasRef} className="relative w-full h-full overflow-auto p-12">
      {/* Grid Background */}
      <div
        className="absolute inset-0 opacity-30"
        style={{
          backgroundImage: "radial-gradient(circle, #CBD5E0 1px, transparent 1px)",
          backgroundSize: "30px 30px",
        }}
      />

      {/* Connections */}
      <svg className="absolute inset-0 w-full h-full pointer-events-none" style={{ zIndex: 1 }}>
        {connections.map((conn, idx) => {
          const fromCard = cards.find((c) => c.id === conn.from)
          const toCard = cards.find((c) => c.id === conn.to)
          if (!fromCard || !toCard) return null

          const x1 = fromCard.col * 200 + 100
          const y1 = fromCard.row * 180 + 90
          const x2 = toCard.col * 200 + 100
          const y2 = toCard.row * 180 + 90

          return (
            <line key={idx} x1={x1} y1={y1} x2={x2} y2={y2} stroke="#CBD5E0" strokeWidth="2" strokeDasharray="5,5" />
          )
        })}
      </svg>

      {/* Cards */}
      {cards.map((card) => (
        <div
          key={card.id}
          className={`absolute w-[180px] bg-white rounded-xl p-4 cursor-pointer transition-all shadow-md hover:shadow-xl hover:-translate-y-1 ${
            selectedCard === card.id ? "ring-2 ring-[#5A95A8]" : ""
          }`}
          style={{
            left: `${card.col * 200}px`,
            top: `${card.row * 180}px`,
            zIndex: 10,
          }}
          onClick={() => onCardSelect(card.id)}
          onMouseEnter={() => setHoveredCard(card.id)}
          onMouseLeave={() => setHoveredCard(null)}
        >
          {/* Card Header */}
          <div className="flex justify-between items-start mb-3">
            <div className="flex-1">
              <div className="text-xs text-[#A0AEC0] uppercase tracking-wide mb-1">{card.type}</div>
              <div className="text-sm font-semibold text-[#1A202C] leading-tight">{card.title}</div>
            </div>
            <div className="px-2 py-1 bg-[#E6F7FF] text-[#5A95A8] text-xs font-medium rounded">{card.badge}</div>
          </div>

          {/* Card Stats */}
          <div className="space-y-2">
            {Object.entries(card.stats).map(([key, value]) => (
              <div key={key} className="flex justify-between text-xs">
                <span className="text-[#718096]">{key}</span>
                <span className="text-[#2D3748] font-medium">{value}</span>
              </div>
            ))}
          </div>

          {/* Card Actions (show on hover) */}
          {hoveredCard === card.id && (
            <div className="absolute top-2 right-2 flex gap-1">
              <button
                onClick={(e) => {
                  e.stopPropagation()
                  onCardEdit(card.id)
                }}
                className="w-6 h-6 bg-white rounded shadow-md flex items-center justify-center text-[#718096] hover:text-[#5A95A8] hover:bg-[#F8F9FA]"
              >
                ✎
              </button>
              <button
                onClick={(e) => {
                  e.stopPropagation()
                  onCardDelete(card.id)
                }}
                className="w-6 h-6 bg-white rounded shadow-md flex items-center justify-center text-[#718096] hover:text-[#EF4444] hover:bg-[#FEF2F2]"
              >
                ×
              </button>
            </div>
          )}
        </div>
      ))}
    </div>
  )
}
