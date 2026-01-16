"use client"

import type React from "react"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent } from "@/components/ui/card"
import { X, Sparkles, User, Bot, ArrowRight } from "lucide-react"
import { cn } from "@/lib/utils"
import { useProjectStore } from "@/lib/project-store"

type ConversationStep = "greeting" | "business_type" | "role" | "name_suggestion" | "complete"

const businessTypes = [
  { id: "ecommerce", label: "E-commerce", icon: "🛒" },
  { id: "fintech", label: "FinTech", icon: "💰" },
  { id: "saas", label: "SaaS", icon: "📱" },
  { id: "gaming", label: "Gaming", icon: "🎮" },
  { id: "healthcare", label: "Healthcare", icon: "❤️" },
  { id: "edtech", label: "EdTech", icon: "📚" },
]

const roles = [
  { id: "product_manager", label: "Product Manager" },
  { id: "operations", label: "Operations" },
  { id: "data_analyst", label: "Data Analyst" },
]

export function ConversationalProjectWizard() {
  const router = useRouter()
  const setAllProjects = useProjectStore((state) => state.setAllProjects)
  const allProjects = useProjectStore((state) => state.allProjects)
  const enterProject = useProjectStore((state) => state.enterProject)

  const [step, setStep] = useState<ConversationStep>("greeting")
  const [userInput, setUserInput] = useState("")
  const [businessType, setBusinessType] = useState("")
  const [selectedRole, setSelectedRole] = useState("")
  const [suggestedName, setSuggestedName] = useState("")
  const [messages, setMessages] = useState<Array<{ role: "user" | "ai"; content: React.ReactNode }>>([])

  const addMessage = (role: "user" | "ai", content: React.ReactNode) => {
    setMessages((prev) => [...prev, { role, content }])
  }

  const handleGreeting = () => {
    addMessage("user", userInput)
    addMessage(
      "ai",
      <div className="space-y-3">
        <p>Got it! {userInput}</p>
        <p>I bet you care about:</p>
        <ul className="space-y-1 ml-4">
          <li>• Conversion rate and GMV</li>
          <li>• User retention</li>
          <li>• Purchase funnel</li>
        </ul>
        <p className="mt-3">What's your role?</p>
        <div className="flex flex-wrap gap-2 mt-2">
          {roles.map((role) => (
            <Button
              key={role.id}
              variant="outline"
              size="sm"
              onClick={() => handleRoleSelection(role.id, role.label)}
              className="frosted-card hover:bg-primary/20 border-primary/30"
            >
              {role.label}
            </Button>
          ))}
        </div>
      </div>,
    )
    setStep("role")
    setUserInput("")
  }

  const handleRoleSelection = (roleId: string, roleLabel: string) => {
    setSelectedRole(roleId)
    addMessage("user", roleLabel)

    const name = `E-commerce Analytics Q1 2024`
    setSuggestedName(name)

    addMessage(
      "ai",
      <div className="space-y-3">
        <p>Perfect! I suggest naming it:</p>
        <div className="flex items-center gap-2 mt-2">
          <Input
            value={suggestedName || name}
            onChange={(e) => setSuggestedName(e.target.value)}
            className="frosted-card border-primary/30 text-foreground"
          />
        </div>
        <Button onClick={handleCreateProject} className="w-full mt-3 bg-gradient-to-r from-primary to-accent">
          <Sparkles className="mr-2 h-4 w-4" />
          Create Project
        </Button>
      </div>,
    )
    setStep("name_suggestion")
  }

  const handleCreateProject = () => {
    const newProject = {
      id: `proj_${Date.now()}`,
      name: suggestedName,
      icon: businessTypes.find((t) => t.id === businessType)?.icon || "📊",
      businessType: businessType || "E-commerce",
      role: selectedRole,
      status: "active" as const,
      lastUpdate: new Date(),
      isPinned: false,
      description: userInput,
    }

    setAllProjects([...allProjects, newProject])
    enterProject(newProject)
    router.push(`/projects/${newProject.id}/upload`)
  }

  const handleClose = () => {
    router.push("/projects")
  }

  return (
    <div className="flex items-center justify-center min-h-screen p-4">
      <Card className="w-full max-w-2xl frosted-card border-primary/20">
        <CardContent className="p-8">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-3">
              <div className="h-10 w-10 rounded-full bg-gradient-to-br from-primary to-accent flex items-center justify-center">
                <Sparkles className="h-5 w-5 text-white" />
              </div>
              <h1 className="text-2xl font-bold">Let's Get Started</h1>
            </div>
            <Button variant="ghost" size="icon" onClick={handleClose} className="hover:bg-white/10">
              <X className="h-4 w-4" />
            </Button>
          </div>

          {step === "greeting" && (
            <div className="space-y-6">
              <div className="space-y-4">
                <div className="flex items-start gap-3">
                  <div className="h-8 w-8 rounded-full bg-gradient-to-br from-primary to-accent flex items-center justify-center flex-shrink-0">
                    <Bot className="h-4 w-4 text-white" />
                  </div>
                  <div className="frosted-card p-4 rounded-2xl rounded-tl-none flex-1">
                    <p className="text-sm">I'm your AI analysis assistant</p>
                    <p className="text-sm mt-2">Just chat with me to set up</p>
                    <p className="text-sm mt-4 font-medium">What kind of business data would you like to analyze?</p>
                  </div>
                </div>
              </div>

              <div className="flex items-end gap-3">
                <Input
                  placeholder="I run an e-commerce platform, want to analyze user behavior"
                  value={userInput}
                  onChange={(e) => setUserInput(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && userInput && handleGreeting()}
                  className="frosted-card border-primary/30 text-foreground"
                />
                <Button
                  onClick={handleGreeting}
                  disabled={!userInput}
                  className="bg-gradient-to-r from-primary to-accent"
                >
                  <ArrowRight className="h-4 w-4" />
                </Button>
              </div>
            </div>
          )}

          {step !== "greeting" && (
            <div className="space-y-4 max-h-[500px] overflow-y-auto">
              {messages.map((message, index) => (
                <div key={index} className="flex items-start gap-3">
                  <div
                    className={cn(
                      "h-8 w-8 rounded-full flex items-center justify-center flex-shrink-0",
                      message.role === "ai" ? "bg-gradient-to-br from-primary to-accent" : "bg-white/10",
                    )}
                  >
                    {message.role === "ai" ? (
                      <Bot className="h-4 w-4 text-white" />
                    ) : (
                      <User className="h-4 w-4 text-white" />
                    )}
                  </div>
                  <div
                    className={cn(
                      "p-4 rounded-2xl flex-1",
                      message.role === "ai" ? "frosted-card rounded-tl-none" : "bg-white/10 rounded-tr-none",
                    )}
                  >
                    <div className="text-sm">{message.content}</div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
