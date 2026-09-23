"use client"

import { useEffect, useState, useCallback } from "react"
import { useRouter } from "next/navigation"
import {
  listProfiles,
  deleteProfile,
  setDefaultProfile,
} from "@/lib/api/profiles"
import { useAuth } from "@/lib/auth-context"
import { cn } from "@/lib/utils"

// ── Helpers ───────────────────────────────────────────────────────────────────

function formatDate(iso: string | null): string {
  if (!iso) return "—"
  const d = new Date(iso)
  return d.toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  })
}

function completenessRing(score: number): string {
  if (score >= 80) return "bg-emerald-500"
  if (score >= 60) return "bg-amber-500"
  if (score >= 40) return "bg-orange-500"
  return "bg-red-500"
}

function completenessLabel(score: number): string {
  if (score >= 80) return "Ready"
  if (score >= 60) return "Mostly complete"
  if (score >= 40) return "Partial"
  return "Starter"
}

// ── Component ─────────────────────────────────────────────────────────────────

export default function ProfilesPage() {
  const router = useRouter()
  const { user, loading: authLoading } = useAuth()
  const [profiles, setProfiles] = useState<
    Array<{
      id: string
      title: string
      is_default: boolean
      is_draft: boolean
      completeness_score: number
      updated_at: string | null
      created_at: string | null
    }>
  >([])
  const [loading, setLoading] = useState(true)
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null)
  const [actionLoading, setActionLoading] = useState<string | null>(null)

  const load = useCallback(async () => {
    if (!user) return
    try {
      const list = await listProfiles()
      setProfiles(
        list.map((p) => ({
          id: p.id,
          title: p.title,
          is_default: p.is_default,
          is_draft: p.is_draft,
          completeness_score: p.completeness_score,
          updated_at: p.updated_at,
          created_at: p.created_at,
        })),
      )
    } catch {
      setProfiles([])
    } finally {
      setLoading(false)
    }
  }, [user])

  useEffect(() => {
    if (user) load()
  }, [user, load])

  async function handleDelete(id: string) {
    if (!confirm(`Delete "${profiles.find((p) => p.id === id)?.title}"? This cannot be undone.`)) {
      return
    }
    setActionLoading(id)
    try {
      await deleteProfile(id)
      setProfiles((prev) => prev.filter((p) => p.id !== id))
    } catch (err: any) {
      alert(err.detail ?? err.message ?? "Could not delete profile")
    } finally {
      setActionLoading(null)
      setDeleteTarget(null)
    }
  }

  async function handleSetDefault(id: string) {
    setActionLoading(id)
    try {
      await setDefaultProfile(id)
      setProfiles((prev) =>
        prev.map((p) => ({
          ...p,
          is_default: p.id === id,
        })),
      )
    } catch (err: any) {
      alert(err.detail ?? err.message ?? "Could not set default")
    } finally {
      setActionLoading(null)
    }
  }

  if (authLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-[var(--color-text-faint)] text-sm">Loading…</div>
      </div>
    )
  }

  if (!user) {
    router.push("/login")
    return null
  }

  return (
    <main className="min-h-screen bg-[var(--color-bg)] text-[var(--color-text)]">
      {/* ── Header ─────────────────────────────────────────────────────────── */}
      <header className="border-b border-[rgba(0,0,0,0.08)] px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <svg
            className="w-6 h-6 text-[var(--color-text-medium)]"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth={1.5}
          >
            <path d="M6 9l6-3 6 3" />
            <path d="M6 15l6 3 6-3" />
            <path d="M6 12h12" />
          </svg>
          <h1 className="text-lg font-medium tracking-tight text-[var(--color-text-high)]">
            Resumes
          </h1>
        </div>
        <div className="flex items-center gap-2">
          <a
            href="/profiles"
            className="text-sm text-[var(--color-text-faint)] hover:text-[var(--color-text-high)] transition-colors"
          >
            New resume
          </a>
          <a
            href="/profiles/upload"
            className="text-sm text-[var(--color-text-faint)] hover:text-[var(--color-text-high)] transition-colors"
          >
            Upload CV
          </a>
        </div>
      </header>

      {/* ── Content ────────────────────────────────────────────────────────── */}
      <div className="max-w-3xl mx-auto px-6 py-8">
        {loading ? (
          <div className="flex items-center justify-center py-16">
            <div className="text-[var(--color-text-faint)] text-sm">Loading profiles…</div>
          </div>
        ) : profiles.length === 0 ? (
          /* Empty state */
          <div className="border border-[rgba(0,0,0,0.08)] rounded-xl p-8 text-center">
            <div className="w-12 h-12 mx-auto mb-4 rounded-full bg-[rgba(0,0,0,0.04)] flex items-center justify-center">
              <svg
                className="w-6 h-6 text-[var(--color-text-faint)]"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth={1.5}
              >
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                <polyline points="14,2 14,8 20,8" />
                <line x1="16" y1="13" x2="8" y2="13" />
                <line x1="16" y1="17" x2="8" y2="17" />
                <polyline points="10,9 9,9 8,9" />
              </svg>
            </div>
            <h2 className="text-lg font-medium text-[var(--color-text-high)] mb-2">
              No resumes yet
            </h2>
            <p className="text-sm text-[var(--color-text-faint)] mb-6 max-w-sm mx-auto">
              Create your first resume from scratch, or upload an existing CV
              and we'll parse it for you.
            </p>
            <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
              <a
                href="/profiles"
                className="w-full sm:w-auto px-5 py-2.5 rounded-lg bg-[rgba(0,0,0,0.08)] hover:bg-[rgba(0,0,0,0.12)] text-sm font-medium text-[var(--color-text)] transition-colors"
              >
                Create from scratch
              </a>
              <a
                href="/profiles/upload"
                className="w-full sm:w-auto px-5 py-2.5 rounded-lg border border-[rgba(0,0,0,0.12)] hover:border-[rgba(0,0,0,0.15)] text-sm font-medium text-[var(--color-text-high)] hover:text-[var(--color-text)] transition-colors"
              >
                Upload CV
              </a>
            </div>
          </div>
        ) : (
          /* Profile cards */
          <div className="space-y-3">
            {profiles.map((profile) => (
              <article
                key={profile.id}
                className={cn(
                  "border rounded-xl p-4 transition-colors",
                  profile.is_default
                    ? "border-amber-500/30 bg-amber-500/5"
                    : "border-[rgba(0,0,0,0.08)] bg-[rgba(0,0,0,0.02)] hover:bg-[rgba(0,0,0,0.04)]",
                )}
              >
                <div className="flex items-start justify-between gap-4">
                  {/* Left: title + meta */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <h2 className="text-base font-medium truncate text-[var(--color-text-high)]">
                        {profile.title}
                      </h2>
                      {profile.is_default && (
                        <span className="shrink-0 px-2 py-0.5 rounded text-[10px] font-medium uppercase tracking-wider bg-amber-500/20 text-amber-400 border border-amber-500/20">
                          Default
                        </span>
                      )}
                      {profile.is_draft && (
                        <span className="shrink-0 px-2 py-0.5 rounded text-[10px] font-medium uppercase tracking-wider bg-[rgba(0,0,0,0.08)] text-[var(--color-text-faint)] border border-[rgba(0,0,0,0.08)]">
                          Draft
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-3 text-xs text-[var(--color-text-faint)]">
                      <span>Updated {formatDate(profile.updated_at)}</span>
                      {profile.created_at && (
                        <span>· Created {formatDate(profile.created_at)}</span>
                      )}
                    </div>
                  </div>

                  {/* Right: completeness + actions */}
                  <div className="flex items-center gap-3 shrink-0">
                    {/* Completeness gauge */}
                    <div className="flex flex-col items-center">
                      <div className="relative w-12 h-12">
                        <svg
                          className="w-12 h-12 -rotate-90"
                          viewBox="0 0 36 36"
                        >
                          <circle
                            cx="18"
                            cy="18"
                            r="15"
                            fill="none"
                            stroke="currentColor"
                            strokeWidth="2.5"
                            className="text-[var(--color-text-faint)]"
                          />
                          <circle
                            cx="18"
                            cy="18"
                            r="15"
                            fill="none"
                            stroke="currentColor"
                            strokeWidth="2.5"
                            strokeDasharray={`${profile.completeness_score * 0.942} 36`}
                            strokeLinecap="round"
                            className={cn(
                              "transition-colors",
                              completenessRing(profile.completeness_score),
                            )}
                          />
                        </svg>
                        <span className="absolute inset-0 flex items-center justify-center text-xs font-medium text-[var(--color-text-high)]">
                          {profile.completeness_score}
                        </span>
                      </div>
                      <span className="text-[11px] text-[var(--color-text-faint)] mt-1">
                        {completenessLabel(profile.completeness_score)}
                      </span>
                    </div>

                    {/* Actions */}
                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => handleSetDefault(profile.id)}
                        disabled={profile.is_default || !!actionLoading}
                        className={cn(
                          "px-2 py-1 rounded text-xs font-medium transition-colors",
                          profile.is_default
                            ? "text-[var(--color-text-faint)] cursor-not-allowed"
                            : "text-[var(--color-text-medium)] hover:text-[var(--color-text)] hover:bg-[rgba(0,0,0,0.08)]",
                        )}
                      >
                        {actionLoading === profile.id ? "…" : "Set default"}
                      </button>
                      <button
                        onClick={() => router.push(`/profiles?edit=${profile.id}`)}
                        className="px-2 py-1 rounded text-xs font-medium text-[var(--color-text-medium)] hover:text-[var(--color-text)] hover:bg-[rgba(0,0,0,0.08)] transition-colors"
                      >
                        Edit
                      </button>
                      <button
                        onClick={() => setDeleteTarget(profile.id)}
                        disabled={!!actionLoading}
                        className="px-2 py-1 rounded text-xs font-medium text-[var(--color-text-faint)] hover:text-red-400 hover:bg-red-500/10 transition-colors"
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                </div>

                {/* Delete confirmation inline */}
                {deleteTarget === profile.id && (
                  <div className="mt-3 pt-3 border-t border-[rgba(0,0,0,0.08)] flex items-center justify-end gap-2">
                    <span className="text-xs text-[var(--color-text-low)]">
                      Delete this resume?
                    </span>
                    <button
                      onClick={() => setDeleteTarget(null)}
                      className="text-xs px-2 py-1 rounded text-[var(--color-text-medium)] hover:text-[var(--color-text)] transition-colors"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={() => handleDelete(profile.id)}
                      disabled={!!actionLoading}
                      className="text-xs px-2 py-1 rounded text-red-400 hover:bg-red-500/10 transition-colors disabled:opacity-40"
                    >
                      {actionLoading ? "…" : "Delete"}
                    </button>
                  </div>
                )}
              </article>
            ))}
          </div>
        )}

        {/* Footer CTAs */}
        <div className="mt-8 flex flex-col sm:flex-row items-center justify-center gap-3 border-t border-[rgba(0,0,0,0.08)] pt-6">
          <a
            href="/profiles"
            className="w-full sm:w-auto px-5 py-2.5 rounded-lg bg-[rgba(0,0,0,0.08)] hover:bg-[rgba(0,0,0,0.12)] text-sm font-medium text-[var(--color-text)] transition-colors"
          >
            + New resume
          </a>
          <a
            href="/profiles/upload"
            className="w-full sm:w-auto px-5 py-2.5 rounded-lg border border-[rgba(0,0,0,0.12)] hover:border-[rgba(0,0,0,0.15)] text-sm font-medium text-[var(--color-text-high)] hover:text-[var(--color-text)] transition-colors"
          >
            Upload CV
          </a>
        </div>
      </div>
    </main>
  )
}
