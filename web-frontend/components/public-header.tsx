"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { Button } from "@/components/ui/button"
import { AuthModal } from "@/components/auth-modal"
import { Menu, X, CreditCard, LogOut } from "lucide-react"
import { useAuth } from "@/lib/auth-context"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"

export function PublicHeader() {
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const router = useRouter()
  const { user, logout } = useAuth()

  return (
    <>
      <nav className="fixed top-0 left-0 right-0 z-[100] h-16 bg-white border-b border-[#E2E8F0] shadow-sm">
        <div className="mx-auto flex h-full max-w-[1400px] items-center justify-between px-6">
          {/* Logo */}
          <div className="flex items-center gap-3 cursor-pointer" onClick={() => router.push("/")}>
            <svg width="32" height="32" viewBox="0 0 32 32" fill="none">
              <rect width="32" height="32" rx="8" fill="#5A95A8" />
              <path d="M16 8L24 16L16 24L8 16L16 8Z" fill="white" opacity="0.9" />
              <circle cx="16" cy="16" r="3" fill="white" />
            </svg>
            <span className="text-lg font-bold tracking-tight text-[#1A202C]">Trantor</span>
          </div>

          {/* Desktop Actions */}
          <div className="hidden items-center gap-2 md:flex">
            {user ? (
              // 登录后的状态 - 类似 DashboardHeader
              <>
                {/* 新用户提示 */}
                {!user.hasProjects && (
                  <div className="mr-3 px-3 py-1.5 bg-green-50 border border-green-200 rounded-lg">
                    <span className="text-sm text-green-700 font-medium">
                      🎉 Welcome! Start by creating your first project
                    </span>
                  </div>
                )}
                
                {/* 用户信息 */}
                <div className="flex items-center gap-3">
                  <div className="hidden sm:flex items-center gap-2.5 text-sm font-medium border border-[#E5E7EB] rounded-full px-4 py-2 bg-white shadow-sm">
                    <CreditCard className="w-4 h-4 text-[#10B981]"/>
                    <span className="text-[#2D3748]">Free Plan</span>
                    <div className="w-px h-4 bg-[#E5E7EB]"></div>
                    <span className="text-[#4A5568]">100 Credits</span>
                  </div>

                  {/* 进入 Dashboard 按钮（如果有项目） */}
                  {user.hasProjects && (
                    <Button
                      onClick={() => router.push('/dashboard')}
                      className="bg-[#5A95A8] text-white hover:bg-[#7AB8CC]"
                    >
                      Go to Dashboard
                    </Button>
                  )}
                  
                  {/* 创建项目按钮（如果没有项目） */}
                  {!user.hasProjects && (
                    <Button
                      onClick={() => router.push('/dashboard')}
                      className="bg-[#5A95A8] text-white hover:bg-[#7AB8CC]"
                    >
                      Create First Project
                    </Button>
                  )}

                  {/* 用户头像 */}
                  <div className="flex items-center gap-2">
                    <div className="flex h-9 w-9 items-center justify-center rounded-full bg-white border border-[#E5E7EB] shadow-sm">
                      <Avatar className="h-8 w-8">
                        <AvatarImage src={user.image} alt={user.name} />
                        <AvatarFallback className="bg-slate-200 text-slate-500 font-semibold">
                          {user.name?.[0]?.toUpperCase() || user.email?.[0]?.toUpperCase()}
                        </AvatarFallback>
                      </Avatar>
                    </div>
                    
                    {/* 登出按钮 */}
                    <Button 
                      variant="ghost" 
                      size="icon" 
                      onClick={() => { logout(); router.push('/') }} 
                      className="h-9 w-9 rounded-full bg-white border border-[#E5E7EB] shadow-sm text-[#6B7280] hover:bg-[#F8F9FA] hover:text-[#2D3748]"
                    >
                      <LogOut className="h-4 w-4"/>
                    </Button>
                  </div>
                </div>
              </>
            ) : (
              // 未登录的状态
              <>
                <Button
                  variant="ghost"
                  onClick={() => router.push("/pricing")}
                  className="text-[#4A5568] hover:text-[#2D3748] hover:bg-[#F8F9FA]"
                >
                  Pricing
                </Button>
                <Button
                  variant="ghost"
                  onClick={() => setIsModalOpen(true)}
                  className="text-[#4A5568] hover:text-[#2D3748] hover:bg-[#F8F9FA]"
                >
                  Sign In
                </Button>
                <div className="h-4 w-px bg-slate-200 mx-2"></div>
                <Button
                  onClick={() => setIsModalOpen(true)}
                  className="bg-[#5A95A8] text-white hover:bg-[#7AB8CC] shadow-lg transition-all hover:shadow-xl"
                >
                  Get Started
                </Button>
              </>
            )}
          </div>

          {/* Mobile Menu Button */}
          <button className="p-2 text-[#4A5568] md:hidden" onClick={() => setMobileMenuOpen(!mobileMenuOpen)}>
            {mobileMenuOpen ? <X size={24} /> : <Menu size={24} />}
          </button>
        </div>

        {/* Mobile Menu */}
        {mobileMenuOpen && (
          <div className="absolute left-0 right-0 top-16 bg-white border-b border-[#E2E8F0] p-4 shadow-lg md:hidden">
            <div className="flex flex-col gap-2">
              {user ? (
                // 登录后的移动端菜单
                <>
                  <div className="py-2 px-3 bg-gray-50 rounded-lg text-sm">
                    <div className="font-medium text-[#2D3748]">{user.name || user.email}</div>
                    <div className="text-xs text-[#6B7280] mt-1">Free Plan • 100 Credits</div>
                  </div>
                  {user.hasProjects ? (
                    <Button
                      onClick={() => router.push('/dashboard')}
                      className="w-full bg-[#5A95A8] text-white hover:bg-[#7AB8CC]"
                    >
                      Go to Dashboard
                    </Button>
                  ) : (
                    <Button
                      onClick={() => router.push('/dashboard')}
                      className="w-full bg-[#5A95A8] text-white hover:bg-[#7AB8CC]"
                    >
                      Create First Project
                    </Button>
                  )}
                  <Button
                    variant="ghost"
                    onClick={() => { logout(); router.push('/'); setMobileMenuOpen(false); }}
                    className="w-full justify-start text-[#4A5568] hover:text-[#2D3748] hover:bg-[#F8F9FA]"
                  >
                    Sign Out
                  </Button>
                </>
              ) : (
                // 未登录的移动端菜单
                <>
                  <Button
                    variant="ghost"
                    onClick={() => { router.push("/pricing"); setMobileMenuOpen(false); }}
                    className="w-full justify-start text-[#4A5568] hover:text-[#2D3748] hover:bg-[#F8F9FA]"
                  >
                    Pricing
                  </Button>
                  <Button
                    variant="ghost"
                    onClick={() => { setIsModalOpen(true); setMobileMenuOpen(false); }}
                    className="w-full justify-start text-[#4A5568] hover:text-[#2D3748] hover:bg-[#F8F9FA]"
                  >
                    Sign In
                  </Button>
                  <Button
                    onClick={() => { setIsModalOpen(true); setMobileMenuOpen(false); }}
                    className="w-full bg-[#5A95A8] text-white hover:bg-[#7AB8CC] shadow-lg transition-all hover:shadow-xl"
                  >
                    Get Started
                  </Button>
                </>
              )}
            </div>
          </div>
        )}
      </nav>

      <AuthModal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)} />
    </>
  )
}
