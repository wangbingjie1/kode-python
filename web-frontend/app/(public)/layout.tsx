import type React from "react"
import { PublicHeader } from "@/components/public-header"

export default function PublicLayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      <PublicHeader />
      <main className="pt-16">{children}</main>
    </>
  )
}
