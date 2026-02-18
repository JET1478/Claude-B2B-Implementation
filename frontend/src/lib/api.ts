const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

let token: string | null = null;

export function setToken(t: string) {
  token = t;
  if (typeof window !== "undefined") {
    localStorage.setItem("admin_token", t);
  }
}

export function getToken(): string | null {
  if (token) return token;
  if (typeof window !== "undefined") {
    token = localStorage.getItem("admin_token");
  }
  return token;
}

export function clearToken() {
  token = null;
  if (typeof window !== "undefined") {
    localStorage.removeItem("admin_token");
  }
}

async function apiFetch(path: string, options: RequestInit = {}) {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string> || {}),
  };
  const t = getToken();
  if (t) {
    headers["Authorization"] = `Bearer ${t}`;
  }
  const res = await fetch(`${API_URL}${path}`, { ...options, headers });
  if (res.status === 401) {
    clearToken();
    if (typeof window !== "undefined") {
      window.location.href = "/";
    }
    throw new Error("Unauthorized");
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `API error ${res.status}`);
  }
  if (res.status === 204) return null;
  return res.json();
}

// Auth
export const login = (email: string, password: string) =>
  apiFetch("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });

// Tenants
export const listTenants = (page = 1) => apiFetch(`/tenants?page=${page}`);
export const getTenant = (id: string) => apiFetch(`/tenants/${id}`);
export const createTenant = (data: any) =>
  apiFetch("/tenants", { method: "POST", body: JSON.stringify(data) });
export const updateTenant = (id: string, data: any) =>
  apiFetch(`/tenants/${id}`, { method: "PATCH", body: JSON.stringify(data) });
export const deleteTenant = (id: string) =>
  apiFetch(`/tenants/${id}`, { method: "DELETE" });

// Runs
export const listRuns = (params?: Record<string, string>) => {
  const qs = params ? "?" + new URLSearchParams(params).toString() : "";
  return apiFetch(`/runs${qs}`);
};
export const getRun = (id: string) => apiFetch(`/runs/${id}`);

// Tickets
export const listTickets = (params?: Record<string, string>) => {
  const qs = params ? "?" + new URLSearchParams(params).toString() : "";
  return apiFetch(`/tickets${qs}`);
};

// Leads
export const listLeads = (params?: Record<string, string>) => {
  const qs = params ? "?" + new URLSearchParams(params).toString() : "";
  return apiFetch(`/leads${qs}`);
};

// Audit
export const listAuditLogs = (params?: Record<string, string>) => {
  const qs = params ? "?" + new URLSearchParams(params).toString() : "";
  return apiFetch(`/audit${qs}`);
};

// Usage
export const getUsage = (tenantId: string) => apiFetch(`/usage/${tenantId}`);

// Health
export const getHealth = () =>
  fetch(`${API_URL}/health`).then((r) => r.json()).catch(() => null);
