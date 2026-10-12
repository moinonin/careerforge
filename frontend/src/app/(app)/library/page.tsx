"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { AppShell } from "@/components/app-shell";
import { listLibrary, downloadWithAuth, type LibraryDocument } from "@/lib/api/generate";

function artifactLabel(type: string): string {
  const labels: Record<string, string> = {
    cv_docx: "CV (DOCX)",
    cv_pdf: "CV (PDF)",
    cl_docx: "Cover Letter (DOCX)",
    cl_pdf: "Cover Letter (PDF)",
  };
  return labels[type] ?? type;
}

function filenameFor(doc: LibraryDocument): string {
  const ext = doc.artifact_type.endsWith("pdf") ? "pdf" : "docx";
  const base = doc.title?.replace(/\s+/g, "_") || doc.artifact_type;
  return `${base}.${ext}`;
}

type Tab = "all" | "cv" | "cover-letter";

export default function LibraryPage() {
  const [documents, setDocuments] = useState<LibraryDocument[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [downloading, setDownloading] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<Tab>("all");

  useEffect(() => {
    listLibrary()
      .then((data) => setDocuments(data.documents))
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load library"))
      .finally(() => setLoading(false));
  }, []);

  async function handleDownload(doc: LibraryDocument) {
    setDownloading(doc.id);
    setError(null);
    try {
      await downloadWithAuth(`/generate/library/${doc.id}/download`, filenameFor(doc));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Download failed");
    } finally {
      setDownloading(null);
    }
  }

  // Filter documents by active tab
  const filteredDocs = documents.filter((doc) => {
    if (activeTab === "cv") return doc.artifact_type.startsWith("cv_");
    if (activeTab === "cover-letter") return doc.artifact_type.startsWith("cl_");
    return true;
  });

  // Group documents by title so CV + cover letter artifacts sit together.
  const groups = filteredDocs.reduce<Record<string, LibraryDocument[]>>((acc, doc) => {
    (acc[doc.title] ??= []).push(doc);
    return acc;
  }, {});

  return (
    <AppShell title="Document Library" subtitle="All saved CVs and cover letters.">
      <div className="dashboard-content">
        <div className="dashboard-card">
          <div className="dashboard-card-header">
            <h2 className="dashboard-card-title">Your Documents</h2>
            <Link href="/generate" className="dashboard-button dashboard-button-primary dashboard-button-sm">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} className="dashboard-button-icon">
                <line x1="12" y1="5" x2="12" y2="19" />
                <line x1="5" y1="12" x2="19" y2="12" />
              </svg>
              New Generation
            </Link>
          </div>

          {/* Tab Navigation */}
          <div className="dashboard-tabs" style={{ marginBottom: "1rem" }}>
            {(["all", "cv", "cover-letter"] as const).map((tab) => (
              <button
                key={tab}
                className={`dashboard-tab ${activeTab === tab ? "active" : ""}`}
                onClick={() => setActiveTab(tab)}
              >
                {tab === "all" ? "All" : tab === "cv" ? "Resumes" : "Cover Letters"}
                <span className="badge badge-neutral ml-2">
                  {tab === "all"
                    ? documents.length
                    : tab === "cv"
                    ? documents.filter((d) => d.artifact_type.startsWith("cv_")).length
                    : documents.filter((d) => d.artifact_type.startsWith("cl_")).length}
                </span>
              </button>
            ))}
          </div>

          {error && (
            <div className="dashboard-generation-error"><p>{error}</p></div>
          )}

          {loading ? (
            <div className="dashboard-empty">Loading...</div>
          ) : documents.length === 0 ? (
            <div className="dashboard-empty-state">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} className="dashboard-empty-icon">
                <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
                <polyline points="14,2 14,8 20,8" />
              </svg>
              <h3>No documents yet</h3>
              <p>Generate your first CV and save it to the library.</p>
              <Link href="/generate" className="dashboard-button dashboard-button-primary" style={{ marginTop: "1rem" }}>
                Go to Generation Studio
              </Link>
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
              {Object.entries(groups).map(([title, docs]) => (
                <div key={title}>
                  <h3 className="dashboard-section-title" style={{ marginBottom: "0.5rem" }}>
                    {title}
                    {docs[0]?.job_title && <span style={{ fontWeight: 400 }}> — {docs[0].job_title}{docs[0].company_name ? ` @ ${docs[0].company_name}` : ""}</span>}
                  </h3>
                  <div className="dashboard-doc-list">
                    {docs.map((doc) => (
                      <div key={doc.id} className="dashboard-doc-item">
                        <div className="dashboard-doc-info">
                          <span className="dashboard-doc-title">
                            {doc.title}
                            <span className="dashboard-badge dashboard-badge-success" style={{ marginLeft: "0.5rem" }}>
                              {artifactLabel(doc.artifact_type)}
                            </span>
                          </span>
                          <span className="dashboard-doc-meta">
                            {doc.job_title && `${doc.job_title}`}
                            {doc.company_name && ` · ${doc.company_name}`}
                            {doc.at_score !== null && ` · ATS: ${doc.at_score}/100`}
                            {doc.created_at && ` · ${new Date(doc.created_at).toLocaleDateString()}`}
                          </span>
                        </div>
                        <button
                          className="dashboard-button dashboard-button-sm dashboard-button-secondary"
                          onClick={() => handleDownload(doc)}
                          disabled={downloading === doc.id}
                        >
                          {downloading === doc.id ? "Downloading..." : "Download"}
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </AppShell>
  );
}

// Filter and group logic (outside component for SSR compatibility)
function getFilteredDocs(documents: LibraryDocument[], activeTab: "all" | "cv" | "cover-letter") {
  return documents.filter((doc) => {
    if (activeTab === "cv") return doc.artifact_type.startsWith("cv_");
    if (activeTab === "cover-letter") return doc.artifact_type.startsWith("cl_");
    return true;
  });
}

function groupDocs(docs: LibraryDocument[]) {
  return docs.reduce<Record<string, LibraryDocument[]>>((acc, doc) => {
    (acc[doc.title] ??= []).push(doc);
    return acc;
  }, {});
}