"use client"

import { useRef, useCallback } from "react"
import { ChevronRight } from "lucide-react"
import type { DataSourceType, PreviewData } from "@/lib/types"
import { getDataSourcePreviewData } from "@/lib/preview-data"

interface DataSourceCardProps {
  source: {
    type: DataSourceType
    name: string
    badge: string
    logo: string
    brandColor: string // Added brandColor for hover effects
  }
  onShowPreview: (data: PreviewData, position: { x: number; y: number }) => void
  onHidePreview: () => void
}

export function DataSourceCard({ source, onShowPreview, onHidePreview }: DataSourceCardProps) {
  const cardRef = useRef<HTMLDivElement>(null)
  const hoverTimerRef = useRef<NodeJS.Timeout>()
  const hideTimerRef = useRef<NodeJS.Timeout>()

  const handleMouseEnter = useCallback(() => {
    if (hideTimerRef.current) {
      clearTimeout(hideTimerRef.current)
    }

    hoverTimerRef.current = setTimeout(() => {
      if (cardRef.current) {
        const rect = cardRef.current.getBoundingClientRect()
        const previewData = getDataSourcePreviewData(source.type)
        onShowPreview(previewData, {
          x: rect.right + 16,
          y: rect.top + rect.height / 2,
        })
      }
    }, 300)
  }, [source.type, onShowPreview])

  const handleMouseLeave = useCallback(() => {
    if (hoverTimerRef.current) {
      clearTimeout(hoverTimerRef.current)
    }

    hideTimerRef.current = setTimeout(() => {
      onHidePreview()
    }, 200)
  }, [onHidePreview])

  return (
    <div
      ref={cardRef}
      className="group relative z-[2] flex cursor-pointer items-center gap-3 rounded-[10px] bg-white p-4 shadow-sm transition-all duration-300 hover:z-[3] hover:-translate-y-1 hover:shadow-md"
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
    >
      <div
        className="absolute inset-0 rounded-[10px] opacity-0 transition-opacity duration-300 group-hover:opacity-100"
        style={{
          background: `linear-gradient(135deg, ${source.brandColor} 0%, white 100%)`,
        }}
      />

      <div className="relative flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-lg bg-[#F8F9FA] text-2xl">
        {source.logo}
      </div>
      <div className="relative flex-1">
        <div className="mb-1 text-[15px] font-semibold text-[#2C3E50]">{source.name}</div>
        <span className="inline-block rounded bg-[#F8F9FA] px-2 py-0.5 text-[11px] font-medium text-[#6B7280]">
          {source.badge}
        </span>
      </div>
      <ChevronRight className="relative h-4 w-4 flex-shrink-0 text-[#9CA3AF] transition-all duration-300 group-hover:translate-x-1 group-hover:text-[#5A95A8]" />
    </div>
  )
}
