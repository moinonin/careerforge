"use client";

import { useCallback, useEffect, useState } from "react";
import { AppShell } from "@/components/app-shell";
import { getToken } from "@/lib/token-store";

const API_BASE = "/api/v1";

const LLM_PROVIDERS = [
  { id: "openai", name: "OpenAI", models: ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"], requiresKey: true },
  { id: "anthropic", name: "Anthropic", models: ["claude-3-5-sonnet-20241022", "claude-3-5-haiku-20241022", "claude-3-opus-20240229"], requiresKey: true },
  { id: "ollama", name: "Ollama (Local)", models: [] as string[], requiresKey: false },
  { id: "custom", name: "Custom OpenAI-Compatible", models: [] as string[], requiresKey: true },
];

type LLMConfig = {
  id: string;
  provider: string;
  base_url: string | null;
  model_name: string;
  is_active: boolean;
  has_api_key: boolean;
  created_at: string;
  updated_at: string;
};

type TestResult = { success: boolean; message: string; latency_ms: number | null };

async function apiRequest<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
    credentials: "include",
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Request failed" }));
    const detail = Array.isArray(err.detail)
      ? err.detail.map((e: { msg?: string }) => e.msg ?? String(e)).join("; ")
      : err.detail;
    throw new Error(detail || `HTTP ${res.status}`);
  }
  if (res.status === 204) return {} as T;
  return res.json();
}

