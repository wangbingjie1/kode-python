"use client"

import { useState, useRef } from "react"
import { ChevronLeft, ChevronRight } from "lucide-react"

const CASE_GALLERY_CASES = [
  {
    id: "csv-sales-dashboard",
    icon: "📊",
    title: "CSV to Sales Dashboard",
    description: "Transform raw CSV data into interactive sales dashboards with AI-powered insights",
  },
  {
    id: "notes-knowledge-graph",
    icon: "📚",
    title: "Reading Notes to Knowledge Graph",
    description: "Convert your reading notes into interconnected knowledge graphs automatically",
  },
  {
    id: "health-wellness-plan",
    icon: "🏥",
    title: "Health Report to Wellness Plan",
    description: "Generate personalized wellness plans from your health reports and medical data",
  },
  {
    id: "pdf-research-summary",
    icon: "🔬",
    title: "PDF to Research Summary",
    description: "Extract key findings and create concise summaries from research papers",
  },
  {
    id: "game-strategy-guide",
    icon: "🎮",
    title: "Game Logs to Strategy Guide",
    description: "Analyze game logs and generate strategic recommendations for better gameplay",
  },
  {
    id: "excel-financial-forecast",
    icon: "💰",
    title: "Excel to Financial Forecast",
    description: "Build predictive financial models from your Excel spreadsheets",
  },
  {
    id: "meeting-action-items",
    icon: "🎙️",
    title: "Meeting to Action Items",
    description: "Extract action items and decisions from meeting transcripts automatically",
  },
  {
    id: "json-api-docs",
    icon: "🔌",
    title: "JSON to API Documentation",
    description: "Generate comprehensive API documentation from JSON schema files",
  },
  {
    id: "social-sentiment-analysis",
    icon: "📱",
    title: "Social Media to Sentiment Report",
    description: "Analyze social media data and generate detailed sentiment analysis reports",
  },
  {
    id: "images-data-tables",
    icon: "📸",
    title: "Images to Data Tables",
    description: "Extract structured data from images and convert to organized tables",
  },
  {
    id: "survey-insights-report",
    icon: "📋",
    title: "Survey Data to Insights Report",
    description: "Transform survey responses into actionable insights and visualizations",
  },
  {
    id: "sql-performance-report",
    icon: "⚡",
    title: "SQL to Performance Report",
    description: "Analyze SQL queries and generate performance optimization recommendations",
  },
  {
    id: "email-summary",
    icon: "✉️",
    title: "Email Threads to Summary",
    description: "Summarize long email threads into concise action points and decisions",
  },
  {
    id: "code-documentation",
    icon: "💻",
    title: "Code to Documentation",
    description: "Automatically generate technical documentation from your codebase",
  },
  {
    id: "parquet-ml-pipeline",
    icon: "🤖",
    title: "Parquet to ML Pipeline",
    description: "Build machine learning pipelines from Parquet data files with AI assistance",
  },
  {
    id: "zip-project-archive",
    icon: "📁",
    title: "ZIP to Project Archive",
    description: "Organize and analyze compressed project files with intelligent categorization",
  },
]

// 假的样例详细信息
const SAMPLE_CASE_DETAIL = {
  overview: "This AI-powered transformation takes your raw data and creates stunning, interactive visualizations that help you understand patterns and make data-driven decisions instantly.",
  features: [
    "Automatic data cleaning and preprocessing",
    "Smart chart type recommendations",
    "Real-time data updates",
    "Export to multiple formats"
  ],
  stats: {
    processingTime: "< 30 seconds",
    accuracy: "99.8%",
    dataPoints: "Up to 1M rows",
    formats: "15+ output formats"
  },
  example: "Transform your monthly sales CSV into an interactive dashboard showing revenue trends, top performers, and predictive forecasts - all in one click."
}

