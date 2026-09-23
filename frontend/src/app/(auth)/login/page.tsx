"use client";

import { Suspense, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/lib/auth-context";

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const registered = searchParams.get("registered") === "true";
  const { login } = useAuth();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    if (!email.includes("@")) {
      setError("Enter a valid email address");
      return;
    }
    if (!password) {
      setError("Enter your password");
      return;
    }

    setLoading(true);
    try {
      await login(email, password);
      router.push("/dashboard");
    } catch (err: unknown) {
      setError(
        err instanceof Error
          ? (err as any).detail ?? (err as any).message ?? err.message
          : "Login failed",
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="auth-form" noValidate>
      <h1 className="auth-title">Welcome back</h1>
      <p className="auth-subtitle">
        Log in to continue building your resume.
      </p>

      {registered && (
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
          <p className="auth-success-text">Account ready!</p>
          <p className="auth-success-detail">
            Check your email for a verification link, then log in.
          </p>
        </div>
      )}

      <div className="auth-field">
        <label htmlFor="login-email" className="auth-label">
          Email
        </label>
        <input
          id="login-email"
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
        <label htmlFor="login-password" className="auth-label">
          Password
        </label>
        <input
          id="login-password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="auth-input"
          placeholder="Your password"
          autoComplete="current-password"
          disabled={loading}
        />
      </div>

      {error && <p className="auth-error">{error}</p>}

      <button
        type="submit"
        className="auth-submit"
        disabled={loading || (!email || !password)}
      >
        {loading ? (
          <span className="auth-spinner" aria-hidden="true" />
        ) : (
          "Log in"
        )}
      </button>

      <p className="auth-switch">
        Don't have an account?{" "}
        <a href="/signup" className="auth-link">
          Create one
        </a>
      </p>

      <div className="auth-secondary">
        <a href="/forgot-password" className="auth-link-secondary">
          Forgot your password?
        </a>
      </div>
    </form>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={<div className="auth-suspense"><div className="auth-spinner" /></div>}>
      <LoginForm />
    </Suspense>
  );
}