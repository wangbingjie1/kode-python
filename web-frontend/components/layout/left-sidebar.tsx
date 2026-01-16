// 文件路径: components/layout/left-sidebar.tsx (最终优化版)
"use client"

import Link from "next/link"
import { useState } from "react"
import { Plus, Database, Folder, PanelLeftClose, PanelRightClose } from "lucide-react"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { NewProjectModal } from "@/components/modals/new-project-modal"

interface LeftSidebarProps {
  isCollapsed: boolean
  onToggle: () => void
}

export function LeftSidebar({ isCollapsed, onToggle }: LeftSidebarProps) {
  const [projects] = useState([
    { id: "proj_1", name: "Sales Analysis Q2" },
    { id: "proj_2", name: "Customer Churn Prediction" },
    { id: "proj_3", name: "Website Traffic Insights" },
    { id: "proj_4", name: "Marketing Campaign ROI" },
  ])
  const [activeProjectId, setActiveProjectId] = useState("proj_2")
  const [showNewProjectModal, setShowNewProjectModal] = useState(false)

  const ProjectItem = ({ id, name }: { id: string; name: string }) => {
    const getInitials = (name: string) => {
      return name
        .split(" ")
        .map((n) => n[0])
        .join("")
        .substring(0, 2)
        .toUpperCase()
    }

    return (
      <Link
        href="/dashboard"
        className={`w-full h-9 flex items-center rounded-md transition-colors text-sm overflow-hidden ${
          isCollapsed ? "justify-center px-2" : "px-4 gap-3"
        } ${
          activeProjectId === id
            ? "bg-slate-100 font-semibold text-slate-900"
            : "text-slate-600 hover:bg-slate-100 hover:text-slate-800"
        }`}
        onClick={() => setActiveProjectId(id)}
      >
        {isCollapsed ? (
          <div className="flex items-center justify-center text-xs font-bold text-slate-500 flex-shrink-0">
            {getInitials(name)}
          </div>
        ) : (
          <Folder className="h-4 w-4 flex-shrink-0 text-slate-500" />
        )}

        {!isCollapsed && <span className="truncate">{name}</span>}
      </Link>
    )
  }

  return (
    <>
      <aside
        className={`fixed left-0 top-0 z-40 flex h-full flex-col bg-white transition-all duration-300 border-r border-slate-200 ${
          isCollapsed ? "w-[72px]" : "w-64"
        }`}
      >
        {/* 1. 顶部: Logo 和 展开/收起按钮 (交互重构) */}
        <div className={`flex h-16 shrink-0 items-center ${isCollapsed ? "justify-center" : "justify-between px-4"}`}>
          {/* --- 展开状态 --- */}
          {!isCollapsed && (
            <>
              <Link href="/dashboard" className="flex items-center gap-3">
                <div className="flex h-8 w-8 items-center justify-center shrink-0">
                  <svg width="32" height="32" viewBox="0 0 32 32" fill="none">
                    <rect width="32" height="32" rx="8" fill="#5A95A8" />
                  </svg>
                </div>
                <span className="text-lg font-bold tracking-tight text-slate-800">Trantor</span>
              </Link>
              <Button
                onClick={onToggle}
                variant="ghost"
                className="h-8 w-8 p-0 text-slate-500 hover:bg-slate-100 border-primary"
              >
                <PanelLeftClose size={18} />
              </Button>
            </>
          )}

          {/* --- 收起状态 (实现悬停重叠效果) --- */}
          {isCollapsed && (
            // 使用 group 来控制内部元素的 hover 状态
            <div className="group relative flex h-8 w-8 items-center justify-center">
              {/* 1. 默认显示的 LOGO，悬停在 group 上时隐藏 */}
              <Link href="/dashboard" className="block group-hover:hidden">
                <svg width="32" height="32" viewBox="0 0 32 32" fill="none">
                  <rect width="32" height="32" rx="8" fill="#5A95A8" />
                </svg>
              </Link>
              {/* 2. 默认隐藏的按钮，悬停在 group 上时显示，并覆盖在 LOGO 之上 */}
              <Button
                onClick={onToggle}
                variant="ghost"
                className="absolute inset-0 z-10 hidden h-full w-full items-center justify-center rounded-lg bg-slate-800 text-white group-hover:flex"
              >
                <PanelRightClose size={18} />
              </Button>
            </div>
          )}
        </div>

        {/* 主导航区 */}
        <div className="flex-grow flex flex-col gap-y-4 pt-4 overflow-y-hidden">
          <div className="px-3 space-y-1">
            <Button
              onClick={() => setShowNewProjectModal(true)}
              variant="ghost"
              className={`w-full h-10 flex gap-3 text-slate-600 hover:bg-slate-100 ${isCollapsed ? "justify-center px-2" : "justify-start px-4"}`}
            >
              <Plus className="h-5 w-5 shrink-0" />
              {!isCollapsed && <span className="font-medium">New Project</span>}
            </Button>
            <Button
              asChild
              variant="ghost"
              className={`w-full h-10 flex gap-3 text-slate-600 hover:bg-slate-100 ${isCollapsed ? "justify-center px-2" : "justify-start px-4"}`}
            >
              <Link href="/datasources">
                <Database className="h-5 w-5 shrink-0" />
                {!isCollapsed && <span className="font-medium">Data Sources</span>}
              </Link>
            </Button>
          </div>

          <div className="px-4">
            <hr className="border-slate-200" />
          </div>

          <div className="flex-grow flex flex-col px-3 space-y-2 overflow-y-hidden">
            {!isCollapsed && (
              <h3 className="px-1 mb-2 text-xs font-semibold text-slate-400 tracking-wider">PROJECTS</h3>
            )}
            <ScrollArea className="flex-1 -mr-3 pr-3">
              <div className="space-y-1">
                {projects.map((project) => (
                  <ProjectItem key={project.id} id={project.id} name={project.name} />
                ))}
              </div>
            </ScrollArea>
          </div>
        </div>
      </aside>

      {/* New Project Modal */}
      <NewProjectModal isOpen={showNewProjectModal} onClose={() => setShowNewProjectModal(false)} />
    </>
  )
}
