"use client"

import { useState, useRef, useEffect } from "react"
import type { ObjectType, RelationType } from "@/types/ontology"
import { ChevronDown, ChevronUp, Check, Info, CreditCard, LogOut, History, ChevronRight } from "lucide-react"
import { useAuth } from "@/lib/auth-context"
import { useRouter } from "next/navigation"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { useSidebar } from "@/components/layout/app-layout"

// Version type
interface OntologyVersion {
  id: string
  version: number
  updatedAt: string
  description: string
  isCurrent: boolean
}

interface DashboardHeaderProps {
  // Filter states
  selectedNodeTypes?: ObjectType[]
  onTypeToggle?: (type: ObjectType) => void
  selectedLevels?: number[]
  onLevelToggle?: (level: number) => void
  selectedRelationTypes?: RelationType[]
  onRelationToggle?: (relation: RelationType) => void

  // Button callbacks
  onQuickNote?: () => void
  onUpdateData?: () => void

  // Project info
  projectName?: string
  projectDescription?: string
  nodeCount?: number
  topicCount?: number
  dataSize?: string

  // Version info
  versions?: OntologyVersion[]
  currentVersion?: OntologyVersion
  onVersionSwitch?: (version: OntologyVersion) => void
}

export function DashboardHeader({
  selectedNodeTypes = [],
  onTypeToggle = () => {},
  selectedLevels = [],
  onLevelToggle = () => {},
  selectedRelationTypes = [],
  onRelationToggle = () => {},
  onQuickNote = () => {},
  onUpdateData = () => {},
  projectName = "My Project",
  projectDescription = "Project description",
  nodeCount = 0,
  topicCount = 0,
  dataSize = "0 MB",
  versions = [],
  currentVersion,
  onVersionSwitch = () => {},
}: DashboardHeaderProps) {
  const [showFilters, setShowFilters] = useState(false)
  const [showTooltip, setShowTooltip] = useState(false)
  const [showVersionHistory, setShowVersionHistory] = useState(false)
  const tooltipTimer = useRef<NodeJS.Timeout>()

  const { user, loading, logout } = useAuth()
  const router = useRouter()
  const { isSidebarCollapsed } = useSidebar()

  const handleMouseEnter = () => {
    tooltipTimer.current = setTimeout(() => {
      setShowTooltip(true)
    }, 300)
  }

  const handleMouseLeave = () => {
    if (tooltipTimer.current) {
      clearTimeout(tooltipTimer.current)
    }
    // Don't hide if showing version history
    if (!showVersionHistory) {
      setShowTooltip(false)
    }
  }

  const handleTooltipMouseLeave = () => {
    setShowTooltip(false)
    setShowVersionHistory(false)
  }

  useEffect(() => {
    return () => {
      if (tooltipTimer.current) {
        clearTimeout(tooltipTimer.current)
      }
    }
  }, [])

  const maxSelectedLevel = selectedLevels && selectedLevels.length > 0 ? Math.max(...selectedLevels) : 0

  const typeColors: Record<ObjectType, string> = {
    DataSet: "#A8D5BA",
    Analysis: "#F4E4C1",
    Report: "#C9B6E4",
    MLModel: "#7AB8CC",
    UserCohort: "#F5CAC3",
    MarketingCampaign: "#FED7AA",
    StrategyPlaybook: "#BAE6FD",
  }

  const levels = [
    { value: 1, label: "L1", description: "Data" },
    { value: 2, label: "L2", description: "Analysis/Model" },
    { value: 3, label: "L3", description: "Report/Cohort" },
    { value: 4, label: "L4", description: "Strategy/Campaign" },
  ]

  const nodeTypes: ObjectType[] = [
    "DataSet",
    "Analysis",
    "Report",
    "MLModel",
    "UserCohort",
    "MarketingCampaign",
    "StrategyPlaybook",
  ]

  const relationTypes: RelationType[] = [
    "USES_DATA",
    "TRAINS_MODEL",
    "GENERATES_REPORT",
    "INFORMS_STRATEGY",
    "TARGETS_COHORT",
    "AFFECTS_CAMPAIGN",
  ]

  const baseButtonClass = "flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium transition-all"

  if (loading) {
    return (
      <div
        className={`fixed top-0 z-30 bg-white/95 backdrop-blur-md shadow-md transition-all duration-300 ${
          isSidebarCollapsed ? "left-[72px]" : "left-64"
        } right-0`}
      >
        <div className="px-6 py-3 flex items-center justify-end">
          <div className="flex items-center gap-4">
            <Skeleton className="h-9 w-40 rounded-full bg-slate-200" />
            <Skeleton className="h-9 w-9 rounded-full bg-slate-200" />
          </div>
        </div>
      </div>
    )
  }

  return (
    <div
      className={`fixed top-0 z-30 bg-white/95 backdrop-blur-md shadow-md transition-all duration-300 ${
        isSidebarCollapsed ? "left-[72px]" : "left-64"
      } right-0`}
    >
      <div className="px-6 py-3 flex items-center gap-6">
        {/* Left: Project title with tooltip */}
        <div className="relative">
          <div
            className="flex items-center gap-2 cursor-default"
            onMouseEnter={handleMouseEnter}
            onMouseLeave={handleMouseLeave}
          >
            <h1 className="text-base font-semibold text-[#1A202C] whitespace-nowrap">{projectName}</h1>
            <Info className="w-4 h-4 text-slate-400" />
          </div>

          {showTooltip && (
            <div
              className="absolute top-full left-0 mt-2 w-[320px] bg-white rounded-lg shadow-xl border border-slate-200 p-4 z-50 animate-in fade-in duration-200"
              onMouseEnter={() => setShowTooltip(true)}
              onMouseLeave={handleTooltipMouseLeave}
            >
              <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Project Details</div>
              <div className="space-y-2.5">
                <div>
                  <div className="text-xs text-slate-500 mb-0.5">Description</div>
                  <div className="text-sm text-slate-800">{projectDescription}</div>
                </div>

                {/* Version Info */}
                {currentVersion && (
                  <div className="pt-2 border-t border-slate-200">
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="text-xs text-slate-500">Ontology Version</div>
                        <div className="text-sm font-semibold text-slate-800">
                          v{currentVersion.version}
                          <span className="ml-2 text-xs font-normal text-slate-500">
                            Updated {currentVersion.updatedAt}
                          </span>
                        </div>
                      </div>
                      <button
                        onClick={() => setShowVersionHistory(!showVersionHistory)}
                        className="flex items-center gap-1 px-2 py-1 text-xs text-[#5A95A8] hover:bg-slate-50 rounded transition-all"
                      >
                        <History className="w-3 h-3" />
                        <span>History</span>
                        <ChevronRight className={`w-3 h-3 transition-transform ${showVersionHistory ? "rotate-90" : ""}`} />
                      </button>
                    </div>

                    {/* Version History Dropdown */}
                    {showVersionHistory && versions.length > 0 && (
                      <div className="mt-2 p-2 bg-slate-50 rounded-lg border border-slate-100 max-h-[200px] overflow-y-auto">
                        <div className="text-xs font-medium text-slate-500 mb-2">Version History</div>
                        <div className="space-y-1">
                          {versions.map((v) => (
                            <button
                              key={v.id}
                              onClick={() => {
                                onVersionSwitch(v)
                                setShowVersionHistory(false)
                              }}
                              className={`w-full flex items-center justify-between p-2 rounded text-left text-sm transition-all ${
                                v.isCurrent
                                  ? "bg-[#5A95A8]/10 text-[#5A95A8]"
                                  : "hover:bg-white text-slate-700"
                              }`}
                            >
                              <div>
                                <div className="font-medium">
                                  v{v.version}
                                  {v.isCurrent && (
                                    <span className="ml-2 text-xs bg-[#5A95A8] text-white px-1.5 py-0.5 rounded">
                                      Current
                                    </span>
                                  )}
                                </div>
                                <div className="text-xs text-slate-500">{v.description}</div>
                              </div>
                              <div className="text-xs text-slate-400">{v.updatedAt}</div>
                            </button>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}

                <div className="grid grid-cols-2 gap-2 pt-2 border-t border-slate-200">
                  <div>
                    <div className="text-xs text-slate-500">Topics</div>
                    <div className="text-sm font-semibold text-slate-800">{topicCount}</div>
                  </div>
                  <div>
                    <div className="text-xs text-slate-500">Nodes</div>
                    <div className="text-sm font-semibold text-slate-800">{nodeCount}</div>
                  </div>
                  <div>
                    <div className="text-xs text-slate-500">Data Size</div>
                    <div className="text-sm font-semibold text-slate-800">{dataSize}</div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Middle: Data saturation */}
        <div className="flex items-center gap-2">
          <div className="relative w-10 h-10">
            <svg className="w-full h-full" viewBox="0 0 36 36">
              <circle cx="18" cy="18" r="15" strokeWidth="3" stroke="#E9EEF3" fill="none" />
              <circle
                cx="18"
                cy="18"
                r="15"
                strokeWidth="3"
                stroke="#5A95A8"
                fill="none"
                strokeLinecap="round"
                transform="rotate(-90 18 18)"
                strokeDasharray={2 * Math.PI * 15}
                strokeDashoffset={2 * Math.PI * 15 * (1 - 0.78)}
              />
            </svg>
            <div className="absolute inset-0 flex items-center justify-center">
              <span className="text-xs font-bold text-[#5A95A8]">78</span>
            </div>
          </div>
          <div className="text-xs font-medium text-slate-500 leading-tight">
            Data
            <br />
            Saturation
          </div>
        </div>

        {/* Three function buttons */}
        <div className="flex items-center gap-2">
          <button onClick={onQuickNote} className={`${baseButtonClass} bg-[#A8D5BA] text-white hover:bg-[#8FC5A3]`}>
            <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
              <path
                d="M3 2h10v12l-2-2H3V2z"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
              <path d="M6 5h4M6 8h2" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
            </svg>
            <span>Quick Note</span>
          </button>

          <button
            onClick={onUpdateData}
            className={`${baseButtonClass} bg-white border border-slate-200 text-slate-600 hover:bg-slate-50 hover:border-slate-300`}
          >
            <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
              <path d="M8 10V3M8 3L5 6M8 3L11 6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
              <path d="M3 10V13H13V10" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
            </svg>
            <span>Update Data</span>
          </button>

          <button
            onClick={() => setShowFilters(!showFilters)}
            className={`${baseButtonClass} bg-white border border-slate-200 text-slate-600 hover:bg-slate-50 hover:border-slate-300`}
          >
            <span>Filters</span>
            {showFilters ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
          </button>
        </div>

        {/* Flex spacer */}
        <div className="flex-1"></div>

        {/* User info */}
        <div className="flex items-center gap-2">
          {/* Credits display */}
          <div className="hidden sm:flex items-center gap-2.5 text-sm font-medium border border-[#E5E7EB] rounded-full px-4 py-2 bg-white shadow-sm">
            <CreditCard className="w-4 h-4 text-[#10B981]" />
            <span className="text-[#2D3748]">{user?.plan || "Pro"}</span>
            <div className="w-px h-4 bg-[#E5E7EB]"></div>
            <span className="text-[#4A5568]">{user?.credits ?? "1,000"} Credits</span>
          </div>

          {/* User avatar */}
          <div className="flex h-9 w-9 items-center justify-center rounded-full bg-white border border-[#E5E7EB] shadow-sm">
            <Avatar className="h-8 w-8">
              <AvatarImage src={user?.image || "/placeholder.svg"} alt={user?.name} />
              <AvatarFallback className="bg-slate-200 text-slate-500 font-semibold">
                {user?.name?.[0]?.toUpperCase() || user?.email?.[0]?.toUpperCase()}
              </AvatarFallback>
            </Avatar>
          </div>

          {/* Logout button */}
          <Button
            variant="ghost"
            size="icon"
            onClick={() => {
              logout()
              router.push("/")
            }}
            className="h-9 w-9 rounded-full bg-white border border-[#E5E7EB] shadow-sm text-[#6B7280] hover:bg-[#F8F9FA] hover:text-[#2D3748]"
          >
            <LogOut className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {showFilters && (
        <div className="px-6 pb-4 pt-2 border-t border-slate-200 space-y-3 animate-in fade-in duration-200">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <h4 className="text-xs font-semibold text-[#4A5568] uppercase tracking-wider">Hierarchy Depth</h4>
              <div className="text-[10px] text-[#6B7280] bg-[#F8F9FB] px-2 py-0.5 rounded">Cumulative</div>
            </div>
            <div className="flex gap-2">
              {levels.map((level) => {
                const isSelected = maxSelectedLevel >= level.value
                return (
                  <button
                    key={level.value}
                    onClick={() => onLevelToggle(level.value)}
                    className={`flex-1 px-3 py-2 rounded-lg transition-all text-xs ${
                      isSelected ? "bg-[#5A95A8] text-white" : "bg-[#F8F9FB] text-[#2D3748] hover:bg-[#E5E7EB]"
                    }`}
                  >
                    <div className="flex items-center justify-between mb-0.5">
                      <span className="font-medium">{level.label}</span>
                      {isSelected && <Check className="w-3 h-3" />}
                    </div>
                    <div className={`text-[10px] ${isSelected ? "text-white/80" : "text-[#6B7280]"}`}>
                      {level.description}
                    </div>
                  </button>
                )
              })}
            </div>
          </div>

          <div>
            <h4 className="text-xs font-semibold text-[#4A5568] uppercase tracking-wider mb-2">Relation Types</h4>
            <div className="flex flex-wrap gap-1.5">
              {relationTypes.map((type) => {
                const isSelected = selectedRelationTypes?.includes(type) ?? false
                return (
                  <button
                    key={type}
                    onClick={() => onRelationToggle(type)}
                    className="px-2.5 py-1 rounded-md text-xs font-medium transition-all"
                    style={{
                      backgroundColor: isSelected ? "#5A95A8" : "#F8F9FB",
                      color: isSelected ? "#FFFFFF" : "#6B7280",
                      boxShadow: isSelected ? "0 2px 8px rgba(90,149,168,0.25)" : "none",
                    }}
                  >
                    {type.replace(/_/g, " ")}
                  </button>
                )
              })}
            </div>
          </div>

          <div>
            <h4 className="text-xs font-semibold text-[#4A5568] uppercase tracking-wider mb-2">Node Types</h4>
            <div className="flex flex-wrap gap-1.5">
              {nodeTypes.map((type) => {
                const isSelected = selectedNodeTypes?.includes(type) ?? false
                return (
                  <button
                    key={type}
                    onClick={() => onTypeToggle(type)}
                    className="px-2.5 py-1 rounded-md text-xs font-medium transition-all"
                    style={{
                      backgroundColor: isSelected ? typeColors[type] : "#F8F9FB",
                      color: isSelected ? "#FFFFFF" : "#6B7280",
                      boxShadow: isSelected ? "0 2px 8px rgba(0,0,0,0.1)" : "none",
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
