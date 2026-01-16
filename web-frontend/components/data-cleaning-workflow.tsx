"use client"

import { useState, useEffect } from "react"
import { useRouter, useParams } from "next/navigation"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import { Badge } from "@/components/ui/badge"
import { CheckCircle2, AlertTriangle, Info, Loader2 } from "lucide-react"
import { cn } from "@/lib/utils"

type CleaningStep = "understanding" | "plan" | "cleaning" | "complete"

const mockDatasets = [
  {
    name: "User Events",
    table: "user_events",
    primaryKey: "user_id + event_time",
    eventTypes: ["view", "add_to_cart", "purchase", "remove"],
    dateRange: "2024-01-01 ~ 03-31",
    uniqueUsers: 85234,
    status: "confirmed",
  },
  {
    name: "Orders",
    table: "orders",
    primaryKey: "order_id",
    keyMetrics: ["amount", "discount"],
    relations: "user_id → users",
    detectedIssues: "refund orders (status='refunded')",
    status: "confirmed",
  },
  {
    name: "Product Catalog",
    table: "products",
    primaryKey: "product_id",
    issue: "Inconsistent category naming detected",
    issueDetail: '"Phone" vs "Smartphone" → Merge?',
    status: "warning",
  },
]

const cleaningIssues = [
  {
    category: "Missing Values",
    items: [
      {
        field: "user_events.device_type",
        missing: "1,245 rows (1.01%)",
        suggestion: 'Fill with "unknown"',
        options: ["accept", "delete", "skip"],
        selected: "accept",
      },
      {
        field: "orders.customer_age",
        missing: "3,456 rows (7.56%)",
        suggestion: "Fill from users table",
        options: ["accept", "delete", "skip"],
        selected: "accept",
      },
    ],
  },
  {
    category: "Outliers",
    items: [
      {
        field: "orders.amount",
        issue: "Found 23 orders > $5,000",
        detail: "(exceeds 99.9th percentile $850)",
        suggestion: 'Tag as "large_order"',
        options: ["accept", "delete", "ignore"],
        selected: "accept",
      },
      {
        field: "user_events.event_time",
        issue: "Found 156 future timestamps",
        suggestion: "Delete these records",
        options: ["accept", "fix"],
        selected: "accept",
      },
    ],
  },
  {
    category: "Standardization",
    items: [
      {
        field: "products.category",
        issue: "Inconsistent naming:",
        detail: '"Phone" (234) + "Smartphone" (89)\n"Laptop" (156) + "Notebook" (45)',
        suggestion: "Merge to unified",
        options: ["accept", "keep"],
        selected: "accept",
      },
    ],
  },
  {
    category: "Duplicates",
    items: [
      {
        field: "orders table",
        issue: "Found 45 duplicate order records",
        suggestion: "Keep earliest, remove duplicates",
        options: ["accept", "keep_all"],
        selected: "accept",
      },
    ],
  },
]