// 浮窗组件
function CaseTooltip({ 
  show, 
  position, 
  caseItem 
}: { 
  show: boolean; 
  position: { x: number; y: number }; 
  caseItem: typeof CASE_GALLERY_CASES[0] | null 
}) {
  if (!show || !caseItem) return null;

  return (
    <div
      className="pointer-events-none fixed z-50 animate-fadeIn"
      style={{
        left: `${position.x}px`,
        top: `${position.y}px`,
        transform: 'translate(-50%, -100%) translateY(-10px)',
      }}
    >
      <div className="w-[380px] rounded-xl bg-white p-5 shadow-2xl border border-slate-200">
        {/* Header */}
        <div className="mb-4 flex items-start gap-3">
          <div className="text-3xl">{caseItem.icon}</div>
          <div>
            <h3 className="text-base font-semibold text-slate-800">{caseItem.title}</h3>
            <div className="mt-1 flex items-center gap-2">
              <span className="inline-flex items-center rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-700">
                Popular
              </span>
              <span className="text-xs text-slate-500">Used by 10k+ users</span>
            </div>
          </div>
        </div>

        {/* Overview */}
        <div className="mb-4">
          <p className="text-sm leading-relaxed text-slate-600">{SAMPLE_CASE_DETAIL.overview}</p>
        </div>

        {/* Features */}
        <div className="mb-4">
          <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">Key Features</h4>
          <ul className="space-y-1">
            {SAMPLE_CASE_DETAIL.features.map((feature, idx) => (
              <li key={idx} className="flex items-start gap-2 text-sm text-slate-700">
                <span className="text-green-500 mt-0.5">✓</span>
                <span>{feature}</span>
              </li>
            ))}
          </ul>
        </div>

        {/* Stats Grid */}
        <div className="mb-4 grid grid-cols-2 gap-3 rounded-lg bg-slate-50 p-3">
          <div>
            <div className="text-xs font-medium text-slate-500">Processing</div>
            <div className="text-sm font-semibold text-slate-800">{SAMPLE_CASE_DETAIL.stats.processingTime}</div>
          </div>
          <div>
            <div className="text-xs font-medium text-slate-500">Accuracy</div>
            <div className="text-sm font-semibold text-slate-800">{SAMPLE_CASE_DETAIL.stats.accuracy}</div>
          </div>
          <div>
            <div className="text-xs font-medium text-slate-500">Data Size</div>
            <div className="text-sm font-semibold text-slate-800">{SAMPLE_CASE_DETAIL.stats.dataPoints}</div>
          </div>
          <div>
            <div className="text-xs font-medium text-slate-500">Outputs</div>
            <div className="text-sm font-semibold text-slate-800">{SAMPLE_CASE_DETAIL.stats.formats}</div>
          </div>
        </div>

        {/* Example */}
        <div className="border-t border-slate-200 pt-3">
          <p className="text-xs leading-relaxed text-slate-500">
            <span className="font-semibold">Example:</span> {SAMPLE_CASE_DETAIL.example}
          </p>
        </div>

        {/* Arrow pointing down */}
        <div className="absolute -bottom-2 left-1/2 h-4 w-4 -translate-x-1/2 rotate-45 border-b border-r border-slate-200 bg-white"></div>
      </div>
    </div>
  );
}

