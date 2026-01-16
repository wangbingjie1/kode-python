"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { TrendingUp, TrendingDown, AlertCircle, CheckCircle2, Clock } from "lucide-react"
import { cn } from "@/lib/utils"

const realtimeMetrics = [
  { label: "GMV", value: "$1.245M", change: 18.5, status: "normal" },
  { label: "Orders", value: "45.6K", change: 22.3, status: "normal" },
  { label: "UV", value: "425.6K", change: 15.2, status: "alert" },
  { label: "Conv.", value: "10.7%", change: 6.1, status: "normal" },
]

const alerts = [
  {
    severity: "medium",
    time: "Today 3:00 PM",
    title: "UV dropped 12.3% vs yesterday same time",
    description: "Possible cause: Campaign ended",
    status: "active",
  },
  {
    severity: "low",
    time: "Today 10:30 AM",
    title: "Payment success rate briefly dropped to 85%, now back to normal",
    description: "",
    status: "recovered",
  },
  {
    severity: "high",
    time: "Yesterday 11:45 PM",
    title: "Abnormal refund rate spike (3.2% vs 1.1%)",
    description: "Resolved - Bug fixed by engineering team",
    status: "resolved",
  },
]

const categoryPerformance = [
  { name: "Electronics", percentage: 42.3, trending: true },
  { name: "Home & Garden", percentage: 28.7, trending: false },
  { name: "Fashion", percentage: 15.2, trending: false },
  { name: "Beauty", percentage: 8.9, trending: false },
  { name: "Others", percentage: 4.9, trending: false },
]

