"use client"

import { useState } from "react"
import { Card, CardContent } from "@/components/ui/card"
import { Lightbulb, MessageSquare, Plug } from "lucide-react"
import { AIInsightsPanel } from "@/components/ai-insights-panel"
import { ChatPanel } from "@/components/chat-panel"
import { IntegrationsPanel } from "@/components/integrations-panel"

type PanelMode = "insights" | "chat" | "integrations" | null

interface InteractionPanelProps {
  projectId?: string
  conversationId?: string
}

export function InteractionPanel({ projectId, conversationId }: InteractionPanelProps) {
  const [mode, setMode] = useState<PanelMode>(null)

  if (mode === "insights") {
    return <AIInsightsPanel onClose={() => setMode(null)} />
  }

  if (mode === "chat") {
    return (
      <ChatPanel
        onClose={() => setMode(null)}
        projectId={projectId}
        conversationId={conversationId}
      />
    )
  }

  if (mode === "integrations") {
    return <IntegrationsPanel onClose={() => setMode(null)} />
  }

  return (
    <div className="w-80 space-y-3 flex-shrink-0">
      <Card
        className="bg-card border-border cursor-pointer hover:border-primary/50 transition-colors group"
        onClick={() => setMode("insights")}
      >
        <CardContent className="p-4 space-y-3">
          <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center group-hover:bg-primary/20 transition-colors">
            <Lightbulb className="h-5 w-5 text-primary" />
          </div>
          <div className="space-y-1">
            <div className="font-semibold">AI Insights</div>
            <div className="text-sm text-muted-foreground">Get automated business recommendations</div>
          </div>
        </CardContent>
      </Card>

      <Card
        className="bg-card border-border cursor-pointer hover:border-primary/50 transition-colors group"
        onClick={() => setMode("chat")}
      >
        <CardContent className="p-4 space-y-3">
          <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center group-hover:bg-primary/20 transition-colors">
            <MessageSquare className="h-5 w-5 text-primary" />
          </div>
          <div className="space-y-1">
            <div className="font-semibold">Chat</div>
            <div className="text-sm text-muted-foreground">Ask anything about your data</div>
          </div>
        </CardContent>
      </Card>

      <Card
        className="bg-card border-border cursor-pointer hover:border-primary/50 transition-colors group"
        onClick={() => setMode("integrations")}
      >
        <CardContent className="p-4 space-y-3">
          <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center group-hover:bg-primary/20 transition-colors">
            <Plug className="h-5 w-5 text-primary" />
          </div>
          <div className="space-y-1">
            <div className="font-semibold">Integrations</div>
            <div className="text-sm text-muted-foreground">Connect external apps & automate</div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
