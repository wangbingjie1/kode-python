"use client"

import { useState, useEffect } from "react"
import { X, Save, Database, Network } from "lucide-react"

interface QuickNoteModalProps {
  isOpen: boolean
  onClose: () => void
  onAddAsNode: (content: string, title: string) => void
  onIntegrateToGraph: (content: string, title: string) => void
  initialContent?: string
  initialTitle?: string
}

export function QuickNoteModal({
  isOpen,
  onClose,
  onAddAsNode,
  onIntegrateToGraph,
  initialContent = "",
  initialTitle = "",
}: QuickNoteModalProps) {
  const [content, setContent] = useState(initialContent)
  const [title, setTitle] = useState(initialTitle)

  useEffect(() => {
    if (isOpen) {
      const savedDraft = localStorage.getItem("quickNoteDraft")
      const savedTitle = localStorage.getItem("quickNoteTitle")
      if (savedDraft && !initialContent) {
        setContent(savedDraft)
      }
      if (savedTitle && !initialTitle) {
        setTitle(savedTitle)
      }
    }
  }, [isOpen, initialContent, initialTitle])

  const handleSaveDraft = () => {
    localStorage.setItem("quickNoteDraft", content)
    localStorage.setItem("quickNoteTitle", title)
    onClose()
  }

  const handleAddAsNode = () => {
    onAddAsNode(content, title || "Quick Note")
    localStorage.removeItem("quickNoteDraft")
    localStorage.removeItem("quickNoteTitle")
    setContent("")
    setTitle("")
    onClose()
  }

  const handleIntegrateToGraph = () => {
    onIntegrateToGraph(content, title || "Quick Note")
    localStorage.removeItem("quickNoteDraft")
    localStorage.removeItem("quickNoteTitle")
    setContent("")
    setTitle("")
    onClose()
  }

  const handleClose = () => {
    if (content.trim() && !window.confirm("Discard this note? All content will be lost.")) {
      return
    }
    setContent("")
    setTitle("")
    onClose()
  }

  if (!isOpen) return null

  return (
    <>
      <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-[100]" onClick={handleClose} />

      <div className="fixed inset-x-4 inset-y-4 md:inset-x-auto md:inset-y-auto md:left-1/2 md:top-1/2 md:-translate-x-1/2 md:-translate-y-1/2 md:w-[800px] md:h-[600px] bg-white rounded-2xl shadow-2xl z-[101] flex flex-col overflow-hidden">
        <button
          onClick={handleClose}
          className="absolute top-4 right-4 p-2 rounded-lg hover:bg-slate-100 transition-colors z-10"
        >
          <X className="w-5 h-5 text-slate-500" />
        </button>

        <div className="px-6 py-4 border-b border-slate-100 shrink-0">
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Note title (optional)"
            className="w-full text-xl font-semibold text-slate-800 placeholder-slate-400 bg-transparent outline-none"
          />
        </div>

        {/* Content Area */}
        <div className="flex-1 px-6 py-4 overflow-y-auto">
          <textarea
            value={content}
            onChange={(e) => setContent(e.target.value)}
            placeholder="Start typing your note here..."
            className="w-full h-full resize-none outline-none text-sm leading-relaxed text-slate-700 placeholder-slate-400 bg-transparent"
            autoFocus
          />
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-slate-200 bg-slate-50/70 shrink-0">
          <div className="flex items-center justify-end gap-3">
            <div className="mr-auto text-xs text-slate-500 font-mono">
              {content.length} chars • {content.split(/\s+/).filter(Boolean).length} words
            </div>

            <button
              onClick={handleSaveDraft}
              className="px-4 py-2 text-sm font-medium text-slate-700 bg-white border border-slate-300 hover:bg-slate-50 rounded-lg transition-colors flex items-center gap-2"
            >
              <Save className="w-4 h-4" />
              <span>Save Draft</span>
            </button>

            <button
              onClick={handleIntegrateToGraph}
              disabled={!content.trim()}
              className="px-4 py-2 text-sm font-medium text-white bg-indigo-500 hover:bg-indigo-600 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              <Network className="w-4 h-4" />
              <span>Integrate</span>
            </button>

            <button
              onClick={handleAddAsNode}
              disabled={!content.trim()}
              className="px-4 py-2 text-sm font-medium text-white bg-[#5A95A8] hover:bg-[#7AB8CC] rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              <Database className="w-4 h-4" />
              <span>Add as Node</span>
            </button>
          </div>
        </div>
      </div>
    </>
  )
}
