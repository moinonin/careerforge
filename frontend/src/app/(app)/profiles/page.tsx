"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  listProfiles,
  createProfile,
  updateProfile,
  deleteProfile,
  getProfile,
  type ProfileListEntry,
  type MasterProfileData,
  type ProfileDetail,
} from "@/lib/api/profiles";

const STEP_LABELS = [
  "Contact",
  "Summary",
  "Education",
  "Experience",
  "Skills",
  "Publications",
  "Certifications",
  "Languages",
  "Projects",
  "Additional",
];

interface FormState {
  contact: ContactForm;
  summary: string;
  education: EducationForm[];
  experience: ExperienceForm[];
  skills: SkillsForm;
  publications: PublicationForm[];
  certifications: CertificationForm[];
  languages: LanguageForm[];
  projects: ProjectForm[];
  additional_info: string;
}

interface ContactForm {
  full_name: string;
  location: string;
  phone: string | null;
  email: string | null;
  linkedin: string | null;
  website_portfolio: string | null;
}

interface EducationForm {
  degree: string;
  institution: string;
  location: string;
  start_date: string;
  end_date: string;
  thesis: string;
  details: string;
}

interface ExperienceForm {
  role: string;
  company: string;
  location: string;
  start_date: string;
  end_date: string;
  bullets: string;
}

interface SkillsForm {
  technical: string;
  domain: string;
  tools: string;
  soft: string;
}

interface PublicationForm {
  citation: string;
  year: string;
  doi: string;
  link: string;
}

interface CertificationForm {
  name: string;
  issuer: string;
  year: string;
}

interface LanguageForm {
  language: string;
  proficiency: string;
}

interface ProjectForm {
  name: string;
  description: string;
  tech_stack: string;
  link: string;
}

function formFromApi(data: MasterProfileData | ProfileDetail["profile_data"]): FormState {
  const pd = data as MasterProfileData;
  return {
    contact: {
      full_name: pd.contact?.full_name ?? "",
      location: pd.contact?.location ?? "",
      phone: pd.contact?.phone ?? null,
      email: pd.contact?.email ?? null,
      linkedin: pd.contact?.linkedin ?? null,
      website_portfolio: pd.contact?.website_portfolio ?? null,
    },
    summary: pd.summary ?? "",
    education: (pd.education ?? []).map((e) => ({
      degree: e.degree ?? "",
      institution: e.institution ?? "",
      location: e.location ?? "",
      start_date: e.start_date ?? "",
      end_date: e.end_date ?? "",
      thesis: e.thesis ?? "",
      details: (e.details ?? []).join(", "),
    })),
    experience: (pd.experience ?? []).map((e) => ({
      role: e.role ?? "",
      company: e.company ?? "",
      location: e.location ?? "",
      start_date: e.start_date ?? "",
      end_date: e.end_date ?? "",
      bullets: (e.bullets ?? []).join("\n"),
    })),
    skills: {
      technical: (pd.skills?.technical ?? []).join(", "),
      domain: (pd.skills?.domain ?? []).join(", "),
      tools: (pd.skills?.tools ?? []).join(", "),
      soft: (pd.skills?.soft ?? []).join(", "),
    },
    publications: (pd.publications ?? []).map((p) => ({
      citation: p.citation ?? "",
      year: p.year ? String(p.year) : "",
      doi: p.doi ?? "",
      link: p.link ?? "",
    })),
    certifications: (pd.certifications ?? []).map((c) => ({
      name: c.name ?? "",
      issuer: c.issuer ?? "",
      year: c.year ? String(c.year) : "",
    })),
    languages: (pd.languages ?? []).map((l) => ({
      language: l.language ?? "",
      proficiency: l.proficiency ?? "",
    })),
    projects: (pd.projects ?? []).map((p) => ({
      name: p.name ?? "",
      description: p.description ?? "",
      tech_stack: (p.tech_stack ?? []).join(", "),
      link: p.link ?? "",
    })),
    additional_info: pd.additional_info ?? "",
  };
}

