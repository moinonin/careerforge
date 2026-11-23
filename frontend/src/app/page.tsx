"use client";

import { useTheme } from "next-themes";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { useState, useEffect } from "react";

interface TrackSample {
  id: string;
  label: string;
  role: string;
  company: string;
  location: string;
  salary: string;
  atsMatch: number;
  requiredSkills: string[];
  impliedSkills: string[];
  cvHeadline: string;
  cvBullets: string[];
  relevanceNote: string;
}

const TRACKS: TrackSample[] = [
  {
    id: "quant",
    label: "Quant Research",
    role: "Quantitative Researcher — Execution & Microstructure",
    company: "G-Research",
    location: "London, UK · Hybrid",
    salary: "£140,000 – £210,000 + bonus",
    atsMatch: 94,
    requiredSkills: ["Python", "C++", "Stochastic Calculus", "Order Book Modeling", "Time Series"],
    impliedSkills: ["Low-Latency Backtesting", "Statistical Arbitrage", "Market Impact"],
    cvHeadline: "Quantitative Researcher | Market Microstructure & Statistical Learning",
    cvBullets: [
      "Built tick-level order-book simulator in Python/C++ reducing execution slippage by 11 bps across 14 liquid pairs.",
      "Published 8 peer-reviewed papers on stochastic dynamical systems and high-frequency signal extraction.",
      "Designed walk-forward cross-validation pipeline enforcing strict out-of-sample leakage prevention.",
    ],
    relevanceNote:
      "Reframes academic physics & distributed systems work directly into microstructure research language.",
  },
  {
    id: "backend",
    label: "Backend Systems",
    role: "Senior Backend Engineer — Distributed APIs",
    company: "Stripe",
    location: "Dublin / Remote EU",
    salary: "€105,000 – €138,000",
    atsMatch: 96,
    requiredSkills: ["Python", "FastAPI", "PostgreSQL", "Redis", "Docker", "Kubernetes"],
    impliedSkills: ["Idempotency", "Observability", "Zero-Downtime Migrations"],
    cvHeadline: "Senior Backend Engineer | High-Throughput Python & Distributed Data",
    cvBullets: [
      "Architected async FastAPI + PostgreSQL ingestion service sustaining 4,200 req/s at p99 < 45ms.",
      "Eliminated thundering-herd retries via Redis-backed idempotency keys and circuit breakers.",
      "Led multi-arch Docker releases with automated schema verification and rollback safety.",
    ],
    relevanceNote:
      "Surfaces latency, reliability, and schema ownership metrics hiring managers screen for first.",
  },
  {
    id: "academic",
    label: "Academic & PhD",
    role: "Postdoctoral Research Fellow — Applied ML",
    company: "ETH Zürich",
    location: "Zürich, CH · On-site",
    salary: "CHF 92,000 – CHF 108,000",
    atsMatch: 92,
    requiredSkills: ["PyTorch", "Bayesian Inference", "Scientific Computing", "Peer-Reviewed Publishing"],
    impliedSkills: ["Grant Writing", "PhD Supervision", "Reproducible Benchmarks"],
    cvHeadline: "Research Scientist | Probabilistic Modeling & Reproducible ML",
    cvBullets: [
      "Authored 8 peer-reviewed journal and conference articles with open-source PyTorch artifacts.",
      "Co-supervised 4 MSc theses on uncertainty quantification and calibration under distribution shift.",
      "Secured competitive compute allocation across 64-GPU cluster for large-scale ablation studies.",
    ],
    relevanceNote:
      "Preserves academic publication rigor while keeping formatting crisp and single-column ATS safe.",
  },
  {
    id: "ai",
    label: "AI / ML Systems",
    role: "Staff ML Engineer — RAG & Evaluation",
    company: "Anthropic",
    location: "London / SF · Hybrid",
    salary: "$210,000 – $285,000",
    atsMatch: 95,
    requiredSkills: ["LLM Evaluation", "Retrieval Systems", "Python", "Calibration", "Model Distillation"],
    impliedSkills: ["Latency Budgeting", "Grounded Generation", "Safety Guardrails"],
    cvHeadline: "ML Systems Engineer | Grounded RAG, Calibration & Model Distillation",
    cvBullets: [
      "Distilled lightweight local decision classifier matching teacher F1 within 1.4% at < 2ms CPU inference.",
      "Built multi-source retrieval corpus with source attribution and deterministic hallucination checks.",
      "Reduced end-to-end document synthesis cost by 68% via hybrid local routing and temperature scaling.",
    ],
    relevanceNote:
      "Highlights measurable evaluation discipline, latency budgets, and production fallback engineering.",
  },
];

