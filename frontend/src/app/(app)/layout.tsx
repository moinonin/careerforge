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
        <div className="animate-spin rounded-full h-8 w-8 border-2 border-[var(--color-accent)] border-t-transparent" />
      </div>
    )
  }

  return <>{children}</>
}
