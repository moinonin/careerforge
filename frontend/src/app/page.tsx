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
      <div className="min-h-screen flex items-center justify-center bg-bg">
        <div className="flex items-center gap-3 text-text-faint">
          <svg className="animate-spin h-6 w-6 text-brand-500" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="10" strokeOpacity="0.25" />
            <path d="M12 2a10 10 0 0 1 10 10" strokeLinecap="round" />
          </svg>
          <span className="text-sm">Loading CareerForge...</span>
        </div>
      </div>
    );
  }

  const isDark = theme === "dark";

  return (
    <div className="min-h-screen bg-bg text-text hero-gradient">
      {/* Nav */}
      <nav className="sticky top-0 z-40 bg-bg/80 backdrop-blur-xl border-b border-border">
        <div className="container flex items-center justify-between px-4 py-4 md:px-6 md:py-4">
          <Link href="/" className="flex items-center gap-2" aria-label="CareerForge Home">
            <div className="w-9 h-9 rounded-xl bg-brand-600 flex items-center justify-center text-white font-bold text-sm shadow-lg shadow-brand-600/30">
              CF
            </div>
            <span className="text-lg font-bold text-text tracking-tight">CareerForge</span>
          </Link>

          <div className="flex items-center gap-4">
            <Link
              href="/pricing"
              className="hidden md:block text-sm text-text-medium hover:text-text transition-colors"
            >
              Pricing
            </Link>
            <button
              onClick={() => setTheme(isDark ? "light" : "dark")}
              className="p-2 rounded-xl bg-surface hover:bg-surface-hover text-text-medium hover:text-text transition-colors"
              aria-label="Toggle theme"
            >
              {isDark ? (
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth="2">
                  <circle cx="12" cy="12" r="5" />
                  <path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              ) : (
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth="2">
                  <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
                </svg>
              )}
            </button>

            {user ? (
              <Link
                href="/dashboard"
                className="text-sm text-text-medium hover:text-text transition-colors px-4 py-2 rounded-xl hover:bg-surface"
              >
                Dashboard
              </Link>
            ) : (
              <>
                <Link
                  href="/login"
                  className="hidden sm:block text-sm text-text-medium hover:text-text transition-colors"
                >
                  Log in
                </Link>
                <Link
                  href="/signup"
                  className="text-sm bg-brand-600 hover:bg-brand-700 text-white px-5 py-2 rounded-xl font-medium transition-all hover:shadow-lg hover:shadow-brand-500/25"
                >
                  Start free trial
                </Link>
              </>
            )}
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="page-section">
        <div className="container text-center max-w-4xl">
          <p className="text-xs uppercase tracking-widest text-text-faint mb-4 animate-fade-in">
            AI-powered CV generation
          </p>

          <h1 className="text-h1 font-bold tracking-tight leading-tight mb-6 animate-slide-up">
            Generate ATS-compliant CVs
            <br />
            <span className="text-text-medium font-normal">tailored to every job description</span>
          </h1>

          <p className="text-lg text-text-medium max-w-2xl mx-auto mb-10 leading-relaxed animate-slide-up">
            Paste a job description, connect your profile, and get a ready-to-send
            CV and cover letter in DOCX and PDF. Built for professionals who
            apply to real jobs.
          </p>

          {/* Primary CTA Card */}
          <div className="max-w-xl mx-auto glass-strong rounded-2xl p-1 border border-border animate-scale-in">
            <Link
              href="/analyzer"
              className="block w-full py-4 rounded-xl bg-brand-600 hover:bg-brand-700 transition-all hover:shadow-lg hover:shadow-brand-500/25 text-center group"
            >
              <div className="flex flex-col items-center gap-2">
                <p className="text-xs text-white/70">Free — no account needed</p>
                <p className="text-base font-semibold text-white">Analyze a job description now</p>
                <p className="text-xs text-white/60 group-hover:text-white/80 transition-colors">
                  Skills breakdown, salary estimate, red flags →
                </p>
              </div>
            </Link>
          </div>

          {/* Secondary CTAs */}
          <div className="mt-8 flex flex-col sm:flex-row items-center justify-center gap-3 animate-fade-in">
            {user ? (
              <Link
                href="/dashboard"
                className="text-sm bg-surface hover:bg-surface-hover text-text px-6 py-3 rounded-xl font-medium border border-border transition-all"
              >
                Go to Dashboard
              </Link>
            ) : (
              <>
                <Link
                  href="/signup"
                  className="text-sm bg-brand-600 hover:bg-brand-700 text-white px-6 py-3 rounded-xl font-medium transition-all hover:shadow-lg hover:shadow-brand-500/25"
                >
                  Start free trial
                </Link>
                <Link
                  href="/login"
                  className="text-sm text-text-low hover:text-text-high transition-colors"
                >
                  Already have an account?
                </Link>
              </>
            )}
          </div>

          {/* Trust indicators */}
          <div className="mt-16 flex flex-wrap items-center justify-center gap-8 text-text-faint text-xs animate-fade-in">
            <span className="flex items-center gap-1.5">
              <svg className="w-4 h-4 text-accent-500" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth="2">
                <path d="M22 12h-4l-3 9L4 15l-3 9h4" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" />
              </svg>
              ATS-compliant
            </span>
            <span className="flex items-center gap-1.5">
              <svg className="w-4 h-4 text-brand-500" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth="2">
                <circle cx="12" cy="12" r="10" />
                <path d="M2 12h20M12 2v20" strokeLinecap="round" strokeWidth="2" />
              </svg>
              Multi-provider LLM
            </span>
            <span className="flex items-center gap-1.5">
              <svg className="w-4 h-4 text-warning-500" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth="2">
                <rect x="2" y="3" width="20" height="14" rx="2" />
                <path d="M8 21h8M12 17v4" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" />
              </svg>
              14-day free trial
            </span>
            <span className="flex items-center gap-1.5">
              <svg className="w-4 h-4 text-danger-500" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth="2">
                <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" />
                <polyline points="14 2 14 8 20 8" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" />
              </svg>
              DOCX + PDF
            </span>
          </div>
        </div>
      </section>

      {/* Feature highlights */}
      <section className="page-section bg-surface/30 border-y border-border">
        <div className="container">
          <div className="text-center max-w-2xl mx-auto mb-12">
            <p className="text-xs uppercase tracking-widest text-text-faint mb-3">Why CareerForge</p>
            <h2 className="text-h2 font-bold tracking-tight mb-4">
              Built for job seekers who want results
            </h2>
            <p className="text-text-medium">
              Every feature is designed to get you past the ATS and in front of hiring managers.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {[
              {
                icon: (
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth="2">
                    <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z" strokeLinecap="round" strokeLinejoin="round" />
                    <polyline points="14 2 14 8 20 8" />
                  </svg>
                ),
                label: "ATS-compliant output",
                detail: "Clean DOCX + PDF that parsers love",
              },
              {
                icon: (
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth="2">
                    <circle cx="12" cy="12" r="10" />
                    <path d="M2 12h20M12 2v20" />
                  </svg>
                ),
                label: "Multi-provider LLM",
                detail: "OpenAI, Anthropic, Ollama, custom",
              },
              {
                icon: (
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth="2">
                    <rect x="2" y="3" width="20" height="14" rx="2" />
                    <path d="M8 21h8M12 17v4" />
                  </svg>
                ),
                label: "14-day free trial",
                detail: "No card required to start",
              },
              {
                icon: (
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth="2">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M17 18a5 5 0 0 0-10 0" />
                    <path d="M20 12a5 5 0 0 0-10 0M12 7a5 5 0 0 1 0 10" />
                  </svg>
                ),
                label: "Two-method profile",
                detail: "Upload CV or build from scratch",
              },
            ].map((f) => (
              <article
                key={f.label}
                className="group card-hover p-6 flex flex-col"
              >
                <div className="w-12 h-12 rounded-xl bg-brand-500/10 flex items-center justify-center text-brand-500 mb-4 group-hover:bg-brand-500/20 transition-colors">
                  {f.icon}
                </div>
                <h3 className="font-semibold text-text mb-1.5">{f.label}</h3>
                <p className="text-text-medium text-sm flex-1">{f.detail}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      {/* Social proof / Stats */}
      <section className="page-section">
        <div className="container max-w-4xl">
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-6 text-center">
            {[
              { value: "50K+", label: "CVs generated" },
              { value: "94%", label: "ATS pass rate" },
              { value: "2 min", label: "Average generation time" },
              { value: "40+", label: "Countries served" },
            ].map((stat) => (
              <div key={stat.label} className="card-hover p-8">
                <div className="text-3xl sm:text-4xl font-bold text-brand-500 mb-1">{stat.value}</div>
                <div className="text-text-medium text-sm">{stat.label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Footer CTA */}
      <section className="page-section bg-brand-500/5 border-y border-brand-500/10">
        <div className="container text-center max-w-2xl">
          <h2 className="text-h2 font-bold mb-4">Ready to land your next role?</h2>
          <p className="text-text-medium mb-8 max-w-lg mx-auto">
            Join thousands of professionals who use CareerForge to create
            interview-winning CVs in minutes.
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
            <Link
              href="/signup"
              className="text-sm bg-brand-600 hover:bg-brand-700 text-white px-8 py-3 rounded-xl font-semibold transition-all hover:shadow-lg hover:shadow-brand-500/30"
            >
              Start your free trial
            </Link>
            <Link
              href="/analyzer"
              className="text-sm bg-surface hover:bg-surface-hover text-text px-8 py-3 rounded-xl font-medium border border-border transition-all"
            >
              Try the analyzer first
            </Link>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-surface border-t border-border py-10">
        <div className="container flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg bg-brand-600 flex items-center justify-center text-white font-bold text-sm">
              CF
            </div>
            <span className="text-sm font-medium tracking-tight">CareerForge</span>
          </div>
          <nav className="flex flex-wrap items-center justify-center gap-6 text-xs text-text-faint">
            <Link href="/pricing" className="hover:text-text transition-colors">Pricing</Link>
            <Link href="/analyzer" className="hover:text-text transition-colors">Analyzer</Link>
            <span>·</span>
            <Link href="/privacy" className="hover:text-text transition-colors">Privacy</Link>
            <Link href="/terms" className="hover:text-text transition-colors">Terms</Link>
            <span>·</span>
            <span>© {new Date().getFullYear()} CareerForge</span>
          </nav>
        </div>
      </footer>
    </div>
  );
}

