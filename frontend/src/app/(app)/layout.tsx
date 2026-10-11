"use client"

import { useEffect } from "react"
import { useRouter, usePathname } from "next/navigation"
import { useAuth, useAuthLoading } from "@/lib/auth-context"

// Pages that are publicly accessible (no auth required).
const PUBLIC_PATHS = ["/login", "/signup", "/forgot-password", "/reset-password"]
const ROOT_PATH = "/"

export default function AppLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const router = useRouter()
  const pathname = usePathname()
  const { user } = useAuth()
  const loading = useAuthLoading()

  useEffect(() => {
    // Wait for the initial auth check to finish, then gate.
    if (loading) return

    const isPublic = PUBLIC_PATHS.some((p) => pathname.startsWith(p)) || pathname === ROOT_PATH

    if (!isPublic && !user) {
      router.push("/login")
    }
  }, [loading, user, pathname, router])

  // Show nothing (or a spinner) until auth is resolved on protected pages.
  if (loading && !PUBLIC_PATHS.some((p) => pathname.startsWith(p)) && pathname !== ROOT_PATH) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <svg className="animate-spin w-8 h-8 text-brand-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <circle cx="12" cy="12" r="10" strokeOpacity="0.25" />
          <path d="M12 2a10 10 0 0 1 10 10" strokeLinecap="round" />
        </svg>
      </div>
    )
  }

  return <>{children}</>
}
