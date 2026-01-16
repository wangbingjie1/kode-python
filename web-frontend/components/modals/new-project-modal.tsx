"use client"

import type React from "react"

import { useState, useCallback } from "react"
import { X, Upload, FileText, AlertCircle } from "lucide-react"
import { useRouter } from "next/navigation"
import { useProjectStore } from "@/lib/project-store"

interface NewProjectModalProps {
  isOpen: boolean
  onClose: () => void
}

const SUPPORTED_FORMATS = [
  { ext: ".docx", desc: "Word document", color: "bg-[#A8D5BA]/10 text-[#5A95A8]" },
  { ext: ".pptx", desc: "PowerPoint", color: "bg-[#C9B6E4]/10 text-[#5A95A8]" },
  { ext: ".pdf", desc: "PDF document", color: "bg-[#F4E4C1]/10 text-[#5A95A8]" },
  { ext: ".csv", desc: "Comma-separated", color: "bg-[#A8D5BA]/10 text-[#5A95A8]" },
  { ext: ".xlsx", desc: "Excel spreadsheet", color: "bg-[#F5CAC3]/10 text-[#5A95A8]" },
]

const DATA_SOURCES = [
  { id: "mysql", name: "MySQL", desc: "Popular SQL database" },
  { id: "sqlserver", name: "SQL Server", desc: "Microsoft database" },
]

