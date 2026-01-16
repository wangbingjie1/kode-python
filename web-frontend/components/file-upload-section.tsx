"use client"

import type React from "react"

import { useState, useCallback, useRef } from "react"
import { CloudUpload, CheckCircle2, AlertCircle } from "lucide-react"
import { FormatCard } from "./format-card"
import type { FormatType, PreviewData } from "@/lib/types"
import { FileSpreadsheet, FileText, Table, Braces, ImageIcon, Database, FileCode, Archive } from "lucide-react"
import { dataSourceApi, getErrorMessage } from "@/lib/api"

const formats: Array<{
  type: FormatType
  name: string
  icon: React.ComponentType<{ className?: string }>
  color: string
  accept: string
}> = [
  { type: "csv", name: "CSV", icon: Table, color: "#A8D5BA", accept: ".csv" },
  { type: "pdf", name: "PDF", icon: FileText, color: "#F4E4C1", accept: ".pdf" },
  { type: "xlsx", name: "Excel", icon: FileSpreadsheet, color: "#A8D5BA", accept: ".xlsx,.xls" },
  { type: "json", name: "JSON", icon: Braces, color: "#C9B6E4", accept: ".json" },
  { type: "image", name: "IMAGE", icon: ImageIcon, color: "#F5CAC3", accept: ".jpg,.jpeg,.png" },
  { type: "parquet", name: "PARQUET", icon: Database, color: "#5A95A8", accept: ".parquet" },
  { type: "sql", name: "SQL", icon: FileCode, color: "#C9B6E4", accept: ".sql" },
  { type: "zip", name: "ZIP", icon: Archive, color: "#9CA3AF", accept: ".zip" },
]

interface UploadProgress {
  name: string
  size: number
  progress: number
  complete: boolean
  error?: string
}

interface FileUploadSectionProps {
  onShowPreview: (data: PreviewData, position: { x: number; y: number }) => void
  onHidePreview: () => void
  projectId?: string  // 项目 ID，用于关联上传的文件
}

