"use client";

// Auth context & React hooks — Sprint 1.
//
// Client-side auth state: keeps track of who is logged in by calling getMe()
// on mount and after any mutation (login/signup/refresh/logout). Tokens live
// in HTTP-only cookies set by the backend, so the provider just mirrors the
// backend's view of the current user into React state.
//
// IMPORTANT: this file is .tsx because it contains JSX (<AuthContext.Provider>).
// The pure API client lives in sibling auth.ts (no JSX, stays .ts).

import { useState, useEffect, useCallback, createContext, useContext } from "react"
import {
  getMe,
  login as apiLogin,
  signup as apiSignup,
  logout as apiLogout,
  refreshTokens as apiRefresh,
} from "./auth"
import { setToken } from "./token-store"

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface AuthUser {
  id: string
  email: string
  full_name: string | null
  role: string
  subscription: {
    plan_tier: string
    status: string
    trial_ends_at: string | null
    credits_remaining: number
  } | null
  created_at: string
}

interface AuthCtxValue {
  user: AuthUser | null
  loading: boolean
  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string, full_name?: string) => Promise<void>
  logout: () => Promise<void>
  refresh: () => Promise<void>
}

// ---------------------------------------------------------------------------
// Context
// ---------------------------------------------------------------------------

const AuthContext = createContext<AuthCtxValue | null>(null)

// ---------------------------------------------------------------------------
// Provider
// ---------------------------------------------------------------------------

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null)
  const [loading, setLoading] = useState(true)

  const refresh = useCallback(async () => {
    try {
      const me = await getMe()
      setUser(me as AuthUser)
    } catch {
      setUser(null)
    } finally {
      setLoading(false)
    }
  }, [])

  // Initial auth check on mount. Re-run when storage changes (backend sets
  // cookies on login/signup/refresh — a storage event signals a token change).
  useEffect(() => {
    refresh()
    const handler = () => refresh()
    window.addEventListener("storage", handler)
    return () => window.removeEventListener("storage", handler)
  }, [refresh])

  const login = useCallback(
    async (email: string, password: string) => {
      await apiLogin({ email, password })
      await refresh()
    },
    [refresh],
  )

  const register = useCallback(
    async (email: string, password: string, full_name?: string) => {
      await apiSignup({ email, password, full_name })
      await refresh()
    },
    [refresh],
  )

  const logout = useCallback(async () => {
    await apiLogout()
    setUser(null)
  }, [])

  return (
    <AuthContext.Provider
      value={{ user, loading, login, register, logout, refresh }}
    >
      {children}
    </AuthContext.Provider>
  )
}

// ---------------------------------------------------------------------------
// Hooks
// ---------------------------------------------------------------------------

export function useAuth(): AuthCtxValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>")
  return ctx
}

// Returns true while the initial auth check is in flight.
export function useAuthLoading(): boolean {
  const { loading } = useAuth()
  return loading
}
