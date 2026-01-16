"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { X, ShoppingCart, DollarSign, Smartphone, Gamepad2, Heart, BookOpen, ArrowRight } from "lucide-react"
import { cn } from "@/lib/utils"
import { useProjectStore } from "@/lib/project-store"

type BusinessType = "ecommerce" | "fintech" | "saas" | "gaming" | "healthcare" | "edtech" | "custom"
type Role = "product_manager" | "operations" | "data_analyst" | "marketing" | "engineering" | "executive" | "custom"

const businessTypes = [
  { id: "ecommerce" as const, label: "E-commerce", icon: ShoppingCart },
  { id: "fintech" as const, label: "FinTech", icon: DollarSign },
  { id: "saas" as const, label: "SaaS", icon: Smartphone },
  { id: "gaming" as const, label: "Gaming", icon: Gamepad2 },
  { id: "healthcare" as const, label: "Healthcare", icon: Heart },
  { id: "edtech" as const, label: "EdTech", icon: BookOpen },
]

const roles = [
  { id: "product_manager" as const, label: "Product Manager" },
  { id: "operations" as const, label: "Operations" },
  { id: "data_analyst" as const, label: "Data Analyst" },
  { id: "marketing" as const, label: "Marketing" },
  { id: "engineering" as const, label: "Engineering" },
  { id: "executive" as const, label: "Executive" },
]

const roleInsights = {
  product_manager: ["User conversion and retention", "Feature performance metrics", "Product funnel analysis"],
  operations: ["Operational efficiency metrics", "Process optimization insights", "Resource utilization analysis"],
  data_analyst: ["Deep statistical analysis", "Custom metric exploration", "Advanced data modeling"],
  marketing: ["Campaign performance tracking", "Customer acquisition metrics", "Channel attribution analysis"],
  engineering: ["System performance metrics", "Technical KPI monitoring", "Infrastructure optimization"],
  executive: ["High-level business metrics", "Strategic decision support", "Company-wide performance"],
}