export function DataCleaningWorkflow() {
  const router = useRouter()
  const params = useParams()
  const projectId = params.projectId as string

  const [step, setStep] = useState<CleaningStep>("understanding")
  const [progress, setProgress] = useState(0)

  useEffect(() => {
    if (step === "cleaning") {
      const interval = setInterval(() => {
        setProgress((prev) => {
          if (prev >= 100) {
            clearInterval(interval)
            setTimeout(() => setStep("complete"), 500)
            return 100
          }
          return prev + 5
        })
      }, 200)
      return () => clearInterval(interval)
    }
  }, [step])

  const handleConfirmUnderstanding = () => {
    setStep("plan")
  }

  const handleStartCleaning = () => {
    setStep("cleaning")
  }

  const handleContinue = () => {
    router.push(`/projects/${projectId}/graph`)
  }

  return (
    <div className="container max-w-6xl mx-auto p-6 space-y-6">
      {/* Understanding Step */}
      {step === "understanding" && (
        <>
          <div className="space-y-2">
            <h1 className="text-3xl font-bold tracking-tight">AI Data Understanding</h1>
            <p className="text-muted-foreground">
              Based on your business (E-commerce) and role (Product Manager), here's my understanding:
            </p>
          </div>

          <div className="space-y-4">
            <h2 className="text-xl font-semibold">Dataset Overview</h2>
            {mockDatasets.map((dataset, index) => (
              <Card
                key={index}
                className={cn("bg-card border-border", dataset.status === "warning" && "border-warning")}
              >
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <div className="space-y-1">
                      <CardTitle className="text-lg flex items-center gap-2">
                        {dataset.status === "confirmed" ? (
                          <CheckCircle2 className="h-5 w-5 text-success" />
                        ) : (
                          <AlertTriangle className="h-5 w-5 text-warning" />
                        )}
                        {dataset.name}
                      </CardTitle>
                      <CardDescription className="font-mono text-xs">{dataset.table}</CardDescription>
                    </div>
                    <div className="flex gap-2">
                      <Button variant="ghost" size="sm">
                        Edit
                      </Button>
                      <Button variant="ghost" size="sm">
                        Confirm
                      </Button>
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="space-y-2 text-sm">
                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <span className="text-muted-foreground">Primary Key:</span> {dataset.primaryKey}
                    </div>
                    {dataset.eventTypes && (
                      <div>
                        <span className="text-muted-foreground">Event Types:</span> {dataset.eventTypes.join(", ")}
                      </div>
                    )}
                    {dataset.dateRange && (
                      <div>
                        <span className="text-muted-foreground">Date Range:</span> {dataset.dateRange}
                      </div>
                    )}
                    {dataset.uniqueUsers && (
                      <div>
                        <span className="text-muted-foreground">Unique Users:</span>{" "}
                        {dataset.uniqueUsers.toLocaleString()}
                      </div>
                    )}
                    {dataset.keyMetrics && (
                      <div>
                        <span className="text-muted-foreground">Key Metrics:</span> {dataset.keyMetrics.join(", ")}
                      </div>
                    )}
                    {dataset.relations && (
                      <div>
                        <span className="text-muted-foreground">Relations:</span> {dataset.relations}
                      </div>
                    )}
                    {dataset.detectedIssues && (
                      <div className="col-span-2">
                        <span className="text-muted-foreground">Detected:</span> {dataset.detectedIssues}
                      </div>
                    )}
                    {dataset.issue && (
                      <div className="col-span-2 text-warning">
                        <span className="font-medium">Issue:</span> {dataset.issue}
                        <br />
                        <span className="text-xs">{dataset.issueDetail}</span>
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>

          <Card className="bg-secondary/50 border-border">
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <Info className="h-5 w-5 text-primary" />
                Identified Key Metrics
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="space-y-2 text-sm">
                <li className="flex items-start gap-2">
                  <span className="text-primary mt-1">•</span>
                  <span>
                    <strong>GMV</strong> (Gross Merchandise Volume)
                  </span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-primary mt-1">•</span>
                  <span>
                    <strong>Conversion Rate</strong> = Orders / Sessions
                  </span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-primary mt-1">•</span>
                  <span>
                    <strong>AOV</strong> (Average Order Value)
                  </span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-primary mt-1">•</span>
                  <span>
                    <strong>Repeat Purchase Rate</strong>
                  </span>
                </li>
              </ul>
            </CardContent>
          </Card>

          <Button onClick={handleConfirmUnderstanding} className="w-full" size="lg">
            Confirm All & Continue
          </Button>
        </>
      )}

      {/* Cleaning Plan Step */}
      {step === "plan" && (
        <>
          <div className="space-y-2">
            <h1 className="text-3xl font-bold tracking-tight">Data Cleaning Plan</h1>
            <p className="text-muted-foreground">Detected data quality issues:</p>
          </div>

          <div className="space-y-6">
            {cleaningIssues.map((category, catIndex) => (
              <div key={catIndex} className="space-y-3">
                <h2 className="text-lg font-semibold">
                  {catIndex + 1}. {category.category}
                </h2>
                {category.items.map((item, itemIndex) => (
                  <Card key={itemIndex} className="bg-card border-border">
                    <CardContent className="p-4 space-y-3">
                      <div className="space-y-1">
                        <div className="flex items-start justify-between gap-4">
                          <div className="space-y-1 flex-1">
                            <div className="font-medium font-mono text-sm">{item.field}</div>
                            {item.missing && (
                              <div className="text-sm text-muted-foreground">Missing: {item.missing}</div>
                            )}
                            {item.issue && <div className="text-sm text-muted-foreground">{item.issue}</div>}
                            {item.detail && (
                              <div className="text-xs text-muted-foreground whitespace-pre-line">{item.detail}</div>
                            )}
                          </div>
                          <Badge variant="outline" className="bg-primary/10 text-primary border-primary/20">
                            {item.selected === "accept" ? "Accept" : item.selected === "delete" ? "Delete" : "Keep"}
                          </Badge>
                        </div>
                        <div className="text-sm">
                          <span className="text-muted-foreground">Suggestion:</span> {item.suggestion}
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            ))}
          </div>

          <Card className="bg-secondary/50 border-border">
            <CardContent className="p-4">
              <div className="text-sm">
                <span className="text-muted-foreground">Impact:</span> 123,450 rows → 122,890 clean rows
              </div>
            </CardContent>
          </Card>

          <div className="flex gap-3">
            <Button variant="outline" className="flex-1 bg-transparent">
              Customize
            </Button>
            <Button onClick={handleStartCleaning} className="flex-1">
              Start Cleaning
            </Button>
          </div>
        </>
      )}

      {/* Cleaning Progress Step */}
      {step === "cleaning" && (
        <>
          <div className="space-y-2">
            <h1 className="text-3xl font-bold tracking-tight">Cleaning in Progress...</h1>
          </div>

          <Card className="bg-card border-border">
            <CardContent className="p-8 space-y-6">
              <div className="space-y-2">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">Progress</span>
                  <span className="font-medium">{progress}%</span>
                </div>
                <Progress value={progress} className="h-2" />
              </div>

              <div className="space-y-3">
                <div className="text-sm font-medium">Current Task: Standardizing category names</div>
                <div className="space-y-2 text-sm">
                  <div className="flex items-center gap-2 text-success">
                    <CheckCircle2 className="h-4 w-4" />
                    <span>Fill missing values (2.3s)</span>
                  </div>
                  <div className="flex items-center gap-2 text-success">
                    <CheckCircle2 className="h-4 w-4" />
                    <span>Handle outliers (1.8s)</span>
                  </div>
                  <div className="flex items-center gap-2 text-success">
                    <CheckCircle2 className="h-4 w-4" />
                    <span>Remove duplicates (0.9s)</span>
                  </div>
                  <div className="flex items-center gap-2 text-primary">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    <span>Standardize data - In progress</span>
                  </div>
                  <div className="flex items-center gap-2 text-muted-foreground">
                    <div className="h-4 w-4 rounded-full border-2 border-muted" />
                    <span>Generate report - Pending</span>
                  </div>
                </div>
              </div>

              <div className="text-sm text-muted-foreground">
                Processed: {Math.floor((progress / 100) * 122890).toLocaleString()} / 123,450 records
              </div>
            </CardContent>
          </Card>
        </>
      )}

      {/* Complete Step */}
      {step === "complete" && (
        <>
          <div className="space-y-2">
            <div className="flex items-center gap-3">
              <div className="h-12 w-12 rounded-full bg-success/10 flex items-center justify-center">
                <CheckCircle2 className="h-6 w-6 text-success" />
              </div>
              <div>
                <h1 className="text-3xl font-bold tracking-tight">Data Cleaning Complete!</h1>
              </div>
            </div>
          </div>

          <Card className="bg-card border-border">
            <CardHeader>
              <CardTitle>Cleaning Summary</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-3 gap-4 text-center">
                <div className="space-y-1">
                  <div className="text-2xl font-bold">123,450</div>
                  <div className="text-sm text-muted-foreground">Total Records</div>
                </div>
                <div className="space-y-1">
                  <div className="text-2xl font-bold text-success">122,890</div>
                  <div className="text-sm text-muted-foreground">Clean Records (99.5%)</div>
                </div>
                <div className="space-y-1">
                  <div className="text-2xl font-bold">8.7s</div>
                  <div className="text-sm text-muted-foreground">Time Elapsed</div>
                </div>
              </div>

              <div className="border-t border-border pt-4 space-y-2 text-sm">
                <div className="font-medium mb-2">Details:</div>
                <div className="grid grid-cols-2 gap-2">
                  <div>Filled missing values: 4,701</div>
                  <div>Tagged outliers: 23</div>
                  <div>Removed duplicates: 45</div>
                  <div>Fixed errors: 515</div>
                  <div className="col-span-2">Standardized categories: 12</div>
                </div>
              </div>

              <div className="flex items-center gap-2 text-sm text-success bg-success/10 p-3 rounded-lg">
                <CheckCircle2 className="h-4 w-4" />
                <span>Clean data saved automatically</span>
              </div>
            </CardContent>
          </Card>

          <div className="flex gap-3">
            <Button variant="outline" className="flex-1 bg-transparent">
              View Report
            </Button>
            <Button onClick={handleContinue} className="flex-1">
              Continue to Analysis
            </Button>
          </div>
        </>
      )}
    </div>
  )
}
