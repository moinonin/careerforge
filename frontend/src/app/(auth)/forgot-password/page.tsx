"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { forgotPassword } from "@/lib/auth"


function ForgotPasswordForm() {
  const router = useRouter()
  const [email, setEmail] = useState("")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")
  const [sent, setSent] = useState(false)


  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError("")

    if (!email.includes("@")) {
      setError("Enter a valid email address")
      return
    }

    setLoading(true)
    try {
      await forgotPassword({ email })
      setSent(true)
    } catch (err: unknown) {
      setError(
        err instanceof Error
          ? (err as any).detail ?? (err as any).message ?? err.message
          : "Failed to send reset link",
      )
    } finally {
      setLoading(false)
    }
  }


  if (sent) {
    return (
      <div className="auth-card">
        <div className="auth-success">
          <svg
            className="auth-success-icon"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth={2}
          >
            <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
            <polyline points="22 4 12 14.01 9 11.01" />
          </svg>
          <h1 className="auth-title">Reset link sent</h1>
          <p className="auth-success-detail">
            If an account exists for <strong>{email}</strong>, we've sent a
            password reset link to that address.
          </p>
          <p className="auth-subtitle">
            Check your inbox (and spam folder) and follow the link to choose a
            new password.
          </p>
          <button
            type="button"
            onClick={() => setSent(false)}
            className="auth-link-button"
          >
            Back to form
          </button>
        </div>
      </div>
    )
  }


  return (
    <form onSubmit={handleSubmit} className="auth-form" noValidate>
      <h1 className="auth-title">Forgot your password?</h1>
      <p className="auth-subtitle">
        Enter your email and we'll send you a link to reset it.
      </p>

      <div className="auth-field">
        <label htmlFor="forgot-email" className="auth-label">
          Email
        </label>
        <input
          id="forgot-email"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="auth-input"
          placeholder="jane@company.com"
          autoComplete="email"
          disabled={loading || sent}
        />
      </div>

      {error && <p className="auth-error">{error}</p>}

      <button
        type="submit"
        className="auth-submit"
        disabled={loading || sent || !email}
      >
        {loading ? (
          <span className="auth-spinner" aria-hidden="true" />
        ) : (
          "Send reset link"
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


export default function ForgotPasswordPage() {
  return <ForgotPasswordForm />
}