export function MonitorDashboardView() {
  return (
    <div className="space-y-6">
      {/* Real-time Metrics */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold">Real-time Metrics</h2>
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Clock className="h-4 w-4" />
            <span>Updated: 2 min ago</span>
          </div>
        </div>
        <div className="grid grid-cols-4 gap-4">
          {realtimeMetrics.map((metric, index) => (
            <Card key={index} className="bg-card border-border">
              <CardContent className="p-4 space-y-2">
                <div className="flex items-center justify-between">
                  <div className="text-sm font-medium text-muted-foreground">{metric.label}</div>
                  <Badge
                    variant="outline"
                    className={cn(
                      "text-xs",
                      metric.status === "normal" && "bg-success/10 text-success border-success/20",
                      metric.status === "alert" && "bg-warning/10 text-warning border-warning/20",
                    )}
                  >
                    {metric.status === "normal" ? "Normal" : "Alert"}
                  </Badge>
                </div>
                <div className="text-2xl font-bold">{metric.value}</div>
                <div className="flex items-center gap-1">
                  {metric.change > 0 ? (
                    <>
                      <TrendingUp className="h-3 w-3 text-success" />
                      <span className="text-xs font-medium text-success">+{metric.change}%</span>
                    </>
                  ) : (
                    <>
                      <TrendingDown className="h-3 w-3 text-destructive" />
                      <span className="text-xs font-medium text-destructive">{metric.change}%</span>
                    </>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>

      {/* Trend Monitor */}
      <Card className="bg-card border-border">
        <CardHeader>
          <CardTitle className="text-lg">Trend Monitor (7-Day Comparison)</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            <div className="text-sm font-medium">Daily GMV Trend</div>
            <div className="h-48 bg-secondary/30 rounded-lg relative overflow-hidden">
              {/* Simple line chart visualization */}
              <svg className="w-full h-full" viewBox="0 0 700 200" preserveAspectRatio="none">
                {/* Grid lines */}
                <line x1="0" y1="40" x2="700" y2="40" stroke="currentColor" strokeWidth="1" className="text-border" />
                <line x1="0" y1="80" x2="700" y2="80" stroke="currentColor" strokeWidth="1" className="text-border" />
                <line x1="0" y1="120" x2="700" y2="120" stroke="currentColor" strokeWidth="1" className="text-border" />
                <line x1="0" y1="160" x2="700" y2="160" stroke="currentColor" strokeWidth="1" className="text-border" />

                {/* This week line */}
                <polyline
                  points="0,160 100,140 200,120 300,100 400,90 500,70 600,50 700,30"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  className="text-primary"
                />

                {/* Last week line (dashed) */}
                <polyline
                  points="0,170 100,165 200,155 300,150 400,145 500,140 600,135 700,130"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeDasharray="5,5"
                  className="text-muted-foreground"
                  opacity="0.5"
                />

                {/* Current point */}
                <circle cx="700" cy="30" r="4" fill="currentColor" className="text-primary" />
              </svg>
              <div className="absolute bottom-2 left-4 flex items-center gap-4 text-xs">
                <div className="flex items-center gap-2">
                  <div className="w-4 h-0.5 bg-primary" />
                  <span>This Week</span>
                </div>
                <div className="flex items-center gap-2">
                  <div
                    className="w-4 h-0.5 bg-muted-foreground opacity-50"
                    style={{
                      backgroundImage:
                        "repeating-linear-gradient(to right, currentColor 0, currentColor 3px, transparent 3px, transparent 6px)",
                    }}
                  />
                  <span className="text-muted-foreground">Last Week Avg</span>
                </div>
              </div>
            </div>
            <div className="flex justify-between text-xs text-muted-foreground px-2">
              <span>Mon</span>
              <span>Tue</span>
              <span>Wed</span>
              <span>Thu</span>
              <span>Fri</span>
              <span>Sat</span>
              <span>Sun</span>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Anomaly Alert Center */}
      <Card className="bg-card border-border">
        <CardHeader>
          <CardTitle className="text-lg">Anomaly Alert Center</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {alerts.map((alert, index) => (
            <Card
              key={index}
              className={cn(
                "bg-secondary/50 border-l-4",
                alert.severity === "high" && "border-l-destructive",
                alert.severity === "medium" && "border-l-warning",
                alert.severity === "low" && "border-l-success",
              )}
            >
              <CardContent className="p-4 space-y-2">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex items-start gap-3 flex-1">
                    {alert.status === "active" && <AlertCircle className="h-5 w-5 text-warning flex-shrink-0 mt-0.5" />}
                    {alert.status === "recovered" && (
                      <CheckCircle2 className="h-5 w-5 text-success flex-shrink-0 mt-0.5" />
                    )}
                    {alert.status === "resolved" && (
                      <CheckCircle2 className="h-5 w-5 text-muted-foreground flex-shrink-0 mt-0.5" />
                    )}
                    <div className="space-y-1 flex-1">
                      <div className="flex items-center gap-2">
                        <Badge
                          variant="outline"
                          className={cn(
                            "text-xs",
                            alert.severity === "high" && "bg-destructive/10 text-destructive border-destructive/20",
                            alert.severity === "medium" && "bg-warning/10 text-warning border-warning/20",
                            alert.severity === "low" && "bg-success/10 text-success border-success/20",
                          )}
                        >
                          {alert.severity === "high"
                            ? "Critical"
                            : alert.severity === "medium"
                              ? "Medium"
                              : "Recovered"}
                        </Badge>
                        <span className="text-xs text-muted-foreground">{alert.time}</span>
                      </div>
                      <div className="text-sm font-medium">{alert.title}</div>
                      {alert.description && <div className="text-xs text-muted-foreground">{alert.description}</div>}
                    </div>
                  </div>
                </div>
                <div className="flex gap-2">
                  <Button variant="outline" size="sm" className="h-7 text-xs bg-transparent">
                    Details
                  </Button>
                  {alert.status === "active" && (
                    <>
                      <Button variant="outline" size="sm" className="h-7 text-xs bg-transparent">
                        Mark Known
                      </Button>
                      <Button variant="outline" size="sm" className="h-7 text-xs bg-transparent">
                        Get Suggestions
                      </Button>
                    </>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </CardContent>
      </Card>

      {/* Category Performance */}
      <Card className="bg-card border-border">
        <CardHeader>
          <CardTitle className="text-lg">Category Performance (Real-time)</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {categoryPerformance.map((category, index) => (
            <div key={index} className="space-y-1">
              <div className="flex items-center justify-between text-sm">
                <div className="flex items-center gap-2">
                  <span className="font-medium">{category.name}</span>
                  {category.trending && (
                    <Badge
                      variant="outline"
                      className="text-xs bg-destructive/10 text-destructive border-destructive/20"
                    >
                      Hot
                    </Badge>
                  )}
                </div>
                <span className="text-muted-foreground">{category.percentage}%</span>
              </div>
              <div className="h-2 bg-secondary rounded-full overflow-hidden">
                <div
                  className={cn("h-full rounded-full transition-all", category.trending ? "bg-primary" : "bg-muted")}
                  style={{ width: `${category.percentage}%` }}
                />
              </div>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  )
}
