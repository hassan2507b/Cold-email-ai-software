const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function apiFetch(url: string, init: RequestInit = {}, redirectOnUnauthorized = true) {
  const headers = new Headers(init.headers);
  headers.set("X-Requested-With", "ColdMailDashboard");
  const res = await fetch(url, {
    ...init,
    headers,
    credentials: "include",
  });
  if (
    res.status === 401 &&
    redirectOnUnauthorized &&
    typeof window !== "undefined" &&
    window.location.pathname !== "/login"
  ) {
    window.location.assign("/login");
  }
  return res;
}

export async function checkSession(): Promise<boolean> {
  const res = await apiFetch(`${API_BASE}/api/auth/session`, { cache: "no-store" }, false);
  return res.ok;
}

export async function login(username: string, password: string): Promise<void> {
  const res = await apiFetch(
    `${API_BASE}/api/auth/login`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    },
    false,
  );
  const body = await res.json();
  if (!res.ok) {
    throw new Error(body.detail || "Unable to log in.");
  }
}

export async function logout(): Promise<void> {
  const res = await apiFetch(`${API_BASE}/api/auth/logout`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: "{}",
  });
  if (!res.ok) {
    throw new Error("Unable to log out.");
  }
}

export interface Campaign {
  id: number;
  business_type: string;
  service: string;
  total_emails: number;
  created_time: string;
  sent_count: number;
  waiting_count: number;
  sending_count: number;
  failed_count: number;
  blocked_count: number;
  unsubscribed_count: number;
  progress_percentage: number;
}

export interface EmailRecord {
  id: number;
  campaign_id: number;
  recipient: string;
  business_type: string;
  service: string;
  subject: string;
  body: string | null;
  status: "waiting" | "sending" | "sent" | "failed" | "blocked by checks" | "unsubscribed";
  error_reason: string | null;
  attempts: number;
  sent_time: string | null;
  created_time: string;
}

export interface ReportStats {
  sent: number;
  waiting: number;
  not_sent: number;
  blocked_by_checks: number;
  unsubscribed: number;
  sent_last_24h: number;
  daily_limit: number;
}

export async function fetchStats(): Promise<ReportStats> {
  const res = await apiFetch(`${API_BASE}/api/reports/stats`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to load dashboard counters.");
  return res.json();
}

export async function fetchCampaigns(): Promise<Campaign[]> {
  const res = await apiFetch(`${API_BASE}/api/campaigns`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to load campaigns.");
  return res.json();
}

export async function fetchLatestEmails(limit = 20): Promise<EmailRecord[]> {
  const res = await apiFetch(`${API_BASE}/api/reports/latest-emails?limit=${limit}`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to load latest emails.");
  return res.json();
}

export async function fetchAllEmails(
  search = "",
  status = "",
  limit = 50,
  offset = 0,
): Promise<{ emails: EmailRecord[]; hasMore: boolean }> {
  const params = new URLSearchParams();
  if (search) params.append("search", search);
  if (status && status !== "all") params.append("status", status);
  params.append("limit", (limit + 1).toString());
  params.append("offset", offset.toString());

  const res = await apiFetch(`${API_BASE}/api/emails?${params.toString()}`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to load emails list.");
  const emails: EmailRecord[] = await res.json();
  return { emails: emails.slice(0, limit), hasMore: emails.length > limit };
}

export async function createCampaign(data: {
  business_type: string;
  service: string;
  email_addresses: string[];
}): Promise<Campaign> {
  const res = await apiFetch(`${API_BASE}/api/campaigns`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });

  const body = await res.json();
  if (!res.ok) {
    throw new Error(body.detail || "Failed to start sending campaign.");
  }
  return body;
}

export async function retryProblemEmails(): Promise<{ retried_count: number; message: string }> {
  const res = await apiFetch(`${API_BASE}/api/emails/retry-problems`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  });

  const body = await res.json();
  if (!res.ok) {
    throw new Error(body.detail || "Failed to retry problem emails.");
  }
  return body;
}
