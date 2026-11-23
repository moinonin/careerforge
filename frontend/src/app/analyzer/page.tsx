"use client";

import { useState, useEffect, useRef, useMemo } from "react";
import Link from "next/link";
import { useTheme } from "next-themes";

interface CompanyResearch {
  company?: string | null;
  summary?: string | null;
  domain?: string | null;
  size?: string | null;
  technology_stack?: string | null;
  source?: string | null;
}

interface AnalyzerResult {
  required_skills: string[];
  implied_skills: string[];
  red_flags: string[];
  salary_estimate: { range: string; currency: string; location: string } | null;
  company_research: CompanyResearch | string | null;
  keyword_coverage: unknown | null;
}

const SAMPLE_JDS = [
  {
    id: "quant",
    label: "Quant Researcher (G-Research)",
    company: "G-Research",
    description: `We are seeking a Quantitative Researcher to join our London execution and market microstructure team.

Responsibilities:
- Design and backtest statistical models on tick-level order book and trade data using Python and C++.
- Research alpha signals, market impact, and execution schedules across equities and futures.
- Collaborate with software engineers to deploy low-latency research pipelines into production.

Requirements:
- PhD or MSc in Mathematics, Physics, Statistics, Computer Science, or a related quantitative discipline.
- Strong proficiency in Python (NumPy, pandas, PyTorch) and experience with C++ or Rust.
- Deep grounding in probability, stochastic processes, and time-series econometrics.
- Track record of rigorous empirical research or peer-reviewed publications.

Compensation: £140,000 – £210,000 base plus performance bonus. Hybrid in London.`,
  },
  {
    id: "backend",
    label: "Senior Backend (FastAPI)",
    company: "Stripe",
    description: `Senior Backend Engineer — Payments Infrastructure (Dublin / Remote EU)

We are looking for an experienced backend engineer to design and scale resilient payment APIs.

What you'll do:
- Architect and maintain high-throughput services in Python (FastAPI), PostgreSQL, and Redis.
- Own idempotency, distributed tracing, and zero-downtime database migrations on Kubernetes.
- Partner with product and security teams on API design and SLA reliability.

What we look for:
- 5+ years building production backend systems with Python or Go.
- Strong SQL query optimization and PostgreSQL indexing expertise.
- Experience with Docker, CI/CD, and observability stacks (OpenTelemetry, Prometheus).

Salary: €105,000 – €135,000 + equity.`,
  },
  {
    id: "redflag",
    label: "Startup Red-Flag Check",
    company: "Stealth Rocket",
    description: `Urgent hire! Looking for a rockstar ninja 10x full-stack engineer to join our fast-paced family.
You will wear many hats: frontend, backend, DevOps, QA, and customer support.
Must be available on weekends and evenings as needed. Unlimited PTO.
Compensation: Competitive salary (equity only for the first 6 months).
Requirements: 10+ years of experience with React, Python, Rust, Kubernetes, and AI.`,
  },
];

type ResultTab = "all" | "skills" | "company";

