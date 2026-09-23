"use client";

import { useState } from "react";
import Link from "next/link";

interface AnalyzerResult {
  required_skills: string[];
  implied_skills: string[];
  red_flags: string[];
  salary_estimate: { range: string; currency: string; location: string } | null;
  company_research: { domain: string; size: string; technology_stack: string } | null;
  keyword_coverage: unknown | null;
}

export default function AnalyzerPage() {
  const [jobDescription, setJobDescription] = useState("");
  const [companyName, setCompanyName] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AnalyzerResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleAnalyze(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const res = await fetch("/api/v1/analyzer", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          job_description: jobDescription,
          company_name: companyName || null,
        }),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || `Analyzer failed (${res.status})`);
      }

      const data: AnalyzerResult = await res.json();
      setResult(data);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Analysis failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-[var(--color-bg)] text-[var(--color-text)]">
      {/* Nav */}
      <nav className="flex items-center justify-between px-6 py-4 max-w-6xl mx-auto">
        <Link href="/" className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-[rgba(0,0,0,0.08)] flex items-center justify-center text-xs font-bold">
            CF
          </div>
          <span className="text-sm font-medium tracking-tight">CareerForge</span>
        </Link>
        <Link
          href="/"
          className="text-xs text-[var(--color-text-medium)] hover:text-[var(--color-text)] transition-colors"
        >
          ← Back to home
        </Link>
      </nav>

      {/* Hero */}
      <section className="px-6 pt-12 pb-8 max-w-3xl mx-auto text-center">
        <h1 className="text-3xl sm:text-4xl font-bold tracking-tight mb-3">
          Job Post Analyzer
        </h1>
        <p className="text-[var(--color-text-low)] text-sm mb-8 leading-relaxed">
          Paste a job description and get an instant breakdown of required
          skills, implied skills, red flags, salary estimate, and company
          research — no account needed.
        </p>
      </section>

      {/* Analyzer Form */}
      <section className="px-6 pb-8 max-w-3xl mx-auto">
        <form onSubmit={handleAnalyze} className="space-y-4">
          <div>
            <label className="block text-xs text-[var(--color-text-faint)] mb-1.5 uppercase tracking-wider">
              Job Description
            </label>
            <textarea
              value={jobDescription}
              onChange={(e) => setJobDescription(e.target.value)}
              placeholder="Paste the full job description here..."
              className="w-full min-h-[200px] bg-[rgba(0,0,0,0.04)] border border-[rgba(0,0,0,0.08)] rounded-xl px-4 py-3 text-sm text-[var(--color-text)] placeholder-[var(--color-text-faint)] focus:outline-none focus:border-[rgba(0,0,0,0.12)] focus:ring-1 focus:ring-[var(--color-text-faint)] resize-y"
              required
            />
          </div>
          <div>
            <label className="block text-xs text-[var(--color-text-faint)] mb-1.5 uppercase tracking-wider">
              Company Name (optional)
            </label>
            <input
              type="text"
              value={companyName}
              onChange={(e) => setCompanyName(e.target.value)}
              placeholder="Acme Corp"
              className="w-full bg-[rgba(0,0,0,0.04)] border border-[rgba(0,0,0,0.08)] rounded-xl px-4 py-3 text-sm text-[var(--color-text)] placeholder-[var(--color-text-faint)] focus:outline-none focus:border-[rgba(0,0,0,0.12)] focus:ring-1 focus:ring-[var(--color-text-faint)]"
            />
          </div>
          <button
            type="submit"
            disabled={loading || !jobDescription.trim()}
            className="w-full py-3.5 rounded-xl bg-[rgba(0,0,0,0.08)] hover:bg-[rgba(0,0,0,0.12)] transition-colors text-sm font-medium disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {loading ? "Analyzing..." : "Analyze Job"}
          </button>
        </form>
      </section>

      {/* Error */}
      {error && (
        <section className="px-6 pb-8 max-w-3xl mx-auto">
          <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-4 text-red-300 text-sm">
            {error}
          </div>
        </section>
      )}

      {/* Results */}
      {result && (
        <section className="px-6 pb-20 max-w-3xl mx-auto space-y-6">
          <h2 className="text-xl font-bold tracking-tight pt-4">
            Analysis Results
          </h2>

          {/* Required Skills */}
          <div className="bg-[rgba(0,0,0,0.04)] rounded-xl p-4 border border-[rgba(0,0,0,0.04)]">
            <h3 className="text-sm font-medium text-[var(--color-text-high)] mb-2">
              Required Skills
            </h3>
            <div className="flex flex-wrap gap-2">
              {result.required_skills.map((s) => (
                <span
                  key={s}
                  className="bg-[rgba(0,0,0,0.08)] text-xs px-2.5 py-1 rounded-full"
                >
                  {s}
                </span>
              ))}
            </div>
          </div>

          {/* Implied Skills */}
          <div className="bg-[rgba(0,0,0,0.04)] rounded-xl p-4 border border-[rgba(0,0,0,0.04)]">
            <h3 className="text-sm font-medium text-[var(--color-text-high)] mb-2">
              Implied Skills
            </h3>
            <div className="flex flex-wrap gap-2">
              {result.implied_skills.map((s) => (
                <span
                  key={s}
                  className="bg-[rgba(0,0,0,0.04)] text-xs text-[var(--color-text-medium)] px-2.5 py-1 rounded-full border border-[rgba(0,0,0,0.04)]"
                >
                  {s}
                </span>
              ))}
            </div>
          </div>

          {/* Red Flags */}
          {result.red_flags.length > 0 && (
            <div className="bg-amber-500/5 rounded-xl p-4 border border-amber-500/10">
              <h3 className="text-sm font-medium text-amber-300 mb-2">
                Red Flags
              </h3>
              <ul className="space-y-1">
                {result.red_flags.map((f, i) => (
                  <li
                    key={i}
                    className="text-xs text-amber-200/80 flex items-start gap-1.5"
                  >
                    <span>⚠</span>
                    <span>{f}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Salary Estimate */}
          {result.salary_estimate && (
            <div className="bg-[rgba(0,0,0,0.04)] rounded-xl p-4 border border-[rgba(0,0,0,0.04)]">
              <h3 className="text-sm font-medium text-[var(--color-text-high)] mb-2">
                Salary Estimate
              </h3>
              <p className="text-lg font-bold">
                {result.salary_estimate.range}
              </p>
              <p className="text-xs text-[var(--color-text-faint)]">
                {result.salary_estimate.currency} ·{" "}
                {result.salary_estimate.location}
              </p>
            </div>
          )}

          {/* Company Research */}
          {result.company_research && (
            <div className="bg-[rgba(0,0,0,0.04)] rounded-xl p-4 border border-[rgba(0,0,0,0.04)]">
              <h3 className="text-sm font-medium text-[var(--color-text-high)] mb-2">
                Company Research
              </h3>
              <div className="space-y-1 text-xs text-[var(--color-text-low)]">
                {result.company_research.domain && (
                  <p><span className="text-[var(--color-text-medium)]">Domain:</span> {result.company_research.domain}</p>
                )}
                {result.company_research.size && (
                  <p><span className="text-[var(--color-text-medium)]">Size:</span> {result.company_research.size}</p>
                )}
                {result.company_research.technology_stack && (
                  <p><span className="text-[var(--color-text-medium)]">Tech Stack:</span> {result.company_research.technology_stack}</p>
                )}
              </div>
            </div>
          )}
        </section>
      )}
    </div>
  );
}