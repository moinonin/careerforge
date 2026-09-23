"use client"

import { useState, Suspense } from "react"
import { useRouter, useSearchParams } from "next/navigation"
import { resetPassword } from "@/lib/auth"


function ResetPasswordForm() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const token = searchParams.get("token") ?? ""
  const expired = searchParams.get("expired") === "true"

  const [new_password, setNewPassword] = useState("")
  const [confirm, setConfirm] = useState("")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")


  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError("")

    if (new_password.length < 8) {
      setError("Password must be at least 8 characters")
      return
    }
    if (new_password !== confirm) {
      setError("Passwords do not match")
      return
    }

    setLoading(true)
    try {
      await resetPassword({ token, new_password })
      router.push("/login?reset=success")
    } catch (err: unknown) {
      setError(
        err instanceof Error
          ? (err as any).detail ?? (err as any).message ?? err.message
          : "Failed to reset password",
      )
    } finally {
      setLoading(false)
    }
  }


  if (expired) {
    return (
      <div className="auth-card">
        <div className="auth-error-box">
          <h1 className="auth-title">Link expired</h1>
          <p className="auth-subtitle">
            This password reset link has expired. Request a new one below.
          </p>
          <a href="/forgot-password" className="auth-link-button">
            Request a new reset link
          </a>
        </div>
      </div>
    )
  }


  return (
    <form onSubmit={handleSubmit} className="auth-form" noValidate>
      <h1 className="auth-title">Choose a new password</h1>
      <p className="auth-subtitle">
        Enter a new password for your account.
      </p>

      <div className="auth-field">
        <label htmlFor="new-password" className="auth-label">
          New password
        </label>
        <input
          id="new-password"
          type="password"
          value={new_password}
          onChange={(e) => setNewPassword(e.target.value)}
          className="auth-input"
          placeholder="At least 8 characters"
          autoComplete="new-password"
          disabled={loading}
        />
      </div>

      <div className="auth-field">
        <label htmlFor="confirm-password" className="auth-label">
          Confirm new password
        </label>
        <input
          id="confirm-password"
          type="password"
          value={confirm}
          onChange={(e) => setConfirm(e.target.value)}
          className="auth-input"
          placeholder="Repeat your new password"
          autoComplete="new-password"
          disabled={loading}
        />
      </div>

      {error && <p className="auth-error">{error}</p>}

      <button
        type="submit"
        className="auth-submit"
        disabled={loading || (!new_password || !confirm)}
      >
        {loading ? (
          <span className="auth-spinner" aria-hidden="true" />
        ) : (
          "Reset password"
        )}
      </button>

      <p className="auth-switch">
        Remember your password?{" "}
        <a href="/login" className="auth-link">
          Log in
        </a>
      </p>
    </form>
  )
}


export default function ResetPasswordPage() {
  return (
    <Suspense fallback={<div className="auth-suspense" />}>
      <ResetPasswordForm />
    </Suspense>
  )
}
