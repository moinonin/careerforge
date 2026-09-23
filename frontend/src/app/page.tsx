"use client";

import { useTheme } from "next-themes";
import Link from "next/link";
import { useAuth } from "@/lib/auth-context";
import { useState, useEffect } from "react";

export default function LandingPage() {
  const { user, loading } = useAuth();
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (loading || !mounted) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[var(--color-bg)]">
        <div className="text-[var(--color-text-faint)] text-sm">Loading...</div>
      </div>
    );
  }

  const isDark = theme === "dark";

  return (
    <div className="min-h-screen bg-[var(--color-bg)] text-[var(--color-text)]">
      {/* Nav */}
      <nav className="flex items-center justify-between px-6 py-4 max-w-6xl mx-auto">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-[rgba(0,0,0,0.08)] flex items-center justify-center text-xs font-bold">
            CF
          </div>
          <span className="text-sm font-medium tracking-tight">
            CareerForge
          </span>
        </div>
        <div className="flex items-center gap-4">
          <Link
            href="/pricing"
            className="text-xs text-[var(--color-text-medium)] hover:text-[var(--color-text)] transition-colors"
          >
            Pricing
          </Link>
          <button
            onClick={() => setTheme(isDark ? "light" : "dark")}
            className="text-xs text-[var(--color-text-medium)] hover:text-[var(--color-text)] transition-colors"
            aria-label="Toggle theme"
          >
            {isDark ? "☀️" : "🌙"}
          </button>
          {user ? (
            <Link
              href="/dashboard"
              className="text-xs text-[var(--color-text-medium)] hover:text-[var(--color-text)] transition-colors"
            >
              Dashboard
            </Link>
          ) : (
            <>
              <Link
                href="/login"
                className="text-xs text-[var(--color-text-medium)] hover:text-[var(--color-text)] transition-colors"
              >
                Log in
              </Link>
              <Link
                href="/signup"
                className="text-xs bg-[rgba(0,0,0,0.08)] hover:bg-[rgba(0,0,0,0.12)] transition-colors px-4 py-1.5 rounded-full"
              >
                Sign up free
              </Link>
            </>
          )}
        </div>
      </nav>

      {/* Hero */}
      <section className="px-6 pt-20 pb-12 max-w-6xl mx-auto text-center">
        <p className="text-xs uppercase tracking-widest text-[var(--color-text-faint)] mb-4">
          AI-powered CV generation
        </p>
        <h1 className="text-4xl sm:text-5xl font-bold tracking-tight leading-tight mb-5">
          Generate ATS-compliant CVs
          <br />
          <span className="text-[var(--color-text-medium)]">tailored to every job description</span>
        </h1>
        <p className="text-[var(--color-text-low)] text-sm max-w-lg mx-auto mb-8 leading-relaxed">
          Paste a job description, connect your profile, and get a ready-to-send
          CV and cover letter in DOCX and PDF. Built for professionals who
          apply to real jobs.
        </p>

        {/* Analyzer CTA */}
        <div className="max-w-xl mx-auto bg-[rgba(0,0,0,0.04)] rounded-xl p-1 border border-[rgba(0,0,0,0.04)]">
          <Link
            href="/analyzer"
            className="block w-full py-3.5 rounded-xl bg-[rgba(0,0,0,0.08)] hover:bg-[rgba(0,0,0,0.12)] transition-colors text-center"
          >
            <p className="text-xs text-[var(--color-text-faint)] mb-0.5">Free — no account needed</p>
            <p className="text-sm font-medium">Analyze a job description now</p>
            <p className="text-xs text-[var(--color-text-faint)] mt-1">
              Skills breakdown, salary estimate, red flags
            </p>
          </Link>
        </div>

        {/* Signup CTA */}
        <div className="mt-6 flex flex-col sm:flex-row items-center justify-center gap-3">
          {user ? (
            <Link
              href="/dashboard"
              className="text-sm bg-[rgba(0,0,0,0.08)] hover:bg-[rgba(0,0,0,0.12)] transition-colors px-5 py-2 rounded-full"
            >
              Go to Dashboard
            </Link>
          ) : (
            <>
              <Link
                href="/signup"
                className="text-sm bg-[var(--color-bg-elevated)] px-5 py-2 rounded-full font-medium hover:bg-[rgba(0,0,0,0.12)] transition-colors"
              >
                Start free trial
              </Link>
              <Link
                href="/login"
                className="text-sm text-[var(--color-text-low)] hover:text-[var(--color-text-high)] transition-colors"
              >
                Already have an account?
              </Link>
            </>
          )}
        </div>
      </section>

      {/* Feature strip */}
      <section className="px-6 pb-20 max-w-6xl mx-auto">
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          {[
            { label: "ATS-compliant output", detail: "DOCX + PDF" },
            { label: "LLM agnostic", detail: "Any provider" },
            { label: "14-day free trial", detail: "No card required" },
            { label: "Two-method profile", detail: "Upload or build" },
          ].map((f) => (
            <div
              key={f.label}
              className="bg-[rgba(0,0,0,0.03)] rounded-lg p-3 border border-[rgba(0,0,0,0.04)]"
            >
              <p className="text-xs font-medium">{f.label}</p>
              <p className="text-xs text-[var(--color-text-faint)] mt-0.5">{f.detail}</p>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
