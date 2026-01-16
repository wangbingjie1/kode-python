"use client"

import { useEffect } from "react"
import { useRouter } from "next/navigation"
import { useAuth } from "@/lib/auth-context"
import { Loader2 } from "lucide-react"

interface AuthGuardProps {
  children: React.ReactNode
}

/**
 * 认证保护组件
 *
 * 包裹需要登录才能访问的页面/组件
 * 未登录时重定向到首页
 */
export function AuthGuard({ children }: AuthGuardProps) {
  const { user, isLoading } = useAuth()
  const router = useRouter()

  useEffect(() => {
    // 加载完成后，如果未登录则重定向
    if (!isLoading && !user) {
      router.push("/")
    }
  }, [user, isLoading, router])

  // 加载中显示 loading
  if (isLoading) {
    return (
      <div className="flex h-screen w-full items-center justify-center bg-background">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
          <p className="text-sm text-muted-foreground">Loading...</p>
        </div>
      </div>
    )
  }

  // 未登录显示空白（正在重定向）
  if (!user) {
    return null
  }

  // 已登录显示内容
  return <>{children}</>
}
