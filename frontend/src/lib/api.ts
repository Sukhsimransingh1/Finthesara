const BASE = (process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000").replace(/\/$/, "");
const PREFIX = process.env.NEXT_PUBLIC_API_PREFIX || "/api/v1";

export const DEFAULT_PROJECT_ID =
  process.env.NEXT_PUBLIC_PROJECT_ID || "00000000-0000-0000-0000-000000000000";

export function apiUrl(path: string): string {
  const p = path.startsWith("/") ? path : `/${path}`;
  return `${BASE}${p.startsWith(PREFIX) ? "" : PREFIX}${p}`;
}

function getAuthToken(): string | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem("finthesara_token");
    return raw || null;
  } catch {
    return null;
  }
}

export function setAuthToken(token: string | null): void {
  if (typeof window === "undefined") return;
  try {
    if (token) window.localStorage.setItem("finthesara_token", token);
    else window.localStorage.removeItem("finthesara_token");
  } catch {
    /* ignore */
  }
}

export async function api<T = unknown>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const headers = new Headers(init.headers);
  const token = getAuthToken();
  if (token && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  if (!(init.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  let res: Response;
  try {
    res = await fetch(apiUrl(path), { ...init, headers, cache: "no-store" });
  } catch {
    throw new Error("Network error: could not reach the backend.");
  }

  const raw = await res.text();
  let data: unknown = null;
  try {
    data = raw ? JSON.parse(raw) : null;
  } catch {
    data = raw;
  }

  if (!res.ok) {
    const detail =
      (data && typeof data === "object" && "detail" in data
        ? String((data as { detail: unknown }).detail)
        : null) ||
      (data && typeof data === "object" && "message" in data
        ? String((data as { message: unknown }).message)
        : null) ||
      (typeof data === "string" ? data : res.statusText) ||
      "Request failed.";
    const err = new Error(detail) as Error & { status?: number };
    err.status = res.status;
    throw err;
  }

  return data as T;
}

export function rows<T = unknown>(x: unknown): T[] {
  if (Array.isArray(x)) return x as T[];
  if (x && typeof x === "object") {
    const obj = x as Record<string, unknown>;
    for (const key of ["items", "runs", "results", "documents", "data"]) {
      if (Array.isArray(obj[key])) return obj[key] as T[];
    }
  }
  return [];
}

export function dateLabel(x: unknown): string {
  if (!x) return "—";
  const d = new Date(String(x));
  if (Number.isNaN(d.getTime())) return String(x);
  return d.toLocaleString();
}

export function relativeTime(x: unknown): string {
  if (!x) return "—";
  const d = new Date(String(x));
  if (Number.isNaN(d.getTime())) return String(x);
  const diff = Date.now() - d.getTime();
  const min = Math.floor(diff / 60000);
  if (min < 1) return "just now";
  if (min < 60) return `${min}m ago`;
  const hr = Math.floor(min / 60);
  if (hr < 24) return `${hr}h ago`;
  const day = Math.floor(hr / 24);
  if (day < 30) return `${day}d ago`;
  return d.toLocaleDateString();
}

export function statusClass(status: string | null | undefined): string {
  if (!status) return "unknown";
  const s = status.toLowerCase();
  if (/complete|pass|success|done/i.test(s)) return "completed";
  if (/running|active|in_progress|stream/i.test(s)) return "running";
  if (/awaiting|pending|queued|plann|research|verif/i.test(s)) return "awaiting_review";
  if (/fail|error/i.test(s)) return "failed";
  return "unknown";
}

/* ---------- Typed API contracts ---------- */

export interface HealthResponse {
  status: "ok";
  service: string;
  version: string;
  environment: string;
}

export interface ResearchRequest {
  question: string;
  project_id: string;
  user_id?: string | null;
  run_id?: string | null;
}

export interface ResearchResponse {
  run_id: string;
  status: string;
  final_report: string | null;
  draft_report: string | null;
  human_review_required: boolean;
  state: Record<string, unknown> | null;
}

export interface ResearchRun {
  id: string;
  project_id?: string;
  question?: string;
  status?: string;
  metadata?: Record<string, unknown> | null;
  created_at?: string;
  updated_at?: string;
}

export interface HumanReviewRequest {
  decision: "approve" | "reject" | "request_research";
  comment?: string | null;
}

export interface HumanReviewResponse {
  review: Record<string, unknown>;
  research_run_id: string;
  status: string;
  decision: string;
}

export interface UploadResponse {
  document: Record<string, unknown>;
  chunk_count: number;
  message: string;
}

export interface StreamEvent {
  event: string;
  node?: string | null;
  data: Record<string, unknown>;
}

export async function streamResearch(
  request: ResearchRequest,
  onEvent: (evt: StreamEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const res = await fetch(apiUrl("/research/stream"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
    signal,
  });

  if (!res.ok || !res.body) {
    const text = await res.text().catch(() => "");
    throw new Error(text || `Streaming failed (${res.status}).`);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split("\n\n");
    buffer = parts.pop() || "";
    for (const part of parts) {
      const lines = part.split("\n");
      let eventName = "message";
      let dataStr = "";
      for (const line of lines) {
        if (line.startsWith("event:")) eventName = line.slice(6).trim();
        else if (line.startsWith("data:")) dataStr += line.slice(5).trim();
      }
      if (!dataStr) continue;
      try {
        const parsed = JSON.parse(dataStr) as StreamEvent;
        onEvent({ ...parsed, event: parsed.event || eventName });
      } catch {
        onEvent({ event: eventName, data: { raw: dataStr } });
      }
    }
  }
}

export function storeRunResult(result: ResearchResponse): void {
  if (typeof window === "undefined") return;
  try {
    const key = `finthesara_run_${result.run_id}`;
    window.localStorage.setItem(key, JSON.stringify(result));
  } catch {
    /* ignore */
  }
}

export function getStoredRunResult(runId: string): ResearchResponse | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(`finthesara_run_${runId}`);
    return raw ? (JSON.parse(raw) as ResearchResponse) : null;
  } catch {
    return null;
  }
}
