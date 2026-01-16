"use client"

import { useState, useEffect, useRef } from "react"
import type { Card, Message } from "@/types/knowledge-universe"
import type { ObjectType, RelationType } from "@/types/ontology"
import { cardsData } from "@/lib/knowledge-universe-data"
import { ontologyNodes, ontologyRelations } from "@/lib/ontology-data"
import { OntologyCanvas } from "@/components/knowledge-universe/OntologyCanvas"
import { DashboardHeader } from "@/components/dashboard-header"
import { useRouter } from "next/navigation"
import { NewProjectModal } from "@/components/modals/new-project-modal"
import { QuickNoteModal } from "@/components/modals/quick-note-modal"
import { CanvasLoadingState } from "@/components/knowledge-universe/CanvasLoadingState"
import { useProjectStore } from "@/lib/project-store"
import { SimplifiedETLView } from "@/components/simplified-etl-view"
import { ETLChatQuestionnaire } from "@/components/etl-chat-questionnaire"
import { CollapsibleOntologyBuilder } from "@/components/collapsible-ontology-builder"
import { OntologyBuildConfirmationModal } from "@/components/ontology-build-confirmation-modal"

// ========== Question types and data ==========
interface QuestionOption {
  id: string
  label: string
}

interface PendingQuestion {
  id: string
  type: "single" | "multiple" | "text"
  question: string
  description?: string
  options?: QuestionOption[]
  placeholder?: string
}

const pendingQuestions: PendingQuestion[] = [
  {
    id: "q1",
    type: "single",
    question: "What is the primary revenue metric?",
    description: "Multiple revenue fields detected. Please confirm the main metric for analysis.",
    options: [
      { id: "a", label: "Gross Revenue (invoice_amount)" },
      { id: "b", label: "Net Revenue (net_revenue)" },
      { id: "c", label: "Recognized Revenue (recognized_revenue)" },
    ],
  },
  {
    id: "q2",
    type: "multiple",
    question: "Which channels should be classified as 'Online'?",
    description: "Select all sources that should be grouped under online channels.",
    options: [
      { id: "a", label: "Website Direct (website)" },
      { id: "b", label: "Mobile App (app)" },
      { id: "c", label: "Partner API (api)" },
      { id: "d", label: "Social Commerce (social)" },
    ],
  },
  {
    id: "q3",
    type: "text",
    question: "What is the company short name for reports?",
    description: "This name will appear in all generated report titles and charts.",
    placeholder: "e.g., Acme Corp",
  },
  {
    id: "q4",
    type: "single",
    question: "How should 'Active User' be defined?",
    description: "This affects DAU/MAU and other engagement metrics.",
    options: [
      { id: "a", label: "Logged in within last 7 days" },
      { id: "b", label: "Logged in within last 30 days" },
      { id: "c", label: "Made a transaction within last 30 days" },
    ],
  },
  {
    id: "q5",
    type: "multiple",
    question: "Which order statuses should count towards GMV?",
    options: [
      { id: "a", label: "Paid" },
      { id: "b", label: "Shipped" },
      { id: "c", label: "Completed" },
      { id: "d", label: "Refunding" },
    ],
  },
  {
    id: "q6",
    type: "text",
    question: "What is the fiscal year end date?",
    description: "Used to determine analysis time boundaries.",
    placeholder: "e.g., 2024-12-31",
  },
  {
    id: "q7",
    type: "single",
    question: "How should costs be allocated?",
    options: [
      { id: "a", label: "Proportional to revenue" },
      { id: "b", label: "Proportional to order count" },
      { id: "c", label: "Direct SKU attribution" },
    ],
  },
]

const autoResolvableIds = ["q1", "q4", "q6"]

// ========== Version types and data ==========
interface OntologyVersion {
  id: string
  version: number
  updatedAt: string
  description: string
  isCurrent: boolean
}

const initialVersions: OntologyVersion[] = [
  { id: "v3", version: 3, updatedAt: "Jan 15, 2025", description: "Added user cohort analysis", isCurrent: true },
  { id: "v2", version: 2, updatedAt: "Dec 20, 2024", description: "Integrated marketing campaign data", isCurrent: false },
  { id: "v1", version: 1, updatedAt: "Nov 10, 2024", description: "Initial ontology structure", isCurrent: false },
]

