import { getToken } from "@/lib/token-store";

const API_BASE = "/api/v1";

async function _request<T>(
  path: string,
  body?: unknown,
  method?: string,
): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: method ?? "GET",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
      ...(getToken() ? { Authorization: `Bearer ${getToken()}` } : {}),
    },
    credentials: "include",
    body: body ? JSON.stringify(body) : undefined,
  });

  if (res.status === 204) return undefined as T;

  const data = (await res.json().catch(() => ({}))) as {
    error?: string;
    detail?: string | Array<{ msg?: string }>;
  };

  if (!res.ok) {
    const raw = data.error ?? data.detail ?? `HTTP ${res.status}`;
    const msg = Array.isArray(raw)
      ? raw.map((e) => e.msg ?? String(e)).join("; ")
      : String(raw);
    throw new Error(msg);
  }
  return data as T;
}

// ── Types ────────────────────────────────────────────────────────────────

export interface GenerateRequest {
  profile_id: string;
  job_description: string;
  job_title?: string;
  company_name?: string;
  output_language?: string;
  provider?: string;
  model?: string;
}

export interface GenerateResponse {
  job_id: string;
  status: string; // "completed" (inline) | "queued" (celery)
  message?: string;
  cv_markdown?: string | null;
  cover_letter_markdown?: string | null;
  at_score?: number | null;
  missing_keywords?: string[] | null;
}

export interface GenerationJob {
  job_id: string;
  status: "pending" | "processing" | "completed" | "failed" | string;
  job_title?: string | null;
  company_name?: string | null;
  error_message?: string | null;
  cv_docx_url?: string | null;
  cv_pdf_url?: string | null;
  cl_docx_url?: string | null;
  cl_pdf_url?: string | null;
  at_score?: number | null;
  missing_keywords?: string[] | null;
  tokens_used?: number | null;
  execution_time_ms?: number | null;
  created_at?: string | null;
  completed_at?: string | null;
}

export interface LibraryDocument {
  id: string;
  title: string;
  job_title: string | null;
  company_name: string | null;
  artifact_type: string;
  file_url: string;
  at_score: number | null;
  is_temp: boolean;
  created_at: string | null;
}

// ── API functions ────────────────────────────────────────────────────────

export async function startGeneration(data: GenerateRequest): Promise<GenerateResponse> {
  return _request<GenerateResponse>("/generate", data, "POST");
}

export async function fetchJobStatus(jobId: string): Promise<GenerationJob> {
  return _request<GenerationJob>(`/generate/jobs/${jobId}`);
}

export async function saveToLibrary(
  jobId: string,
  data: { title: string; job_title?: string; company_name?: string; at_score?: number; is_temp?: boolean },
): Promise<{ job_id: string; saved: number; title: string; is_temp: boolean }> {
  return _request(`/generate/${jobId}/save`, data, "POST");
}

export async function listLibrary(): Promise<{ documents: LibraryDocument[]; total: number }> {
  return _request<{ documents: LibraryDocument[]; total: number }>("/generate/library");
}

/** Download a binary file with the auth header and trigger a browser save. */
export async function downloadWithAuth(path: string, filename: string): Promise<void> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: {
      ...(getToken() ? { Authorization: `Bearer ${getToken()}` } : {}),
    },
    credentials: "include",
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || data.error || `Download failed (HTTP ${res.status})`);
  }
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
