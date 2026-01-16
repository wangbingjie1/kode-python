"use client"

import { useState } from "react"
import type { ObjectType, RelationType } from "@/types/ontology"
import { ChevronDown, Filter, Check } from "lucide-react"

interface OntologyFiltersProps {
  selectedTypes: ObjectType[]
  onTypeToggle: (type: ObjectType) => void
  selectedLevels: number[]
  onLevelToggle: (level: number) => void
  selectedRelations: RelationType[]
  onRelationToggle: (relation: RelationType) => void
}

export function OntologyFilters({
  selectedTypes,
  onTypeToggle,
  selectedLevels,
  onLevelToggle,
  selectedRelations,
  onRelationToggle
}: OntologyFiltersProps) {
  const [isExpanded, setIsExpanded] = useState(true)

  const nodeTypes: ObjectType[] = [
    'DataSet',
    'Analysis',
    'Report',
    'MLModel',
    'UserCohort',
    'MarketingCampaign',
    'StrategyPlaybook'
  ]

  // 层级定义（向上兼容）
  const levels = [
    { value: 1, label: 'Data Layer', description: 'Raw datasets' },
    { value: 2, label: 'Analysis/Model Layer', description: '+ Analysis & ML Models' },
    { value: 3, label: 'Report/Cohort Layer', description: '+ Reports & User Segments' },
    { value: 4, label: 'Strategy/Campaign Layer', description: '+ Strategies & Campaigns' }
  ]

  const relationTypes: RelationType[] = [
    'USES_DATA',
    'TRAINS_MODEL',
    'GENERATES_REPORT',
    'INFORMS_STRATEGY',
    'TARGETS_COHORT',
    'AFFECTS_CAMPAIGN'
  ]

  const typeColors: Record<ObjectType, string> = {
    'DataSet': '#A8D5BA',
    'Analysis': '#F4E4C1',
    'Report': '#C9B6E4',
    'MLModel': '#7AB8CC',
    'UserCohort': '#F5CAC3',
    'MarketingCampaign': '#FED7AA',
    'StrategyPlaybook': '#BAE6FD'
  }

  // 获取最大选中层级
  const maxSelectedLevel = selectedLevels.length > 0 ? Math.max(...selectedLevels) : 0

  return (
    <div className="absolute left-5 top-24 z-20">
      {!isExpanded && (
        <button
          onClick={() => setIsExpanded(true)}
          className="flex items-center gap-2 px-4 py-2 bg-white/95 backdrop-blur-md rounded-lg shadow-md hover:shadow-lg transition-all"
        >
          <Filter className="w-4 h-4 text-[#5A95A8]" />
          <span className="text-sm font-medium text-[#2D3748]">Filters</span>
          <ChevronDown className="w-4 h-4 text-[#6B7280]" />
        </button>
      )}

      {isExpanded && (
        <div className="bg-white/95 backdrop-blur-md rounded-xl shadow-lg p-4 min-w-[320px]">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <Filter className="w-4 h-4 text-[#5A95A8]" />
              <span className="text-sm font-semibold text-[#1A202C]">Filters</span>
            </div>
            <button
              onClick={() => setIsExpanded(false)}
              className="text-xs text-[#6B7280] hover:text-[#2D3748] transition-colors"
            >
              Collapse
            </button>
          </div>

          {/* Hierarchy Levels (累积式) */}
          <div className="mb-4">
            <div className="flex items-center gap-2 mb-3">
              <h4 className="text-xs font-semibold text-[#4A5568] uppercase tracking-wider">
                Hierarchy Depth
              </h4>
              <div className="text-[10px] text-[#6B7280] bg-[#F8F9FB] px-2 py-0.5 rounded">
                Cumulative
              </div>
            </div>
            <div className="space-y-2">
              {levels.map(level => {
                const isSelected = maxSelectedLevel >= level.value
                return (
                  <button
                    key={level.value}
                    onClick={() => onLevelToggle(level.value)}
                    className={`w-full text-left px-3 py-2 rounded-lg transition-all ${
                      isSelected 
                        ? 'bg-[#5A95A8] text-white' 
                        : 'bg-[#F8F9FB] text-[#2D3748] hover:bg-[#E5E7EB]'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs font-medium">
                        Level {level.value}: {level.label}
                      </span>
                      {isSelected && <Check className="w-3 h-3" />}
                    </div>
                    <div className={`text-[10px] ${isSelected ? 'text-white/80' : 'text-[#6B7280]'}`}>
                      {level.description}
                    </div>
                  </button>
                )
              })}
            </div>
          </div>

          {/* Relation Types */}
          <div className="mb-4">
            <div className="text-xs font-semibold text-[#4A5568] uppercase tracking-wider mb-2">
              Relation Types
            </div>
            <div className="flex flex-wrap gap-1.5">
              {relationTypes.map(type => {
                const isSelected = selectedRelations.includes(type)
                return (
                  <button
                    key={type}
                    onClick={() => onRelationToggle(type)}
                    className="px-2.5 py-1 rounded-md text-xs font-medium transition-all"
                    style={{
                      backgroundColor: isSelected ? '#5A95A8' : '#F8F9FB',
                      color: isSelected ? '#FFFFFF' : '#6B7280',
                      boxShadow: isSelected ? '0 2px 8px rgba(90,149,168,0.25)' : 'none'
                    }}
                  >
                    {type.replace(/_/g, ' ')}
                  </button>
                )
              })}
            </div>
          </div>

          {/* Node Types */}
          <div>
            <div className="text-xs font-semibold text-[#4A5568] uppercase tracking-wider mb-2">
              Node Types
            </div>
            <div className="flex flex-wrap gap-1.5">
              {nodeTypes.map(type => {
                const isSelected = selectedTypes.includes(type)
                return (
                  <button
                    key={type}
                    onClick={() => onTypeToggle(type)}
                    className="px-2.5 py-1 rounded-md text-xs font-medium transition-all"
                    style={{
                      backgroundColor: isSelected ? typeColors[type] : '#F8F9FB',
                      color: isSelected ? '#FFFFFF' : '#6B7280',
                      boxShadow: isSelected ? '0 2px 8px rgba(0,0,0,0.1)' : 'none'
                    }}
                  >
                    {type}
                  </button>
                )
              })}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
