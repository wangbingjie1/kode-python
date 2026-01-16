"use client"

import type React from "react"

import { useState, useRef, useEffect } from "react"
import { Upload, Send, Plus, ChevronDown } from "lucide-react"

const DATABASE_SOURCES = [
  {
    id: "snowflake",
    name: "Snowflake",
    description: "Cloud Data Warehouse",
    icon: "/abstract-geometric-snowflake.png",
  },
  {
    id: "bigquery",
    name: "BigQuery",
    description: "Google Cloud Analytics",
    icon: "/google-bigquery-logo.jpg",
  },
  {
    id: "postgresql",
    name: "PostgreSQL",
    description: "Open Source Database",
    icon: "/postgresql-logo.png",
  },
  {
    id: "mysql",
    name: "MySQL",
    description: "Relational Database",
    icon: "/mysql-logo.png",
  },
  {
    id: "mongodb",
    name: "MongoDB",
    description: "Document Database",
    icon: "/mongodb-logo.png",
  },
  {
    id: "salesforce",
    name: "Salesforce",
    description: "CRM Platform",
    icon: "/salesforce-logo.png",
  },
  {
    id: "hubspot",
    name: "HubSpot",
    description: "Marketing Automation",
    icon: "/hubspot-logo.png",
  },
  {
    id: "google-ads",
    name: "Google Ads",
    description: "Advertising Platform",
    icon: "/google-ads-logo.png",
  },
]

interface CompositeInputSectionProps {
  onFilesUploaded?: (files: File[]) => void
  onOpenNewProjectModal?: () => void
}