export default function AnalyzerPage() {
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  const [jobDescription, setJobDescription] = useState("");
  const [companyName, setCompanyName] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AnalyzerResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Interactive states
  const [checkedSkills, setCheckedSkills] = useState<Set<string>>(new Set());
  const [activeTab, setActiveTab] = useState<ResultTab>("all");
  const [copyMessage, setCopyMessage] = useState("");
  const [copyVisible, setCopyVisible] = useState(false);
  const copyTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const copyCountRef = useRef(0);
  const resultsRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    setMounted(true);
    const draft = sessionStorage.getItem("careerforge_draft_jd");
    if (draft) {
      setJobDescription(draft);
      sessionStorage.removeItem("careerforge_draft_jd");
    }
    return () => {
      if (copyTimerRef.current) clearTimeout(copyTimerRef.current);
    };
  }, []);

  const isDark = !mounted || theme !== "light";

  const wordCount = useMemo(() => {
    const trimmed = jobDescription.trim();
    return trimmed ? trimmed.split(/\s+/).length : 0;
  }, [jobDescription]);

  const matchStats = useMemo(() => {
    if (!result) return { matchedReq: 0, totalReq: 0, matchedImp: 0, totalImp: 0, pct: 0 };
    const req = result.required_skills ?? [];
    const imp = result.implied_skills ?? [];
    const matchedReq = req.filter((s) => checkedSkills.has(s)).length;
    const matchedImp = imp.filter((s) => checkedSkills.has(s)).length;

    let pct = 0;
    if (req.length > 0 && imp.length > 0) {
      pct = Math.round((matchedReq / req.length) * 75 + (matchedImp / imp.length) * 25);
    } else if (req.length > 0) {
      pct = Math.round((matchedReq / req.length) * 100);
    } else if (imp.length > 0) {
      pct = Math.round((matchedImp / imp.length) * 100);
    }
    return { matchedReq, totalReq: req.length, matchedImp, totalImp: imp.length, pct };
  }, [result, checkedSkills]);

  async function runAnalysis() {
    if (!jobDescription.trim() || loading) return;
    setLoading(true);
    setError(null);
    setResult(null);
    setCheckedSkills(new Set());
    setActiveTab("all");

    try {
      const res = await fetch("/api/v1/analyzer", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          job_description: jobDescription,
          company_name: companyName.trim() || null,
        }),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || `Analyzer failed (${res.status})`);
      }

      const data: AnalyzerResult = await res.json();
      setResult(data);
      // On mobile/tablet stacked view, scroll smoothly to results
      if (typeof window !== "undefined" && window.innerWidth < 1024) {
        setTimeout(() => {
          resultsRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
        }, 60);
      }
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Analysis failed");
    } finally {
      setLoading(false);
    }
  }

  function handleAnalyze(e: React.FormEvent) {
    e.preventDefault();
    runAnalysis();
  }

  function handleTextareaKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
      e.preventDefault();
      runAnalysis();
    }
  }

  function loadSample(sample: (typeof SAMPLE_JDS)[number]) {
    setJobDescription(sample.description);
    setCompanyName(sample.company);
    setError(null);
  }

  function toggleSkill(skill: string) {
    setCheckedSkills((prev) => {
      const next = new Set(prev);
      if (next.has(skill)) next.delete(skill);
      else next.add(skill);
      return next;
    });
  }

  function formatSummaryForCopy(): string {
    if (!result) return "";
    const lines: string[] = [];
    if (companyName.trim()) lines.push(`Company: ${companyName.trim()}`);
    if (result.salary_estimate) {
      lines.push(
        `Salary Estimate: ${result.salary_estimate.range} (${result.salary_estimate.currency}, ${result.salary_estimate.location})`
      );
    }
    if (result.required_skills.length) {
      lines.push(`Required Skills: ${result.required_skills.join(", ")}`);
    }
    if (result.implied_skills.length) {
      lines.push(`Implied Skills: ${result.implied_skills.join(", ")}`);
    }
    if (checkedSkills.size > 0) {
      lines.push(`Self-Assessed Readiness: ${matchStats.pct}% (${checkedSkills.size} skills matched)`);
    }
    if (result.red_flags.length) {
      lines.push(`Red Flags:\n- ${result.red_flags.join("\n- ")}`);
    }
    return lines.join("\n");
  }

  async function handleCopySummary() {
    const text = formatSummaryForCopy();
    if (!text) return;
    try {
      await navigator.clipboard.writeText(text);
      copyCountRef.current += 1;
      // Append non-breaking space on alternating clicks so screen readers re-announce
      const suffix = copyCountRef.current % 2 === 0 ? "\u00A0" : "";
      setCopyMessage(`Copied breakdown to clipboard${suffix}`);
      setCopyVisible(true);
      if (copyTimerRef.current) clearTimeout(copyTimerRef.current);
      copyTimerRef.current = setTimeout(() => {
        setCopyVisible(false);
      }, 2200);
    } catch {
      setCopyMessage("Unable to access clipboard");
      setCopyVisible(true);
    }
  }

  return (
    <div className="min-h-screen bg-[var(--color-bg)] text-[var(--color-text)] overflow-x-clip">
      {/* Header */}
      <header className="sticky top-0 z-40 bg-[var(--color-bg)]/85 backdrop-blur-md border-b border-[var(--color-border)]">
        <div className="max-w-7xl 2xl:max-w-[1440px] mx-auto flex items-center justify-between px-4 sm:px-6 lg:px-10 2xl:px-12 py-3.5">
          <Link href="/" className="flex items-center gap-2.5" aria-label="CareerForge Home">
            <div className="w-8 h-8 rounded-lg bg-[var(--color-brand-600)] flex items-center justify-center text-white font-semibold text-xs">
              CF
            </div>
            <span className="text-base font-semibold tracking-tight text-[var(--color-text-high)]">
              CareerForge
            </span>
          </Link>

          <div className="flex items-center gap-3 sm:gap-5">
            <Link
              href="/"
              className="text-xs sm:text-sm text-[var(--color-text-medium)] hover:text-[var(--color-text-high)] transition-colors"
            >
              Home
            </Link>
            <Link
              href="/dashboard"
              className="text-xs sm:text-sm text-[var(--color-text-medium)] hover:text-[var(--color-text-high)] transition-colors"
            >
              Dashboard
            </Link>
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
          </div>
        </div>
      </header>

      <main className="max-w-7xl 2xl:max-w-[1440px] mx-auto px-4 sm:px-6 lg:px-10 2xl:px-12 pt-8 sm:pt-10 pb-20 space-y-6 lg:space-y-8">
        {/* Intro */}
        <section className="flex flex-col lg:flex-row lg:items-end justify-between gap-4 border-b border-[var(--color-border)] pb-6">
          <div className="space-y-2 max-w-2xl">
            <h1 className="font-display text-3xl sm:text-4xl 2xl:text-[2.75rem] font-medium tracking-[-0.02em] text-[var(--color-text-high)]">
              Job Post Analyzer
            </h1>
            <p className="text-sm sm:text-base text-[var(--color-text-medium)] leading-relaxed">
              Paste any job description to surface required skills, implied expectations,
              red flags, compensation estimates, and company context. Click extracted skills
              afterward to score your personal readiness.
            </p>
          </div>

          {/* Sample JD Presets */}
          <div aria-label="Sample job descriptions" className="space-y-2 shrink-0">
            <p className="text-xs font-medium text-[var(--color-text-low)]">
              Try a sample posting
            </p>
            <div className="flex flex-wrap gap-2">
              {SAMPLE_JDS.map((sample) => (
                <button
                  key={sample.id}
                  type="button"
                  onClick={() => loadSample(sample)}
                  className="btn-press min-h-[36px] px-3 py-1.5 rounded-lg text-xs font-medium border border-[var(--color-border)] bg-[var(--color-surface)] hover:bg-[var(--color-surface-hover)] hover:border-[var(--color-border-strong)] text-[var(--color-text-medium)] hover:text-[var(--color-text-high)] cursor-pointer"
                >
                  {sample.label}
                </button>
              ))}
            </div>
          </div>
        </section>

        {/* Responsive Split Workbench: 1 col on mobile/tablet, 12-col split on lg+ */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 lg:gap-8 xl:gap-10 items-start">
          {/* Left Column: Sticky Input Form on Desktop */}
          <section className="lg:col-span-5 xl:col-span-5 lg:sticky lg:top-20 surface-card p-4 sm:p-6 shadow-sm">
            <form onSubmit={handleAnalyze} className="space-y-5">
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <label
                    htmlFor="jd-input"
                    className="text-xs font-medium text-[var(--color-text-medium)]"
                  >
                    Job Description
                  </label>
                  <div className="flex items-center gap-3 text-xs text-[var(--color-text-faint)] font-mono-code">
                    <span>{wordCount} words</span>
                    {jobDescription && (
                      <button
                        type="button"
                        onClick={() => {
                          setJobDescription("");
                          setCompanyName("");
                          setResult(null);
                          setError(null);
                        }}
                        className="text-[var(--color-text-low)] hover:text-[var(--color-text-high)] underline underline-offset-2 cursor-pointer"
                      >
                        Clear
                      </button>
                    )}
                  </div>
                </div>
                <textarea
                  id="jd-input"
                  value={jobDescription}
                  onChange={(e) => setJobDescription(e.target.value)}
                  onKeyDown={handleTextareaKeyDown}
                  placeholder="Paste the full job description here..."
                  className="w-full min-h-[220px] lg:min-h-[320px] 2xl:min-h-[380px] bg-[var(--color-surface-elevated)] border border-[var(--color-border)] rounded-xl px-4 py-3 text-sm text-[var(--color-text)] placeholder:text-[var(--color-text-faint)] focus:border-[var(--color-brand-500)] focus:outline-none resize-y leading-relaxed"
                  required
                />
              </div>

              <div className="space-y-4">
                <div>
                  <label
                    htmlFor="company-input"
                    className="block text-xs font-medium text-[var(--color-text-medium)] mb-1.5"
                  >
                    Company Name <span className="text-[var(--color-text-faint)]">(optional — enables lookup)</span>
                  </label>
                  <input
                    id="company-input"
                    type="text"
                    value={companyName}
                    onChange={(e) => setCompanyName(e.target.value)}
                    placeholder="e.g. G-Research, Stripe, Jane Street"
                    className="w-full min-h-[42px] bg-[var(--color-surface-elevated)] border border-[var(--color-border)] rounded-xl px-4 py-2.5 text-sm text-[var(--color-text)] placeholder:text-[var(--color-text-faint)] focus:border-[var(--color-brand-500)] focus:outline-none"
                  />
                </div>

                <button
                  type="submit"
                  disabled={loading || !jobDescription.trim()}
                  className="btn-press w-full min-h-[44px] py-2.5 px-5 rounded-xl bg-[var(--color-brand-600)] hover:bg-[var(--color-brand-700)] text-white text-sm font-medium cursor-pointer disabled:opacity-45 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                >
                  {loading ? (
                    <>
                      <span className="w-4 h-4 rounded-full border-2 border-white/30 border-t-white animate-spin" />
                      <span>Analyzing posting...</span>
                    </>
                  ) : (
                    <>
                      <span>Analyze Job</span>
                      <kbd className="hidden sm:inline-block font-mono-code text-[10px] px-1.5 py-0.5 rounded bg-white/15 text-white/90">
                        ⌘↵
                      </kbd>
                    </>
                  )}
                </button>
              </div>
            </form>
          </section>

          {/* Right Column: Results / Loading / Empty Guide */}
          <div className="lg:col-span-7 xl:col-span-7 space-y-6 min-w-0">
            {/* Error */}
            {error && (
              <section role="alert" className="rounded-xl p-4 border border-[var(--color-danger)] bg-[var(--color-danger-bg)] text-sm text-[var(--color-danger)]">
                {error}
              </section>
            )}

            {/* Loading Skeleton */}
            {loading && (
              <section aria-busy="true" aria-label="Analyzing job description" className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {[1, 2, 3, 4].map((n) => (
                  <div key={n} className="surface-card p-5 space-y-3 skeleton-pulse">
                    <div className="h-4 w-32 rounded bg-[var(--color-surface-hover)]" />
                    <div className="flex flex-wrap gap-2">
                      <div className="h-6 w-20 rounded-full bg-[var(--color-surface-hover)]" />
                      <div className="h-6 w-24 rounded-full bg-[var(--color-surface-hover)]" />
                      <div className="h-6 w-16 rounded-full bg-[var(--color-surface-hover)]" />
                    </div>
                  </div>
                ))}
              </section>
            )}

            {/* Empty State Guide (keeps large screens balanced before first run) */}
            {!loading && !result && !error && (
              <section className="surface-card p-6 sm:p-8 space-y-6">
                <div className="space-y-1.5">
                  <h2 className="font-display text-xl sm:text-2xl font-medium text-[var(--color-text-high)]">
                    Ready to inspect a role
                  </h2>
                  <p className="text-sm text-[var(--color-text-medium)] leading-relaxed">
                    Paste a job description on the left or click one of the sample postings above to see a live structured breakdown here.
                  </p>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
                  {[
                    {
                      title: "Required & Implied Skills",
                      desc: "Separates stated requirements from unspoken team expectations, with clickable self-assessment.",
                    },
                    {
                      title: "Red Flag Screening",
                      desc: "Flags scope creep, unpaid equity traps, weekend-work language, and inflated tenure asks.",
                    },
                    {
                      title: "Compensation Benchmarks",
                      desc: "Extracts or estimates role salary bands with currency and geographic context.",
                    },
                    {
                      title: "Company Context",
                      desc: "Adds live public reference summaries when you include a company name.",
                    },
                  ].map((item) => (
                    <div
                      key={item.title}
                      className="rounded-xl p-4 bg-[var(--color-surface-elevated)] border border-[var(--color-border)] space-y-1"
                    >
                      <h3 className="text-xs font-semibold text-[var(--color-text-high)]">
                        {item.title}
                      </h3>
                      <p className="text-xs text-[var(--color-text-low)] leading-relaxed">
                        {item.desc}
                      </p>
                    </div>
                  ))}
                </div>
              </section>
            )}

            {/* Results */}
            {result && (
              <section ref={resultsRef} className="space-y-6 motion-enter">
                {/* Results Header + Actions */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-[var(--color-border)] pb-4">
                  <div>
                    <h2 className="font-display text-2xl font-medium text-[var(--color-text-high)]">
                      Analysis Breakdown
                    </h2>
                    <p className="text-xs text-[var(--color-text-low)] mt-0.5">
                      Click any skill chip below to check off skills you already have.
                    </p>
                  </div>

                  <div className="flex flex-wrap items-center gap-2">
                    <div className="relative flex items-center gap-2">
                      <button
                        type="button"
                        onClick={handleCopySummary}
                        className="btn-press min-h-[38px] px-3.5 py-1.5 rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)] hover:bg-[var(--color-surface-hover)] text-xs font-medium text-[var(--color-text-high)] cursor-pointer inline-flex items-center gap-1.5"
                      >
                        <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth="2">
                          <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
                          <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
                        </svg>
                        <span>Copy summary</span>
                      </button>
                      <span
                        role="status"
                        aria-live="polite"
                        data-visible={copyVisible ? "true" : "false"}
                        className="copy-status-live text-xs font-medium text-[var(--color-accent-500)]"
                      >
                        {copyMessage}
                      </span>
                    </div>

                    <Link
                      href="/generate"
                      className="btn-press min-h-[38px] px-3.5 py-1.5 rounded-lg bg-[var(--color-brand-600)] hover:bg-[var(--color-brand-700)] text-white text-xs font-medium inline-flex items-center"
                    >
                      Tailor CV in Studio
                    </Link>
                  </div>
                </div>

                {/* Interactive Readiness Meter + Filter Tabs */}
                <div className="surface-card p-4 sm:p-5 flex flex-col xl:flex-row xl:items-center justify-between gap-4">
                  <div className="flex-1 space-y-2 min-w-0">
                    <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
                      <span className="font-medium text-[var(--color-text-high)]">
                        Personal Skill Readiness
                      </span>
                      <span className="font-mono-code font-medium text-[var(--color-brand-400)]">
                        {matchStats.pct}% ({matchStats.matchedReq}/{matchStats.totalReq} req · {matchStats.matchedImp}/{matchStats.totalImp} imp)
                      </span>
                    </div>
                    <div className="h-2 w-full rounded-full bg-[var(--color-surface-elevated)] overflow-hidden">
                      <div
                        className="h-full rounded-full bg-[var(--color-accent-500)] transition-all duration-300"
                        style={{ width: `${matchStats.pct}%` }}
                      />
                    </div>
                  </div>

                  <div
                    role="tablist"
                    aria-label="Filter analysis sections"
                    className="inline-flex self-start xl:self-auto rounded-lg border border-[var(--color-border)] bg-[var(--color-surface-elevated)] p-0.5 text-xs shrink-0"
                  >
                    {(
                      [
                        { id: "all", label: "All" },
                        { id: "skills", label: "Skills & Flags" },
                        { id: "company", label: "Comp & Company" },
                      ] as const
                    ).map((tab) => (
                      <button
                        key={tab.id}
                        type="button"
                        role="tab"
                        aria-selected={activeTab === tab.id}
                        onClick={() => setActiveTab(tab.id)}
                        className={`px-3 py-1.5 rounded-md font-medium transition-colors cursor-pointer ${
                          activeTab === tab.id
                            ? "bg-[var(--color-surface)] text-[var(--color-text-high)] shadow-xs"
                            : "text-[var(--color-text-medium)] hover:text-[var(--color-text-high)]"
                        }`}
                      >
                        {tab.label}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Red Flags Banner */}
                {(activeTab === "all" || activeTab === "skills") && result.red_flags.length > 0 && (
                  <div className="rounded-xl p-5 border border-[var(--color-warning)]/35 bg-[var(--color-warning-bg)]">
                    <h3 className="text-sm font-semibold text-[var(--color-warning)] mb-2.5 flex items-center gap-2">
                      <svg className="w-4 h-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth="2">
                        <path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" strokeLinecap="round" strokeLinejoin="round" />
                        <line x1="12" y1="9" x2="12" y2="13" strokeLinecap="round" />
                        <line x1="12" y1="17" x2="12.01" y2="17" strokeLinecap="round" />
                      </svg>
                      <span>Red Flags ({result.red_flags.length})</span>
                    </h3>
                    <ul className="space-y-1.5">
                      {result.red_flags.map((flag, i) => (
                        <li
                          key={i}
                          className="text-xs sm:text-sm text-[var(--color-text)] leading-relaxed flex items-start gap-2"
                        >
                          <span aria-hidden="true" className="mt-1.5 w-1.5 h-1.5 rounded-full bg-[var(--color-warning)] shrink-0" />
                          <span>{flag}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Skills Grid */}
                {(activeTab === "all" || activeTab === "skills") && (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {/* Required Skills */}
                    <div className="surface-card p-5 space-y-3">
                      <div className="flex items-center justify-between">
                        <h3 className="text-sm font-semibold text-[var(--color-text-high)]">
                          Required Skills
                        </h3>
                        <span className="font-mono-code text-xs text-[var(--color-text-faint)]">
                          {result.required_skills.length} found
                        </span>
                      </div>
                      {result.required_skills.length === 0 ? (
                        <p className="text-xs text-[var(--color-text-faint)]">No explicit skills extracted.</p>
                      ) : (
                        <div className="flex flex-wrap gap-2">
                          {result.required_skills.map((skill) => {
                            const checked = checkedSkills.has(skill);
                            return (
                              <button
                                key={skill}
                                type="button"
                                onClick={() => toggleSkill(skill)}
                                aria-pressed={checked}
                                className={`btn-press min-h-[34px] px-3 py-1.5 rounded-full text-xs font-medium border cursor-pointer inline-flex items-center gap-1.5 ${
                                  checked
                                    ? "bg-[var(--color-success-bg)] border-[var(--color-success)] text-[var(--color-success)]"
                                    : "bg-[var(--color-surface-elevated)] border-[var(--color-border)] text-[var(--color-text-high)] hover:border-[var(--color-border-strong)]"
                                }`}
                              >
                                {checked && (
                                  <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth="2.5">
                                    <polyline points="20 6 9 17 4 12" strokeLinecap="round" strokeLinejoin="round" />
                                  </svg>
                                )}
                                <span>{skill}</span>
                              </button>
                            );
                          })}
                        </div>
                      )}
                    </div>

                    {/* Implied Skills */}
                    <div className="surface-card p-5 space-y-3">
                      <div className="flex items-center justify-between">
                        <h3 className="text-sm font-semibold text-[var(--color-text-high)]">
                          Implied Skills
                        </h3>
                        <span className="font-mono-code text-xs text-[var(--color-text-faint)]">
                          {result.implied_skills.length} inferred
                        </span>
                      </div>
                      {result.implied_skills.length === 0 ? (
                        <p className="text-xs text-[var(--color-text-faint)]">No implied skills inferred.</p>
                      ) : (
                        <div className="flex flex-wrap gap-2">
                          {result.implied_skills.map((skill) => {
                            const checked = checkedSkills.has(skill);
                            return (
                              <button
                                key={skill}
                                type="button"
                                onClick={() => toggleSkill(skill)}
                                aria-pressed={checked}
                                className={`btn-press min-h-[34px] px-3 py-1.5 rounded-full text-xs border cursor-pointer inline-flex items-center gap-1.5 ${
                                  checked
                                    ? "bg-[var(--color-success-bg)] border-[var(--color-success)] text-[var(--color-success)] font-medium"
                                    : "bg-transparent border-dashed border-[var(--color-border-strong)] text-[var(--color-text-medium)] hover:text-[var(--color-text-high)] hover:bg-[var(--color-surface-elevated)]"
                                }`}
                              >
                                {checked && (
                                  <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth="2.5">
                                    <polyline points="20 6 9 17 4 12" strokeLinecap="round" strokeLinejoin="round" />
                                  </svg>
                                )}
                                <span>{skill}</span>
                              </button>
                            );
                          })}
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {/* Salary & Company Research Grid */}
                {(activeTab === "all" || activeTab === "company") && (
                  <div className="grid grid-cols-1 md:grid-cols-12 gap-4">
                    {result.salary_estimate && (
                      <div className="surface-card p-5 md:col-span-5 flex flex-col justify-between">
                        <div>
                          <h3 className="text-sm font-semibold text-[var(--color-text-high)] mb-2">
                            Salary Estimate
                          </h3>
                          <p className="font-mono-code text-xl sm:text-2xl font-medium text-[var(--color-text-high)]">
                            {result.salary_estimate.range}
                          </p>
                        </div>
                        <p className="text-xs text-[var(--color-text-low)] mt-3 pt-3 border-t border-[var(--color-border)]">
                          {result.salary_estimate.currency} — {result.salary_estimate.location}
                        </p>
                      </div>
                    )}

                    {result.company_research && (
                      <div
                        className={`surface-card p-5 space-y-2.5 ${
                          result.salary_estimate ? "md:col-span-7" : "md:col-span-12"
                        }`}
                      >
                        <h3 className="text-sm font-semibold text-[var(--color-text-high)]">
                          Company Research
                        </h3>
                        {typeof result.company_research === "string" ? (
                          <p className="text-xs sm:text-sm text-[var(--color-text-medium)] leading-relaxed">
                            {result.company_research}
                          </p>
                        ) : (
                          <div className="space-y-2 text-xs sm:text-sm text-[var(--color-text-medium)]">
                            {result.company_research.company && (
                              <p className="font-semibold text-[var(--color-text-high)]">
                                {result.company_research.company}
                              </p>
                            )}
                            {result.company_research.summary && (
                              <p className="leading-relaxed">
                                {result.company_research.summary}
                              </p>
                            )}
                            <div className="flex flex-wrap gap-x-5 gap-y-1 pt-1 text-xs">
                              {result.company_research.domain && (
                                <span>
                                  <strong className="text-[var(--color-text-high)] font-medium">Domain:</strong>{" "}
                                  {result.company_research.domain}
                                </span>
                              )}
                              {result.company_research.size && (
                                <span>
                                  <strong className="text-[var(--color-text-high)] font-medium">Size:</strong>{" "}
                                  {result.company_research.size}
                                </span>
                              )}
                              {result.company_research.technology_stack && (
                                <span>
                                  <strong className="text-[var(--color-text-high)] font-medium">Stack:</strong>{" "}
                                  {result.company_research.technology_stack}
                                </span>
                              )}
                            </div>
                            {result.company_research.source && (
                              <p className="pt-1">
                                <a
                                  href={result.company_research.source}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="text-xs font-medium text-[var(--color-brand-400)] hover:text-[var(--color-brand-300)] underline underline-offset-3"
                                >
                                  View public reference
                                </a>
                              </p>
                            )}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )}
              </section>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
