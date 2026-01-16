"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { X, Mail, Code, BarChart3, Plus, Settings } from "lucide-react"

const connectedIntegrations = [
  {
    name: "Gmail",
    icon: Mail,
    status: "active",
    description: "Auto-send weekly reports and real-time anomaly alerts",
    recipients: ["mike.zhang@company.com", "team-product@company.com"],
  },
  {
    name: "Cursor IDE",
    icon: Code,
    status: "active",
    description: "Export SQL queries with one click",
    recentExports: ["New user conversion logic (2h ago)", "Repeat purchase analysis (yesterday)"],
  },
  {
    name: "Tableau",
    icon: BarChart3,
    status: "active",
    description: "Auto-sync data to Tableau workbook",
    frequency: "Daily at 00:00",
    lastSync: "2024-04-01 00:15",
  },
]

const availableIntegrations = [
  { name: "Slack", icon: "💬" },
  { name: "DingTalk", icon: "📱" },
  { name: "Lark", icon: "🚀" },
  { name: "WeCom", icon: "💼" },
  { name: "Jira", icon: "📋" },
  { name: "Notion", icon: "📝" },
]

export function IntegrationsPanel({ onClose }: { onClose: () => void }) {
  return (
    <Card className="w-96 h-[calc(100vh-8rem)] flex flex-col bg-card border-border">
      <CardHeader className="flex-shrink-0 border-b border-border">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg">Integration Hub</CardTitle>
          <Button variant="ghost" size="icon" className="h-8 w-8" onClick={onClose}>
            <X className="h-4 w-4" />
          </Button>
        </div>
      </CardHeader>

      <CardContent className="flex-1 overflow-y-auto p-4 space-y-4">
        <div className="flex items-center justify-between">
          <Badge variant="outline" className="bg-success/10 text-success border-success/20">
            Connected: {connectedIntegrations.length}
          </Badge>
          <Button size="sm" className="h-7 text-xs">
            <Plus className="h-3 w-3 mr-1" />
            Add Integration
          </Button>
        </div>

        <div className="space-y-3">
          <div className="text-sm font-semibold">Connected Apps</div>
          {connectedIntegrations.map((integration, index) => {
            const Icon = integration.icon
            return (
              <Card key={index} className="bg-secondary/50 border-border">
                <CardContent className="p-3 space-y-3">
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-start gap-3 flex-1">
                      <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center flex-shrink-0">
                        <Icon className="h-5 w-5 text-primary" />
                      </div>
                      <div className="space-y-1 flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <div className="font-medium text-sm">{integration.name}</div>
                          <Badge variant="outline" className="text-xs bg-success/10 text-success border-success/20">
                            Active
                          </Badge>
                        </div>
                        <div className="text-xs text-muted-foreground">{integration.description}</div>
                      </div>
                    </div>
                  </div>

                  {integration.recipients && (
                    <div className="text-xs space-y-1">
                      <div className="text-muted-foreground">Recipients:</div>
                      {integration.recipients.map((recipient, i) => (
                        <div key={i} className="font-mono">
                          • {recipient}
                        </div>
                      ))}
                    </div>
                  )}

                  {integration.recentExports && (
                    <div className="text-xs space-y-1">
                      <div className="text-muted-foreground">Recent Exports:</div>
                      {integration.recentExports.map((exp, i) => (
                        <div key={i}>• {exp}</div>
                      ))}
                    </div>
                  )}

                  {integration.frequency && (
                    <div className="text-xs space-y-1">
                      <div>
                        <span className="text-muted-foreground">Frequency:</span> {integration.frequency}
                      </div>
                      <div>
                        <span className="text-muted-foreground">Last Sync:</span> {integration.lastSync}
                      </div>
                    </div>
                  )}

                  <div className="flex gap-2">
                    <Button variant="outline" size="sm" className="flex-1 h-7 text-xs bg-transparent">
                      <Settings className="h-3 w-3 mr-1" />
                      Configure
                    </Button>
                    <Button variant="outline" size="sm" className="h-7 text-xs bg-transparent">
                      Disconnect
                    </Button>
                  </div>
                </CardContent>
              </Card>
            )
          })}
        </div>

        <div className="space-y-3 pt-4 border-t border-border">
          <div className="text-sm font-semibold">Available Integrations</div>
          <div className="grid grid-cols-3 gap-2">
            {availableIntegrations.map((integration, index) => (
              <button
                key={index}
                className="flex flex-col items-center gap-2 p-3 rounded-lg border border-border bg-secondary/30 hover:border-primary/50 hover:bg-secondary/50 transition-colors"
              >
                <span className="text-2xl">{integration.icon}</span>
                <span className="text-xs font-medium">{integration.name}</span>
              </button>
            ))}
          </div>
          <Button variant="outline" size="sm" className="w-full bg-transparent">
            Browse All Integrations
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}
