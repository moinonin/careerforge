"use client"

import { useState, useCallback, useRef } from "react"
import { useRouter } from "next/navigation"
import { importCv, getImportStatus } from "@/lib/api/profiles"
import { useAuth } from "@/lib/auth-context"

type Status =
  | "idle"
  | "dragging"
  | "uploading"
  | "parsing"
  | "done"
  | "error"

export default function UploadPage() {
  const router = useRouter()
  const { user, loading: authLoading } = useAuth()
  const [status, setStatus] = useState<Status>("idle")
  const [parseJobId, setParseJobId] = useState<string | null>(null)
  const [profileId, setProfileId] = useState<string | null>(null)
  const [progress, setProgress] = useState<number>(0)
  const [message, setMessage] = useState<string | null>(null)
  const [profileData, setProfileData] = useState<any>(null)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleFile = useCallback((file: File) => {
    const ext = file.name.split(".").pop()?.toLowerCase()
    if (ext !== "pdf" && ext !== "docx" && ext !== "doc") {
      setMessage("Please upload a PDF or DOCX file.")
      return
    }
    if (file.size > 5 * 1024 * 1024) {
      setMessage("File must be under 5 MB.")
      return
    }
    setSelectedFile(file)
    setMessage(null)
    setStatus("uploading")
    setProgress(0)
    setProfileData(null)
    setParseJobId(null)
  }, [])

  async function startUpload() {
    if (!selectedFile) return
    try {
      const result = await importCv(selectedFile)
      setParseJobId(result.parse_job_id)
      setStatus("parsing")
      setProgress(10)
      pollStatus(result.parse_job_id)
    } catch (err: any) {
      setStatus("error")
      setMessage(err.detail ?? err.message ?? "Upload failed")
    }
  }

  async function pollStatus(jobId: string) {
    let attempts = 0
    const maxAttempts = 30
    while (attempts < maxAttempts) {
      await new Promise((r) => setTimeout(r, 1500))
      attempts++
      try {
        const s = await getImportStatus(jobId)
        if (s.status === "completed") {
          setStatus("done")
          setProgress(100)
          setProfileData(s.profile_data ?? null)
          if (s.profile_id) setProfileId(s.profile_id)
          return
        }
        if (s.status === "failed") {
          setStatus("error")
          setMessage(s.message ?? "Parse failed")
          return
        }
        // Progress estimation: queued → parsing → completed
        setProgress(Math.min(10 + attempts * 3, 90))
      } catch {
        // Keep polling on transient errors
      }
    }
    // Timeout — assume still parsing
    setProgress(90)
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault()
    setStatus("idle")
    const file = e.dataTransfer.files[0]
    if (file) handleFile(file)
  }

  function handleDragOver(e: React.DragEvent) {
    e.preventDefault()
    if (status === "idle" || status === "dragging") {
      setStatus("dragging")
    }
  }

  function handleDragLeave() {
    setStatus("idle")
  }

  function handleInputChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (file) handleFile(file)
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
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
            <polyline points="17,8 12,3 7,8" />
            <line x1="12" y1="3" x2="12" y2="15" />
          </svg>
          <h1 className="text-lg font-medium tracking-tight text-[var(--color-text-high)]">
            Upload CV
          </h1>
        </div>
        <button
          onClick={() => router.push("/profiles")}
          className="text-sm text-[var(--color-text-faint)] hover:text-[var(--color-text-high)] transition-colors"
        >
          Back to resumes
        </button>
      </header>

      {/* ── Content ────────────────────────────────────────────────────────── */}
      <div className="max-w-2xl mx-auto px-6 py-10">
        {/* Status messages */}
        {message && (
          <div
            className={`mb-6 px-4 py-3 rounded-lg text-sm ${
              status === "error"
                ? "bg-red-500/10 text-red-400 border border-red-500/20"
                : "bg-amber-500/10 text-amber-400 border border-amber-500/20"
            }`}
          >
            {message}
          </div>
        )}

        {/* Upload zone */}
        {status === "idle" || status === "dragging" ? (
          <div
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            className={`border-2 border-dashed rounded-xl p-10 text-center transition-colors cursor-pointer ${
              status === "dragging"
                ? "border-amber-500/40 bg-amber-500/5"
                : "border-[rgba(0,0,0,0.12)] hover:border-[rgba(0,0,0,0.15)] hover:bg-[rgba(0,0,0,0.02)]"
            }`}
            onClick={() => fileInputRef.current?.click()}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.docx,.doc"
              onChange={handleInputChange}
              className="hidden"
            />
            <div className="w-12 h-12 mx-auto mb-4 rounded-full bg-[rgba(0,0,0,0.04)] flex items-center justify-center">
              <svg
                className="w-6 h-6 text-[var(--color-text-faint)]"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth={1.5}
              >
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                <polyline points="17,8 12,3 7,8" />
                <line x1="12" y1="3" x2="12" y2="15" />
              </svg>
            </div>
            <p className="text-sm text-[var(--color-text-medium)] mb-1">
              Drag and drop your CV here
            </p>
            <p className="text-xs text-[var(--color-text-faint)] mb-4">
              or click to browse — PDF or DOCX, up to 5 MB
            </p>
            {selectedFile && (
              <p className="text-xs text-[var(--color-text-low)]">
                Selected: {selectedFile.name} ({Math.round(selectedFile.size / 1024)} KB)
              </p>
            )}
            {!selectedFile && (
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation()
                  fileInputRef.current?.click()
                }}
                className="mt-2 px-4 py-2 rounded-lg bg-[rgba(0,0,0,0.08)] hover:bg-[rgba(0,0,0,0.12)] text-sm text-[var(--color-text)] transition-colors"
              >
                Choose file
              </button>
            )}
          </div>
        ) : null}

        {/* File selected + upload button */}
        {selectedFile && status === "uploading" && (
          <div className="mt-4 flex items-center justify-between gap-4 p-4 border border-[rgba(0,0,0,0.08)] rounded-xl">
            <div>
              <p className="text-sm font-medium text-[var(--color-text-high)]">{selectedFile.name}</p>
              <p className="text-xs text-[var(--color-text-faint)]">
                {Math.round(selectedFile.size / 1024)} KB
              </p>
            </div>
            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={() => {
                  setSelectedFile(null)
                  setStatus("idle")
                  setMessage(null)
                  setProgress(0)
                }}
                className="text-xs text-[var(--color-text-faint)] hover:text-[var(--color-text)] transition-colors"
              >
                Remove
              </button>
              <button
                onClick={startUpload}
                className="px-4 py-2 rounded-lg bg-[rgba(0,0,0,0.08)] hover:bg-[rgba(0,0,0,0.12)] text-sm font-medium text-[var(--color-text)] transition-colors"
              >
                Upload & parse
              </button>
            </div>
          </div>
        )}

        {/* Parsing progress */}
        {(status === "uploading" || status === "parsing") && parseJobId && (
          <div className="mt-6 p-4 border border-[rgba(0,0,0,0.08)] rounded-xl">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-[var(--color-text-medium)]">
                {status === "uploading" ? "Uploading…" : "Parsing CV…"}
              </span>
              <span className="text-xs text-[var(--color-text-faint)] font-mono">
                {progress}%
              </span>
            </div>
            <div className="w-full h-1.5 rounded-full bg-[rgba(0,0,0,0.08)] overflow-hidden">
              <div
                className="h-full rounded-full bg-amber-500 transition-all duration-300"
                style={{ width: `${progress}%` }}
              />
            </div>
            <p className="text-xs text-[var(--color-text-faint)] mt-2">
              Job ID: {parseJobId.slice(0, 8)}…
            </p>
          </div>
        )}

        {/* Done state */}
        {status === "done" && (
          <div className="mt-6 p-4 border border-emerald-500/20 rounded-xl bg-emerald-500/5">
            <div className="flex items-center gap-2 mb-3">
              <svg
                className="w-5 h-5 text-emerald-400"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth={2}
              >
                <polyline points="20,6 9,17 4,12" />
              </svg>
              <span className="text-sm font-medium text-emerald-400">
                CV imported successfully
              </span>
            </div>

            <p className="text-xs text-[var(--color-text-faint)] mb-4">
              Your profile has been created from the uploaded CV.
              You&apos;re taken directly to your profile editor.
            </p>

            <div className="flex flex-col sm:flex-row items-center gap-3 mt-4">
              <button
                onClick={() => {
                  if (profileId) {
                    router.push(`/profiles/${profileId}`)
                  } else if (parseJobId) {
                    router.push(`/profiles?imported=true`)
                  }
                }}
                className="w-full sm:w-auto px-5 py-2.5 rounded-lg bg-[rgba(0,0,0,0.08)] hover:bg-[rgba(0,0,0,0.12)] text-sm font-medium text-[var(--color-text)] transition-colors"
              >
                View profile
              </button>
              <button
                onClick={() => {
                  setStatus("idle")
                  setProgress(0)
                  setProfileData(null)
                  setProfileId(null)
                  setParseJobId(null)
                  setSelectedFile(null)
                  setMessage(null)
                  if (fileInputRef.current) fileInputRef.current.value = ""
                }}
                className="text-sm text-[var(--color-text-faint)] hover:text-[var(--color-text-high)] transition-colors"
              >
                Upload another
              </button>
            </div>
          </div>
        )}

        {/* Error state */}
        {status === "error" && (
          <div className="mt-6 p-4 border border-red-500/20 rounded-xl bg-red-500/5 text-center">
            <div className="flex items-center gap-2 mb-3 justify-center">
              <svg
                className="w-5 h-5 text-red-400"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth={2}
              >
                <circle cx="12" cy="12" r="10" />
                <line x1="15" y1="9" x2="9" y2="15" />
                <line x1="9" y1="9" x2="15" y2="15" />
              </svg>
              <span className="text-sm font-medium text-red-400">
                Something went wrong
              </span>
            </div>
            <p className="text-xs text-[var(--color-text-faint)] mb-4">{message}</p>
            <button
              onClick={() => {
                setStatus("idle")
                setProgress(0)
                setMessage(null)
                setProfileData(null)
                setProfileId(null)
                setParseJobId(null)
                setSelectedFile(null)
                if (fileInputRef.current) fileInputRef.current.value = ""
              }}
              className="text-sm px-4 py-2 rounded-lg bg-[rgba(0,0,0,0.08)] hover:bg-[rgba(0,0,0,0.12)] text-[var(--color-text)] transition-colors"
            >
              Try again
            </button>
          </div>
        )}

        {/* Info note */}
        <div className="mt-8 p-4 border border-[rgba(0,0,0,0.04)] rounded-xl">
          <p className="text-xs text-[var(--color-text-faint)] leading-relaxed">
            Upload a PDF or DOCX of your existing CV. We'll extract your contact
            details, work history, education, and skills, then take you to the
            wizard where you can review and refine everything before saving.
          </p>
        </div>
      </div>
    </main>
  )
}