export default function LLMSettingsPage() {
  const [configs, setConfigs] = useState<LLMConfig[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<LLMConfig | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [testResults, setTestResults] = useState<Record<string, TestResult & { loading: boolean }>>({});
  const [form, setForm] = useState({
    provider: "openai",
    base_url: "",
    api_key: "",
    model_name: "",
    is_active: true,
  });

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setConfigs(await apiRequest<LLMConfig[]>("/llm-config"));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load configs");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const provider = LLM_PROVIDERS.find((p) => p.id === form.provider);
  const needsBaseUrl = form.provider === "ollama" || form.provider === "custom";

  function resetForm() {
    setForm({ provider: "openai", base_url: "", api_key: "", model_name: "", is_active: true });
    setEditing(null);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const body = {
        provider: form.provider,
        base_url: form.base_url || null,
        api_key: form.api_key || null,
        model_name: form.model_name,
        is_active: form.is_active,
      };
      if (editing) {
        await apiRequest(`/llm-config/${editing.id}`, { method: "PUT", body: JSON.stringify(body) });
      } else {
        await apiRequest("/llm-config", { method: "POST", body: JSON.stringify(body) });
      }
      setShowForm(false);
      resetForm();
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setSaving(false);
    }
  }

  async function handleTest(id: string) {
    setTestResults((prev) => ({ ...prev, [id]: { success: false, message: "Testing...", latency_ms: null, loading: true } }));
    try {
      const result = await apiRequest<TestResult>(`/llm-config/${id}/test`, { method: "POST" });
      setTestResults((prev) => ({ ...prev, [id]: { ...result, loading: false } }));
    } catch (err) {
      setTestResults((prev) => ({
        ...prev,
        [id]: { success: false, message: err instanceof Error ? err.message : "Test failed", latency_ms: null, loading: false },
      }));
    }
  }

  async function handleDelete(id: string) {
    if (!confirm("Delete this LLM configuration?")) return;
    try {
      await apiRequest(`/llm-config/${id}`, { method: "DELETE" });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Delete failed");
    }
  }

  function handleEdit(config: LLMConfig) {
    setEditing(config);
    setForm({
      provider: config.provider,
      base_url: config.base_url || "",
      api_key: "",
      model_name: config.model_name,
      is_active: config.is_active,
    });
    setShowForm(true);
  }

  return (
    <AppShell title="LLM Settings" subtitle="Configure your LLM providers (BYOK). Keys are encrypted at rest.">
      <div className="dashboard-content">
        <div className="dashboard-card">
          <div className="dashboard-card-header">
            <h2 className="dashboard-card-title">LLM Configurations</h2>
            {!showForm && (
              <button className="dashboard-button dashboard-button-primary dashboard-button-sm" onClick={() => { resetForm(); setShowForm(true); }}>
                Add Configuration
              </button>
            )}
          </div>

          {error && <div className="dashboard-generation-error"><p>{error}</p></div>}

          {loading ? (
            <div className="dashboard-empty">Loading...</div>
          ) : (
            <>
              {configs.length === 0 && !showForm && (
                <div className="dashboard-empty-state">
                  <h3>No LLM configurations yet</h3>
                  <p>Add your first LLM provider to start generating resumes and cover letters.</p>
                  <button className="dashboard-button dashboard-button-primary" style={{ marginTop: "1rem" }} onClick={() => setShowForm(true)}>
                    Add LLM Configuration
                  </button>
                </div>
              )}

              {showForm && (
                <form onSubmit={handleSubmit} className="dashboard-form">
                  <div className="dashboard-form-group">
                    <label htmlFor="llm-provider" className="dashboard-form-label">Provider</label>
                    <select
                      id="llm-provider"
                      className="dashboard-form-select"
                      value={form.provider}
                      onChange={(e) => {
                        const next = LLM_PROVIDERS.find((p) => p.id === e.target.value);
                        setForm((prev) => ({
                          ...prev,
                          provider: e.target.value,
                          model_name: next?.models[0] ?? (e.target.value === "openai" ? "gpt-4o" : ""),
                          base_url: e.target.value === "ollama" ? "http://localhost:11434/v1" : prev.base_url,
                        }));
                      }}
                    >
                      {LLM_PROVIDERS.map((p) => (
                        <option key={p.id} value={p.id}>{p.name}</option>
                      ))}
                    </select>
                  </div>

                  {needsBaseUrl && (
                    <div className="dashboard-form-group">
                      <label htmlFor="llm-base-url" className="dashboard-form-label">Base URL</label>
                      <input
                        id="llm-base-url"
                        type="text"
                        className="dashboard-form-input"
                        value={form.base_url}
                        onChange={(e) => setForm((prev) => ({ ...prev, base_url: e.target.value }))}
                        placeholder={form.provider === "ollama" ? "http://localhost:11434/v1" : "https://api.example.com/v1"}
                      />
                    </div>
                  )}

                  <div className="dashboard-form-group">
                    <label htmlFor="llm-model" className="dashboard-form-label">Model</label>
                    {(provider?.models.length ?? 0) > 0 ? (
                      <select
                        id="llm-model"
                        className="dashboard-form-select"
                        value={form.model_name}
                        onChange={(e) => setForm((prev) => ({ ...prev, model_name: e.target.value }))}
                      >
                        {provider!.models.map((m) => (
                          <option key={m} value={m}>{m}</option>
                        ))}
                      </select>
                    ) : (
                      <input
                        id="llm-model"
                        type="text"
                        className="dashboard-form-input"
                        value={form.model_name}
                        onChange={(e) => setForm((prev) => ({ ...prev, model_name: e.target.value }))}
                        placeholder="e.g. gpt-4o, llama3.1:70b"
                        required
                      />
                    )}
                  </div>

                  {provider?.requiresKey && (
                    <div className="dashboard-form-group">
                      <label htmlFor="llm-key" className="dashboard-form-label">API Key</label>
                      <input
                        id="llm-key"
                        type="password"
                        className="dashboard-form-input"
                        value={form.api_key}
                        onChange={(e) => setForm((prev) => ({ ...prev, api_key: e.target.value }))}
                        placeholder={editing ? "Leave blank to keep current key" : "Enter your API key"}
                        required={!editing}
                        autoComplete="off"
                      />
                      <p className="dashboard-form-hint">Encrypted at rest with AES-256-GCM; never returned in API responses.</p>
                    </div>
                  )}

                  <div className="dashboard-form-group dashboard-form-checkbox">
                    <input
                      type="checkbox"
                      id="llm-active"
                      checked={form.is_active}
                      onChange={(e) => setForm((prev) => ({ ...prev, is_active: e.target.checked }))}
                    />
                    <label htmlFor="llm-active">Set as active configuration</label>
                  </div>

                  <div className="dashboard-form-actions">
                    <button type="button" className="dashboard-button dashboard-button-secondary" onClick={() => { setShowForm(false); resetForm(); }}>
                      Cancel
                    </button>
                    <button type="submit" className="dashboard-button dashboard-button-primary" disabled={saving}>
                      {saving ? "Saving..." : editing ? "Update Configuration" : "Add Configuration"}
                    </button>
                  </div>
                </form>
              )}

              {configs.length > 0 && (
                <div className="dashboard-config-list">
                  {configs.map((config) => (
                    <div key={config.id} className={`dashboard-config-item ${config.is_active ? "active" : ""}`}>
                      <div className="dashboard-config-info">
                        <div className="dashboard-config-header">
                          <span className="dashboard-config-provider">
                            {LLM_PROVIDERS.find((p) => p.id === config.provider)?.name ?? config.provider}
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
                        <button
                          className="dashboard-button dashboard-button-sm dashboard-button-secondary"
                          onClick={() => handleTest(config.id)}
                          disabled={testResults[config.id]?.loading}
                        >
                          {testResults[config.id]?.loading ? "Testing..." : "Test"}
                        </button>
                        {testResults[config.id] && !testResults[config.id].loading && (
                          <span className={`dashboard-test-result ${testResults[config.id].success ? "success" : "error"}`}>
                            {testResults[config.id].message}
                            {testResults[config.id].latency_ms != null && ` (${testResults[config.id].latency_ms}ms)`}
                          </span>
                        )}
                        <button className="dashboard-button dashboard-button-sm dashboard-button-secondary" onClick={() => handleEdit(config)}>
                          Edit
                        </button>
                        <button className="dashboard-button dashboard-button-sm dashboard-button-danger" onClick={() => handleDelete(config.id)}>
                          Delete
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </AppShell>
  );
}
