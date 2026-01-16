"use client"

import { DataSourceCard } from "./data-source-card"
import type { DataSourceType, PreviewData } from "@/lib/types"

const dataSources: Array<{
  type: DataSourceType
  name: string
  badge: string
  logo: string
  brandColor: string
}> = [
  { type: "snowflake", name: "Snowflake", badge: "Enterprise", logo: "❄️", brandColor: "rgba(41, 187, 239, 0.05)" },
  { type: "bigquery", name: "BigQuery", badge: "Real-time", logo: "🔷", brandColor: "rgba(66, 133, 244, 0.05)" },
  { type: "postgresql", name: "PostgreSQL", badge: "Open Source", logo: "🐘", brandColor: "rgba(51, 103, 145, 0.05)" },
  { type: "google-ads", name: "Google Ads", badge: "Marketing", logo: "🎯", brandColor: "rgba(52, 168, 83, 0.05)" },
  { type: "salesforce", name: "Salesforce", badge: "CRM", logo: "☁️", brandColor: "rgba(0, 161, 224, 0.05)" },
  { type: "mysql", name: "MySQL", badge: "Popular", logo: "🐬", brandColor: "rgba(0, 117, 143, 0.05)" },
  { type: "mongodb", name: "MongoDB", badge: "NoSQL", logo: "🍃", brandColor: "rgba(0, 237, 100, 0.05)" },
  { type: "hubspot", name: "HubSpot", badge: "Automation", logo: "🧲", brandColor: "rgba(255, 122, 89, 0.05)" },
]

interface DataIntegrationSectionProps {
  onShowPreview: (data: PreviewData, position: { x: number; y: number }) => void
  onHidePreview: () => void
}

export function DataIntegrationSection({ onShowPreview, onHidePreview }: DataIntegrationSectionProps) {
  return (
    <section className="animate-slide-in-right flex min-h-[600px] flex-col rounded-xl bg-white p-8 shadow-sm">
      <h2 className="mb-2 text-xl font-semibold text-[#2C3E50]">Connect Your Data Sources</h2>
      <p className="mb-8 text-sm text-[#6B7280]">One-click integration, real-time analysis</p>

      <div className="flex-1">
        <div className="grid grid-cols-2 gap-3">
          {dataSources.map((source) => (
            <DataSourceCard
              key={source.type}
              source={source}
              onShowPreview={onShowPreview}
              onHidePreview={onHidePreview}
            />
          ))}
        </div>
      </div>
    </section>
  )
}