export function FileUploadSection({ onShowPreview, onHidePreview, projectId }: FileUploadSectionProps) {
  const [isDragging, setIsDragging] = useState(false)
  const [uploadProgress, setUploadProgress] = useState<UploadProgress[]>([])
  const fileInputRef = useRef<HTMLInputElement>(null)
  const uploadAreaRef = useRef<HTMLDivElement>(null)

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }, [])

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    // Only remove if leaving the upload area entirely
    if (uploadAreaRef.current && !uploadAreaRef.current.contains(e.relatedTarget as Node)) {
      setIsDragging(false)
    }
  }, [])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    const files = Array.from(e.dataTransfer.files)
    handleFiles(files)
  }, [])

  const handleFiles = (files: File[]) => {
    console.log("[FileUpload] Files received:", files)

    files.forEach((file, index) => {
      const newProgress: UploadProgress = {
        name: file.name,
        size: file.size,
        progress: 0,
        complete: false,
      }

      setUploadProgress((prev) => [...prev, newProgress])
      uploadFile(file, uploadProgress.length + index)
    })
  }

  const uploadFile = async (file: File, index: number) => {
    // 如果没有 projectId，暂时使用默认值或提示用户
    const targetProjectId = projectId || "default"

    try {
      const response = await dataSourceApi.uploadFile(
        file,
        targetProjectId,
        (progress) => {
          // 更新进度条
          setUploadProgress((prev) => {
            const updated = [...prev]
            if (updated[index]) {
              updated[index].progress = progress
            }
            return updated
          })
        }
      )

      // 上传完成
      console.log("[FileUpload] Upload success:", response)
      setUploadProgress((prev) => {
        const updated = [...prev]
        if (updated[index]) {
          updated[index].progress = 100
          updated[index].complete = true
        }
        return updated
      })
    } catch (error) {
      // 上传失败
      console.error("[FileUpload] Upload failed:", error)
      const errorMessage = getErrorMessage(error)
      setUploadProgress((prev) => {
        const updated = [...prev]
        if (updated[index]) {
          updated[index].error = errorMessage
        }
        return updated
      })
    }
  }

  const handleFormatClick = (accept: string) => {
    const input = document.createElement("input")
    input.type = "file"
    input.multiple = true
    input.accept = accept

    input.onchange = (e) => {
      const target = e.target as HTMLInputElement
      if (target.files && target.files.length > 0) {
        handleFiles(Array.from(target.files))
      }
    }

    input.click()
  }

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return "0 Bytes"
    const k = 1024
    const sizes = ["Bytes", "KB", "MB", "GB"]
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + " " + sizes[i]
  }

  return (
    <section className="animate-slide-in-left flex min-h-[600px] flex-col rounded-xl bg-white p-8 shadow-sm">
      <h2 className="mb-2 text-xl font-semibold text-[#2C3E50]">Upload Your Data</h2>
      <p className="mb-6 text-sm text-[#6B7280]">Multiple formats supported, drag & drop to start analyzing</p>

      <div
        ref={uploadAreaRef}
        className={`flex flex-1 flex-col rounded-xl border-2 border-dashed bg-white p-8 transition-all duration-300 ${
          isDragging
            ? "border-[#5A95A8] bg-[#5A95A8]/5 shadow-[0_0_0_4px_rgba(90,149,168,0.1),0_4px_16px_rgba(0,0,0,0.1)]"
            : "border-[#E5E7EB]"
        }`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        {/* Upload Hint */}
        <div
          className={`mb-8 text-center transition-opacity duration-300 ${isDragging ? "opacity-30" : "opacity-100"}`}
        >
          <CloudUpload
            className={`mx-auto mb-3 h-12 w-12 text-[#5A95A8] transition-all duration-300 ${
              isDragging ? "scale-115" : ""
            }`}
          />
          <div className="mb-1.5 text-[15px] font-medium text-[#2D3748]">
            Drag files here, or click any format below
          </div>
          <div className="text-[13px] text-[#9CA3AF]">Supports multiple files, max 200MB per file</div>
        </div>

        <div className="grid grid-cols-4 gap-3">
          {formats.map((format, index) => (
            <FormatCard
              key={format.type}
              format={format}
              index={index}
              onShowPreview={onShowPreview}
              onHidePreview={onHidePreview}
              onCardClick={() => handleFormatClick(format.accept)}
            />
          ))}
        </div>

        {uploadProgress.length > 0 && (
          <div className="mt-6 flex flex-col gap-3">
            {uploadProgress.map((progress, index) => (
              <div
                key={index}
                className={`rounded-lg p-3 transition-all duration-300 ${
                  progress.complete
                    ? "border border-[#A8D5BA] bg-[#A8D5BA]/10"
                    : progress.error
                      ? "border border-[#F87171] bg-[#FEF2F2]"
                      : "bg-[#F8F9FA]"
                }`}
              >
                {progress.error ? (
                  <div className="flex items-center gap-2 text-[14px] text-[#DC2626]">
                    <AlertCircle className="h-5 w-5 flex-shrink-0 text-[#F87171]" />
                    <span className="flex-1 overflow-hidden text-ellipsis whitespace-nowrap">{progress.name}</span>
                    <span className="ml-2 text-[12px]">{progress.error}</span>
                  </div>
                ) : progress.complete ? (
                  <div className="flex items-center gap-2 text-[14px] text-[#2D3748]">
                    <CheckCircle2 className="h-5 w-5 text-[#A8D5BA]" />
                    <span className="flex-1 overflow-hidden text-ellipsis whitespace-nowrap">{progress.name}</span>
                    <span className="text-[12px] text-[#6B7280]">uploaded successfully</span>
                  </div>
                ) : (
                  <>
                    <div className="mb-2 flex items-center justify-between">
                      <span className="flex-1 overflow-hidden text-ellipsis whitespace-nowrap text-[14px] font-medium text-[#2D3748]">
                        {progress.name}
                      </span>
                      <span className="ml-3 text-[12px] text-[#6B7280]">{formatFileSize(progress.size)}</span>
                    </div>
                    <div className="mb-1 h-1 overflow-hidden rounded-full bg-[#E5E7EB]">
                      <div
                        className="h-full rounded-full bg-[#5A95A8] transition-all duration-300"
                        style={{ width: `${progress.progress}%` }}
                      />
                    </div>
                    <div className="text-right text-[12px] text-[#6B7280]">{Math.round(progress.progress)}%</div>
                  </>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </section>
  )
}
