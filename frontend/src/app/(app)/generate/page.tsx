"use client";

import { useEffect, useState } from "react";
import { AppShell } from "@/components/app-shell";
import { listProfiles, type ProfileListEntry } from "@/lib/api/profiles";
import {
  startGeneration,
  fetchJobStatus,
  saveToLibrary,
  downloadWithAuth,
  type GenerationJob,
} from "@/lib/api/generate";

const LANGUAGES = [
  { code: "en", label: "English" },
  { code: "es", label: "Spanish" },
  { code: "de", label: "German" },
  { code: "fr", label: "French" },
];

type Result = {
  jobId: string;
  status: string;
  atScore: number | null;
  missingKeywords: string[];
  cvMarkdown: string | null;
  clMarkdown: string | null;
} | null;

export default function GeneratePage() {
  const [profiles, setProfiles] = useState<ProfileListEntry[]>([]);
  const [profileId, setProfileId] = useState("");
  const [jobDesc, setJobDesc] = useState("");
  const [jobTitle, setJobTitle] = useState("");
  const [company, setCompany] = useState("");
  const [language, setLanguage] = useState("en");
  const [generating, setGenerating] = useState(false);
  const [progressNote, setProgressNote] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<Result>(null);
  const [previewTab, setPreviewTab] = useState<"cv" | "cl">("cv");
  const [saveTitle, setSaveTitle] = useState("");
  const [showSave, setShowSave] = useState(false);
  const [saving, setSaving] = useState(false);
  const [savedMsg, setSavedMsg] = useState<string | null>(null);
  const [downloading, setDownloading] = useState<string | null>(null);

  useEffect(() => {
    listProfiles()
      .then((data) => {
        setProfiles(data);
        const defaultProfile = data.find((p) => p.is_default) ?? data[0];
        if (defaultProfile) setProfileId(defaultProfile.id);
      })
      .catch(() => setError("Failed to load profiles"));
  }, []);

  async function pollJob(jobId: string): Promise<GenerationJob> {
    const maxAttempts = 40; // ~2 minutes at 3s intervals
    for (let i = 0; i < maxAttempts; i++) {
      await new Promise((r) => setTimeout(r, 3000));
      const job = await fetchJobStatus(jobId);
      setProgressNote(`Status: ${job.status} (${i + 1}/${maxAttempts})`);
      if (job.status === "completed" || job.status === "failed") return job;
    }
    throw new Error("Generation timed out after ~2 minutes. Check the library later.");
  }

  async function handleGenerate() {
    if (!jobDesc.trim() || !profileId) return;
    setGenerating(true);
    setError(null);
    setResult(null);
    setSavedMsg(null);
    setProgressNote("Starting generation...");
    try {
      const res = await startGeneration({
        profile_id: profileId,
        job_description: jobDesc,
        job_title: jobTitle || undefined,
        company_name: company || undefined,
        output_language: language,
      });

      if (res.status === "completed") {
        // Inline mode: markdown is in the response.
        setResult({
          jobId: res.job_id,
          status: "completed",
          atScore: res.at_score ?? null,
          missingKeywords: res.missing_keywords ?? [],
          cvMarkdown: res.cv_markdown ?? null,
          clMarkdown: res.cover_letter_markdown ?? null,
        });
      } else {
        // Queued mode: poll for completion.
        const job = await pollJob(res.job_id);
        if (job.status === "failed") {
          setError(job.error_message || "Generation failed");
          return;
        }
        setResult({
          jobId: job.job_id,
          status: "completed",
          atScore: job.at_score ?? null,
          missingKeywords: job.missing_keywords ?? [],
          cvMarkdown: null,
          clMarkdown: null,
        });
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Generation failed");
    } finally {
      setGenerating(false);
      setProgressNote("");
    }
  }

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    if (!result || !saveTitle.trim()) return;
    setSaving(true);
    try {
      await saveToLibrary(result.jobId, {
        title: saveTitle.trim(),
        job_title: jobTitle || undefined,
        company_name: company || undefined,
        at_score: result.atScore ?? undefined,
        is_temp: false,
      });
      setSavedMsg("Saved to your document library.");
      setShowSave(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setSaving(false);
    }
  }

  async function handleDownload(kind: "cv" | "cl") {
    if (!result) return;
    setDownloading(kind);
    try {
      const base = jobTitle ? jobTitle.replace(/\s+/g, "_") : "document";
      const name = kind === "cv" ? `${base}_CV.docx` : `${base}_Cover_Letter.docx`;
      await downloadWithAuth(`/generate/jobs/${result.jobId}/${kind === "cv" ? "cv" : "cover-letter"}`, name);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Download failed");
    } finally {
      setDownloading(null);
    }
  }

  const activeMarkdown = previewTab === "cv" ? result?.cvMarkdown : result?.clMarkdown;

  return (
    <AppShell title="Generation Studio" subtitle="Paste a job description and generate a tailored CV + cover letter.">
      <div className="dashboard-content">
        <div className="grid gap-6 lg:grid-cols-2">
          {/* ── Left: input form ── */}
          <div className="dashboard-card">
            <div className="dashboard-card-header">
              <h2 className="dashboard-card-title">Job Input</h2>
            </div>
            <div className="dashboard-generate-form">
              <div className="dashboard-form-group">
                <label htmlFor="g-profile" className="dashboard-form-label">Source Profile</label>
                {profiles.length === 0 ? (
                  <div className="dashboard-empty" style={{ padding: "0.5rem 0" }}>
                    <p className="text-sm text-[var(--color-text-faint)]">No profiles yet.</p>
                    <a href="/profiles" className="dashboard-button dashboard-button-sm dashboard-button-primary" style={{ marginTop: "0.5rem" }}>
                      Create Your First Profile
                    </a>
                  </div>
                ) : (
                  <select id="g-profile" className="dashboard-form-select" value={profileId} onChange={(e) => setProfileId(e.target.value)}>
                    {profiles.map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.title}{p.is_default ? " (default)" : ""}
                      </option>
                    ))}
                  </select>
                )}
              </div>

              <div className="dashboard-form-group">
                <label htmlFor="g-desc" className="dashboard-form-label">Job Description</label>
                <textarea
                  id="g-desc"
                  className="dashboard-form-textarea"
                  rows={10}
                  value={jobDesc}
                  onChange={(e) => setJobDesc(e.target.value)}
                  placeholder="Paste the full job description here..."
                />
              </div>

              <div className="dashboard-form-row">
                <div className="dashboard-form-group">
                  <label htmlFor="g-title" className="dashboard-form-label">Job Title</label>
                  <input id="g-title" type="text" className="dashboard-form-input" value={jobTitle} onChange={(e) => setJobTitle(e.target.value)} placeholder="e.g. Senior Engineer" />
                </div>
                <div className="dashboard-form-group">
                  <label htmlFor="g-company" className="dashboard-form-label">Company</label>
                  <input id="g-company" type="text" className="dashboard-form-input" value={company} onChange={(e) => setCompany(e.target.value)} placeholder="e.g. Acme Corp" />
                </div>
                <div className="dashboard-form-group">
                  <label htmlFor="g-lang" className="dashboard-form-label">Output Language</label>
                  <select id="g-lang" className="dashboard-form-select" value={language} onChange={(e) => setLanguage(e.target.value)}>
                    {LANGUAGES.map((l) => (
                      <option key={l.code} value={l.code}>{l.label}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="dashboard-form-actions">
                <button
                  className="dashboard-button dashboard-button-primary"
                  onClick={handleGenerate}
                  disabled={generating || !jobDesc.trim() || !profileId}
                >
                  {generating ? "Generating..." : "Generate CV + Cover Letter"}
                </button>
              </div>
              {progressNote && <p className="dashboard-form-hint">{progressNote}</p>}
            </div>
          </div>

          {/* ── Right: result panel ── */}
          <div className="dashboard-card">
            <div className="dashboard-card-header">
              <h2 className="dashboard-card-title">Result</h2>
            </div>

            {error && (
              <div className="dashboard-generation-error">
                <p>Generation failed: {error}</p>
              </div>
            )}

            {generating && (
              <div className="dashboard-empty-state">
                <div className="animate-spin rounded-full h-8 w-8 border-4 border-muted-foreground border-t-transparent" style={{ margin: "0 auto 1rem" }} />
                <p>Generating your documents... this can take up to a minute.</p>
              </div>
            )}

            {!generating && !result && !error && (
              <div className="dashboard-empty-state">
                <h3>Nothing generated yet</h3>
                <p>Fill in the form on the left and hit Generate.</p>
              </div>
            )}

            {result && (
              <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
                <div className="dashboard-at-score">
                  <span className="dashboard-at-score-value" style={{ fontSize: "2rem" }}>
                    ATS Match: {result.atScore ?? "—"}/100
                  </span>
                </div>

                {result.missingKeywords.length > 0 && (
                  <div>
                    <p className="dashboard-form-label" style={{ marginBottom: "0.5rem" }}>Missing keywords</p>
                    <div style={{ display: "flex", flexWrap: "wrap", gap: "0.375rem" }}>
                      {result.missingKeywords.map((kw) => (
                        <span
                          key={kw}
                          style={{
                            display: "inline-block",
                            padding: "0.125rem 0.625rem",
                            borderRadius: "9999px",
                            fontSize: "0.75rem",
                            border: "1px solid rgba(0,0,0,0.15)",
                            background: "rgba(0,0,0,0.04)",
                          }}
                        >
                          {kw}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                <div>
                  <div style={{ display: "flex", gap: "0.5rem", marginBottom: "0.5rem" }}>
                    <button
                      className={`dashboard-button dashboard-button-sm ${previewTab === "cv" ? "dashboard-button-primary" : "dashboard-button-secondary"}`}
                      onClick={() => setPreviewTab("cv")}
                    >
                      CV Preview
                    </button>
                    <button
                      className={`dashboard-button dashboard-button-sm ${previewTab === "cl" ? "dashboard-button-primary" : "dashboard-button-secondary"}`}
                      onClick={() => setPreviewTab("cl")}
                    >
                      Cover Letter Preview
                    </button>
                  </div>
                  {activeMarkdown ? (
                    <pre
                      style={{
                        whiteSpace: "pre-wrap",
                        wordBreak: "break-word",
                        fontSize: "0.8125rem",
                        maxHeight: "24rem",
                        overflowY: "auto",
                        padding: "1rem",
                        border: "1px solid rgba(0,0,0,0.1)",
                        borderRadius: "0.5rem",
                        background: "rgba(0,0,0,0.02)",
                      }}
                    >
                      {activeMarkdown}
                    </pre>
                  ) : (
                    <p className="dashboard-form-hint">
                      Text preview is only available for inline generations. Use the download buttons for the DOCX files.
                    </p>
                  )}
                </div>

                <div className="dashboard-form-actions">
                  <button
                    className="dashboard-button dashboard-button-secondary"
                    onClick={() => handleDownload("cv")}
                    disabled={downloading !== null}
                  >
                    {downloading === "cv" ? "Downloading..." : "Download CV (DOCX)"}
                  </button>
                  <button
                    className="dashboard-button dashboard-button-secondary"
                    onClick={() => handleDownload("cl")}
                    disabled={downloading !== null}
                  >
                    {downloading === "cl" ? "Downloading..." : "Download Cover Letter (DOCX)"}
                  </button>
                  <button
                    className="dashboard-button dashboard-button-primary"
                    onClick={() => { setSaveTitle(jobTitle ? `${jobTitle} CV` : ""); setShowSave(true); setSavedMsg(null); }}
                  >
                    Save to Library
                  </button>
                </div>

                {savedMsg && <p className="dashboard-form-hint">✓ {savedMsg}</p>}

                {showSave && (
                  <form onSubmit={handleSave} className="dashboard-form" style={{ display: "flex", gap: "0.5rem", alignItems: "end" }}>
                    <div className="dashboard-form-group" style={{ flex: 1 }}>
                      <label htmlFor="g-save-title" className="dashboard-form-label">Library title</label>
                      <input
                        id="g-save-title"
                        type="text"
                        className="dashboard-form-input"
                        value={saveTitle}
                        onChange={(e) => setSaveTitle(e.target.value)}
                        placeholder="e.g. Acme Senior Engineer CV"
                        required
                      />
                    </div>
                    <button type="submit" className="dashboard-button dashboard-button-primary" disabled={saving}>
                      {saving ? "Saving..." : "Save"}
                    </button>
                    <button type="button" className="dashboard-button dashboard-button-secondary" onClick={() => setShowSave(false)}>
                      Cancel
                    </button>
                  </form>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </AppShell>
  );
}
