"use client"

import { useState } from "react"
import { CaseGallerySection } from "./case-gallery-section"
import { CompositeInputSection } from "./composite-input-section"
import { TrustSection } from "./trust-section"
import { CTASection } from "./cta-section"
import { PageFooter } from "./page-footer"
import { AppWorkspace } from "./app-workspace"
import { NewProjectModal } from "@/components/modals/new-project-modal"

export function LandingPage() {
  const [uploadedFiles, setUploadedFiles] = useState<File[]>([])
  const [showWorkspace, setShowWorkspace] = useState(false)
  const [showNewProjectModal, setShowNewProjectModal] = useState(false)

  const handleFilesUploaded = (files: File[]) => {
    console.log("[v0] Files uploaded:", files)
    setUploadedFiles(files)
    setTimeout(() => {
      setShowWorkspace(true)
    }, 500)
  }

  const handleBackToLanding = () => {
    setShowWorkspace(false)
    setUploadedFiles([])
  }

  const handleOpenNewProjectModal = () => {
    setShowNewProjectModal(true)
  }

  if (showWorkspace) {
    return <AppWorkspace uploadedFiles={uploadedFiles} onBack={handleBackToLanding} />
  }

  return (
    <div className="min-h-screen bg-[#F8F9FB]">
      <header className="animate-fade-in-down px-10 pt-16 text-center pb-1">
        <h1 className="mb-5 text-balance leading-[1.1] tracking-tight">
          <span className="text-[72px] font-normal text-[#5A95A8] md:text-[72px] sm:text-[48px]">Trantor</span>
        </h1>
        <p className="mx-auto max-w-[640px] text-balance text-xl leading-relaxed tracking-[0.01em] text-[#6B7280]">
          Transform data into insights, let AI be your Chief Analyst
        </p>
      </header>

      <CaseGallerySection />

      <CompositeInputSection onFilesUploaded={handleFilesUploaded} onOpenNewProjectModal={handleOpenNewProjectModal} />

      <TrustSection />
      <CTASection />
      <PageFooter />

      <NewProjectModal isOpen={showNewProjectModal} onClose={() => setShowNewProjectModal(false)} />
    </div>
  )
}