export default function LandingPage() {
  const { user, loading } = useAuth();
  const { theme, setTheme } = useTheme();
  const router = useRouter();

  const [mounted, setMounted] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [activeTrackId, setActiveTrackId] = useState<string>(TRACKS[0].id);
  const [previewMode, setPreviewMode] = useState<"cv" | "jd">("cv");
  const [quickJd, setQuickJd] = useState("");

  useEffect(() => {
    setMounted(true);
  }, []);

  const activeTrack = TRACKS.find((t) => t.id === activeTrackId) ?? TRACKS[0];
  const isDark = !mounted || theme !== "light";

  function handleQuickAnalyze(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = quickJd.trim();
    if (trimmed) {
      sessionStorage.setItem("careerforge_draft_jd", trimmed);
    }
    router.push("/analyzer");
  }

  function handleTrackKeyDown(e: React.KeyboardEvent, idx: number) {
    if (e.key === "ArrowRight") {
      e.preventDefault();
      const next = TRACKS[(idx + 1) % TRACKS.length];
      setActiveTrackId(next.id);
    } else if (e.key === "ArrowLeft") {
      e.preventDefault();
      const prev = TRACKS[(idx - 1 + TRACKS.length) % TRACKS.length];
      setActiveTrackId(prev.id);
    }
  }

  return (
    <div className="min-h-screen bg-[var(--color-bg)] text-[var(--color-text)] overflow-x-clip">
      {/* Header */}
      <header className="sticky top-0 z-40 bg-[var(--color-bg)]/85 backdrop-blur-md border-b border-[var(--color-border)]">
        <div className="max-w-7xl 2xl:max-w-[1440px] mx-auto flex items-center justify-between px-4 sm:px-6 lg:px-10 2xl:px-12 py-3.5">
          <Link href="/" className="flex items-center gap-2.5 group" aria-label="CareerForge Home">
            <div className="w-8 h-8 rounded-lg bg-[var(--color-brand-600)] flex items-center justify-center text-white font-semibold text-xs tracking-tight shadow-sm">
              CF
            </div>
            <span className="text-base font-semibold tracking-tight text-[var(--color-text-high)]">
              CareerForge
            </span>
          </Link>

          <nav className="hidden md:flex items-center gap-8 text-sm text-[var(--color-text-medium)]">
            <Link href="/analyzer" className="hover:text-[var(--color-text-high)] transition-colors">
              Job Analyzer
            </Link>
            <Link href="/pricing" className="hover:text-[var(--color-text-high)] transition-colors">
              Pricing
            </Link>
            {user && (
              <Link href="/dashboard" className="hover:text-[var(--color-text-high)] transition-colors">
                Dashboard
              </Link>
            )}
          </nav>

          <div className="flex items-center gap-2 sm:gap-2.5">
            <button
              type="button"
              onClick={() => setTheme(isDark ? "light" : "dark")}
              className="btn-press p-2.5 sm:p-2 rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] hover:bg-[var(--color-surface-hover)] text-[var(--color-text-medium)] hover:text-[var(--color-text-high)] cursor-pointer"
              aria-label={isDark ? "Switch to light theme" : "Switch to dark theme"}
            >
              {isDark ? (
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth="2">
                  <circle cx="12" cy="12" r="5" />
                  <path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              ) : (
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth="2">
                  <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
                </svg>
              )}
            </button>

            {!loading && user ? (
              <Link
                href="/dashboard"
                className="btn-press hidden sm:inline-flex text-sm bg-[var(--color-brand-600)] hover:bg-[var(--color-brand-700)] text-white px-4 py-2 rounded-lg font-medium"
              >
                Open Studio
              </Link>
            ) : (
              <>
                <Link
                  href="/login"
                  className="hidden sm:inline-flex text-sm text-[var(--color-text-medium)] hover:text-[var(--color-text-high)] px-3 py-2 rounded-lg transition-colors"
                >
                  Log in
                </Link>
                <Link
                  href="/signup"
                  className="btn-press hidden sm:inline-flex text-sm bg-[var(--color-brand-600)] hover:bg-[var(--color-brand-700)] text-white px-4 py-2 rounded-lg font-medium"
                >
                  Start free trial
                </Link>
              </>
            )}

            {/* Mobile menu toggle */}
            <button
              type="button"
              onClick={() => setMobileMenuOpen((v) => !v)}
              className="md:hidden btn-press p-2.5 rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] hover:bg-[var(--color-surface-hover)] text-[var(--color-text-high)] cursor-pointer"
              aria-label={mobileMenuOpen ? "Close menu" : "Open menu"}
              aria-expanded={mobileMenuOpen}
            >
              {mobileMenuOpen ? (
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth="2">
                  <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
                </svg>
              ) : (
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth="2">
                  <line x1="3" y1="6" x2="21" y2="6" /><line x1="3" y1="12" x2="21" y2="12" /><line x1="3" y1="18" x2="21" y2="18" />
                </svg>
              )}
            </button>
          </div>
        </div>

        {/* Mobile dropdown nav */}
        {mobileMenuOpen && (
          <nav
            aria-label="Mobile navigation"
            className="md:hidden border-t border-[var(--color-border)] bg-[var(--color-surface)] px-4 py-3 space-y-1.5"
          >
            <Link
              href="/analyzer"
              onClick={() => setMobileMenuOpen(false)}
              className="block px-3 py-2.5 rounded-lg text-sm font-medium text-[var(--color-text-high)] hover:bg-[var(--color-surface-hover)]"
            >
              Job Analyzer
            </Link>
            <Link
              href="/pricing"
              onClick={() => setMobileMenuOpen(false)}
              className="block px-3 py-2.5 rounded-lg text-sm font-medium text-[var(--color-text-medium)] hover:bg-[var(--color-surface-hover)] hover:text-[var(--color-text-high)]"
            >
              Pricing
            </Link>
            {!loading && user ? (
              <Link
                href="/dashboard"
                onClick={() => setMobileMenuOpen(false)}
                className="block px-3 py-2.5 rounded-lg text-sm font-medium bg-[var(--color-brand-600)] text-white text-center"
              >
                Open Studio
              </Link>
            ) : (
              <div className="grid grid-cols-2 gap-2 pt-1.5">
                <Link
                  href="/login"
                  onClick={() => setMobileMenuOpen(false)}
                  className="px-3 py-2.5 rounded-lg text-sm font-medium border border-[var(--color-border)] text-center text-[var(--color-text-high)]"
                >
                  Log in
                </Link>
                <Link
                  href="/signup"
                  onClick={() => setMobileMenuOpen(false)}
                  className="px-3 py-2.5 rounded-lg text-sm font-medium bg-[var(--color-brand-600)] text-white text-center"
                >
                  Start free trial
                </Link>
              </div>
            )}
          </nav>
        )}
      </header>

      <main>
        {/* Editorial Hero + Interactive Blueprint */}
        <section className="max-w-7xl 2xl:max-w-[1440px] mx-auto px-4 sm:px-6 lg:px-10 2xl:px-12 pt-10 pb-16 sm:pt-14 sm:pb-20 lg:pt-20 lg:pb-24 2xl:pt-24">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-10 lg:gap-12 xl:gap-16 items-start">
            {/* Left column: Headline + Quick-Start */}
            <div className="lg:col-span-6 xl:col-span-5 2xl:col-span-6 space-y-6 motion-enter">
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-[var(--color-border)] bg-[var(--color-surface)] text-xs text-[var(--color-text-medium)]">
                <span className="w-1.5 h-1.5 rounded-full bg-[var(--color-accent-500)] shrink-0" />
                <span>DOCX + PDF synthesis grounded in your real career history</span>
              </div>

              <h1 className="font-display text-[var(--text-h1)] 2xl:text-[4rem] font-medium leading-[1.08] tracking-[-0.02em] text-[var(--color-text-high)]">
                Tailor every CV with{" "}
                <span className="italic text-[var(--color-brand-400)]">editorial precision</span>,
                never boilerplate.
              </h1>

              <p className="text-base sm:text-lg 2xl:text-xl text-[var(--color-text-medium)] max-w-xl 2xl:max-w-2xl leading-relaxed">
                Paste a job description to extract explicit skills, implied expectations,
                salary benchmarks, and red flags — then generate a clean, ATS-safe CV
                and cover letter directly from your verified career corpus.
              </p>

              {/* Quick-launch JD bar */}
              <form
                onSubmit={handleQuickAnalyze}
                className="surface-card p-2 flex flex-col sm:flex-row gap-2 shadow-sm max-w-2xl"
              >
                <label htmlFor="quick-jd" className="sr-only">
                  Paste a job description snippet
                </label>
                <input
                  id="quick-jd"
                  type="text"
                  value={quickJd}
                  onChange={(e) => setQuickJd(e.target.value)}
                  placeholder="Paste a job title or description snippet to test..."
                  className="flex-1 min-w-0 bg-transparent px-3 py-2.5 text-sm text-[var(--color-text)] placeholder:text-[var(--color-text-faint)] focus:outline-none"
                />
                <button
                  type="submit"
                  className="btn-press shrink-0 min-h-[42px] bg-[var(--color-brand-600)] hover:bg-[var(--color-brand-700)] text-white text-sm font-medium px-5 py-2.5 rounded-lg cursor-pointer"
                >
                  Analyze free
                </button>
              </form>

              <div className="flex flex-wrap items-center gap-x-4 gap-y-2 pt-1 text-xs text-[var(--color-text-low)]">
                <span>No account required for Analyzer</span>
                <span aria-hidden="true" className="hidden sm:inline text-[var(--color-border-strong)]">|</span>
                <span>Single-column ATS layout</span>
                <span aria-hidden="true" className="hidden sm:inline text-[var(--color-border-strong)]">|</span>
                <span>Bring your own LLM or use local S1</span>
              </div>
            </div>

            {/* Right column: Interactive Track & Document Preview */}
            <div className="lg:col-span-6 xl:col-span-7 2xl:col-span-6 min-w-0">
              <div className="surface-card overflow-hidden shadow-lg">
                {/* Track selector tabs */}
                <div className="border-b border-[var(--color-border)] bg-[var(--color-surface-elevated)] px-4 pt-3 pb-3">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5 mb-3">
                    <span className="text-xs font-medium text-[var(--color-text-medium)]">
                      Interactive tailoring preview
                    </span>
                    <div
                      className="inline-flex self-start sm:self-auto rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] p-0.5 text-xs"
                      role="group"
                      aria-label="Preview view mode"
                    >
                      <button
                        type="button"
                        onClick={() => setPreviewMode("cv")}
                        aria-pressed={previewMode === "cv"}
                        className={`px-2.5 py-1.5 sm:py-1 rounded-md font-medium transition-colors cursor-pointer ${
                          previewMode === "cv"
                            ? "bg-[var(--color-brand-600)] text-white"
                            : "text-[var(--color-text-medium)] hover:text-[var(--color-text-high)]"
                        }`}
                      >
                        Tailored CV
                      </button>
                      <button
                        type="button"
                        onClick={() => setPreviewMode("jd")}
                        aria-pressed={previewMode === "jd"}
                        className={`px-2.5 py-1.5 sm:py-1 rounded-md font-medium transition-colors cursor-pointer ${
                          previewMode === "jd"
                            ? "bg-[var(--color-brand-600)] text-white"
                            : "text-[var(--color-text-medium)] hover:text-[var(--color-text-high)]"
                        }`}
                      >
                        JD Signals
                      </button>
                    </div>
                  </div>

                  <div
                    role="tablist"
                    aria-label="Role domain tracks"
                    className="flex flex-wrap gap-1.5"
                  >
                    {TRACKS.map((track, idx) => {
                      const selected = track.id === activeTrack.id;
                      return (
                        <button
                          key={track.id}
                          type="button"
                          role="tab"
                          aria-selected={selected}
                          onClick={() => setActiveTrackId(track.id)}
                          onKeyDown={(e) => handleTrackKeyDown(e, idx)}
                          className={`btn-press px-3 py-1.5 rounded-lg text-xs font-medium cursor-pointer border ${
                            selected
                              ? "bg-[var(--color-surface)] border-[var(--color-brand-500)] text-[var(--color-text-high)]"
                              : "bg-transparent border-transparent text-[var(--color-text-medium)] hover:bg-[var(--color-surface-hover)] hover:text-[var(--color-text-high)]"
                          }`}
                        >
                          {track.label}
                        </button>
                      );
                    })}
                  </div>
                </div>

                {/* Preview body */}
                <div className="p-4 sm:p-6 space-y-4">
                  <div className="flex items-start justify-between gap-3 border-b border-[var(--color-border)] pb-3.5">
                    <div className="min-w-0">
                      <h2 className="text-sm sm:text-base font-semibold text-[var(--color-text-high)]">
                        {activeTrack.role}
                      </h2>
                      <p className="text-xs text-[var(--color-text-low)] mt-0.5">
                        {activeTrack.company} — {activeTrack.location}
                      </p>
                    </div>
                    <div className="text-right shrink-0">
                      <div className="font-mono-code text-sm font-medium text-[var(--color-accent-500)]">
                        {activeTrack.atsMatch}% fit
                      </div>
                      <div className="text-[11px] text-[var(--color-text-faint)]">
                        ATS alignment
                      </div>
                    </div>
                  </div>

                  {previewMode === "cv" ? (
                    <div className="space-y-3.5 motion-fade" key={`${activeTrack.id}-cv`}>
                      <div>
                        <p className="font-display italic text-sm sm:text-base text-[var(--color-text-high)]">
                          {activeTrack.cvHeadline}
                        </p>
                      </div>
                      <ul className="space-y-2.5 text-xs sm:text-sm text-[var(--color-text-medium)] leading-relaxed">
                        {activeTrack.cvBullets.map((bullet) => (
                          <li key={bullet} className="flex items-start gap-2.5">
                            <span
                              aria-hidden="true"
                              className="mt-2 w-1.5 h-1.5 rounded-full bg-[var(--color-brand-500)] shrink-0"
                            />
                            <span>{bullet}</span>
                          </li>
                        ))}
                      </ul>
                      <div className="rounded-lg bg-[var(--color-surface-elevated)] border border-[var(--color-border)] px-3.5 py-2.5 text-xs text-[var(--color-text-medium)]">
                        <span className="font-medium text-[var(--color-text-high)]">Framing note: </span>
                        {activeTrack.relevanceNote}
                      </div>
                    </div>
                  ) : (
                    <div className="space-y-4 motion-fade" key={`${activeTrack.id}-jd`}>
                      <div>
                        <p className="text-xs font-medium text-[var(--color-text-low)] mb-2">
                          Required skills detected
                        </p>
                        <div className="flex flex-wrap gap-1.5">
                          {activeTrack.requiredSkills.map((skill) => (
                            <span
                              key={skill}
                              className="px-2.5 py-1 rounded-md text-xs font-medium bg-[var(--color-surface-elevated)] border border-[var(--color-border)] text-[var(--color-text-high)]"
                            >
                              {skill}
                            </span>
                          ))}
                        </div>
                      </div>
                      <div>
                        <p className="text-xs font-medium text-[var(--color-text-low)] mb-2">
                          Implied expectations
                        </p>
                        <div className="flex flex-wrap gap-1.5">
                          {activeTrack.impliedSkills.map((skill) => (
                            <span
                              key={skill}
                              className="px-2.5 py-1 rounded-md text-xs bg-transparent border border-dashed border-[var(--color-border-strong)] text-[var(--color-text-medium)]"
                            >
                              {skill}
                            </span>
                          ))}
                        </div>
                      </div>
                      <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg bg-[var(--color-surface-elevated)] border border-[var(--color-border)] px-3.5 py-2.5">
                        <span className="text-xs text-[var(--color-text-low)]">Estimated comp</span>
                        <span className="font-mono-code text-xs font-medium text-[var(--color-text-high)]">
                          {activeTrack.salary}
                        </span>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Workflow Steps */}
        <section className="border-t border-[var(--color-border)] bg-[var(--color-surface)]/40">
          <div className="max-w-7xl 2xl:max-w-[1440px] mx-auto px-4 sm:px-6 lg:px-10 2xl:px-12 py-14 sm:py-16 lg:py-20">
            <div className="max-w-2xl mb-10 sm:mb-12">
              <h2 className="font-display text-[var(--text-h2)] font-medium tracking-[-0.015em] text-[var(--color-text-high)] mb-3">
                Three steps from raw posting to submission-ready files.
              </h2>
              <p className="text-sm sm:text-base text-[var(--color-text-medium)]">
                Built around factual grounding so your generated documents never invent credentials or break ATS parsers.
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-5 xl:gap-6">
              {[
                {
                  step: "01",
                  title: "Decode the job description",
                  body: "Extract explicit requirements, unspoken team signals, salary range, company context, and potential red flags before you invest an hour applying.",
                  link: { href: "/analyzer", label: "Open Job Analyzer" },
                },
                {
                  step: "02",
                  title: "Ground in your career corpus",
                  body: "Upload your master CV, publication list, or project notes. Retrieval selects only verified achievements relevant to the target role track.",
                  link: { href: user ? "/profiles" : "/signup", label: "Build your profile" },
                },
                {
                  step: "03",
                  title: "Export crisp DOCX & PDF",
                  body: "Render clean typography, balanced margins, and single-column structure that both automated parsers and human reviewers read effortlessly.",
                  link: { href: user ? "/generate" : "/signup", label: "Launch Studio" },
                },
              ].map((item) => (
                <article key={item.step} className="card-interactive p-6 xl:p-7 flex flex-col justify-between">
                  <div>
                    <div className="font-mono-code text-xs text-[var(--color-brand-400)] mb-3">
                      {item.step}
                    </div>
                    <h3 className="text-base font-semibold text-[var(--color-text-high)] mb-2">
                      {item.title}
                    </h3>
                    <p className="text-sm text-[var(--color-text-medium)] leading-relaxed">
                      {item.body}
                    </p>
                  </div>
                  <div className="pt-5 mt-5 border-t border-[var(--color-border)]">
                    <Link
                      href={item.link.href}
                      className="text-xs font-medium text-[var(--color-brand-400)] hover:text-[var(--color-brand-300)] transition-colors"
                    >
                      {item.link.label}
                    </Link>
                  </div>
                </article>
              ))}
            </div>
          </div>
        </section>

        {/* Bottom CTA */}
        <section className="border-t border-[var(--color-border)]">
          <div className="max-w-4xl mx-auto px-4 sm:px-6 py-14 sm:py-16 text-center space-y-5">
            <h2 className="font-display text-[var(--text-h2)] font-medium text-[var(--color-text-high)]">
              Test your next job description right now.
            </h2>
            <p className="text-sm sm:text-base text-[var(--color-text-medium)] max-w-lg mx-auto">
              Run the Job Post Analyzer with zero sign-up, or create a workspace to generate tailored CVs and cover letters.
            </p>
            <div className="flex flex-col sm:flex-row items-center justify-center gap-3 pt-2">
              <Link
                href="/analyzer"
                className="btn-press w-full sm:w-auto min-h-[44px] inline-flex items-center justify-center bg-[var(--color-brand-600)] hover:bg-[var(--color-brand-700)] text-white text-sm font-medium px-6 py-3 rounded-lg"
              >
                Open Job Analyzer
              </Link>
              <Link
                href={user ? "/dashboard" : "/signup"}
                className="btn-press w-full sm:w-auto min-h-[44px] inline-flex items-center justify-center bg-[var(--color-surface)] hover:bg-[var(--color-surface-hover)] border border-[var(--color-border)] text-[var(--color-text-high)] text-sm font-medium px-6 py-3 rounded-lg"
              >
                {user ? "Go to Dashboard" : "Create free account"}
              </Link>
            </div>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="border-t border-[var(--color-border)] py-8">
        <div className="max-w-7xl 2xl:max-w-[1440px] mx-auto px-4 sm:px-6 lg:px-10 2xl:px-12 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-[var(--color-text-faint)]">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-[var(--color-text-medium)]">CareerForge</span>
            <span>© {new Date().getFullYear()}</span>
          </div>
          <nav className="flex flex-wrap items-center justify-center gap-5">
            <Link href="/analyzer" className="hover:text-[var(--color-text-high)] transition-colors">
              Analyzer
            </Link>
            <Link href="/pricing" className="hover:text-[var(--color-text-high)] transition-colors">
              Pricing
            </Link>
            <Link href="/privacy" className="hover:text-[var(--color-text-high)] transition-colors">
              Privacy
            </Link>
            <Link href="/terms" className="hover:text-[var(--color-text-high)] transition-colors">
              Terms
            </Link>
          </nav>
        </div>
      </footer>
    </div>
  );
}
