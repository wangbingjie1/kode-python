"use client"

import { useEffect, useState, useRef } from "react"
import type { PreviewData } from "@/lib/types"

interface PreviewLayerProps {
  data: PreviewData
  position: { x: number; y: number }
  onClose: () => void
}

export function PreviewLayer({ data, position, onClose }: PreviewLayerProps) {
  const [isVisible, setIsVisible] = useState(false)
  const [adjustedPosition, setAdjustedPosition] = useState(position)
  const layerRef = useRef<HTMLDivElement>(null)
  const hideTimerRef = useRef<NodeJS.Timeout>()

  useEffect(() => {
    requestAnimationFrame(() => {
      setIsVisible(true)

      if (layerRef.current) {
        const rect = layerRef.current.getBoundingClientRect()
        const viewportHeight = window.innerHeight
        const viewportWidth = window.innerWidth

        let finalY = position.y - rect.height / 2
        let finalX = position.x

        if (finalX + rect.width > viewportWidth - 20) {
          // Not enough space on right, position on left
          const cardElement = document.elementFromPoint(position.x - 10, position.y)
          if (cardElement) {
            const cardRect = cardElement.getBoundingClientRect()
            finalX = cardRect.left - rect.width - 16
          }
        }

        // Adjust vertical position if exceeds viewport
        if (finalY + rect.height > viewportHeight - 20) {
          finalY = viewportHeight - rect.height - 20
        }
        if (finalY < 20) {
          finalY = 20
        }

        setAdjustedPosition({ x: finalX, y: finalY })
      }
    })
  }, [position])

  const handleMouseEnter = () => {
    if (hideTimerRef.current) {
      clearTimeout(hideTimerRef.current)
    }
  }

  const handleMouseLeave = () => {
    hideTimerRef.current = setTimeout(() => {
      setIsVisible(false)
      setTimeout(onClose, 200)
    }, 200)
  }

  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setIsVisible(false)
        setTimeout(onClose, 200)
      }
    }

    document.addEventListener("keydown", handleEscape)
    return () => document.removeEventListener("keydown", handleEscape)
  }, [onClose])

  return (
    <div
      ref={layerRef}
      className={`fixed z-[9999] w-[420px] rounded-2xl bg-white p-6 shadow-[0_0_0_1px_rgba(90,149,168,0.1),0_8px_32px_rgba(0,0,0,0.12)] transition-all duration-250 ${
        isVisible ? "pointer-events-auto translate-x-0 opacity-100" : "pointer-events-none -translate-x-2.5 opacity-0"
      }`}
      style={{
        left: `${adjustedPosition.x}px`,
        top: `${adjustedPosition.y}px`,
      }}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
    >
      <div className="mb-4 border-b border-dashed border-[#E5E7EB] pb-3 text-base font-semibold text-[#2C3E50]">
        {data.title}
      </div>
      <div className="max-h-[60vh] overflow-y-auto text-sm leading-relaxed text-[#4A5568]">
        {data.sections.map((section, index) => (
          <div key={index} className="mb-4">
            {section.title && <div className="mb-2 font-semibold text-[#2D3748]">{section.title}</div>}
            <ul className="space-y-3">
              {section.items.map((item, itemIndex) => (
                <li key={itemIndex} className="relative pl-5">
                  <span className="absolute left-0 top-2 h-1.5 w-1.5 rounded-full bg-[#5A95A8]" />
                  <div>
                    {item.title && <strong>{item.title}</strong>}
                    {item.description && <div className="mt-1">{item.description}</div>}
                    {item.subItems && (
                      <ul className="mt-2 space-y-1.5">
                        {item.subItems.map((subItem, subIndex) => (
                          <li key={subIndex} className="relative pl-5 text-[13px]">
                            <span className="absolute left-0 top-2.5 h-1 w-1 rounded-full bg-[#A8D5BA]" />
                            {subItem}
                          </li>
                        ))}
                      </ul>
                    )}
                    {item.result && <div className="mt-1 text-[13px] text-[#6B7280]">→ {item.result}</div>}
                  </div>
                </li>
              ))}
            </ul>
          </div>
        ))}
        {data.output && (
          <div className="mt-4 rounded-lg border-l-3 border-[#5A95A8] bg-[#F8F9FB] p-4">
            <div className="mb-1 text-xs font-semibold text-[#6B7280]">Output Formats:</div>
            <div className="text-[13px] text-[#2D3748]">{data.output}</div>
          </div>
        )}
      </div>
    </div>
  )
}