function ViewModal({
  onClose,
  onSelectTemplate,
}: {
  onClose: () => void
  onSelectTemplate: (template: { id: string; title: string; icon: string }) => void
}) {
  const templates = [
    { id: "freeform", icon: "✨", title: "Freeform", desc: "Create a custom view from scratch" },
    { id: "analytics", icon: "📊", title: "Analytics Dashboard", desc: "Standard metrics and KPI tracking" },
    { id: "monitor", icon: "📈", title: "Monitoring Dashboard", desc: "Real-time data monitoring" },
    { id: "report", icon: "📝", title: "Report Builder", desc: "Generate custom reports" },
    { id: "goals", icon: "🎯", title: "Goal Tracking", desc: "Monitor progress on KPIs" },
    { id: "sales", icon: "💰", title: "Sales Funnel", desc: "Track sales funnels and deals" },
  ]

  return (
    <div className="fixed inset-0 z-[2000] flex items-center justify-center">
      <div className="absolute inset-0 bg-black/30 backdrop-blur-sm cursor-pointer" onClick={onClose} />
      <div className="relative z-10 w-[90%] max-w-[700px] bg-white border border-slate-200 rounded-xl shadow-2xl animate-scale-in">
        <div className="px-6 py-5 border-b border-slate-200 flex justify-between items-center">
          <h3 className="text-base font-semibold text-slate-800 m-0">Create New View</h3>
          <button
            onClick={onClose}
            className="w-7 h-7 rounded bg-transparent text-slate-500 text-xl cursor-pointer flex items-center justify-center transition-all hover:bg-slate-100 hover:text-slate-800"
          >
            ×
          </button>
        </div>
        <div className="px-6 py-6 max-h-[500px] overflow-y-auto">
          <div className="grid grid-cols-2 gap-4">
            {templates.map((template, idx) => (
              <div
                key={idx}
                onClick={() => {
                  onSelectTemplate(template)
                  onClose()
                }}
                className="px-4 py-5 bg-slate-50 border border-slate-200 rounded-lg cursor-pointer transition-all hover:bg-slate-100 hover:border-slate-300 hover:-translate-y-0.5 hover:shadow-md"
              >
                <div className="text-[32px] mb-3 opacity-80">{template.icon}</div>
                <div className="text-sm text-slate-800 font-semibold mb-1.5">{template.title}</div>
                <div className="text-xs text-slate-500 leading-normal">{template.desc}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

export default function KnowledgeUniversePage() {
  const router = useRouter()
  const { currentProject, markOntologyComplete } = useProjectStore()
  
  // Dashboard mode: 'building' or 'result'
  const [dashboardMode, setDashboardMode] = useState<'building' | 'result'>('result')
  const [buildingStage, setBuildingStage] = useState<'etl' | 'questions' | 'ontology' | 'complete'>('etl')
  const [showConfirmationModal, setShowConfirmationModal] = useState(false)
  const [currentETLQuestion, setCurrentETLQuestion] = useState<any>(null)
  
  const [cards, setCards] = useState<Card[]>(cardsData)
  const [selectedCard, setSelectedCard] = useState<string | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [inputValue, setInputValue] = useState("")
  const [showViewModal, setShowViewModal] = useState(false)
  const [showNewProjectModal, setShowNewProjectModal] = useState(false)
  const [showQuickNoteModal, setShowQuickNoteModal] = useState(false)
  const [isCanvasLoading, setIsCanvasLoading] = useState(false)
  const [isProcessing, setIsProcessing] = useState(false)
  const [generatedDashboard, setGeneratedDashboard] = useState<{ template: string; ready: boolean } | null>(null)
  const chatMessagesRef = useRef<HTMLDivElement>(null)
  const questionsListRef = useRef<HTMLDivElement>(null)
  const etlMessageSentRef = useRef(false)

  // Tab state
  const [activeRightTab, setActiveRightTab] = useState<"chat" | "questions">("chat")

  // Questions state
  const [answers, setAnswers] = useState<Record<string, string | string[]>>({})
  const [resolvedIds, setResolvedIds] = useState<string[]>([])
  const [isResolving, setIsResolving] = useState(false)
  const [resolveLog, setResolveLog] = useState<Array<{ qId: string; question: string; table: string; rows: number; resolved: boolean }>>([])

  // Version state
  const [versions, setVersions] = useState<OntologyVersion[]>(initialVersions)
  const [pendingVersionUpdate, setPendingVersionUpdate] = useState(false)

  // Ontology filter state
  const [selectedNodeTypes, setSelectedNodeTypes] = useState<ObjectType[]>([
    "DataSet",
    "Analysis",
    "Report",
    "MLModel",
    "UserCohort",
    "MarketingCampaign",
    "StrategyPlaybook",
  ])
  const [selectedLevels, setSelectedLevels] = useState<number[]>([1, 2, 3, 4])
  const [selectedRelationTypes, setSelectedRelationTypes] = useState<RelationType[]>([
    "USES_DATA",
    "TRAINS_MODEL",
    "GENERATES_REPORT",
    "INFORMS_STRATEGY",
    "TARGETS_COHORT",
    "AFFECTS_CAMPAIGN",
  ])

  const currentVersion = versions.find((v) => v.isCurrent)

  // Check if we need to enter building mode
  useEffect(() => {
    if (currentProject?.needsETL && !currentProject?.ontologyBuilt) {
      setDashboardMode('building')
      setBuildingStage('etl')
      // 在ETL阶段添加初始消息(只添加一次)
      if (!etlMessageSentRef.current && messages.length === 0) {
        etlMessageSentRef.current = true
        setTimeout(() => {
          addMessage('assistant', 'Starting data cleaning process. This may take a moment...')
        }, 500)
      }
    } else {
      setDashboardMode('result')
    }
  }, [currentProject])

  useEffect(() => {
    // 只在真正进入结果态时显示预置消息
    // 检查: 1) 是结果态 2) 消息为空 3) 项目已完成本体构建
    if (dashboardMode === 'result' && 
        messages.length === 0 && 
        currentProject?.ontologyBuilt) {
      setTimeout(() => {
        addMessage("assistant", `Your knowledge universe is ready! I've analyzed ${ontologyNodes.length} data nodes.`)
        setTimeout(() => {
          showInitialSuggestions()
        }, 500)
      }, 200)
    }
  }, [dashboardMode, currentProject?.ontologyBuilt])

  const addMessage = (role: "user" | "assistant", content: string, marker?: string) => {
    const newMessage: Message = {
      role,
      content: marker ? content + marker : content,
      time: new Date().toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" }),
    }
    setMessages((prev) => [...prev, newMessage])
    setTimeout(() => {
      if (chatMessagesRef.current) {
        chatMessagesRef.current.scrollTop = chatMessagesRef.current.scrollHeight
      }
    }, 100)
  }

  // ========== Building Stage Handlers ==========
  const handleETLComplete = () => {
    setBuildingStage('questions')
    addMessage('assistant', 'Data cleaning completed! Now I need to ask you a few questions to clarify some ambiguities.')
  }

  const handleQuestionsComplete = () => {
    setShowConfirmationModal(true)
  }

  const handleConfirmBuild = () => {
    setShowConfirmationModal(false)
    setBuildingStage('ontology')
    addMessage('assistant', 'Starting ontology construction process...')
  }

  const handleOntologyComplete = () => {
    if (currentProject) {
      markOntologyComplete(currentProject.id)
    }
    setBuildingStage('complete')
    addMessage('assistant', 'Ontology construction completed! Refreshing view...')
    
    // Switch to result mode after a delay
    setTimeout(() => {
      setDashboardMode('result')
    }, 2000)
  }

  const showInitialSuggestions = () => {
    const suggestions = [
      {
        content:
          "Your data saturation is currently at 78%, which is below the optimal range (85%+). Adding more data sources will improve analysis accuracy and reveal deeper insights.",
        marker: "##SUGGEST_UPLOAD##",
      },
      {
        content:
          'I\'ve detected potential relationships between "User Behavior" and "Revenue Analytics" nodes. Auto-connecting related nodes can help visualize data dependencies and patterns.',
        marker: "##SUGGEST_CONNECT##",
      },
      {
        content:
          "Your current node layout has 23% overlapping connections, which may reduce readability. Optimizing the layout will improve clarity and make data patterns more visible.",
        marker: "##SUGGEST_OPTIMIZE##",
      },
    ]
    suggestions.forEach((suggestion, index) => {
      setTimeout(() => {
        addMessage("assistant", suggestion.content, suggestion.marker)
      }, index * 800)
    })
  }

  const handleAutoConnect = () => {
    addMessage("user", "Auto-connect related nodes")
    addMessage("assistant", "🔗 Analyzing node relationships...")
    setTimeout(() => {
      addMessage(
        "assistant",
        "✓ Connected 3 related node pairs:\n• User Behavior ↔ Revenue Analytics\n• Customer Data ↔ Sales Metrics\n• Product Info ↔ Inventory Data",
      )
    }, 1500)
  }


  const handleConfirmOntologyUpdate = () => {
    setPendingVersionUpdate(false)
    addMessage("user", "Yes, please update the ontology")
    addMessage("assistant", "🔄 Updating ontology structure...")

    setIsCanvasLoading(true)

    setTimeout(() => {
      // Create new version
      const newVersionNumber = Math.max(...versions.map((v) => v.version)) + 1
      const newVersion: OntologyVersion = {
        id: `v${newVersionNumber}`,
        version: newVersionNumber,
        updatedAt: new Date().toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" }),
        description: "Updated based on conversation insights",
        isCurrent: true,
      }

      // Update versions - mark all as not current, add new one
      setVersions((prev) =>
        [newVersion, ...prev.map((v) => ({ ...v, isCurrent: false }))]
      )

      setIsCanvasLoading(false)
      addMessage(
        "assistant",
        `✓ Ontology updated successfully!\n\n• New version: v${newVersionNumber}\n• Changes: Added 2 new relationships, refined 3 node definitions\n• Updated: ${newVersion.updatedAt}\n\nYou can switch between versions using the project info panel.`,
      )
    }, 2000)
  }

  const handleDeclineOntologyUpdate = () => {
    setPendingVersionUpdate(false)
    addMessage("user", "No, keep the current version")
    addMessage("assistant", "Understood. I'll keep the current ontology structure. Let me know if you need anything else!")
  }

  const handleVersionSwitch = (version: OntologyVersion) => {
    if (version.isCurrent) return

    setIsCanvasLoading(true)
    addMessage("assistant", `🔄 Switching to ontology v${version.version}...`)

    setTimeout(() => {
      setVersions((prev) =>
        prev.map((v) => ({ ...v, isCurrent: v.id === version.id }))
      )
      setIsCanvasLoading(false)
      addMessage("assistant", `✓ Now viewing ontology v${version.version} (${version.description})`)
    }, 1000)
  }

  const handleSelectCard = (cardId: string) => {
    setSelectedCard(cardId)
  }

  const handleEditCard = (cardId: string) => {
    addMessage("assistant", `Edit mode: "${cards.find((c) => c.id === cardId)?.title}"`)
  }

  const handleDeleteCard = (cardId: string) => {
    const card = cards.find((c) => c.id === cardId)
    if (card) {
      addMessage("assistant", `Deleting "${card.title}"...`)
      setTimeout(() => {
        setCards((prev) => prev.filter((c) => c.id !== cardId))
        addMessage("assistant", `✓ Removed`)
        setSelectedCard(null)
      }, 300)
    }
  }

  const handleAutoLayout = () => {
    addMessage("assistant", "✓ Layout reset to default positions")
  }

  const handleUploadData = () => {
    setShowNewProjectModal(true)
  }

  const handleQuickNote = () => {
    setShowQuickNoteModal(true)
  }

  const etlQuestionnaireRef = useRef<any>(null)

  const handleSendMessage = () => {
    if (!inputValue.trim()) return
    
    // If in questions stage, treat input as answer
    if (dashboardMode === 'building' && buildingStage === 'questions' && currentETLQuestion) {
      handleETLAnswer(inputValue)
      setInputValue("")
      return
    }
    
    addMessage("user", inputValue)
    setInputValue("")

    setTimeout(() => {
      setIsProcessing(true)
      setTimeout(() => {
        setIsProcessing(false)
        addMessage(
          "assistant",
          `Based on your data, I notice that the current node layout has 23% overlapping connections, which may reduce readability. Optimizing the layout will improve clarity and make data patterns more visible.`,
          "##SUGGEST_OPTIMIZE##",
        )
      }, 1500)
    }, 300)
  }

  const handleETLAnswer = (answer: string) => {
    if (etlQuestionnaireRef.current?.handleAnswer) {
      etlQuestionnaireRef.current.handleAnswer(answer)
    }
  }

  const handleAddAsNode = (content: string, title: string) => {
    setIsCanvasLoading(true)

    const newCard: Card = {
      id: "note-" + Date.now(),
      title: title,
      type: "Note",
      badge: "📝",
      row: Math.floor(Math.random() * 3) + 1,
      col: Math.floor(Math.random() * 8) + 1,
      stats: {
        Content: content.substring(0, 50) + "...",
        Words: content.split(/\s+/).filter(Boolean).length + "",
        Created: new Date().toLocaleDateString(),
        Type: "Quick Note",
      },
    }

    setTimeout(() => {
      setCards((prev) => [...prev, newCard])
      addMessage("assistant", `✓ Quick note "${title}" has been added as a new node.`)
      setIsCanvasLoading(false)
    }, 1000)
  }

  const handleIntegrateToGraph = (content: string, title: string) => {
    setIsCanvasLoading(true)

    setTimeout(() => {
      const updatedCards = [...cards]
      if (updatedCards.length >= 2) {
        updatedCards[0] = { ...updatedCards[0], badge: "🔄 Updated" }
        updatedCards[1] = { ...updatedCards[1], badge: "🔄 Updated" }
      }
      setCards(updatedCards)
      addMessage(
        "assistant",
        `✓ Knowledge from "${title}" has been integrated into the graph. Updated 2 related nodes.`,
      )
      setIsCanvasLoading(false)
    }, 1500)
  }

  const handleTemplateSelect = (template: { id: string; title: string; icon: string }) => {
    setIsProcessing(true)
    setGeneratedDashboard(null)
    addMessage("user", `I want to create a ${template.title} dashboard`)
    setTimeout(() => {
      addMessage(
        "assistant",
        `Great choice! I'll help you create a ${template.title}. Let me analyze your data...\n\n${template.icon} Starting process...`,
      )
    }, 500)
    setTimeout(() => {
      addMessage(
        "assistant",
        `📋 Step 1/4: Requirements Analysis\n\n• Analyzing data structure\n• Identifying key metrics\n• Validating data quality\n\n✅ Complete!`,
      )
    }, 2000)
    setTimeout(() => {
      addMessage(
        "assistant",
        `⚙️ Step 2/4: Generating Configuration\n\n• Creating dashboard layout\n• Setting up widgets\n• Configuring data connections\n\n✅ Complete!`,
      )
    }, 4000)
    setTimeout(() => {
      addMessage(
        "assistant",
        `💻 Step 3/4: Compiling Code\n\n• Generating dashboard code\n• Optimizing performance\n\n✅ Complete!`,
      )
    }, 6000)
    setTimeout(() => {
      addMessage(
        "assistant",
        `🚀 Step 4/4: Deploying\n\n• Setting up environment\n• Creating shareable link\n\n✅ Complete!`,
      )
    }, 8000)
    setTimeout(() => {
      setGeneratedDashboard({ template: template.id, ready: true })
      setIsProcessing(false)
      addMessage("assistant", `🎉 Your ${template.title} is ready!\n\nClick the button below to view your dashboard:`)
    }, 10000)
  }

  // ========== Question handlers ==========
  const handleSingleChoice = (questionId: string, optionId: string) => {
    setAnswers((prev) => ({ ...prev, [questionId]: optionId }))
  }

  const handleMultipleChoice = (questionId: string, optionId: string) => {
    setAnswers((prev) => {
      const current = (prev[questionId] as string[]) || []
      if (current.includes(optionId)) {
        return { ...prev, [questionId]: current.filter((id) => id !== optionId) }
      }
      return { ...prev, [questionId]: [...current, optionId] }
    })
  }

  const handleTextInput = (questionId: string, value: string) => {
    setAnswers((prev) => ({ ...prev, [questionId]: value }))
  }

  const handleAutoResolve = async () => {
    setIsResolving(true)
    setResolveLog([])

    const tables = ["finance.revenue_records", "analytics.user_sessions", "finance.fiscal_calendar"]

    for (let i = 0; i < autoResolvableIds.length; i++) {
      const qId = autoResolvableIds[i]
      const question = pendingQuestions.find((q) => q.id === qId)
      if (!question) continue

      await new Promise((resolve) => setTimeout(resolve, 1200))

      const logEntry = {
        qId,
        question: question.question,
        table: tables[i] || "data.unknown",
        rows: Math.floor(Math.random() * 50000) + 10000,
        resolved: true,
      }

      setResolveLog((prev) => [...prev, logEntry])

      if (question.type === "single" && question.options) {
        setAnswers((prev) => ({ ...prev, [qId]: question.options![0].id }))
      } else if (question.type === "text") {
        if (qId === "q6") {
          setAnswers((prev) => ({ ...prev, [qId]: "2024-12-31" }))
        }
      }
    }

    setResolvedIds(autoResolvableIds)
    setIsResolving(false)
  }

  const handleSubmitAnswers = () => {
    const answeredCount = Object.keys(answers).filter((key) => {
      const val = answers[key]
      if (Array.isArray(val)) return val.length > 0
      return val && String(val).trim() !== ""
    }).length

    addMessage("assistant", `✓ Received ${answeredCount} answers. Updating analysis model...`)
    setActiveRightTab("chat")
  }

  const getAnsweredCount = () => {
    return Object.keys(answers).filter((key) => {
      const val = answers[key]
      if (Array.isArray(val)) return val.length > 0
      return val && String(val).trim() !== ""
    }).length
  }

  const unresolvedQuestions = pendingQuestions.filter((q) => !resolvedIds.includes(q.id))

  // Filter handlers
  const handleTypeToggle = (type: ObjectType) => {
    setSelectedNodeTypes((prev) => (prev.includes(type) ? prev.filter((t) => t !== type) : [...prev, type]))
  }

  const handleLevelToggle = (level: number) => {
    setSelectedLevels((prev) => (prev.includes(level) ? prev.filter((l) => l !== level) : [...prev, level]))
  }

  const handleRelationToggle = (relation: RelationType) => {
    setSelectedRelationTypes((prev) =>
      prev.includes(relation) ? prev.filter((r) => r !== relation) : [...prev, relation],
    )
  }

  return (
    <>
      {dashboardMode === 'result' && (
        <DashboardHeader
          selectedNodeTypes={selectedNodeTypes}
          onTypeToggle={handleTypeToggle}
          selectedLevels={selectedLevels}
          onLevelToggle={handleLevelToggle}
          selectedRelationTypes={selectedRelationTypes}
          onRelationToggle={handleRelationToggle}
          onQuickNote={handleQuickNote}
          onUpdateData={handleUploadData}
          projectName="Trantor Analytics Project"
          projectDescription="Optimize conversion rates and user retention"
          nodeCount={ontologyNodes.length}
          topicCount={5}
          dataSize="1.2GB"
          versions={versions}
          currentVersion={currentVersion}
          onVersionSwitch={handleVersionSwitch}
        />
      )}

      {/* Main Content Area */}
      <div className={`relative h-[calc(100vh-4rem)] mr-[400px] overflow-hidden bg-[#F8F9FB] ${dashboardMode === 'result' ? 'pt-[72px]' : ''}`}>
        {dashboardMode === 'building' ? (
          /* Building Mode */
          <div className="h-full overflow-y-auto p-6">
            {(buildingStage === 'etl' || buildingStage === 'questions') && (
              <SimplifiedETLView onComplete={handleETLComplete} buildingStage={buildingStage} />
            )}
            {buildingStage === 'ontology' && (
              <div className="pt-6 border-t-2 border-slate-200 mt-6 bg-white rounded-lg p-6">
                <h2 className="text-lg font-semibold text-[#2D3748] mb-4">Ontology Construction Process</h2>
                <CollapsibleOntologyBuilder onComplete={handleOntologyComplete} />
              </div>
            )}
            {buildingStage === 'complete' && (
              <div className="flex items-center justify-center h-full">
                <div className="text-center">
                  <div className="w-16 h-16 rounded-full bg-[#10B981] flex items-center justify-center mx-auto mb-4">
                    <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="3">
                      <path d="M5 13l4 4L19 7" />
                    </svg>
                  </div>
                  <p className="text-lg font-semibold text-[#2D3748]">Ontology Construction Complete!</p>
                  <p className="text-sm text-[#6B7280] mt-2">Preparing your dashboard...</p>
                </div>
              </div>
            )}
          </div>
        ) : (
          /* Result Mode */
          <>
            <button
              onClick={handleAutoLayout}
              className="absolute right-5 bottom-5 w-11 h-11 bg-white/95 backdrop-blur-md rounded-full flex items-center justify-center cursor-pointer z-20 transition-all shadow-md text-slate-600 hover:bg-white hover:text-[#7AB8CC] hover:-translate-y-0.5 hover:rotate-180 hover:shadow-lg"
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M21 10c-1.5-4-5.5-7-10-7S3 6 1.5 10"></path>
                <path d="M3 14c1.5 4 5.5 7 10 7s8.5-3 10-7"></path>
                <polyline points="21 6 21 10 17 10"></polyline>
                <polyline points="3 18 3 14 7 14"></polyline>
              </svg>
            </button>

            {isCanvasLoading && <CanvasLoadingState />}

            <OntologyCanvas
              nodes={ontologyNodes}
              relations={ontologyRelations}
              selectedNodeTypes={selectedNodeTypes}
              selectedLevels={selectedLevels}
              selectedRelationTypes={selectedRelationTypes}
            />
          </>
        )}
      </div>

      {/* Right Panel with Tabs */}
      <div className="fixed top-16 right-0 bottom-0 w-[400px] bg-[#F5F6F7] flex flex-col border-l border-slate-200 z-20">
        {/* Tab Bar - Only show in result mode */}
        {dashboardMode === 'result' && (
          <div className="shrink-0 flex border-b border-slate-200 bg-white">
            <button
              onClick={() => setActiveRightTab("chat")}
              className={`flex-1 px-4 py-3 text-sm font-medium transition-all relative ${
                activeRightTab === "chat"
                  ? "text-[#5A95A8]"
                  : "text-slate-500 hover:text-slate-700"
              }`}
            >
              Chat
              {activeRightTab === "chat" && (
                <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-[#5A95A8]"></div>
              )}
            </button>
            <button
              onClick={() => setActiveRightTab("questions")}
              className={`flex-1 px-4 py-3 text-sm font-medium transition-all relative flex items-center justify-center gap-2 ${
                activeRightTab === "questions"
                  ? "text-[#5A95A8]"
                  : "text-slate-500 hover:text-slate-700"
              }`}
            >
              <span>{pendingQuestions.length} Pending</span>
              <span className="w-2 h-2 bg-amber-400 rounded-full animate-pulse"></span>
              {activeRightTab === "questions" && (
                <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-[#5A95A8]"></div>
              )}
            </button>
          </div>
        )}

        {/* Tab Content */}
        {dashboardMode === 'building' || activeRightTab === "chat" ? (
          <>
            <div ref={chatMessagesRef} className="flex-1 overflow-y-auto px-5 py-6">
              <div className="flex flex-col gap-4">
                {messages.map((msg, idx) => {
                  const isUploadSuggestion = msg.content.includes("##SUGGEST_UPLOAD##")
                  const isConnectSuggestion = msg.content.includes("##SUGGEST_CONNECT##")
                  const isOptimizeSuggestion = msg.content.includes("##SUGGEST_OPTIMIZE##")
                  const isOntologyUpdateSuggestion = msg.content.includes("##SUGGEST_ONTOLOGY_UPDATE##")
                  const isQuestion = msg.content.includes("##QUESTION##")
                  const displayContent = msg.content
                    .replace("##SUGGEST_UPLOAD##", "")
                    .replace("##SUGGEST_CONNECT##", "")
                    .replace("##SUGGEST_OPTIMIZE##", "")
                    .replace("##SUGGEST_ONTOLOGY_UPDATE##", "")
                    .replace("##QUESTION##", "")

                  return (
                    <div key={idx}>
                      <div
                        className={`px-3.5 py-3 rounded-lg max-w-[90%] ${msg.role === "assistant" ? "self-start bg-white shadow-sm" : "self-end bg-blue-50/70 shadow-sm ml-auto"}`}
                      >
                        <div className="flex justify-between mb-1.5 text-xs text-slate-500 font-medium">
                          <span>{msg.role === "user" ? "👤 You" : "🤖 AI"}</span>
                          <span>{msg.time}</span>
                        </div>
                        <div className="text-sm leading-relaxed text-slate-800 whitespace-pre-line">{displayContent}</div>
                      </div>
                      {isUploadSuggestion && (
                        <button
                          onClick={() => setShowNewProjectModal(true)}
                          className="mt-2 flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-[#7AB8CC] to-[#5A95A8] text-white rounded-lg text-sm font-medium shadow-md hover:shadow-lg transition-all hover:-translate-y-0.5"
                        >
                          <span>📤</span>
                          <span>Upload More Data</span>
                        </button>
                      )}
                      {isConnectSuggestion && (
                        <button
                          onClick={handleAutoConnect}
                          className="mt-2 flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-[#7AB8CC] to-[#5A95A8] text-white rounded-lg text-sm font-medium shadow-md hover:shadow-lg transition-all hover:-translate-y-0.5"
                        >
                          <span>🔗</span>
                          <span>Auto-Connect Nodes</span>
                        </button>
                      )}
                      {isOptimizeSuggestion && (
                        <button
                          onClick={handleAutoLayout}
                          className="mt-2 flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-[#7AB8CC] to-[#5A95A8] text-white rounded-lg text-sm font-medium shadow-md hover:shadow-lg transition-all hover:-translate-y-0.5"
                        >
                          <span>✨</span>
                          <span>Optimize Layout</span>
                        </button>
                      )}
                      {isOntologyUpdateSuggestion && pendingVersionUpdate && (
                        <div className="mt-2 flex gap-2">
                          <button
                            onClick={handleConfirmOntologyUpdate}
                            className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-[#5A95A8] to-[#7AB8CC] text-white rounded-lg text-sm font-medium shadow-md hover:shadow-lg transition-all hover:-translate-y-0.5"
                          >
                            <span>✓</span>
                            <span>Yes, Update</span>
                          </button>
                          <button
                            onClick={handleDeclineOntologyUpdate}
                            className="flex items-center gap-2 px-4 py-2 bg-white border border-slate-200 text-slate-600 rounded-lg text-sm font-medium shadow-sm hover:bg-slate-50 transition-all"
                          >
                            <span>✗</span>
                            <span>No, Keep Current</span>
                          </button>
                        </div>
                      )}
                      {idx === messages.length - 1 &&
                        generatedDashboard?.ready &&
                        msg.role === "assistant" &&
                        msg.content.includes("ready!") && (
                          <button
                            onClick={() => router.push(`/bi-dashboard?template=${generatedDashboard.template}`)}
                            className="mt-3 flex items-center gap-2 px-5 py-3 bg-gradient-to-r from-[#5A95A8] to-[#7AB8CC] text-white rounded-xl shadow-lg hover:shadow-xl transition-all hover:-translate-y-0.5"
                          >
                            <svg
                              width="18"
                              height="18"
                              viewBox="0 0 24 24"
                              fill="none"
                              stroke="currentColor"
                              strokeWidth="2"
                            >
                              <rect x="3" y="3" width="18" height="18" rx="2" />
                              <line x1="9" y1="3" x2="9" y2="21" />
                            </svg>
                            <span className="font-medium">Open Dashboard</span>
                            <span>→</span>
                          </button>
                        )}
                    </div>
                  )
                })}
                {isProcessing && (
                  <div className="self-start bg-white shadow-sm px-3.5 py-3 rounded-lg">
                    <div className="flex items-center gap-2">
                      <div className="flex gap-1">
                        <div className="w-2 h-2 bg-[#5A95A8] rounded-full animate-bounce"></div>
                        <div
                          className="w-2 h-2 bg-[#5A95A8] rounded-full animate-bounce"
                          style={{ animationDelay: "150ms" }}
                        ></div>
                        <div
                          className="w-2 h-2 bg-[#5A95A8] rounded-full animate-bounce"
                          style={{ animationDelay: "300ms" }}
                        ></div>
                      </div>
                      <span className="text-sm text-slate-500">AI is working...</span>
                    </div>
                  </div>
                )}
              </div>
            </div>
            
            {/* ETL Chat Questionnaire - Only in building mode questions stage */}
            {dashboardMode === 'building' && buildingStage === 'questions' && (
              <ETLChatQuestionnaire 
                ref={etlQuestionnaireRef}
                onAddMessage={addMessage}
                onComplete={handleQuestionsComplete}
                isActive={true}
                onGetCurrentQuestion={setCurrentETLQuestion}
              />
            )}
            
            {/* Input Area - Always show to maintain layout */}
            <div className="shrink-0 px-5 py-4 bg-slate-100/80 border-t border-slate-200">
              {/* Show action buttons only in result mode */}
              {dashboardMode === 'result' && (
                <div className="mb-2.5 flex gap-2 items-center">
                  <button
                    onClick={showInitialSuggestions}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-white rounded-md text-xs text-slate-700 font-medium cursor-pointer transition-all shadow-sm hover:bg-slate-50 hover:shadow-md hover:-translate-y-px"
                  >
                    <span className="text-sm">✨</span>
                    <span>Get AI Suggestions</span>
                  </button>
                  <button
                    onClick={() => setShowViewModal(true)}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-white rounded-md text-xs text-slate-700 font-medium cursor-pointer transition-all shadow-sm hover:bg-slate-50 hover:shadow-md hover:-translate-y-px"
                  >
                    <span className="text-sm">+</span>
                    <span>Create View</span>
                  </button>
                </div>
              )}
              
              {/* Input always visible */}
              <div className="relative flex flex-wrap items-end bg-white rounded-lg px-3 py-2.5 gap-1.5 transition-all min-h-[80px] shadow-md focus-within:shadow-lg focus-within:ring-2 focus-within:ring-blue-400/50">
                <textarea
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  onKeyPress={(e) => {
                    if (e.key === "Enter" && !e.shiftKey) {
                      e.preventDefault()
                      handleSendMessage()
                    }
                  }}
                  className="flex-1 min-w-[200px] min-h-[60px] bg-transparent border-0 text-slate-800 text-sm leading-normal resize-none outline-none max-h-[120px]"
                  placeholder="Ask anything about your data..."
                  rows={3}
                />
                <button
                  onClick={handleSendMessage}
                  className="w-8 h-8 p-0 bg-[#5A95A8] rounded-md text-white text-base cursor-pointer flex items-center justify-center transition-all flex-shrink-0 hover:bg-[#7AB8CC]"
                >
                  →
                </button>
              </div>
            </div>
          </>
        ) : (
          /* Questions Panel */
          <>
            <div ref={questionsListRef} className="flex-1 overflow-y-auto px-5 py-4">
              <div className="mb-4 text-sm text-slate-500">
                {pendingQuestions.length} questions total, {getAnsweredCount()} answered
                {resolvedIds.length > 0 && (
                  <span className="ml-2 text-green-600">(AI resolved {resolvedIds.length})</span>
                )}
              </div>

              {/* AI Resolve Log */}
              {resolveLog.length > 0 && (
                <div className="mb-6 p-4 bg-blue-50 rounded-lg border border-blue-100">
                  <div className="text-sm font-medium text-blue-800 mb-3 flex items-center gap-2">
                    <span>🤖</span>
                    <span>AI Agent Execution Log</span>
                  </div>
                  <div className="space-y-2">
                    {resolveLog.map((log) => (
                      <div key={log.qId} className="text-sm">
                        <div className="flex items-start gap-2">
                          <span className="text-green-600">✓</span>
                          <div className="flex-1">
                            <div className="text-slate-700">{log.question}</div>
                            <div className="text-xs text-slate-500 mt-1">
                              Queried <span className="font-mono text-blue-600">{log.table}</span>
                              , scanned {log.rows.toLocaleString()} rows
                              <span className="ml-2 text-green-600">→ Resolved</span>
                            </div>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                  {isResolving && (
                    <div className="mt-3 flex items-center gap-2 text-sm text-blue-600">
                      <div className="flex gap-1">
                        <div className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-bounce"></div>
                        <div className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: "150ms" }}></div>
                        <div className="w-1.5 h-1.5 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: "300ms" }}></div>
                      </div>
                      <span>Analyzing...</span>
                    </div>
                  )}
                </div>
              )}

              {/* Question Cards */}
              <div className="space-y-4">
                {unresolvedQuestions.map((q, index) => (
                  <div key={q.id} className="p-4 bg-white rounded-lg shadow-sm border border-slate-100">
                    <div className="flex items-start gap-3 mb-3">
                      <span className="flex-shrink-0 w-6 h-6 bg-slate-100 rounded-full flex items-center justify-center text-xs font-medium text-slate-600">
                        {index + 1 + resolvedIds.length}
                      </span>
                      <div className="flex-1">
                        <div className="text-sm font-medium text-slate-800">{q.question}</div>
                        {q.description && (
                          <div className="mt-1 text-xs text-slate-500">{q.description}</div>
                        )}
                      </div>
                    </div>

                    <div className="pl-9">
                      {q.type === "single" && q.options && (
                        <div className="space-y-2">
                          {q.options.map((option) => (
                            <label
                              key={option.id}
                              className="flex items-center gap-2 cursor-pointer group"
                              onClick={() => handleSingleChoice(q.id, option.id)}
                            >
                              <div
                                className={`w-4 h-4 rounded-full border-2 flex items-center justify-center transition-all ${
                                  answers[q.id] === option.id
                                    ? "border-[#5A95A8] bg-[#5A95A8]"
                                    : "border-slate-300 group-hover:border-slate-400"
                                }`}
                              >
                                {answers[q.id] === option.id && (
                                  <div className="w-1.5 h-1.5 bg-white rounded-full"></div>
                                )}
                              </div>
                              <span className="text-sm text-slate-700">{option.label}</span>
                            </label>
                          ))}
                        </div>
                      )}

                      {q.type === "multiple" && q.options && (
                        <div className="space-y-2">
                          {q.options.map((option) => {
                            const currentAnswers = (answers[q.id] as string[]) || []
                            const isChecked = currentAnswers.includes(option.id)
                            return (
                              <label
                                key={option.id}
                                className="flex items-center gap-2 cursor-pointer group"
                                onClick={() => handleMultipleChoice(q.id, option.id)}
                              >
                                <div
                                  className={`w-4 h-4 rounded border-2 flex items-center justify-center transition-all ${
                                    isChecked
                                      ? "border-[#5A95A8] bg-[#5A95A8]"
                                      : "border-slate-300 group-hover:border-slate-400"
                                  }`}
                                >
                                  {isChecked && (
                                    <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="3">
                                      <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                                    </svg>
                                  )}
                                </div>
                                <span className="text-sm text-slate-700">{option.label}</span>
                              </label>
                            )
                          })}
                        </div>
                      )}

                      {q.type === "text" && (
                        <input
                          type="text"
                          value={(answers[q.id] as string) || ""}
                          onChange={(e) => handleTextInput(q.id, e.target.value)}
                          placeholder={q.placeholder}
                          className="w-full px-3 py-2 text-sm border border-slate-200 rounded-lg outline-none transition-all focus:border-[#5A95A8] focus:ring-2 focus:ring-[#5A95A8]/20"
                        />
                      )}
                    </div>
                  </div>
                ))}
              </div>

              {unresolvedQuestions.length === 0 && resolvedIds.length > 0 && (
                <div className="text-center py-8 text-slate-500">
                  <div className="text-4xl mb-3">🎉</div>
                  <div className="text-sm">All questions resolved by AI</div>
                </div>
              )}
            </div>

            {/* Fixed Bottom Action Area - Same structure as Chat input area */}
            <div className="shrink-0 px-5 py-4 bg-slate-100/80 border-t border-slate-200">
              {resolveLog.length === 0 && (
                <div className="mb-3 p-3 bg-amber-50 rounded-lg border border-amber-100">
                  <div className="text-sm text-amber-800">
                    After reading more data, AI can auto-resolve{" "}
                    <span className="font-semibold text-amber-900">{autoResolvableIds.length}</span>{" "}
                    questions. Execute?
                  </div>
                  <button
                    onClick={handleAutoResolve}
                    disabled={isResolving}
                    className="mt-2 flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-amber-500 to-amber-600 text-white rounded-lg text-sm font-medium shadow-md hover:shadow-lg transition-all hover:-translate-y-0.5 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {isResolving ? (
                      <>
                        <div className="flex gap-1">
                          <div className="w-1.5 h-1.5 bg-white rounded-full animate-bounce"></div>
                          <div className="w-1.5 h-1.5 bg-white rounded-full animate-bounce" style={{ animationDelay: "150ms" }}></div>
                          <div className="w-1.5 h-1.5 bg-white rounded-full animate-bounce" style={{ animationDelay: "300ms" }}></div>
                        </div>
                        <span>Executing...</span>
                      </>
                    ) : (
                      <>
                        <span>⚡</span>
                        <span>Execute</span>
                      </>
                    )}
                  </button>
                </div>
              )}

              <button
                onClick={handleSubmitAnswers}
                className="w-full py-3 bg-gradient-to-r from-[#5A95A8] to-[#7AB8CC] text-white rounded-lg text-sm font-medium shadow-md hover:shadow-lg transition-all hover:-translate-y-0.5"
              >
                Submit Answers ({getAnsweredCount()}/{pendingQuestions.length})
              </button>
            </div>
          </>
        )}
      </div>

      {showViewModal && <ViewModal onClose={() => setShowViewModal(false)} onSelectTemplate={handleTemplateSelect} />}
      <NewProjectModal isOpen={showNewProjectModal} onClose={() => setShowNewProjectModal(false)} />
      <QuickNoteModal
        isOpen={showQuickNoteModal}
        onClose={() => setShowQuickNoteModal(false)}
        onAddAsNode={handleAddAsNode}
        onIntegrateToGraph={handleIntegrateToGraph}
      />
      <OntologyBuildConfirmationModal
        isOpen={showConfirmationModal}
        onClose={() => setShowConfirmationModal(false)}
        onReupload={() => {}}
        onConfirmBuild={handleConfirmBuild}
        dataSize="1.2GB"
        estimatedTokens={45000}
        estimatedTime="2-3 minutes"
      />
    </>
  )
}