export function ProjectCreationWizard() {
  const router = useRouter()
  const setAllProjects = useProjectStore((state) => state.setAllProjects)
  const allProjects = useProjectStore((state) => state.allProjects)
  const enterProject = useProjectStore((state) => state.enterProject)

  const [step, setStep] = useState(1)
  const [projectName, setProjectName] = useState("")
  const [businessType, setBusinessType] = useState<BusinessType | null>(null)
  const [customDescription, setCustomDescription] = useState("")
  const [selectedRole, setSelectedRole] = useState<Role | null>(null)
  const [showCustomRole, setShowCustomRole] = useState(false)
  const [customRole, setCustomRole] = useState("")

  const handleNext = () => {
    if (step === 1 && projectName) {
      setStep(2)
    } else if (step === 2 && (businessType || customDescription)) {
      setStep(3)
    }
  }

  const handleCreateProject = () => {
    const newProject = {
      id: `proj_${Date.now()}`,
      name: projectName,
      icon:
        businessType === "ecommerce"
          ? "🛒"
          : businessType === "fintech"
            ? "💰"
            : businessType === "saas"
              ? "📱"
              : businessType === "gaming"
                ? "🎮"
                : businessType === "healthcare"
                  ? "❤️"
                  : businessType === "edtech"
                    ? "📚"
                    : "📊",
      businessType: businessType || "Custom",
      role: selectedRole ? roles.find((r) => r.id === selectedRole)?.label || customRole : customRole,
      status: "active" as const,
      lastUpdate: new Date(),
      isPinned: false,
      description: customDescription || projectName,
    }

    // Add to projects list
    setAllProjects([...allProjects, newProject])

    // Enter the project
    enterProject(newProject)

    // Navigate to data ingestion
    router.push(`/projects/${newProject.id}/upload`)
  }

  const handleClose = () => {
    router.push("/projects")
  }

  return (
    <div className="flex items-center justify-center min-h-screen p-4">
      <Card className="w-full max-w-2xl bg-card border-border">
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-4">
          <div className="space-y-1">
            <CardTitle className="text-xl">Create New Project</CardTitle>
            <CardDescription>
              Step {step}/3 - {step === 1 ? "Project Information" : step === 2 ? "Business Type" : "Role Selection"}
            </CardDescription>
          </div>
          <Button variant="ghost" size="icon" className="h-8 w-8" onClick={handleClose}>
            <X className="h-4 w-4" />
          </Button>
        </CardHeader>

        <CardContent className="space-y-6">
          {/* Progress indicator */}
          <div className="flex gap-2">
            {[1, 2, 3].map((s) => (
              <div
                key={s}
                className={cn("h-1 flex-1 rounded-full transition-colors", s <= step ? "bg-primary" : "bg-muted")}
              />
            ))}
          </div>

          {/* Step 1: Project Name */}
          {step === 1 && (
            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="project-name">Project Name *</Label>
                <Input
                  id="project-name"
                  placeholder="E-commerce Analytics Q1 2024"
                  value={projectName}
                  onChange={(e) => setProjectName(e.target.value)}
                  className="bg-secondary border-border"
                />
              </div>

              <Button onClick={handleNext} disabled={!projectName} className="w-full">
                Next: Business Type
                <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </div>
          )}

          {/* Step 2: Business Type */}
          {step === 2 && (
            <div className="space-y-6">
              <div className="space-y-3">
                <Label>Common Business Types</Label>
                <div className="grid grid-cols-3 gap-3">
                  {businessTypes.map((type) => {
                    const Icon = type.icon
                    return (
                      <button
                        key={type.id}
                        onClick={() => setBusinessType(type.id)}
                        className={cn(
                          "flex flex-col items-center justify-center p-4 rounded-lg border-2 transition-all hover:border-primary/50",
                          businessType === type.id ? "border-primary bg-primary/10" : "border-border bg-secondary",
                        )}
                      >
                        <Icon className="h-8 w-8 mb-2" />
                        <span className="text-sm font-medium">{type.label}</span>
                      </button>
                    )
                  })}
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="custom-description">Custom Description</Label>
                <textarea
                  id="custom-description"
                  placeholder="We run a vertical e-commerce platform focused on consumer electronics and home goods, serving 25-40 age group in major cities"
                  value={customDescription}
                  onChange={(e) => setCustomDescription(e.target.value)}
                  className="w-full min-h-[120px] px-3 py-2 rounded-md bg-secondary border border-border text-sm resize-none focus:outline-none focus:ring-2 focus:ring-ring"
                />
              </div>

              <div className="flex gap-3">
                <Button variant="outline" onClick={() => setStep(1)} className="flex-1">
                  Back
                </Button>
                <Button onClick={handleNext} disabled={!businessType && !customDescription} className="flex-1">
                  Next: Role Selection
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
              </div>
            </div>
          )}

          {/* Step 3: Role Selection */}
          {step === 3 && (
            <div className="space-y-6">
              <div className="space-y-3">
                <Label>Recommended Roles</Label>
                <div className="grid grid-cols-2 gap-3">
                  {roles.map((role) => (
                    <button
                      key={role.id}
                      onClick={() => {
                        setSelectedRole(role.id)
                        setShowCustomRole(false)
                      }}
                      className={cn(
                        "flex items-center gap-2 p-3 rounded-lg border-2 transition-all hover:border-primary/50 text-left",
                        selectedRole === role.id ? "border-primary bg-primary/10" : "border-border bg-secondary",
                      )}
                    >
                      <div
                        className={cn(
                          "h-4 w-4 rounded-full border-2 flex items-center justify-center",
                          selectedRole === role.id ? "border-primary" : "border-muted-foreground",
                        )}
                      >
                        {selectedRole === role.id && <div className="h-2 w-2 rounded-full bg-primary" />}
                      </div>
                      <span className="text-sm font-medium">{role.label}</span>
                    </button>
                  ))}
                </div>

                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setShowCustomRole(!showCustomRole)}
                  className="text-primary"
                >
                  + Add Custom Role
                </Button>

                {showCustomRole && (
                  <Input
                    placeholder="Enter custom role"
                    value={customRole}
                    onChange={(e) => setCustomRole(e.target.value)}
                    className="bg-secondary border-border"
                  />
                )}
              </div>

              {selectedRole && !showCustomRole && (
                <div className="p-4 rounded-lg bg-secondary/50 border border-border space-y-2">
                  <div className="flex items-center gap-2 text-sm font-medium">
                    <span className="text-primary">Selected:</span>
                    <span>{roles.find((r) => r.id === selectedRole)?.label}</span>
                  </div>
                  <div className="space-y-1">
                    <p className="text-sm text-muted-foreground">AI will focus on:</p>
                    <ul className="space-y-1">
                      {roleInsights[selectedRole].map((insight, i) => (
                        <li key={i} className="text-sm text-foreground flex items-start gap-2">
                          <span className="text-primary mt-1">•</span>
                          <span>{insight}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              )}

              <div className="flex gap-3">
                <Button variant="outline" onClick={() => setStep(2)} className="flex-1">
                  Back
                </Button>
                <Button onClick={handleCreateProject} disabled={!selectedRole && !customRole} className="flex-1">
                  Create Project
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
