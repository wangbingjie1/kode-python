"use client"

import type React from "react"

import { useState, useRef, useCallback } from "react"
import type { FormatType, PreviewData } from "@/lib/types"
import { getFormatPreviewData } from "@/lib/preview-data"

interface FormatCardProps {
  format: {
    type: FormatType
    name: string
    icon: React.ComponentType<{ className?: string }>
    color: string
    accept: string
  }
  index: number
  onShowPreview: (data: PreviewData, position: { x: number; y: number }) => void
  onHidePreview: () => void
  onCardClick: () => void
}

export function FormatCard({ format, index, onShowPreview, onHidePreview, onCardClick }: FormatCardProps) {
  const [isHovered, setIsHovered] = useState(false)
  const cardRef = useRef<HTMLDivElement>(null)
  const hoverTimerRef = useRef<NodeJS.Timeout>()
  const hideTimerRef = useRef<NodeJS.Timeout>()

  const Icon = format.icon

  const handleMouseEnter = useCallback(() => {
    if (hideTimerRef.current) {
      clearTimeout(hideTimerRef.current)
    }

    hoverTimerRef.current = setTimeout(() => {
      if (cardRef.current) {
        const rect = cardRef.current.getBoundingClientRect()
        const previewData = getFormatPreviewData(format.type)
        onShowPreview(previewData, {
          x: rect.right + 16,
          y: rect.top + rect.height / 2,
        })
        setIsHovered(true)
      }
    }, 300)
  }, [format.type, onShowPreview])

  const handleMouseLeave = useCallback(() => {
    if (hoverTimerRef.current) {
      clearTimeout(hoverTimerRef.current)
    }

    hideTimerRef.current = setTimeout(() => {
      onHidePreview()
      setIsHovered(false)
    }, 200)
  }, [onHidePreview])

  const handleClick = useCallback(
    (e: React.MouseEvent) => {
      e.stopPropagation()
      onCardClick()
    },
    [onCardClick],
  )

  return (
    <div
      ref={cardRef}
      className="group relative z-10 cursor-pointer rounded-lg bg-white p-4 text-center shadow-sm transition-all duration-300 hover:z-20 hover:-translate-y-1 hover:shadow-md"
      style={{ borderTop: `3px solid ${format.color}`, animationDelay: `${0.6 + index * 0.05}s` }}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      onClick={handleClick}
    >
      <div
        className="absolute inset-0 rounded-lg opacity-0 transition-opacity duration-300 group-hover:opacity-100"
        style={{
          background: `linear-gradient(to bottom, ${format.color}0D 0%, white 100%)`,
        }}
      />
      <div className="relative">
        <Icon className="mx-auto mb-2 h-10 w-10" style={{ color: format.color }} />
        <div className="text-[13px] font-semibold text-[#2C3E50]">{format.name}</div>
      </div>
    </div>
  )
}
