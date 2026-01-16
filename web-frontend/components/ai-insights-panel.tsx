"use client"

import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { X, TrendingUp, Target, ChevronDown, ChevronUp } from "lucide-react"
import { cn } from "@/lib/utils"

const insights = [
  {
    priority: "high",
    title: "Improve First Purchase Experience to Boost Repeat Rate",
    category: "User Retention",
    dataFindings: [
      "30-day repeat rate: 12.3%",
      "Industry avg: 25%",
      "First order AOV: $21.50",
      "Repeat order AOV: $29.80",
    ],
    recommendations: [
      'Launch "First Order Rewards"',
      "Send personalized recommendations within 7 days after first purchase",
      "Create new user community",
    ],
    expectedImpact: {
      metric: "Repeat rate",
      current: "12.3%",
      target: "18-20%",
      revenue: "~$180K quarterly",
    },
  },
  {
    priority: "medium",
    title: "Optimize Electronics Pricing",
    category: "Revenue",
    dataFindings: ["Price sensitivity detected in $50-$100 range", "Competitor pricing 8% lower on average"],
    recommendations: ["Implement dynamic pricing", "Bundle offers for high-margin items"],
    expectedImpact: {
      metric: "Margin",
      current: "22%",
      target: "25-27%",
      revenue: "~$95K quarterly",
    },
  },
  {
    priority: "medium",
    title: "Enhance Weekend Traffic Strategy",
    category: "Marketing",
    dataFindings: ["Weekend traffic 35% lower", "Conversion rate 2.3% higher on weekends"],
    recommendations: ["Weekend-specific campaigns", "Flash sales on Saturday mornings"],
    expectedImpact: {
      metric: "Weekend GMV",
      current: "$280K",
      target: "$380K",
      revenue: "~$100K quarterly",
    },
  },
]

export function AIInsightsPanel({ onClose }: { onClose: () => void }) {
  const [expandedIndex, setExpandedIndex] = useState<number | null>(0)
  const [customRequirements, setCustomRequirements] = useState("")

  return (
    <Card className="w-96 h-[calc(100vh-8rem)] flex flex-col bg-card border-border">
      <CardHeader className="flex-shrink-0 border-b border-border">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg flex items-center gap-2">
            <Target className="h-5 w-5 text-primary" />
            AI Insights
          </CardTitle>
          <Button variant="ghost" size="icon" className="h-8 w-8" onClick={onClose}>
            <X className="h-4 w-4" />
          </Button>
        </div>
      </CardHeader>

      <CardContent className="flex-1 overflow-y-auto p-4 space-y-4">
        <div className="space-y-2">
          <label className="text-sm font-medium">Custom Requirements (Optional)</label>
          <textarea
            placeholder="Focus on new user conversion and repeat purchase improvement"
            value={customRequirements}
            onChange={(e) => setCustomRequirements(e.target.value)}
            className="w-full min-h-[80px] px-3 py-2 rounded-md bg-secondary border border-border text-sm resize-none focus:outline-none focus:ring-2 focus:ring-ring"
          />
          <Button size="sm" className="w-full">
            Generate Insights
          </Button>
        </div>

        <div className="border-t border-border pt-4 space-y-3">
          <div className="text-sm font-semibold">Business Insights Based on Q1 (3 items)</div>

          {insights.map((insight, index) => (
            <Card
              key={index}
              className={cn(
                "bg-secondary/50 border-border cursor-pointer transition-colors",
                expandedIndex === index && "border-primary/50",
              )}
            >
              <CardContent className="p-3 space-y-3">
                <div
                  className="flex items-start justify-between gap-2"
                  onClick={() => setExpandedIndex(expandedIndex === index ? null : index)}
                >
                  <div className="flex-1 space-y-2">
                    <div className="flex items-center gap-2">
                      <Badge
                        variant="outline"
                        className={cn(
                          "text-xs",
                          insight.priority === "high"
                            ? "bg-destructive/10 text-destructive border-destructive/20"
                            : "bg-warning/10 text-warning border-warning/20",
                        )}
                      >
                        Priority: {insight.priority === "high" ? "High" : "Medium"}
                      </Badge>
                    </div>
                    <div className="text-sm font-medium leading-tight">{insight.title}</div>
                  </div>
                  <Button variant="ghost" size="icon" className="h-6 w-6 flex-shrink-0">
                    {expandedIndex === index ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                  </Button>
                </div>

                {expandedIndex === index && (
                  <div className="space-y-3 pt-2 border-t border-border">
                    <div className="space-y-1">
                      <div className="text-xs font-semibold text-primary">Data Discovery:</div>
                      <ul className="space-y-1">
                        {insight.dataFindings.map((finding, i) => (
                          <li key={i} className="text-xs text-muted-foreground flex items-start gap-1">
                            <span className="text-primary mt-0.5">•</span>
                            <span>{finding}</span>
                          </li>
                        ))}
                      </ul>
                    </div>

                    <div className="space-y-1">
                      <div className="text-xs font-semibold text-primary">Recommended Actions:</div>
                      <ul className="space-y-1">
                        {insight.recommendations.map((rec, i) => (
                          <li key={i} className="text-xs text-muted-foreground flex items-start gap-1">
                            <span className="text-primary mt-0.5">•</span>
                            <span>{rec}</span>
                          </li>
                        ))}
                      </ul>
                    </div>

                    <div className="space-y-1">
                      <div className="text-xs font-semibold text-primary flex items-center gap-1">
                        <TrendingUp className="h-3 w-3" />
                        Expected Impact:
                      </div>
                      <div className="text-xs space-y-0.5">
                        <div>
                          <span className="text-muted-foreground">{insight.expectedImpact.metric}:</span>{" "}
                          {insight.expectedImpact.current} → {insight.expectedImpact.target}
                        </div>
                        <div>
                          <span className="text-muted-foreground">Incremental GMV:</span>{" "}
                          {insight.expectedImpact.revenue}
                        </div>
                      </div>
                    </div>

                    <div className="flex gap-2 pt-2">
                      <Button variant="outline" size="sm" className="flex-1 h-7 text-xs bg-transparent">
                        Detailed Plan
                      </Button>
                      <Button variant="outline" size="sm" className="flex-1 h-7 text-xs bg-transparent">
                        Export
                      </Button>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          ))}
        </div>

        <div className="flex gap-2 pt-2">
          <Button variant="outline" size="sm" className="flex-1 bg-transparent">
            Regenerate
          </Button>
          <Button variant="outline" size="sm" className="flex-1 bg-transparent">
            Export All
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}
