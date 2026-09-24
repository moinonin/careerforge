// Auth API client — Sprint 1.
//
// Talks to the backend auth endpoints. Tokens are stored client-side in
// token-store.ts and sent as the Authorization: Bearer header on every
// authenticated request.
//
// ---------------------------------------------------------------------------
// Base URL — the Next.js config rewrites /api/* to the backend on the
// same host, so we can point the client at "/api" relative to the app origin.
// ---------------------------------------------------------------------------

import { getToken, setToken } from "./token-store"

const API_BASE = "/api/v1"

interface SignupBody {
  email: string
  password: string
  full_name?: string
}

interface LoginBody {
  email: string
  password: string
}

interface ForgotPasswordBody {
  email: string
}

interface ResetPasswordBody {
  token: string
  new_password: string
}

// ---------------------------------------------------------------------------
// Low-level fetcher — every request sends the Bearer token and expects JSON.
// ---------------------------------------------------------------------------

async function _request<T>(
  path: string,
  body?: unknown,
  method?: string,
  extraHeaders?: Record<string, string>,
): Promise<T> {
  const opts: RequestInit = {
    method: method ?? "POST",
    headers: {
      "Accept": "application/json",
      "Content-Type": "application/json",
      ...extraHeaders,
      ...(getToken() ? { Authorization: `Bearer ${getToken()}` } : {}),
    },
    credentials: "include",
    body: body ? JSON.stringify(body) : undefined,
  }

  const res = await fetch(`${API_BASE}${path}`, opts)

  if (res.status === 204) {
    return undefined as T
  }

  const data = (await res.json()) as {
    success?: boolean
    error?: string
    detail?: string
    data?: T
  }

  if (!res.ok) {
    const msg = data.error ?? data.detail ?? `HTTP ${res.status}`
    throw new Error(msg)
  }

  if (data.success && data.data) {
    return data.data as T
  }
  return data as T
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

export async function signup(
  body: SignupBody,
): Promise<{
  access_token: string
  refresh_token: string
  token_type: string
  email: string
  expires_in: number
}> {
  const result = await _request<{
    access_token: string
    refresh_token: string
    token_type: string
    email: string
    expires_in: number
  }>("/auth/signup", body, "POST")
  setToken(result.access_token)
  return result
}

export async function login(
  body: LoginBody,
): Promise<{
  access_token: string
  refresh_token: string
  token_type: string
  email: string
  expires_in: number
}> {
  const result = await _request<{
    access_token: string
    refresh_token: string
    token_type: string
    email: string
    expires_in: number
  }>("/auth/login", body, "POST")
  setToken(result.access_token)
  return result
}

export async function refreshTokens(): Promise<{
  access_token: string
  refresh_token: string
  token_type: string
  email: string
  expires_in: number
}> {
  const result = await _request<{
    access_token: string
    refresh_token: string
    token_type: string
    email: string
    expires_in: number
  }>("/auth/refresh", undefined, "POST")
  setToken(result.access_token)
  return result
}

export async function logout(): Promise<void> {
  const token = getToken()
  await fetch(`${API_BASE}/auth/logout`, {
    method: "POST",
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    credentials: "include",
  })
  setToken(null)
}

export async function forgotPassword(
  body: ForgotPasswordBody,
): Promise<{ message: string }> {
  return _request<{ message: string }>("/auth/forgot-password", body, "POST")
}

export async function resetPassword(
  body: ResetPasswordBody,
): Promise<{ message: string; email: string }> {
  return _request<{ message: string; email: string }>(
    "/auth/reset-password",
    body,
    "POST",
  )
}

// ---------------------------------------------------------------------------
// Authenticated resource requests — Bearer token sent automatically.
// ---------------------------------------------------------------------------

export async function getMe(): Promise<{
  id: string
  email: string
  full_name: string | null
  role: string
  created_at: string
  subscription: {
    plan_tier: string
    status: string
    trial_ends_at: string | null
    credits_remaining: number
  } | null
}> {
  return _request<any>("/users/me", undefined, "GET")
}

export async function updateMe(
  body: { full_name?: string; current_password?: string; new_password?: string },
): Promise<{
  id: string
  email: string
  full_name: string | null
  role: string
  created_at: string
  subscription: any
}> {
  return _request<any>("/users/me", body, "PUT")
}
