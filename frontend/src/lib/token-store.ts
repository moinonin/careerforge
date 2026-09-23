// Token store — Sprint 1.
// Keeps the access token in memory for fast reads, and persists it in
// sessionStorage so it survives full page reloads within the same tab.
// sessionStorage is cleared when the tab closes — appropriate for a
// bearer token. The backend sets HTTP-only cookies too, but the
// frontend reads the token from here to attach it as the Authorization
// header on every API request.

const STORAGE_KEY = "cf_access_token"

let _token: string | null = (() => {
  try {
    return sessionStorage.getItem(STORAGE_KEY)
  } catch {
    return null
  }
})()

export function setToken(token: string | null): void {
  _token = token
  try {
    if (token) {
      sessionStorage.setItem(STORAGE_KEY, token)
    } else {
      sessionStorage.removeItem(STORAGE_KEY)
    }
  } catch {
    // sessionStorage unavailable (SSR, private browsing) — memory-only
  }
}

export function getToken(): string | null {
  if (_token !== null) return _token
  try {
    const stored = sessionStorage.getItem(STORAGE_KEY)
    _token = stored
    return stored
  } catch {
    return null
  }
}

export function clearToken(): void {
  _token = null
  try {
    sessionStorage.removeItem(STORAGE_KEY)
  } catch {
    // ignore
  }
}