function formToApi(form: FormState): MasterProfileData {
  return {
    contact: {
      full_name: form.contact.full_name || null,
      location: form.contact.location || null,
      phone: form.contact.phone || null,
      email: form.contact.email || null,
      linkedin: form.contact.linkedin || null,
      website_portfolio: form.contact.website_portfolio || null,
    },
    summary: form.summary || null,
    education: form.education
      .filter((e) => e.degree || e.institution)
      .map((e) => ({
        degree: e.degree || null,
        institution: e.institution || null,
        location: e.location || null,
        start_date: e.start_date || null,
        end_date: e.end_date || null,
        thesis: e.thesis || null,
        details: e.details
          ? e.details.split(",").map((s) => s.trim()).filter(Boolean)
          : null,
      })),
    experience: form.experience
      .filter((e) => e.role || e.company)
      .map((e) => ({
        role: e.role || null,
        company: e.company || null,
        location: e.location || null,
        start_date: e.start_date || null,
        end_date: e.end_date || null,
        bullets: e.bullets
          ? e.bullets.split("\n").map((s) => s.trim()).filter(Boolean)
          : null,
      })),
    skills: {
      technical: form.skills.technical
        ? form.skills.technical.split(",").map((s) => s.trim()).filter(Boolean)
        : null,
      domain: form.skills.domain
        ? form.skills.domain.split(",").map((s) => s.trim()).filter(Boolean)
        : null,
      tools: form.skills.tools
        ? form.skills.tools.split(",").map((s) => s.trim()).filter(Boolean)
        : null,
      soft: form.skills.soft
        ? form.skills.soft.split(",").map((s) => s.trim()).filter(Boolean)
        : null,
    },
    publications: form.publications
      .filter((p) => p.citation)
      .map((p) => ({
        citation: p.citation || null,
        year: p.year ? parseInt(p.year, 10) : null,
        doi: p.doi || null,
        link: p.link || null,
      })),
    certifications: form.certifications
      .filter((c) => c.name)
      .map((c) => ({
        name: c.name || null,
        issuer: c.issuer || null,
        year: c.year ? parseInt(c.year, 10) : null,
      })),
    languages: form.languages
      .filter((l) => l.language)
      .map((l) => ({
        language: l.language || null,
        proficiency: l.proficiency || null,
      })),
    projects: form.projects
      .filter((p) => p.name || p.description)
      .map((p) => ({
        name: p.name || null,
        description: p.description || null,
        tech_stack: p.tech_stack
          ? p.tech_stack.split(",").map((s) => s.trim()).filter(Boolean)
          : null,
        link: p.link || null,
      })),
    additional_info: form.additional_info || null,
  };
}

function emptyForm(): FormState {
  return {
    contact: { full_name: "", location: "", phone: null, email: null, linkedin: null, website_portfolio: null },
    summary: "",
    education: [],
    experience: [],
    skills: { technical: "", domain: "", tools: "", soft: "" },
    publications: [],
    certifications: [],
    languages: [],
    projects: [],
    additional_info: "",
  };
}

function SectionCard({
  title,
  addLabel,
  addFn,
  children,
  onRemove,
}: {
  title: string;
  addLabel: string;
  addFn: () => void;
  children: React.ReactNode;
  onRemove?: (i: number) => void;
}) {
  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-medium">{title}</h3>
        <button onClick={addFn} className="btn btn-secondary btn-sm">
          + {addLabel}
        </button>
      </div>
      {children}
    </div>
  );
}

function EntryField({
  value,
  onChange,
  placeholder,
  label,
  multiline,
}: {
  value: string;
  onChange: (v: string) => void;
  placeholder: string;
  label: string;
  multiline?: boolean;
}) {
  return (
    <div>
      <label className="label">{label}</label>
      {multiline ? (
        <textarea
          className="input-field min-h-[60px] resize-y"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
        />
      ) : (
        <input
          className="input-field"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
        />
      )}
    </div>
  );
}