export function CaseGallerySection() {
  const [hoveredCase, setHoveredCase] = useState<string | null>(null)
  const [currentPage, setCurrentPage] = useState(0)
  const [tooltipPosition, setTooltipPosition] = useState({ x: 0, y: 0 })
  const [tooltipCase, setTooltipCase] = useState<typeof CASE_GALLERY_CASES[0] | null>(null)
  const scrollContainerRef = useRef<HTMLDivElement>(null)

  const casesPerPage = 4
  const totalPages = Math.ceil(CASE_GALLERY_CASES.length / casesPerPage)
  const pages = Array.from({ length: totalPages }, (_, i) =>
    CASE_GALLERY_CASES.slice(i * casesPerPage, (i + 1) * casesPerPage),
  )

  const handleCaseClick = (caseId: string) => {
    console.log("[v0] Case clicked:", caseId)
    // Future: Show case detail modal or navigate to case page
  }

  const handleMouseEnter = (e: React.MouseEvent<HTMLButtonElement>, caseItem: typeof CASE_GALLERY_CASES[0]) => {
    setHoveredCase(caseItem.id)
    setTooltipCase(caseItem)
    const rect = e.currentTarget.getBoundingClientRect()
    setTooltipPosition({
      x: rect.left + rect.width / 2,
      y: rect.top
    })
  }

  const handleMouseLeave = () => {
    setHoveredCase(null)
    setTooltipCase(null)
  }

  const scrollToPage = (pageIndex: number) => {
    if (scrollContainerRef.current) {
      const container = scrollContainerRef.current
      const pageWidth = container.offsetWidth
      container.scrollTo({
        left: pageWidth * pageIndex,
        behavior: "smooth",
      })
      setCurrentPage(pageIndex)
    }
  }

  const handlePrevPage = () => {
    if (currentPage > 0) {
      scrollToPage(currentPage - 1)
    }
  }

  const handleNextPage = () => {
    if (currentPage < totalPages - 1) {
      scrollToPage(currentPage + 1)
    }
  }

  return (
    <section className="bg-[#F8F9FB] px-10 py-12">
      <div className="mx-auto max-w-[900px]">
        <div className="relative">
          {currentPage > 0 && (
            <button
              onClick={handlePrevPage}
              className="absolute left-0 top-1/2 z-10 -translate-x-12 -translate-y-1/2 rounded-full bg-white p-2 shadow-lg transition-all hover:bg-gray-50 hover:shadow-xl"
              aria-label="Previous page"
            >
              <ChevronLeft className="h-5 w-5 text-gray-700" />
            </button>
          )}

          {currentPage < totalPages - 1 && (
            <button
              onClick={handleNextPage}
              className="absolute right-0 top-1/2 z-10 -translate-y-1/2 translate-x-12 rounded-full bg-white p-2 shadow-lg transition-all hover:bg-gray-50 hover:shadow-xl"
              aria-label="Next page"
            >
              <ChevronRight className="h-5 w-5 text-gray-700" />
            </button>
          )}

          <div
            ref={scrollContainerRef}
            className="hide-scrollbar overflow-x-auto"
            style={{ scrollSnapType: "x mandatory" }}
          >
            <div className="flex" style={{ width: `${totalPages * 100}%` }}>
              {pages.map((pageCases, pageIndex) => (
                <div
                  key={pageIndex}
                  className="flex-shrink-0"
                  style={{
                    width: `${100 / totalPages}%`,
                    scrollSnapAlign: "start",
                  }}
                >
                  <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                    {pageCases.map((caseItem) => (
                      <button
                        key={caseItem.id}
                        onClick={() => handleCaseClick(caseItem.id)}
                        onMouseEnter={(e) => handleMouseEnter(e, caseItem)}
                        onMouseLeave={handleMouseLeave}
                        className={`group flex items-start gap-4 rounded-xl border border-[#E5E7EB] bg-white p-5 text-left transition-all duration-300 hover:-translate-y-0.5 hover:border-[#D1D5DB] hover:shadow-[0_4px_16px_rgba(0,0,0,0.08)] ${
                          hoveredCase === caseItem.id
                            ? "shadow-[0_4px_16px_rgba(0,0,0,0.08)]"
                            : "shadow-[0_2px_8px_rgba(0,0,0,0.04)]"
                        }`}
                      >
                        <div className="flex-shrink-0 text-2xl">{caseItem.icon}</div>

                        <div className="flex-1 space-y-1.5">
                          <h3 className="text-sm font-semibold leading-tight text-[#2C3E50]">{caseItem.title}</h3>
                          <p className="text-xs leading-relaxed text-[#6B7280]">{caseItem.description}</p>
                        </div>

                        <div className="flex-shrink-0 rounded-md bg-[#F3F4F6] px-2.5 py-1 text-xs font-medium text-[#6B7280]">
                          Example
                        </div>
                      </button>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* 浮窗组件 */}
      <CaseTooltip 
        show={!!hoveredCase} 
        position={tooltipPosition} 
        caseItem={tooltipCase} 
      />

      {/* 添加动画样式 */}
      <style jsx global>{`
        @keyframes fadeIn {
          from { 
            opacity: 0; 
            transform: translate(-50%, -100%) translateY(0px);
          }
          to { 
            opacity: 1; 
            transform: translate(-50%, -100%) translateY(-10px);
          }
        }
        .animate-fadeIn {
          animation: fadeIn 0.2s ease-out;
        }
        .hide-scrollbar {
          -ms-overflow-style: none;
          scrollbar-width: none;
        }
        .hide-scrollbar::-webkit-scrollbar {
          display: none;
        }
      `}</style>
    </section>
  )
}
