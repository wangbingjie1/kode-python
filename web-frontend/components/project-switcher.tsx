"use client"
import { useRouter, usePathname } from "next/navigation"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { useProjectStore } from "@/lib/project-store"
import { ChevronDown, Check, Home } from "lucide-react"
import { formatDistanceToNow } from "date-fns"

export function ProjectSwitcher() {
  const router = useRouter()
  const pathname = usePathname()
  const currentProject = useProjectStore((state) => state.currentProject)
  const recentProjects = useProjectStore((state) => state.recentProjects)
  const switchProject = useProjectStore((state) => state.switchProject)

  const handleSwitchProject = (projectId: string) => {
    const project = recentProjects.find((p) => p.id === projectId)
    if (!project || project.id === currentProject?.id) return

    // Get current view from pathname
    const pathParts = pathname.split("/")
    const currentView = pathParts[pathParts.length - 1] || "graph"

    // Switch project and navigate to same view
    switchProject(project)
    router.push(`/projects/${projectId}/${currentView}`)
  }

  const handleBackToProjects = () => {
    router.push("/projects")
  }

  if (!currentProject) return null

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" className="gap-2 text-base font-semibold">
          <span>{currentProject.icon}</span>
          <span>{currentProject.name}</span>
          <ChevronDown className="h-4 w-4 opacity-50" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start" className="w-[400px]">
        <div className="px-2 py-2 text-sm font-semibold text-muted-foreground">Switch to Another Project</div>
        <DropdownMenuSeparator />

        {/* Current Project */}
        <DropdownMenuItem className="flex items-start gap-3 py-3">
          <div className="flex items-center gap-3 flex-1">
            <span className="text-primary">●</span>
            <span className="text-xl">{currentProject.icon}</span>
            <div className="flex-1">
              <div className="font-medium">{currentProject.name}</div>
              <div className="text-xs text-muted-foreground">
                {formatDistanceToNow(currentProject.lastUpdate, { addSuffix: true })}
              </div>
            </div>
            <div className="flex items-center gap-1 text-xs text-primary">
              <Check className="h-3 w-3" />
              <span>Active</span>
            </div>
          </div>
        </DropdownMenuItem>

        <DropdownMenuSeparator />

        {/* Recent Projects */}
        {recentProjects
          .filter((p) => p.id !== currentProject.id)
          .map((project) => (
            <DropdownMenuItem
              key={project.id}
              className="flex items-start gap-3 py-3 cursor-pointer"
              onClick={() => handleSwitchProject(project.id)}
            >
              <span className="text-muted-foreground">○</span>
              <span className="text-xl">{project.icon}</span>
              <div className="flex-1">
                <div className="font-medium">{project.name}</div>
                <div className="text-xs text-muted-foreground">
                  {formatDistanceToNow(project.lastUpdate, { addSuffix: true })}
                </div>
              </div>
            </DropdownMenuItem>
          ))}

        <DropdownMenuSeparator />

        {/* Back to All Projects */}
        <DropdownMenuItem className="flex items-center gap-2 py-2 cursor-pointer" onClick={handleBackToProjects}>
          <Home className="h-4 w-4" />
          <span>Back to All Projects</span>
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
