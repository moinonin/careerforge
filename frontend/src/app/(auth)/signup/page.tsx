"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { signup } from "@/lib/auth"


function SignupForm() {
  const router = useRouter()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")
  const [submitted, setSubmitted] = useState(false)
  const [full_name, setFull_name] = useState("")
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [confirm, setConfirm] = useState("")


  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError("")
    if (password !== confirm) {
      setError("Passwords do not match")
      return
    }
    if (password.length < 8) {
      setError("Password must be at least 8 characters")
      return
    }
    if (!email.includes("@")) {
      setError("Enter a valid email address")
      return
    }

    setLoading(true)
    try {
      await signup({ full_name: full_name || undefined, email, password })
      window.location.href = "/login?registered=true"
    } catch (err) {
      setError(
        err && typeof err === "object" && "detail" in err
          ? String((err as { detail: unknown }).detail)
          : err && typeof err === "object" && "message" in err
            ? String((err as { message: unknown }).message)
            : "Registration failed",
      )
    } finally {
      setLoading(false)
    }
  }


  return (
    <form onSubmit={handleSubmit} className="auth-form" noValidate>
      <h1 className="auth-title">Create your account</h1>
      <p className="auth-subtitle">
        Build a standout resume in minutes with AI.
      </p>

      {submitted ? (
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
          <p className="auth-success-text">Account created!</p>
          <p className="auth-success-detail">
            Check your email for a verification link, then log in.
          </p>
          <button
            type="button"
            onClick={() => setSubmitted(false)}
            className="auth-link-button"
          >
            Register another account
          </button>
        </div>
      ) : (
        <>
          <div className="auth-field">
            <label htmlFor="full_name" className="auth-label">
              Full name{" "}
              <span className="auth-label-optional">(optional)</span>
            </label>
            <input
              id="full_name"
              type="text"
              value={full_name}
              onChange={(e) => setFull_name(e.target.value)}
              className="auth-input"
              placeholder="Jane Doe"
              autoComplete="name"
              disabled={loading}
            />
          </div>

          <div className="auth-field">
            <label htmlFor="signup-email" className="auth-label">
              Work email
            </label>
            <input
              id="signup-email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="auth-input"
              placeholder="jane@company.com"
              autoComplete="email"
              disabled={loading}
            />
          </div>

          <div className="auth-field">
            <label htmlFor="signup-password" className="auth-label">
              Password
            </label>
            <input
              id="signup-password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="auth-input"
              placeholder="At least 8 characters"
              autoComplete="new-password"
              disabled={loading}
            />
          </div>

          <div className="auth-field">
            <label htmlFor="signup-confirm" className="auth-label">
              Confirm password
            </label>
            <input
              id="signup-confirm"
              type="password"
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              className="auth-input"
              placeholder="Repeat your password"
              autoComplete="new-password"
              disabled={loading}
            />
          </div>

          {error && <p className="auth-error">{error}</p>}

          <button
            type="submit"
            className="auth-submit"
            disabled={loading || !email || !password}
          >
            {loading ? (
              <span className="auth-spinner" aria-hidden="true" />
            ) : (
              "Create account"
            )}
          </button>

          <p className="auth-switch">
            Already have an account?{" "}
            <a href="/login" className="auth-link">
              Log in
            </a>
          </p>
        </>
      )}
    </form>
  )
}


export default function SignupPage() {
  return <SignupForm />
}