export function CompositeInputSection({ onFilesUploaded, onOpenNewProjectModal }: CompositeInputSectionProps) {
  const [inputValue, setInputValue] = useState("")
  const [isDragOver, setIsDragOver] = useState(false)
  const [isDropdownOpen, setIsDropdownOpen] = useState(false)
  const [uploadedFiles, setUploadedFiles] = useState<File[]>([])
  const [showFeedback, setShowFeedback] = useState<{ type: string; message: string } | null>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const dropdownRef = useRef<HTMLDivElement>(null)

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto"
      const newHeight = Math.min(textareaRef.current.scrollHeight, 200)
      textareaRef.current.style.height = `${newHeight}px`
    }
  }, [inputValue])

  // Close dropdown on outside click
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsDropdownOpen(false)
      }
    }
    document.addEventListener("mousedown", handleClickOutside)
    return () => document.removeEventListener("mousedown", handleClickOutside)
  }, [])

  useEffect(() => {
    function handleEscape(event: KeyboardEvent) {
      if (event.key === "Escape" && isDropdownOpen) {
        setIsDropdownOpen(false)
      }
    }
    document.addEventListener("keydown", handleEscape)
    return () => document.removeEventListener("keydown", handleEscape)
  }, [isDropdownOpen])

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragOver(true)
  }

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragOver(false)
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragOver(false)
    const files = Array.from(e.dataTransfer.files)
    handleFiles(files)
  }

  const handleFiles = (files: File[]) => {
    setUploadedFiles((prev) => [...prev, ...files])
    const fileNames = files.map((f) => f.name).join(", ")
    setInputValue((prev) => `Files attached: ${fileNames}\n\n${prev}`)
    showTemporaryFeedback("upload", `✓ ${files.length} file${files.length > 1 ? "s" : ""} attached`)
  }

  const handleUploadClick = () => {
    // 改为打开 Modal 而不是触发文件选择
    if (onOpenNewProjectModal) {
      onOpenNewProjectModal()
    }
  }

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      handleFiles(Array.from(e.target.files))
    }
  }

  const handleDatabaseSelect = (source: (typeof DATABASE_SOURCES)[0]) => {
    // 点击具体数据源时打开 Modal
    setIsDropdownOpen(false)
    if (onOpenNewProjectModal) {
      onOpenNewProjectModal()
    }
  }

  const handleNewProject = () => {
    // 打开 Modal
    if (onOpenNewProjectModal) {
      onOpenNewProjectModal()
    }
  }

  const handleSend = () => {
    if (!inputValue.trim() && uploadedFiles.length === 0) return
    console.log("[v0] Sending message:", inputValue)
    console.log("[v0] Uploaded files:", uploadedFiles)

    if (uploadedFiles.length > 0 && onFilesUploaded) {
      onFilesUploaded(uploadedFiles)
      return
    }

    showTemporaryFeedback("send", "Analysis started!")
    setTimeout(() => {
      setInputValue("")
      setUploadedFiles([])
    }, 1000)
  }

  const showTemporaryFeedback = (type: string, message: string) => {
    setShowFeedback({ type, message })
    setTimeout(() => setShowFeedback(null), 2500)
  }

  const isInputEmpty = !inputValue.trim() && uploadedFiles.length === 0

  return (
    <section className="bg-[#F8F9FB] px-10 pb-32 pt-0">
      <div className="mx-auto max-w-[900px]">
        <div
          className={`relative rounded-2xl bg-white shadow-[0_0_0_1px_rgba(0,0,0,0.04),0_8px_32px_rgba(0,0,0,0.08)] transition-all duration-300 ${
            isDragOver ? "bg-[rgba(90,149,168,0.02)] shadow-[0_0_0_2px_#5A95A8,0_12px_48px_rgba(90,149,168,0.2)]" : ""
          } ${inputValue ? "shadow-[0_0_0_2px_#5A95A8,0_12px_48px_rgba(90,149,168,0.15)]" : ""}`}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          style={{ overflow: "visible", zIndex: 1 }}
        >
          {/* Drag overlay */}
          {isDragOver && (
            <div className="pointer-events-none absolute inset-0 z-50 flex items-center justify-center bg-[#5A95A8]/5">
              <p className="text-lg font-semibold text-[#5A95A8]">Drop files to upload</p>
            </div>
          )}

          {/* Feedback messages */}
          {showFeedback && (
            <div
              className={`absolute left-1/2 top-2 z-[10000] flex -translate-x-1/2 items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium text-white shadow-lg ${
                showFeedback.type === "database" ? "bg-[#5A95A8]" : "bg-[#A8D5BA]"
              } animate-in slide-in-from-top-4 fade-in duration-300`}
            >
              {showFeedback.message}
            </div>
          )}

          <div className="min-h-[140px] bg-transparent px-6 pb-4 pl-10 pt-8">
            <textarea
              ref={textareaRef}
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              placeholder="Drop any file here (CSV, PDF, Excel, JSON, Images, Parquet, SQL, ZIP) or paste information..."
              className="w-full resize-none border-none bg-transparent text-base leading-relaxed text-[#2D3748] outline-none placeholder:text-[#B8B8B8]"
              rows={3}
              maxLength={5000}
              style={{ minHeight: "100px", maxHeight: "200px" }}
            />
          </div>

          <div className="flex items-center justify-between gap-4 bg-transparent px-6 pb-4">
            {/* Left Side - Action Buttons Group */}
            <div className="flex items-center gap-2">
              {/* New Project Button - 点击打开 Modal */}
              <button
                onClick={handleNewProject}
                className="flex items-center gap-2 rounded-lg bg-transparent px-4 py-[9px] text-sm font-medium text-[#4A5568] transition-all duration-300 hover:bg-[#F8F9FB] hover:text-[#5A95A8]"
              >
                <Plus className="h-4 w-4" />
                <span className="hidden sm:inline">New Project</span>
              </button>

              {/* Upload Button - 点击打开 Modal */}
              <button
                onClick={handleUploadClick}
                className="flex items-center gap-2 rounded-lg bg-transparent px-4 py-[9px] text-sm font-medium text-[#4A5568] transition-all duration-300 hover:bg-[#F8F9FB] hover:text-[#5A95A8]"
              >
                <Upload className="h-4 w-4" />
                <span className="hidden sm:inline">Upload</span>
              </button>

              {/* Connect Database Button with Dropdown */}
              <div className="relative" ref={dropdownRef}>
                <button
                  onClick={() => setIsDropdownOpen(!isDropdownOpen)}
                  className={`flex items-center gap-2 rounded-lg bg-transparent px-4 py-[9px] text-sm font-medium text-[#4A5568] transition-all duration-300 hover:bg-[#F8F9FB] hover:text-[#5A95A8] ${
                    isDropdownOpen ? "bg-[#F8F9FB]" : ""
                  }`}
                >
                  <div className="flex items-center -space-x-1.5">
                    {DATABASE_SOURCES.slice(0, 3).map((source, idx) => (
                      <div
                        key={source.id}
                        className="h-5 w-5 overflow-hidden rounded-full border-2 border-white"
                        style={{ zIndex: 3 - idx }}
                      >
                        <img
                          src={source.icon || "/placeholder.svg"}
                          alt={source.name}
                          className="h-full w-full object-cover"
                        />
                      </div>
                    ))}
                    <div className="flex h-5 w-5 items-center justify-center rounded-full border-2 border-white bg-[#E5E7EB] text-[10px] font-semibold text-[#6B7280]">
                      +5
                    </div>
                  </div>
                  <span className="hidden sm:inline">Connect Database</span>
                  <ChevronDown
                    className={`h-3 w-3 text-[#9CA3AF] transition-transform duration-300 ${isDropdownOpen ? "rotate-180" : ""}`}
                  />
                </button>

                {isDropdownOpen && (
                  <div
                    className="absolute bottom-full right-0 mb-2 w-80 animate-in slide-in-from-bottom-2 fade-in rounded-xl bg-white shadow-[0_0_0_1px_rgba(0,0,0,0.04),0_12px_48px_rgba(0,0,0,0.15)] duration-200"
                    style={{
                      zIndex: 9999,
                    }}
                  >
                    <div className="border-b border-[#F0F0F0] px-5 py-4">
                      <h3 className="text-sm font-semibold text-[#2C3E50]">Select Data Source</h3>
                    </div>
                    <div className="max-h-96 overflow-y-auto p-2">
                      {DATABASE_SOURCES.map((source) => (
                        <button
                          key={source.id}
                          onClick={() => handleDatabaseSelect(source)}
                          className="flex w-full items-center gap-3 rounded-lg p-3 text-left transition-colors hover:bg-[#F8F9FB]"
                        >
                          <div className="h-8 w-8 flex-shrink-0 overflow-hidden rounded-md">
                            <img
                              src={source.icon || "/placeholder.svg"}
                              alt={source.name}
                              className="h-full w-full object-cover"
                            />
                          </div>
                          <div className="flex-1">
                            <div className="text-sm font-semibold text-[#2C3E50]">{source.name}</div>
                            <div className="text-xs text-[#6B7280]">{source.description}</div>
                          </div>
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Right Side - Send Button */}
            <button
              onClick={handleSend}
              disabled={isInputEmpty}
              className={`flex items-center gap-2 rounded-lg px-5 py-[9px] text-sm font-semibold transition-all duration-300 ${
                isInputEmpty
                  ? "cursor-not-allowed bg-[#E5E7EB] text-[#9CA3AF]"
                  : "bg-[#5A95A8] text-white shadow-[0_4px_12px_rgba(90,149,168,0.25)] hover:-translate-y-0.5 hover:bg-[#7AB8CC] hover:shadow-[0_6px_16px_rgba(90,149,168,0.35)]"
              }`}
            >
              <span>Send</span>
              <Send className="h-[18px] w-[18px]" />
            </button>
          </div>

          {/* Hidden file input */}
          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept=".csv,.pdf,.xlsx,.xls,.json,.jpg,.jpeg,.png,.parquet,.sql,.zip"
            onChange={handleFileInputChange}
            className="hidden"
          />
        </div>
      </div>
    </section>
  )
}
