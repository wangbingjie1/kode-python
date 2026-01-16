"use client"

import { useState, useEffect } from "react"
import { useRouter, usePathname } from "next/navigation"
import { Button } from "@/components/ui/button"
import { KnowledgeGraphView } from "@/components/knowledge-graph-view"
import { MonitorDashboardView } from "@/components/monitor-dashboard-view"
import { InteractionPanel } from "@/components/interaction-panel"
import { useProjectStore } from "@/lib/project-store"
import { BarChart3, Activity, MessageSquare, Plug } from "lucide-react"

type ViewMode = "graph" | "monitor" | "chat" | "integrations"

interface DashboardLayoutProps {
  defaultView?: ViewMode
}

export function DashboardLayout({ defaultView = "graph" }: DashboardLayoutProps) {
  const router = useRouter()
  const pathname = usePathname()
  const currentProject = useProjectStore((state) => state.currentProject)
  const [viewMode, setViewMode] = useState<ViewMode>(defaultView)

  // Sync view mode with URL
  useEffect(() => {
    if (pathname.includes("/graph")) setViewMode("graph")
    else if (pathname.includes("/monitor")) setViewMode("monitor")
    else if (pathname.includes("/chat")) setViewMode("chat")
    else if (pathname.includes("/integrations")) setViewMode("integrations")
  }, [pathname])

  const handleViewChange = (view: ViewMode) => {
    setViewMode(view)
    if (currentProject) {
      router.push(`/projects/${currentProject.id}/${view}`)
    }
  }

  if (!currentProject) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <p className="text-muted-foreground">Loading project...</p>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-background">
      {/* View Tabs */}
      <div className="border-b border-border bg-card">
        <div className="container max-w-7xl mx-auto px-6">
          <div className="flex items-center gap-1">
            <Button
              variant={viewMode === "graph" ? "default" : "ghost"}
              size="sm"
              onClick={() => handleViewChange("graph")}
              className="gap-2 rounded-b-none"
            >
              <BarChart3 className="h-4 w-4" />
              Graph
            </Button>
            <Button
              variant={viewMode === "monitor" ? "default" : "ghost"}
              size="sm"
              onClick={() => handleViewChange("monitor")}
              className="gap-2 rounded-b-none"
            >
              <Activity className="h-4 w-4" />
              Monitor
            </Button>
            <Button
              variant={viewMode === "chat" ? "default" : "ghost"}
              size="sm"
              onClick={() => handleViewChange("chat")}
              className="gap-2 rounded-b-none"
            >
              <MessageSquare className="h-4 w-4" />
              Chat
            </Button>
            <Button
              variant={viewMode === "integrations" ? "default" : "ghost"}
              size="sm"
              onClick={() => handleViewChange("integrations")}
              className="gap-2 rounded-b-none"
            >
              <Plug className="h-4 w-4" />
              Integrations
            </Button>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="container max-w-7xl mx-auto px-6 py-6">
        <div className="flex gap-6">
          <div className="flex-1">
            {viewMode === "graph" && <KnowledgeGraphView />}
            {viewMode === "monitor" && <MonitorDashboardView />}
            {(viewMode === "chat" || viewMode === "integrations") && (
              <div className="text-center py-12 text-muted-foreground">
                {viewMode === "chat" ? "Chat view" : "Integrations view"} - Coming soon
              </div>
            )}
          </div>
          <InteractionPanel projectId={currentProject.id} />
        </div>
      </div>
    </div>
  )
}
