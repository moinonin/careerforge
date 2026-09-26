import { getToken } from "@/lib/token-store"

const API_BASE = "/api/v1";

async function _request<T>(
  path: string,
  body?: unknown,
  method?: string,
  query?: Record<string, string>,
): Promise<T> {
  let url = `${API_BASE}${path}`;
  if (query) {
    const params = new URLSearchParams();
    for (const [k, v] of Object.entries(query)) {
      params.set(k, v);
    }
    url += `?${params.toString()}`;
  }

  const opts: RequestInit = {
    method: method ?? "GET",
    headers: {
      "Accept": "application/json",
      "Content-Type": "application/json",
      ...(getToken() ? { Authorization: `Bearer ${getToken()}` } : {}),
    },
    credentials: "include",
    body: body ? JSON.stringify(body) : undefined,
  };

  const res = await fetch(url, opts);

  if (res.status === 204) {
    return undefined as T;
  }

  const data = (await res.json()) as {
    success?: boolean;
    error?: string;
    detail?: string;
    data?: T;
  };

  if (!res.ok) {
    const rawMsg = data.error ?? data.detail ?? `HTTP ${res.status}`;
    const msg = Array.isArray(rawMsg) ? rawMsg.map((e: any) => e.msg ?? e).join("; ") : rawMsg;
    throw new Error(msg);
  }

  if (data.success && data.data) {
    return data.data as T;
  }
  return data as T;
}

// ── Types ────────────────────────────────────────────────────────────────────

export interface ProfileContact {
  full_name: string | null;
  location: string | null;
  phone: string | null;
  email: string | null;
  linkedin: string | null;
  website_portfolio: string | null;
}

export interface ProfileEducation {
  degree: string | null;
  institution: string | null;
  location: string | null;
  start_date: string | null;
  end_date: string | null;
  thesis: string | null;
  details: string[] | null;
}

export interface ProfileExperience {
  role: string | null;
  company: string | null;
  location: string | null;
  start_date: string | null;
  end_date: string | null;
  bullets: string[] | null;
}

export interface ProfileSkills {
  technical: string[] | null;
  domain: string[] | null;
  tools: string[] | null;
  soft: string[] | null;
}

export interface ProfilePublication {
  citation: string | null;
  year: number | null;
  doi: string | null;
  link: string | null;
}

export interface ProfileCertification {
  name: string | null;
  issuer: string | null;
  year: number | null;
}

export interface ProfileLanguage {
  language: string | null;
  proficiency: string | null;
}

export interface ProfileProject {
  name: string | null;
  description: string | null;
  tech_stack: string[] | null;
  link: string | null;
}

export interface MasterProfileData {
  contact: ProfileContact | null;
  summary: string | null;
  education: ProfileEducation[];
  experience: ProfileExperience[];
  skills: ProfileSkills | null;
  publications: ProfilePublication[];
  certifications: ProfileCertification[];
  languages: ProfileLanguage[];
  projects: ProfileProject[];
  additional_info: string | null;
}

export interface ProfileListEntry {
  id: string;
  title: string;
  profile_data: MasterProfileData;
  is_default: boolean;
  is_draft: boolean;
  completeness_score: number;
  created_at: string | null;
  updated_at: string | null;
}

export interface ProfileDetail extends ProfileListEntry {
  master_prompt_text: string | null;
  owner?: {
    id: string;
    email: string;
    full_name: string | null;
  } | null;
}

export interface SkillSuggestion {
  skill: string;
  category: string | null;
}

// ── API functions ────────────────────────────────────────────────────────────

export async function listProfiles(): Promise<ProfileListEntry[]> {
  const data = await _request<{ profiles: ProfileListEntry[] }>("/profiles", undefined, "GET");
  return data.profiles;
}

export async function getProfile(profileId: string): Promise<ProfileDetail> {
  return _request<ProfileDetail>(`/profiles/${profileId}`, undefined, "GET");
}

export async function createProfile(
  title: string,
  profileData: MasterProfileData,
): Promise<ProfileDetail> {
  return _request<ProfileDetail>("/profiles", { title, profile_data: profileData }, "POST");
}

export async function updateProfile(
  profileId: string,
  updates: Partial<{
    title: string;
    profile_data: MasterProfileData;
    is_default: boolean;
    is_draft: boolean;
  }>,
): Promise<ProfileDetail> {
  return _request<ProfileDetail>(`/profiles/${profileId}`, updates, "PUT");
}

export async function patchSection(
  profileId: string,
  sectionName: string,
  sectionData: Record<string, unknown>,
): Promise<ProfileDetail> {
  return _request<ProfileDetail>(
    `/profiles/${profileId}/sections/${sectionName}`,
    sectionData,
    "PATCH",
  );
}

export async function deleteProfile(profileId: string): Promise<void> {
  await _request<void>(`/profiles/${profileId}`, undefined, "DELETE");
}

export async function setDefaultProfile(profileId: string): Promise<{ id: string; title: string; is_default: boolean }> {
  return _request<{ id: string; title: string; is_default: boolean }>(
    `/profiles/${profileId}/set-default`,
    undefined,
    "POST",
  );
}

export async function getSkillSuggestions(
  query: string,
  limit?: number,
): Promise<SkillSuggestion[]> {
  const data = await _request<{ suggestions: SkillSuggestion[] }>(
    "/profiles/skills/suggestions",
    undefined,
    "GET",
    query ? { query, limit: String(limit ?? 20) } : undefined,
  );
  return data.suggestions;
}

export async function importCv(
  file: File,
): Promise<{ parse_job_id: string; status: string; profile_id?: string }> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${API_BASE}/profiles/import`, {
    method: "POST",
    headers: {
      ...(getToken() ? { Authorization: `Bearer ${getToken()}` } : {}),
    },
    credentials: "include",
    body: form,
  });
  const data = await res.json();
  if (!res.ok) {
    const rawMsg = (data.error ?? data.detail ?? `HTTP ${res.status}`);
    const msg = Array.isArray(rawMsg) ? rawMsg.map((e: any) => e.msg ?? e).join("; ") : (rawMsg as string);
    throw new Error(msg);
  }
  return data.data ?? data as any;
}

export async function getImportStatus(parseJobId: string): Promise<{
  parse_job_id: string;
  status: string;
  message?: string;
  profile_data?: MasterProfileData;
  profile_id?: string;
  confidence_flags?: Record<string, string>;
  missing_sections?: string[];
}> {
  return _request<any>(`/profiles/import/${parseJobId}`, undefined, "GET");
}