export function NewProjectModal({ isOpen, onClose }: NewProjectModalProps) {
  const router = useRouter()
  const { enterProject, allProjects, setAllProjects } = useProjectStore()
  const [isDragging, setIsDragging] = useState(false)
  const [uploadedFiles, setUploadedFiles] = useState<File[]>([])
  const [selectedSource, setSelectedSource] = useState<string | null>(null)

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }, [])

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
  }, [])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    const files = Array.from(e.dataTransfer.files)
    setUploadedFiles((prev) => [...prev, ...files])
  }, [])

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const files = Array.from(e.target.files)
      setUploadedFiles((prev) => [...prev, ...files])
    }
  }

  const handleConnectSource = (sourceId: string) => {
    setSelectedSource(sourceId)
  }

  const handleCreateProject = () => {
    // Generate new project
    const newProject = {
      id: "proj_" + Date.now(),
      name: selectedSource ? `${selectedSource.toUpperCase()} Data Project` : "New Data Project",
      icon: selectedSource ? "🗄️" : "📊",
      businessType: "Data Analysis",
      role: "Data Analyst",
      status: "active" as const,
      lastUpdate: new Date(),
      isPinned: false,
      description: selectedSource ? `Project with ${selectedSource} connection` : "New project",
      needsETL: selectedSource ? true : false, // Set needsETL to true if database source is selected
      ontologyBuilt: false,
    }

    // Add to all projects
    setAllProjects([...allProjects, newProject])
    
    // Enter the project
    enterProject(newProject)
    
    // Close modal
    onClose()
    
    // Navigate to dashboard
    router.push("/dashboard")
  }

  if (!isOpen) return null

  return (
    <>
      <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-[100]" onClick={onClose} />

      <div className="fixed inset-x-4 inset-y-4 md:inset-auto md:left-1/2 md:top-1/2 md:-translate-x-1/2 md:-translate-y-1/2 md:w-[90vw] md:max-w-[1200px] md:max-h-[90vh] bg-white rounded-xl shadow-2xl z-[101] flex flex-col overflow-hidden">
        <div className="flex items-center justify-between px-6 py-5 border-b border-[#E2E8F0] shrink-0">
          <div>
            <h2 className="text-xl font-semibold text-[#1A202C]">Create New Project</h2>
            <p className="mt-1 text-sm text-[#6B7280]">Import your data or connect to a data source</p>
          </div>
          <button onClick={onClose} className="p-2 rounded-lg hover:bg-[#F8F9FA] transition-all">
            <X className="w-5 h-5 text-[#6B7280]" />
          </button>
        </div>

        <div className="flex-1 flex overflow-hidden">
          <div className="flex-1 p-6 bg-[#F8F9FB] overflow-y-auto">
            <div className="mb-4">
              <h3 className="text-base font-semibold text-[#2C3E50] mb-1">Upload Files</h3>
              <p className="text-sm text-[#6B7280]">Drag and drop your files or click to browse</p>
            </div>

            <div
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              className={`relative mb-4 rounded-xl transition-all duration-300 ${
                isDragging ? "bg-[#5A95A8]/10 shadow-lg" : "bg-white shadow-md hover:shadow-lg"
              }`}
            >
              <input
                type="file"
                multiple
                onChange={handleFileSelect}
                className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                accept=".docx,.doc,.pptx,.ppt,.pdf,.csv,.xlsx,.xls"
              />
              <div className="p-10 text-center">
                <Upload
                  className={`w-10 h-10 mx-auto mb-3 transition-colors ${isDragging ? "text-[#5A95A8]" : "text-[#9CA3AF]"}`}
                />
                <p className="font-medium text-slate-700 mb-1">
                  {isDragging ? "Drop files here" : "Drop files here or click to upload"}
                </p>
                <p className="text-xs text-slate-500">Maximum file size: 500MB</p>
              </div>
            </div>

            {uploadedFiles.length > 0 && (
              <div className="mb-4">
                <h4 className="text-sm font-semibold text-[#4A5568] mb-3">Uploaded Files ({uploadedFiles.length})</h4>
                <div className="space-y-2">
                  {uploadedFiles.map((file, idx) => (
                    <div key={idx} className="flex items-center gap-3 p-3 bg-white rounded-lg shadow-sm">
                      <FileText className="w-4 h-4 text-[#5A95A8]" />
                      <span className="flex-1 text-sm text-[#2D3748] font-medium truncate">{file.name}</span>
                      <span className="text-xs text-[#6B7280] font-mono">
                        {(file.size / 1024 / 1024).toFixed(2)} MB
                      </span>
                      <button
                        onClick={() => setUploadedFiles((prev) => prev.filter((_, i) => i !== idx))}
                        className="text-[#9CA3AF] hover:text-[#EF4444] transition-colors"
                      >
                        <X className="w-4 h-4" />
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div>
              <h4 className="text-sm font-semibold text-[#4A5568] mb-3">Supported Formats</h4>
              <div className="grid grid-cols-2 gap-2">
                {SUPPORTED_FORMATS.map((format) => (
                  <div key={format.ext} className={`flex items-center gap-2 px-3 py-2 rounded-lg ${format.color}`}>
                    <span className="font-mono text-xs font-semibold">{format.ext}</span>
                    <span className="text-xs">{format.desc}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="flex-1 p-6 bg-[#F5F6F7] overflow-y-auto">
            <div className="mb-4">
              <h3 className="text-base font-semibold text-[#2C3E50] mb-1">Connect Data Source</h3>
              <p className="text-sm text-[#6B7280]">Connect to your database</p>
            </div>

            <div className="grid grid-cols-2 gap-4">
              {DATA_SOURCES.map((source) => (
                <button
                  key={source.id}
                  onClick={() => handleConnectSource(source.id)}
                  className={`p-4 rounded-xl bg-white transition-all duration-300 text-left group ${
                    selectedSource === source.id
                      ? "shadow-lg ring-2 ring-[#5A95A8]"
                      : "shadow-sm hover:shadow-md hover:-translate-y-px"
                  }`}
                >
                  <div className="flex items-start gap-3">
                    <div className="w-8 h-8 rounded-lg bg-[#5A95A8]/10 flex items-center justify-center">
                      <div className="w-4 h-4 rounded bg-[#5A95A8]" />
                    </div>
                    <div>
                      <h4 className="font-semibold text-slate-800">{source.name}</h4>
                      <p className="text-xs text-slate-500 mt-0.5">{source.desc}</p>
                    </div>
                  </div>
                </button>
              ))}
            </div>

            <div className="mt-6 p-4 bg-[#5A95A8]/10 rounded-xl">
              <div className="flex gap-3">
                <AlertCircle className="w-5 h-5 text-[#5A95A8] shrink-0 mt-0.5" />
                <div className="text-sm text-slate-700">
                  <p className="font-semibold mb-1">Pro tip</p>
                  <p>
                    You can connect multiple data sources to a single project. Mix and match files with live database
                    connections.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="px-6 py-4 border-t border-[#E2E8F0] flex items-center justify-between bg-white shrink-0">
          <p className="text-sm text-[#6B7280]">
            {uploadedFiles.length > 0 ? `${uploadedFiles.length} file(s) selected` : "No files selected"}
          </p>
          <div className="flex gap-3">
            <button
              onClick={onClose}
              className="px-6 py-2.5 text-sm font-medium text-[#6B7280] hover:bg-[#F8F9FA] rounded-lg transition-all"
            >
              Cancel
            </button>
            <button
              onClick={handleCreateProject}
              disabled={uploadedFiles.length === 0 && !selectedSource}
              className="px-6 py-2.5 text-sm font-medium text-white bg-[#5A95A8] hover:bg-[#7AB8CC] rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed hover:shadow-lg hover:-translate-y-px"
            >
              Create Project
            </button>
          </div>
        </div>
      </div>
    </>
  )
}
