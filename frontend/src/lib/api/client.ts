// src/lib/api/client.ts — Core HTTP client shared by all API modules
// Auth uses httpOnly cookies (credentials:'include') with CSRF double-submit.
// downloadBlob() handles authenticated file downloads via the same cookie mechanism.
// No tokens are ever stored in localStorage — that was an XSS risk (fixed).

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8080/api/v1";

let _csrfToken: string | null = null;
let _csrfFetchedAt = 0;
const CSRF_TTL = 7 * 60 * 60 * 1000;
const CSRF_REFRESH_BEFORE = 30 * 60 * 1000;

export async function getCsrfToken(): Promise<string | null> {
  if (_csrfToken && Date.now() - _csrfFetchedAt < CSRF_TTL - CSRF_REFRESH_BEFORE) {
    return _csrfToken;
  }
  if (_csrfToken && Date.now() - _csrfFetchedAt < CSRF_TTL) {
    setTimeout(() => { _csrfFetchedAt = 0; }, 100);
    return _csrfToken;
  }
  try {
    const resp = await fetch(`${API_BASE}/users/csrf-token`, { credentials: "include" });
    if (resp.ok) {
      const data = await resp.json();
      _csrfToken = data.csrf_token;
      _csrfFetchedAt = Date.now();
      return _csrfToken;
    }
  } catch {}
  return null;
}

export class APIError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = "APIError";
    this.status = status;
  }
}

export async function fetchClient(endpoint: string, options: RequestInit = {}) {
  const method = (options.method || "GET").toUpperCase();
  const headers: Record<string, string> = {
    ...((options.headers as Record<string, string>) || {})
  };

  if (method !== "GET" && !(options.body instanceof FormData)) {
    headers["Content-Type"] = headers["Content-Type"] || "application/json";
  }

  if (["POST", "PUT", "PATCH", "DELETE"].includes(method)) {
    const csrfToken = await getCsrfToken();
    if (csrfToken) {
      headers["X-CSRF-Token"] = csrfToken;
    }
  }

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 60000);

  try {
    const response = await fetch(`${API_BASE}${endpoint}`, {
      ...options,
      headers,
      credentials: "include",
      signal: controller.signal,
    });
    clearTimeout(timeoutId);

  if (response.status === 401) {
    if (typeof window !== "undefined" && !window.location.pathname.endsWith("/login")) {
      window.location.href = "/login";
    }
    throw new APIError("Session expired. Please log in again.", 401);
  }

  if (!response.ok) {
    const errData = await response.json().catch(() => ({}));
    let detail = errData.detail;
    if (Array.isArray(detail)) {
      detail = detail.map((d: any) => d.msg || JSON.stringify(d)).join("; ");
    }
    throw new APIError(detail || "Server request failed", response.status);
  }

  const contentType = response.headers.get("content-type");
  if (contentType && contentType.includes("application/json")) {
    return response.json();
  }
  return response;
  } catch (err: any) {
    clearTimeout(timeoutId);
    if (err.name === "AbortError") {
      throw new APIError("Request timed out. Please try again.", 408);
    }
    throw err;
  }
}

export async function downloadBlob(endpoint: string, filename: string, method: string = "GET") {
  const headers: Record<string, string> = {};
  if (["POST", "PUT", "PATCH", "DELETE"].includes(method.toUpperCase())) {
    const csrfToken = await getCsrfToken();
    if (csrfToken) {
      headers["X-CSRF-Token"] = csrfToken;
    }
  }
  const res = await fetch(`${API_BASE}${endpoint}`, {
    method,
    headers,
    credentials: "include",
  });
  if (res.status === 401) {
    if (typeof window !== "undefined" && !window.location.pathname.endsWith("/login")) {
      window.location.href = "/login";
    }
    throw new APIError("Session expired. Please log in again.", 401);
  }
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new APIError(errData.detail || "Error downloading file", res.status);
  }
  const blob = await res.blob();
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.URL.revokeObjectURL(url);
}

export { API_BASE };