export default function ProfilesPage() {
  const router = useRouter();
  const [profiles, setProfiles] = useState<ProfileListEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeStep, setActiveStep] = useState(0);
  const [profileId, setProfileId] = useState<string | null>(null);
  const [form, setForm] = useState<FormState>(emptyForm());
  const [saving, setSaving] = useState(false);
  const [successMsg, setSuccessMsg] = useState("");
  const [errorMsg, setErrorMsg] = useState("");
  const searchParams = useSearchParams()
  const profileIdFromUrl = searchParams.get("profileId")
  const imported = searchParams.get("imported") === "true"

  useEffect(() => {
    listProfiles()
      .then(setProfiles)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  // Pre-fill form with profile data when arriving from CV import
  useEffect(() => {
    if (!profileIdFromUrl) return
    let cancelled = false
    const fetchAndFill = async () => {
      try {
        const detail = await getProfile(profileIdFromUrl)
        if (cancelled) return
        const newForm = formFromApi(detail.profile_data)
        setForm(newForm)
        setProfileId(profileIdFromUrl)
      } catch { /* ignore errors */ }
    }
    fetchAndFill()
    return () => { cancelled = true }
  }, [profileIdFromUrl])

  const selectProfile = async (id: string) => {
    try {
      const detail = await getProfile(id);
      setProfileId(id);
      setForm(formFromApi(detail.profile_data));
      setActiveStep(0);
      setErrorMsg("");
    } catch (e: any) {
      setErrorMsg("Failed to load profile: " + e.message);
    }
  };

  const handleDeleteProfile = async (id: string, title: string) => {
    if (!confirm(`Delete "${title}"? This cannot be undone.`)) return
    try {
      await deleteProfile(id)
      setProfiles(prev => prev.filter(p => p.id !== id))
      if (profileId === id) {
        setProfileId(null)
        setForm(emptyForm())
      }
      setErrorMsg("Profile deleted")
      setTimeout(() => setErrorMsg(""), 3000)
    } catch (e: any) {
      setErrorMsg("Failed to delete profile: " + e.message)
    }
  };

  const handleNewProfile = async () => {
    try {
      const data = await createProfile("New Profile", {
        contact: {
          full_name: "",
          location: "",
          phone: null,
          email: null,
          linkedin: null,
          website_portfolio: null,
        },
        summary: "",
        education: [],
        experience: [],
        skills: { technical: null, domain: null, tools: null, soft: null },
        publications: [],
        certifications: [],
        languages: [],
        projects: [],
        additional_info: "",
      });
      setProfileId(data.id);
      setProfiles((prev) => [data, ...prev]);
      setForm(formFromApi(data.profile_data));
      setActiveStep(0);
      setErrorMsg("");
    } catch (e: any) {
      setErrorMsg("Failed to create profile: " + e.message);
    }
  };

  const handleSave = async (asDraft = false) => {
    if (!profileId) return;
    setSaving(true);
    setSuccessMsg("");
    setErrorMsg("");
    try {
      const data = await updateProfile(profileId, {
        profile_data: formToApi(form),
        is_draft: asDraft,
      });
      setProfileId(data.id);
      setProfiles((prev) => prev.map((p) => (p.id === data.id ? data : p)));
      setSuccessMsg(asDraft ? "Draft saved" : "Profile saved");
      setTimeout(() => setSuccessMsg(""), 3000);
    } catch (e: any) {
      setErrorMsg("Save failed: " + e.message);
    } finally {
      setSaving(false);
    }
  };

  const fieldUpdate = (
    section: keyof FormState,
    index: number,
    key: string,
    value: string
  ) => {
    setForm((f) => {
      if (index === 0 && typeof f[section] === "object" && f[section] !== null && !Array.isArray(f[section])) {
        return {
          ...f,
          [section]: {
            ...(f[section] as unknown as Record<string, string>),
            [key]: value,
          } as any,
        };
      }
      if (Array.isArray(f[section])) {
        const arr = [...f[section] as any[]];
        if (arr[index]) {
          arr[index] = { ...(arr[index] as Record<string, string>), [key]: value };
        }
        return { ...f, [section]: arr as any };
      }
      return f;
    });
  };

  const addEntry = (section: keyof FormState, emptyRow: any) => {
    setForm((f) => {
      const next = { ...f };
      if (Array.isArray(next[section])) {
        next[section] = [...(next[section] as any[]), emptyRow] as any;
      }
      return next as FormState;
    });
  };

  const removeEntry = (section: keyof FormState, index: number) => {
    setForm((f) => {
      const next = { ...f };
      if (Array.isArray(next[section])) {
        next[section] = (next[section] as any[]).filter((_, i) => i !== index) as any;
      }
      return next as FormState;
    });
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[var(--color-bg)] flex items-center justify-center">
        <div className="animate-spin w-5 h-5 border-2 border-[rgba(0,0,0,0.12)] border-t-white rounded-full" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[var(--color-bg)] text-[var(--color-text)]">
      <header className="flex items-center justify-between px-6 py-4 border-b border-[rgba(0,0,0,0.04)]">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-[rgba(0,0,0,0.08)] flex items-center justify-center text-xs font-bold">
            CF
          </div>
          <span className="text-sm font-medium">CareerForge</span>
        </div>
        <nav className="flex items-center gap-4">
          <button
            onClick={() => listProfiles().then(setProfiles).catch(console.error)}
            className="text-xs text-[var(--color-text-low)] hover:text-[var(--color-text)] transition-colors"
          >
            Refresh
          </button>
          <button
            onClick={() => router.push("/")}
            className="text-xs text-[var(--color-text-low)] hover:text-[var(--color-text)] transition-colors"
          >
            Home
          </button>
        </nav>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-6">
        {errorMsg && (
          <div className="mb-4 p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-sm text-red-400">
            {errorMsg}
          </div>
        )}

        <section className="mb-6">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-lg font-semibold">Profiles</h2>
            <button onClick={handleNewProfile} className="btn btn-primary btn-sm">
              + New Profile
            </button>
            <button onClick={() => router.push("/profiles/upload")} className="btn btn-secondary btn-sm">
              Import CV
            </button>
          </div>

          {profiles.length === 0 ? (
            <div className="text-center py-12 text-[var(--color-text-faint)] text-sm">
              No profiles yet. <a href="/profiles/upload" className="text-blue-400 hover:underline">Import a CV</a> to pre-fill your profile, or click "New Profile" to fill the form manually.
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {profiles.map((p) => (
                <div
                  key={p.id}
                  className={`card cursor-pointer transition-colors ${
                    p.id === profileId ? "border-blue-500/50 bg-blue-500/5" : "hover:border-[rgba(0,0,0,0.12)]"
                  }`}
                  onClick={() => selectProfile(p.id)}
                >
                  <div className="flex items-start justify-between gap-2 mb-2">
                    <h3 className="font-medium text-sm truncate">{p.title}</h3>
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        handleDeleteProfile(p.id, p.title)
                      }}
                      className="text-xs text-red-400 hover:text-red-600 transition-colors shrink-0"
                      title="Delete profile"
                    >
                      ✕
                    </button>
                    {p.is_default && (
                      <span className="badge badge-default text-[10px]">Default</span>
                    )}
                  </div>
                  <div className="text-xs text-[var(--color-text-faint)] space-y-0.5">
                    <p>{p.completeness_score}/100 complete</p>
                    <p>Updated {new Date(p.updated_at ?? "").toLocaleDateString()}</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>

        {profileId && (
          <section className="card">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-base font-semibold">
                Edit: {form.contact.full_name || "New Profile"}
              </h2>
              <div className="flex items-center gap-2">
                {successMsg && (
                  <span className="text-xs text-green-400">{successMsg}</span>
                )}
                <button
                  onClick={() => handleSave(true)}
                  disabled={saving}
                  className="btn btn-secondary btn-sm"
                >
                  Save Draft
                </button>
                <button
                  onClick={() => handleSave(false)}
                  disabled={saving}
                  className="btn btn-primary btn-sm"
                >
                  {saving ? "Saving..." : "Save & Finish"}
                </button>
              </div>
            </div>

            <div className="flex items-center gap-1 mb-6 overflow-x-auto pb-2">
              {STEP_LABELS.map((label, i) => (
                <button
                  key={label}
                  onClick={() => setActiveStep(i)}
                  className={`flex-shrink-0 px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                    i === activeStep
                      ? "bg-[rgba(0,0,0,0.08)] text-[var(--color-text)]"
                      : i < activeStep
                      ? "text-[var(--color-text-low)] hover:text-[var(--color-text-high)]"
                      : "text-[var(--color-text-faint)] hover:text-[var(--color-text-low)]"
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>

            <div className="min-h-[320px]">
              {activeStep === 0 && (
                <div className="space-y-3 animate-fade-in">
                  <h3 className="text-sm font-medium">Contact Information</h3>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <EntryField
                      label="Full Name *"
                      placeholder="Jane Smith"
                      value={form.contact.full_name}
                      onChange={(v) => fieldUpdate("contact", 0, "full_name", v)}
                    />
                    <EntryField
                      label="Location *"
                      placeholder="San Francisco, CA"
                      value={form.contact.location}
                      onChange={(v) => fieldUpdate("contact", 0, "location", v)}
                    />
                    <EntryField
                      label="Phone"
                      placeholder="+1 555-000-0000"
                      value={form.contact.phone ?? ""}
                      onChange={(v) => fieldUpdate("contact", 0, "phone", v)}
                    />
                    <EntryField
                      label="Email"
                      placeholder="jane@example.com"
                      value={form.contact.email ?? ""}
                      onChange={(v) => fieldUpdate("contact", 0, "email", v)}
                    />
                    <EntryField
                      label="LinkedIn URL"
                      placeholder="https://linkedin.com/in/jane"
                      value={form.contact.linkedin ?? ""}
                      onChange={(v) => fieldUpdate("contact", 0, "linkedin", v)}
                    />
                    <EntryField
                      label="Portfolio / Website"
                      placeholder="https://janesmith.dev"
                      value={form.contact.website_portfolio ?? ""}
                      onChange={(v) => fieldUpdate("contact", 0, "website_portfolio", v)}
                    />
                  </div>
                </div>
              )}

              {activeStep === 1 && (
                <div className="animate-fade-in">
                  <h3 className="text-sm font-medium mb-3">Professional Summary</h3>
                  <textarea
                    className="input-field min-h-[120px] resize-y"
                    value={form.summary}
                    onChange={(e) => setForm((f) => ({ ...f, summary: e.target.value }))}
                    placeholder="3-4 lines summarizing your background, key strengths, and what you bring to a role..."
                  />
                  <p className="text-xs text-[var(--color-text-faint)] mt-1">
                    Leave blank to auto-generate at generation time.
                  </p>
                </div>
              )}

              {activeStep === 2 && (
                <div className="animate-fade-in">
                  <SectionCard
                    title="Education"
                    addLabel="Add Entry"
                    addFn={() =>
                      addEntry("education", {
                        degree: "",
                        institution: "",
                        location: "",
                        start_date: "",
                        end_date: "",
                        thesis: "",
                        details: "",
                      })
                    }
                    onRemove={(i) => removeEntry("education", i)}
                  >
                    {form.education.map((edu, i) => (
                      <div
                        key={i}
                        className="border border-[rgba(0,0,0,0.04)] rounded-lg p-3 mb-2 relative group"
                      >
                        <button
                          onClick={() => removeEntry("education", i)}
                          className="absolute top-2 right-2 text-[var(--color-text-faint)] hover:text-red-400 transition-colors"
                        >
                          ×
                        </button>
                        <div className="grid grid-cols-2 gap-2">
                          <EntryField
                            label="Degree"
                            placeholder="MSc Computer Science"
                            value={edu.degree}
                            onChange={(v) => fieldUpdate("education", i, "degree", v)}
                          />
                          <EntryField
                            label="Institution"
                            placeholder="University of X"
                            value={edu.institution}
                            onChange={(v) => fieldUpdate("education", i, "institution", v)}
                          />
                          <EntryField
                            label="Location"
                            placeholder="City, Country"
                            value={edu.location}
                            onChange={(v) => fieldUpdate("education", i, "location", v)}
                          />
                          <EntryField
                            label="Details / Honors"
                            placeholder="GPA, honors, coursework"
                            value={edu.details}
                            onChange={(v) => fieldUpdate("education", i, "details", v)}
                          />
                        </div>
                        <div className="grid grid-cols-2 gap-2 mt-2">
                          <EntryField
                            label="Start Date"
                            placeholder="2019"
                            value={edu.start_date}
                            onChange={(v) => fieldUpdate("education", i, "start_date", v)}
                          />
                          <EntryField
                            label="End Date"
                            placeholder="2021 or Present"
                            value={edu.end_date}
                            onChange={(v) => fieldUpdate("education", i, "end_date", v)}
                          />
                        </div>
                        <EntryField
                          label="Thesis (optional)"
                          placeholder="Thesis title"
                          value={edu.thesis}
                          onChange={(v) => fieldUpdate("education", i, "thesis", v)}
                        />
                      </div>
                    ))}
                  </SectionCard>
                </div>
              )}

              {activeStep === 3 && (
                <div className="animate-fade-in">
                  <SectionCard
                    title="Work Experience"
                    addLabel="Add Entry"
                    addFn={() =>
                      addEntry("experience", {
                        role: "",
                        company: "",
                        location: "",
                        start_date: "",
                        end_date: "",
                        bullets: "",
                      })
                    }
                    onRemove={(i) => removeEntry("experience", i)}
                  >
                    {form.experience.map((exp, i) => (
                      <div
                        key={i}
                        className="border border-[rgba(0,0,0,0.04)] rounded-lg p-3 mb-2 relative group"
                      >
                        <button
                          onClick={() => removeEntry("experience", i)}
                          className="absolute top-2 right-2 text-[var(--color-text-faint)] hover:text-red-400 transition-colors"
                        >
                          ×
                        </button>
                        <div className="grid grid-cols-2 gap-2">
                          <EntryField
                            label="Role"
                            placeholder="Senior Engineer"
                            value={exp.role}
                            onChange={(v) => fieldUpdate("experience", i, "role", v)}
                          />
                          <EntryField
                            label="Company"
                            placeholder="Acme Corp"
                            value={exp.company}
                            onChange={(v) => fieldUpdate("experience", i, "company", v)}
                          />
                          <EntryField
                            label="Location"
                            placeholder="City, Country"
                            value={exp.location}
                            onChange={(v) => fieldUpdate("experience", i, "location", v)}
                          />
                          <EntryField
                            label="Tech / Summary"
                            placeholder="Key responsibilities"
                            value={exp.bullets}
                            onChange={(v) => fieldUpdate("experience", i, "bullets", v)}
                          />
                        </div>
                        <div className="grid grid-cols-2 gap-2 mt-2">
                          <EntryField
                            label="Start Date"
                            placeholder="2019"
                            value={exp.start_date}
                            onChange={(v) => fieldUpdate("experience", i, "start_date", v)}
                          />
                          <EntryField
                            label="End Date"
                            placeholder="2021 or Present"
                            value={exp.end_date}
                            onChange={(v) => fieldUpdate("experience", i, "end_date", v)}
                          />
                        </div>
                      </div>
                    ))}
                  </SectionCard>
                </div>
              )}

              {activeStep === 4 && (
                <div className="animate-fade-in">
                  <h3 className="text-sm font-medium mb-3">Skills</h3>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <EntryField
                      label="Technical Skills"
                      placeholder="Python, React, SQL (comma-separated)"
                      value={form.skills.technical}
                      onChange={(v) =>
                        setForm((f) => ({ ...f, skills: { ...f.skills, technical: v } }))
                      }
                    />
                    <EntryField
                      label="Domain Knowledge"
                      placeholder="Machine Learning, Finance"
                      value={form.skills.domain}
                      onChange={(v) =>
                        setForm((f) => ({ ...f, skills: { ...f.skills, domain: v } }))
                      }
                    />
                    <EntryField
                      label="Tools & Platforms"
                      placeholder="Git, Docker, AWS"
                      value={form.skills.tools}
                      onChange={(v) =>
                        setForm((f) => ({ ...f, skills: { ...f.skills, tools: v } }))
                      }
                    />
                    <EntryField
                      label="Soft Skills"
                      placeholder="Leadership, Communication"
                      value={form.skills.soft}
                      onChange={(v) =>
                        setForm((f) => ({ ...f, skills: { ...f.skills, soft: v } }))
                      }
                    />
                  </div>
                </div>
              )}

              {activeStep === 5 && (
                <div className="animate-fade-in">
                  <SectionCard
                    title="Publications"
                    addLabel="Add Publication"
                    addFn={() =>
                      addEntry("publications", {
                        citation: "",
                        year: "",
                        doi: "",
                        link: "",
                      })
                    }
                    onRemove={(i) => removeEntry("publications", i)}
                  >
                    {form.publications.map((pub, i) => (
                      <div
                        key={i}
                        className="border border-[rgba(0,0,0,0.04)] rounded-lg p-3 mb-2 relative group"
                      >
                        <button
                          onClick={() => removeEntry("publications", i)}
                          className="absolute top-2 right-2 text-[var(--color-text-faint)] hover:text-red-400 transition-colors"
                        >
                          ×
                        </button>
                        <div className="grid grid-cols-2 gap-2">
                          <div className="col-span-2">
                            <EntryField
                              label="Citation"
                              placeholder="Author, Title, Journal, Year"
                              value={pub.citation}
                              onChange={(v) => fieldUpdate("publications", i, "citation", v)}
                            />
                          </div>
                          <EntryField
                            label="Year"
                            placeholder="2023"
                            value={pub.year}
                            onChange={(v) => fieldUpdate("publications", i, "year", v)}
                          />
                          <EntryField
                            label="DOI"
                            placeholder="10.xxxx/xxxxx"
                            value={pub.doi}
                            onChange={(v) => fieldUpdate("publications", i, "doi", v)}
                          />
                          <EntryField
                            label="Link"
                            placeholder="https://..."
                            value={pub.link}
                            onChange={(v) => fieldUpdate("publications", i, "link", v)}
                          />
                        </div>
                      </div>
                    ))}
                  </SectionCard>
                </div>
              )}

              {activeStep === 6 && (
                <div className="animate-fade-in">
                  <SectionCard
                    title="Certifications"
                    addLabel="Add Certification"
                    addFn={() =>
                      addEntry("certifications", { name: "", issuer: "", year: "" })
                    }
                    onRemove={(i) => removeEntry("certifications", i)}
                  >
                    {form.certifications.map((cert, i) => (
                      <div
                        key={i}
                        className="border border-[rgba(0,0,0,0.04)] rounded-lg p-3 mb-2 relative group"
                      >
                        <button
                          onClick={() => removeEntry("certifications", i)}
                          className="absolute top-2 right-2 text-[var(--color-text-faint)] hover:text-red-400 transition-colors"
                        >
                          ×
                        </button>
                        <div className="grid grid-cols-3 gap-2">
                          <EntryField
                            label="Name"
                            placeholder="AWS Certified Solutions Architect"
                            value={cert.name}
                            onChange={(v) => fieldUpdate("certifications", i, "name", v)}
                          />
                          <EntryField
                            label="Issuer"
                            placeholder="Amazon Web Services"
                            value={cert.issuer}
                            onChange={(v) => fieldUpdate("certifications", i, "issuer", v)}
                          />
                          <EntryField
                            label="Year"
                            placeholder="2023"
                            value={cert.year}
                            onChange={(v) => fieldUpdate("certifications", i, "year", v)}
                          />
                        </div>
                      </div>
                    ))}
                  </SectionCard>
                </div>
              )}

              {activeStep === 7 && (
                <div className="animate-fade-in">
                  <SectionCard
                    title="Languages"
                    addLabel="Add Language"
                    addFn={() =>
                      addEntry("languages", { language: "", proficiency: "" })
                    }
                    onRemove={(i) => removeEntry("languages", i)}
                  >
                    {form.languages.map((lang, i) => (
                      <div
                        key={i}
                        className="border border-[rgba(0,0,0,0.04)] rounded-lg p-3 mb-2 relative group"
                      >
                        <button
                          onClick={() => removeEntry("languages", i)}
                          className="absolute top-2 right-2 text-[var(--color-text-faint)] hover:text-red-400 transition-colors"
                        >
                          ×
                        </button>
                        <div className="grid grid-cols-2 gap-2">
                          <EntryField
                            label="Language"
                            placeholder="English"
                            value={lang.language}
                            onChange={(v) => fieldUpdate("languages", i, "language", v)}
                          />
                          <div className="gap-1">
                            <label className="label">Proficiency</label>
                            <select
                              className="input-field"
                              value={lang.proficiency}
                              onChange={(e) =>
                                fieldUpdate("languages", i, "proficiency", e.target.value)
                              }
                            >
                              <option value="">Select...</option>
                              <option value="Native">Native</option>
                              <option value="Fluent">Fluent</option>
                              <option value="Advanced">Advanced</option>
                              <option value="Intermediate">Intermediate</option>
                              <option value="Basic">Basic</option>
                            </select>
                          </div>
                        </div>
                      </div>
                    ))}
                  </SectionCard>
                </div>
              )}

              {activeStep === 8 && (
                <div className="animate-fade-in">
                  <SectionCard
                    title="Projects"
                    addLabel="Add Project"
                    addFn={() =>
                      addEntry("projects", {
                        name: "",
                        description: "",
                        tech_stack: "",
                        link: "",
                      })
                    }
                    onRemove={(i) => removeEntry("projects", i)}
                  >
                    {form.projects.map((proj, i) => (
                      <div
                        key={i}
                        className="border border-[rgba(0,0,0,0.04)] rounded-lg p-3 mb-2 relative group"
                      >
                        <button
                          onClick={() => removeEntry("projects", i)}
                          className="absolute top-2 right-2 text-[var(--color-text-faint)] hover:text-red-400 transition-colors"
                        >
                          ×
                        </button>
                        <div className="space-y-2">
                          <EntryField
                            label="Name"
                            placeholder="Project name"
                            value={proj.name}
                            onChange={(v) => fieldUpdate("projects", i, "name", v)}
                          />
                          <EntryField
                            label="Description"
                            placeholder="What did you build?"
                            value={proj.description}
                            onChange={(v) => fieldUpdate("projects", i, "description", v)}
                            multiline
                          />
                          <div className="grid grid-cols-2 gap-2">
                            <EntryField
                              label="Tech Stack"
                              placeholder="React, Node.js"
                              value={proj.tech_stack}
                              onChange={(v) => fieldUpdate("projects", i, "tech_stack", v)}
                            />
                            <EntryField
                              label="Link"
                              placeholder="https://github.com/..."
                              value={proj.link}
                              onChange={(v) => fieldUpdate("projects", i, "link", v)}
                            />
                          </div>
                        </div>
                      </div>
                    ))}
                  </SectionCard>
                </div>
              )}

              {activeStep === 9 && (
                <div className="animate-fade-in">
                  <h3 className="text-sm font-medium mb-3">Additional Information</h3>
                  <textarea
                    className="input-field min-h-[100px] resize-y"
                    value={form.additional_info}
                    onChange={(e) =>
                      setForm((f) => ({ ...f, additional_info: e.target.value }))
                    }
                    placeholder="Awards, volunteer work, interests, professional memberships..."
                  />
                </div>
              )}
            </div>
          </section>
        )}
      </main>
    </div>
  );
}
