// Token store — Sprint 1.
// Keeps the access token in memory (client-side only, not readable by JS if
// we used HTTP-only cookies, but the backend uses Bearer auth so we store it
// here and attach it as the Authorization header on every request).
//
// The token is written by login/signup/refresh and cleared on logout.

let _token: string | null = null;

export function setToken(token: string | null): void {
  _token = token;
}

export function getToken(): string | null {
  return _token;
}

export function clearToken(): void {
  _token = null;
}
