"use client"

import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import { useAuth, useAuthLoading } from "@/lib/auth-context"
import { logout, getMe } from "@/lib/auth"

const LLM_PROVIDERS = [
  { id: "openai", name: "OpenAI", models: ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"], requiresKey: true },
  { id: "anthropic", name: "Anthropic", models: ["claude-3-5-sonnet-20241022", "claude-3-5-haiku-20241022", "claude-3-opus-20240229"], requiresKey: true },
  { id: "ollama", name: "Ollama (Local)", models: ["llama3.1:70b", "llama3.1:8b", "mistral:7b", "codellama:7b"], requiresKey: false },
  { id: "custom", name: "Custom OpenAI-Compatible", models: [], requiresKey: true },
] as const

type LLMConfig = {
  id: string
  provider: string
  base_url: string | null
  model_name: string
  is_active: boolean
  has_api_key: boolean
  created_at: string
  updated_at: string
}

type LLMConfigCreate = {
  provider: string
  base_url: string | null
  api_key: string | null
  model_name: string
  is_active: boolean
}

async function apiRequest<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(`${process.env.NEXT_PUBLIC_API_BASE || ""}/api/v1${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
    credentials: "include",
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Request failed" }))
    throw new Error(err.detail || `HTTP ${res.status}`)
  }
  if (res.status === 204) return {} as T
  return res.json()
}

async function getAuthHeaders(): Promise<Record<string, string>> {
  const token = localStorage.getItem("access_token")
  return token ? { Authorization: `Bearer ${token}` } : {}
}

async function listLLMConfigs(): Promise<LLMConfig[]> {
  const headers = await getAuthHeaders()
  return apiRequest<LLMConfig[]>("/llm-config", { headers })
}

async function createLLMConfig(data: LLMConfigCreate): Promise<LLMConfig> {
  const headers = await getAuthHeaders()
  return apiRequest<LLMConfig>("/llm-config", {
    method: "POST",
    headers,
    body: JSON.stringify(data),
  })
}

async function updateLLMConfig(configId: string, data: Partial<LLMConfigCreate>): Promise<LLMConfig> {
  const headers = await getAuthHeaders()
  return apiRequest<LLMConfig>(`/llm-config/${configId}`, {
    method: "PUT",
    headers,
    body: JSON.stringify(data),
  })
}

async function deleteLLMConfig(configId: string): Promise<void> {
  const headers = await getAuthHeaders()
  return apiRequest<void>(`/llm-config/${configId}`, {
    method: "DELETE",
    headers,
  })
}

async function testLLMConfig(configId: string): Promise<{ success: boolean; message: string; latency_ms: number | null }> {
  const headers = await getAuthHeaders()
  return apiRequest<{ success: boolean; message: string; latency_ms: number | null }>(`/llm-config/${configId}/test`, {
    method: "POST",
    headers,
  })
}

function SettingsTab() {
  const [configs, setConfigs] = useState<LLMConfig[]>([])
  const [loading, setLoading] = useState(false)
  const [showForm, setShowForm] = useState(false)
  const [editingConfig, setEditingConfig] = useState<LLMConfig | null>(null)
  const [formData, setFormData] = useState({
    provider: "openai",
    base_url: "",
    api_key: "",
    model_name: "",
    is_active: true,
  })
  const [testResults, setTestResults] = useState<Record<string, { success: boolean; message: string; loading: boolean; latency_ms: number | null }>>({})

  useEffect(() => {
    loadConfigs()
  }, [])

  async function loadConfigs() {
    try {
      const data = await listLLMConfigs()
      setConfigs(data)
    } catch (err) {
      console.error("Failed to load LLM configs:", err)
    }
  }

  function handleProviderChange(providerId: string) {
    const provider = LLM_PROVIDERS.find(p => p.id === providerId)
    if (provider) {
      setFormData(prev => ({
        ...prev,
        provider: providerId,
        model_name: provider.models[0] || "",
        base_url: providerId === "ollama" ? "http://localhost:11434/v1" : "",
      }))
    }
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const submit = async () => {
      setLoading(true)
      try {
        if (editingConfig) {
          await updateLLMConfig(editingConfig.id, formData)
        } else {
          await createLLMConfig(formData as LLMConfigCreate)
        }
        setShowForm(false)
        setEditingConfig(null)
        resetForm()
        await loadConfigs()
      } catch (err) {
        alert(err instanceof Error ? err.message : "Failed to save config")
      } finally {
        setLoading(false)
      }
    }
    submit()
  }

  function resetForm() {
    setFormData({
      provider: "openai",
      base_url: "",
      api_key: "",
      model_name: "",
      is_active: true,
    })
  }

  function handleEdit(config: LLMConfig) {
    setEditingConfig(config)
    setFormData({
      provider: config.provider,
      base_url: config.base_url || "",
      api_key: "",
      model_name: config.model_name,
      is_active: config.is_active,
    })
    setShowForm(true)
  }

  async function handleTest(configId: string) {
    setTestResults(prev => ({ ...prev, [configId]: { success: false, message: "Testing...", loading: true, latency_ms: null } }))
    try {
      const result = await testLLMConfig(configId)
      setTestResults(prev => ({ ...prev, [configId]: { ...result, loading: false } }))
    } catch (err) {
      setTestResults(prev => ({ ...prev, [configId]: { success: false, message: err instanceof Error ? err.message : "Test failed", loading: false, latency_ms: null } }))
    }
  }

  async function handleDelete(configId: string) {
    if (!confirm("Delete this LLM configuration?")) return
    try {
      await deleteLLMConfig(configId)
      await loadConfigs()
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to delete")
    }
  }

  async function handleActivate(configId: string) {
    try {
      await updateLLMConfig(configId, { is_active: true })
      await loadConfigs()
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to activate")
    }
  }

  const activeConfig = configs.find(c => c.is_active)

  return (
    <div className="dashboard-content">
      <div className="dashboard-card">
        <div className="dashboard-card-header">
          <h2 className="dashboard-card-title">LLM Configuration (BYOK)</h2>
          <p className="dashboard-card-subtitle">
            Configure your LLM providers. Bring your own API keys or use local models via Ollama.
          </p>
        </div>

        {activeConfig && (
          <div className="dashboard-alert dashboard-alert-success">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} className="dashboard-alert-icon">
              <path d="M22 11.08V12a10 10 0 11-5.93-9.14" />
              <polyline points="22 4 12 14.01 9 11.01" />
            </svg>
            <div>
              <p className="dashboard-alert-title">Active Provider: {LLM_PROVIDERS.find(p => p.id === activeConfig.provider)?.name ?? activeConfig.provider}</p>
              <p className="dashboard-alert-text">Model: {activeConfig.model_name} {activeConfig.has_api_key ? "🔒" : "🔓 (no API key needed)"}</p>
            </div>
          </div>
        )}

        {configs.length === 0 && !showForm && (
          <div className="dashboard-empty-state">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} className="dashboard-empty-icon">
              <circle cx="12" cy="12" r="10" />
              <path d="M12 16v-4" />
              <path d="M12 8h.01" />
            </svg>
            <h3>No LLM configurations yet</h3>
            <p>Add your first LLM provider to start generating resumes and cover letters.</p>
            <button
              className="dashboard-button dashboard-button-primary"
              onClick={() => setShowForm(true)}
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} className="dashboard-button-icon">
                <line x1="12" y1="5" x2="12" y2="19" />
                <line x1="5" y1="12" x2="19" y2="12" />
              </svg>
              Add LLM Configuration
            </button>
          </div>
        )}

        {showForm && (
          <form onSubmit={handleSubmit} className="dashboard-form">
            <div className="dashboard-form-group">
              <label htmlFor="provider" className="dashboard-form-label">Provider</label>
              <select
                id="provider"
                value={formData.provider}
                onChange={e => handleProviderChange(e.target.value)}
                className="dashboard-form-select"
              >
                {LLM_PROVIDERS.map(p => (
                  <option key={p.id} value={p.id}>{p.name}</option>
                ))}
              </select>
            </div>

            <div className="dashboard-form-group">
              <label htmlFor="model_name" className="dashboard-form-label">Model</label>
              <select
                id="model_name"
                value={formData.model_name}
                onChange={e => setFormData(prev => ({ ...prev, model_name: e.target.value }))}
                className="dashboard-form-select"
              >
                {LLM_PROVIDERS.find(p => p.id === formData.provider)?.models.map(m => (
                  <option key={m} value={m}>{m}</option>
                ))}
              </select>
              {LLM_PROVIDERS.find(p => p.id === formData.provider)?.models.length === 0 && (
                <input
                  type="text"
                  id="model_name"
                  value={formData.model_name}
                  onChange={e => setFormData(prev => ({ ...prev, model_name: e.target.value }))}
                  className="dashboard-form-input"
                  placeholder="Enter model name (e.g., gpt-4o, llama3.1:70b)"
                  required
                />
              )}
            </div>

            <div className="dashboard-form-group">
              <label htmlFor="base_url" className="dashboard-form-label">
                Base URL (optional)
                {formData.provider === "ollama" && <span className="dashboard-form-hint"> Default: http://localhost:11434/v1</span>}
                {formData.provider === "custom" && <span className="dashboard-form-hint"> Required for custom endpoints</span>}
              </label>
              <input
                type="text"
                id="base_url"
                value={formData.base_url}
                onChange={e => setFormData(prev => ({ ...prev, base_url: e.target.value }))}
                className="dashboard-form-input"
                placeholder={formData.provider === "ollama" ? "http://localhost:11434/v1" : "https://api.example.com/v1"}
              />
            </div>

            {LLM_PROVIDERS.find(p => p.id === formData.provider)?.requiresKey && (
              <div className="dashboard-form-group">
                <label htmlFor="api_key" className="dashboard-form-label">API Key</label>
                <input
                  type="password"
                  id="api_key"
                  value={formData.api_key}
                  onChange={e => setFormData(prev => ({ ...prev, api_key: e.target.value }))}
                  className="dashboard-form-input"
                  placeholder={editingConfig ? "Leave blank to keep current key" : "Enter your API key"}
                  required={!editingConfig}
                  autoComplete="off"
                />
                <p className="dashboard-form-hint">
                  Your API key is encrypted at rest using AES-256-GCM and never returned in API responses.
                </p>
              </div>
            )}

            <div className="dashboard-form-group dashboard-form-checkbox">
              <input
                type="checkbox"
                id="is_active"
                checked={formData.is_active}
                onChange={e => setFormData(prev => ({ ...prev, is_active: e.target.checked }))}
              />
              <label htmlFor="is_active">Set as active configuration</label>
            </div>

            <div className="dashboard-form-actions">
              <button type="button" className="dashboard-button dashboard-button-secondary" onClick={() => { setShowForm(false); setEditingConfig(null); resetForm(); }}>
                Cancel
              </button>
              <button type="submit" className="dashboard-button dashboard-button-primary" disabled={loading}>
                {loading ? "Saving..." : editingConfig ? "Update Configuration" : "Add Configuration"}
              </button>
            </div>
          </form>
        )}

        {configs.length > 0 && (
          <div className="dashboard-config-list">
            <h3 className="dashboard-section-title">Your Configurations</h3>
            {configs.map(config => (
              <div key={config.id} className={`dashboard-config-item ${config.is_active ? "active" : ""}`}>
                <div className="dashboard-config-info">
                  <div className="dashboard-config-header">
                    <span className="dashboard-config-provider">
                      {LLM_PROVIDERS.find(p => p.id === config.provider)?.name ?? config.provider}
                    </span>
                    {config.is_active && <span className="dashboard-badge dashboard-badge-success">Active</span>}
                  </div>
                  <div className="dashboard-config-details">
                    <span>Model: <strong>{config.model_name}</strong></span>
                    {config.base_url && <span>Base URL: <code>{config.base_url}</code></span>}
                    <span>API Key: {config.has_api_key ? "🔒 Configured" : "🔓 Not required / not set"}</span>
                    <span>Created: {new Date(config.created_at).toLocaleDateString()}</span>
                  </div>
                </div>
                <div className="dashboard-config-actions">
                  {!config.is_active && (
                    <button
                      className="dashboard-button dashboard-button-sm"
                      onClick={() => handleActivate(config.id)}
                    >
                      Activate
                    </button>
                  )}
                  <button
                    className="dashboard-button dashboard-button-sm dashboard-button-secondary"
                    onClick={() => handleTest(config.id)}
                    disabled={testResults[config.id]?.loading}
                  >
                    {testResults[config.id]?.loading ? "Testing..." : "Test"}
                  </button>
                  {testResults[config.id] && (
                    <span className={`dashboard-test-result ${testResults[config.id].success ? "success" : "error"}`}>
                      {testResults[config.id].message}
                      {testResults[config.id].latency_ms && ` (${testResults[config.id].latency_ms}ms)`}
                    </span>
                  )}
                  <button
                    className="dashboard-button dashboard-button-sm dashboard-button-secondary"
                    onClick={() => handleEdit(config)}
                  >
                    Edit
                  </button>
                  <button
                    className="dashboard-button dashboard-button-sm dashboard-button-danger"
                    onClick={() => handleDelete(config.id)}
                  >
                    Delete
                  </button>
                </div>
              </div>
            ))}
            <button
              className="dashboard-button dashboard-button-secondary dashboard-button-add"
              onClick={() => { setShowForm(true); setEditingConfig(null); resetForm(); }}
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} className="dashboard-button-icon">
                <line x1="12" y1="5" x2="12" y2="19" />
                <line x1="5" y1="12" x2="19" y2="12" />
              </svg>
              Add Another Configuration
            </button>
          </div>
        )}
      </div>
    </div>
  )
}

function DashboardContent() {
  const router = useRouter()
  const { user, loading: authLoading } = useAuth()
  const [loading, setLoading] = useState(false)
  const [activeTab, setActiveTab] = useState<"overview" | "resumes" | "settings">("overview")

  // Guard: if auth check fails, kick the user to login.
  useEffect(() => {
    if (!authLoading && !user) {
      router.replace("/login")
    }
  }, [user, authLoading, router])

  async function handleLogout() {
    setLoading(true)
    try {
      await logout()
      router.push("/login?logged_out=true")
      router.refresh()
    } catch {
      setLoading(false)
    }
  }

  if (authLoading || !user) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="animate-spin rounded-full h-8 w-8 border-4 border-muted-foreground border-t-transparent" />
      </div>
    )
  }

  return (
    <div className="dashboard-shell">
      {/* ── Sidebar ───────────────────────────────────────────── */}
      <aside className="dashboard-sidebar">
        <div className="dashboard-sidebar-header">
          <a href="/dashboard" className="dashboard-logo">
            <span className="dashboard-logo-mark">CF</span>
            <span className="dashboard-logo-text">CareerForge</span>
          </a>
        </div>

        <nav className="dashboard-nav">
          <button
            className={`dashboard-nav-item ${activeTab === "overview" ? "active" : ""}`}
            onClick={() => setActiveTab("overview")}
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} className="dashboard-nav-icon">
              <path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z" />
              <polyline points="9 22 9 12 15 12 15 22" />
            </svg>
            Overview
          </button>
          <button
            className={`dashboard-nav-item ${activeTab === "resumes" ? "active" : ""}`}
            onClick={() => setActiveTab("resumes")}
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} className="dashboard-nav-icon">
              <path d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            Resumes
          </button>
          <button
            className={`dashboard-nav-item ${activeTab === "settings" ? "active" : ""}`}
            onClick={() => setActiveTab("settings")}
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} className="dashboard-nav-icon">
              <circle cx="12" cy="12" r="3" />
              <path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-2 2 2 2 0 01-2-2v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83 0 2 2 0 010-2.83l.06-.06a1.65 1.65 0 00.33-1.82 1.65 1.65 0 00-1.51-1H3a2 2 0 01-2-2 2 2 0 012-2h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 010-2.83 2 2 0 012.83 0l.06.06a1.65 1.65 0 001.82.33H9a1.65 1.65 0 001-1.51V3a2 2 0 012-2 2 2 0 012 2v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 0 2 2 0 010 2.83l-.06.06a1.65 1.65 0 00-.33 1.82V9a1.65 1.65 0 001.51 1H21a2 2 0 012 2 2 2 0 01-2 2h-.09a1.65 1.65 0 00-1.51 1z" />
            </svg>
            Settings
          </button>
        </nav>

        <div className="dashboard-sidebar-footer">
          <div className="dashboard-user">
            <div className="dashboard-user-avatar">
              {user.full_name?.[0]?.toUpperCase() ?? user.email[0].toUpperCase()}
            </div>
            <div className="dashboard-user-info">
              <p className="dashboard-user-name">
                {user.full_name ?? user.email}
              </p>
              <p className="dashboard-user-email">{user.email}</p>
            </div>
          </div>
          <button
            onClick={handleLogout}
            disabled={loading}
            className="dashboard-logout-button"
          >
            {loading ? (
              <span className="auth-spinner" aria-hidden="true" />
            ) : (
              <>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} className="dashboard-logout-icon">
                  <path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4" />
                  <polyline points="16 17 21 12 16 7" />
                  <line x1="21" y1="12" x2="9" y2="12" />
                </svg>
                Log out
              </>
            )}
          </button>
        </div>
      </aside>

      {/* ── Main content ──────────────────────────────────────── */}
      <main className="dashboard-main">
        <header className="dashboard-header">
          <h1 className="dashboard-title">Dashboard</h1>
          <p className="dashboard-subtitle">
            Welcome back, {user.full_name ?? user.email.split("@")[0]}.
          </p>
        </header>

        {activeTab === "overview" && (
          <div className="dashboard-content">
            {/* Trial / subscription card */}
            <div className="dashboard-card dashboard-card-featured">
              <div className="dashboard-card-header">
                <h2 className="dashboard-card-title">Your account</h2>
              </div>
              <div className="dashboard-stats">
                <div className="dashboard-stat">
                  <span className="dashboard-stat-label">Plan</span>
                  <span className="dashboard-stat-value">
                    {user.subscription?.status === "active"
                      ? user.subscription.plan_tier === "free"
                        ? "Free"
                        : `Pro (${user.subscription.plan_tier})`
                      : user.subscription?.status === "trialing"
                      ? "Trial"
                      : "Free"}
                  </span>
                </div>
                <div className="dashboard-stat">
                  <span className="dashboard-stat-label">Credits remaining</span>
                  <span className="dashboard-stat-value">
                    {user.subscription?.credits_remaining ?? "—"}
                  </span>
                </div>
                <div className="dashboard-stat">
                  <span className="dashboard-stat-label">Resumes generated</span>
                  <span className="dashboard-stat-value">0</span>
                </div>
              </div>
              {user.subscription?.status === "trialing" && (
                <div className="dashboard-trial-banner">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} className="dashboard-trial-icon">
                    <circle cx="12" cy="12" r="10" />
                    <polyline points="12 6 12 12 16 14" />
                  </svg>
                  <div>
                    <p className="dashboard-trial-title">
                      {user.subscription?.trial_ends_at
                        ? `Your 14-day trial ends ${new Date(user.subscription.trial_ends_at).toLocaleDateString()}`
                        : "Your trial is active"}
                    </p>
                    <p className="dashboard-trial-text">
                      {user.subscription?.credits_remaining ?? 5} generations
                      remaining. Upgrade to Pro for unlimited access.
                    </p>
                  </div>
                </div>
              )}
              {user.subscription?.status === "active" &&
                user.subscription.plan_tier === "free" && (
                  <div className="dashboard-upgrade-banner">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} className="dashboard-upgrade-icon">
                      <path d="M12 9v6m3-3H9m12 0a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <div>
                      <p className="dashboard-upgrade-title">Upgrade to Pro</p>
                      <p className="dashboard-upgrade-text">
                        Unlock all templates, faster processing, and custom branding
                        for $29/month.
                      </p>
                      <a href="/pricing" className="dashboard-upgrade-button">
                        View plans
                      </a>
                    </div>
                  </div>
                )}
            </div>

            {/* Quick actions */}
            <div className="dashboard-card">
              <div className="dashboard-card-header">
                <h2 className="dashboard-card-title">Quick actions</h2>
              </div>
              <div className="dashboard-actions">
                <a
                  href="/profiles"
                  className="dashboard-action-button"
                >
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} className="dashboard-action-icon">
                    <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
                    <polyline points="14 2 14 8 20 8" />
                    <line x1="12" y1="18" x2="12" y2="12" />
                    <line x1="9" y1="15" x2="15" y2="15" />
                  </svg>
                  New resume
                </a>
                <button className="dashboard-action-button">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} className="dashboard-action-icon">
                    <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
                    <polyline points="14 2 14 8 20 8" />
                    <line x1="16" y1="13" x2="8" y2="13" />
                    <line x1="16" y1="17" x2="8" y2="17" />
                    <polyline points="10 9 9 11 12 13" />
                  </svg>
                  New cover letter
                </button>
                <a
                  href="/profiles"
                  className="dashboard-action-button"
                >
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} className="dashboard-action-icon">
                    <path d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  My resume drafts
                </a>
              </div>
            </div>

            {/* Recent activity placeholder */}
            <div className="dashboard-card">
              <div className="dashboard-card-header">
                <h2 className="dashboard-card-title">Recent activity</h2>
              </div>
              <p className="dashboard-empty">No activity yet. Start by creating your first resume.</p>
            </div>
          </div>
        )}

        {activeTab === "resumes" && (
          <div className="dashboard-content">
            <div className="dashboard-card">
              <div className="dashboard-card-header">
                <h2 className="dashboard-card-title">Your Resumes</h2>
                <a href="/profiles" className="dashboard-button dashboard-button-primary dashboard-button-sm">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} className="dashboard-button-icon">
                    <line x1="12" y1="5" x2="12" y2="19" />
                    <line x1="5" y1="12" x2="19" y2="12" />
                  </svg>
                  New Resume
                </a>
              </div>
              <div className="dashboard-resume-grid">
                {/* Resume cards will go here */}
                <div className="dashboard-empty-state">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} className="dashboard-empty-icon">
                    <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
                    <polyline points="14 2 14 8 20 8" />
                    <line x1="12" y1="18" x2="12" y2="12" />
                    <line x1="9" y1="15" x2="15" y2="15" />
                  </svg>
                  <h3>No resumes yet</h3>
                  <p>Create your first resume to get started. You can build from a profile or start fresh.</p>
                  <a href="/profiles" className="dashboard-button dashboard-button-primary" style={{marginTop: '1rem'}}>
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} className="dashboard-button-icon">
                      <line x1="12" y1="5" x2="12" y2="19" />
                      <line x1="5" y1="12" x2="19" y2="12" />
                    </svg>
                    Create Resume
                  </a>
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === "settings" && (
          <SettingsTab />
        )}
      </main>
    </div>
  )
}

export default function DashboardPage() {
  const loading = useAuthLoading()
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="animate-spin rounded-full h-8 w-8 border-4 border-muted-foreground border-t-transparent" />
      </div>
    )
  }
  return <DashboardContent />
}