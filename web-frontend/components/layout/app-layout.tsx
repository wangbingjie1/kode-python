"use client"

import { useState, createContext, useContext } from "react"
import { LeftSidebar } from "./left-sidebar"

// 创建 Context 共享侧边栏状态
const SidebarContext = createContext<{ isSidebarCollapsed: boolean }>({ 
  isSidebarCollapsed: false 
})

// 导出 hook 供其他组件使用
export const useSidebar = () => useContext(SidebarContext)

export function AppLayout({ children }: { children: React.ReactNode }) {
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false)

  return (
    <SidebarContext.Provider value={{ isSidebarCollapsed }}>
      <div className="min-h-screen bg-[#F8F9FB]">
        {/* 侧边栏 */}
        <LeftSidebar 
          isCollapsed={isSidebarCollapsed} 
          onToggle={() => setIsSidebarCollapsed(!isSidebarCollapsed)} 
        />
        
        {/* 主内容区 - 只处理左边距，不处理上边距 */}
        <div className={`transition-all duration-300 ${
          isSidebarCollapsed ? "pl-[72px]" : "pl-64"
        }`}>
          {children}
        </div>
      </div>
    </SidebarContext.Provider>
  )
}
