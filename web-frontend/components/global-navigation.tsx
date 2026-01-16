"use client"

import { usePathname, useRouter } from "next/navigation"
import { Button } from "@/components/ui/button"
import { ProjectSwitcher } from "@/components/project-switcher"
import { useProjectStore } from "@/lib/project-store"
import { Settings, User } from "lucide-react"

export function GlobalNavigation() {
  const pathname = usePathname()
  const router = useRouter()
  const currentProject = useProjectStore((state) => state.currentProject)

  // Check if we're inside a project (not on /projects or /projects/new)
  const isInsideProject =
    pathname.startsWith("/projects/") && pathname.split("/").length > 2 && !pathname.includes("/new")

  const handleBrandClick = () => {
    if (isInsideProject) {
      router.push("/projects")
    }
  }

  return (
    <nav className="border-b border-border bg-card">
      <div className="container max-w-7xl mx-auto px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            {/* Product Brand */}
            <button
              onClick={handleBrandClick}
              className={`text-xl font-bold flex items-center gap-2 ${
                isInsideProject ? "hover:text-primary cursor-pointer transition-colors" : "cursor-default"
              }`}
            >
              <span className="text-2xl">🎯</span>
              <span>DataInsight AI</span>
            </button>

            {/* Project Switcher - only show when inside a project */}
            {isInsideProject && currentProject && (
              <>
                <span className="text-muted-foreground">&gt;</span>
                <ProjectSwitcher />
              </>
            )}
          </div>

          {/* User Menu */}
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2 text-sm">
              <User className="h-4 w-4" />
              <span>Mike Zhang</span>
            </div>
            <Button variant="ghost" size="icon">
              <Settings className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </div>
    </nav>
  )
}
