
const BASE = (
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000"
).replace(/\/+$/, "");

const PREFIX = (
  process.env.NEXT_PUBLIC_API_PREFIX || "/api/v1"
).replace(/\/+$/, "");

export const DEFAULT_PROJECT_ID =
  process.env.NEXT_PUBLIC_PROJECT_ID?.trim() || "";

/* ---------- URL helpers ---------- */

export function apiUrl(path: string): string {
  const p = path.startsWith("/") ? path : `/${path}`;

  if (p === PREFIX || p.startsWith(`${PREFIX}/`)) {
    return `${BASE}${p}`;
  }

  return `${BASE}${PREFIX}${p}`;
}

/* ---------- Authentication ---------- */

async function getAuthToken(): Promise<string | null> {
  if (typeof window === "undefined") return null;

  try {
    const { getSupabaseBrowserClient } = await import("@/lib/supabase");
    const client = getSupabaseBrowserClient();

    if (client) {
      const { data, error } = await client.auth.getSession();

      if (error) {
        console.error(
          "Could not retrieve Supabase session:",
          error.message,
        );
      }

      if (data.session?.access_token) {
        return data.session.access_token;
      }
    }

    // Optional token override for development.
    return window.localStorage.getItem("finthesara_token");
  } catch (error) {
    console.error("Supabase session lookup failed:", error);
    return null;
  }
}


export function setAuthToken(token: string | null): void {
  if (typeof window === "undefined") return;

  try {
    if (token) {
      window.localStorage.setItem("finthesara_token", token);
    } else {
      window.localStorage.removeItem("finthesara_token");
    }
  } catch {
    // Ignore localStorage errors.
  }
}

/* ---------- Health check ---------- */

export interface HealthResponse {
  status: "ok";
  service: string;
  version: string;
  environment: string;
}

/**
 * Checks only the backend health endpoint.
 * A research-history or authentication failure must not determine
 * the backend's health status.
 */
export async function checkBackendHealth(
  signal?: AbortSignal,
): Promise<HealthResponse> {
  const url = `${BASE}${PREFIX}/health`;

  let response: Response;

  try {
    response = await fetch(url, {
      method: "GET",
      cache: "no-store",
      signal,
    });
  } catch (error) {
    if (error instanceof Error) {
      console.error("Backend health request failed:", {
        url,
        name: error.name,
        message: error.message,
        cause: error.cause,
      });
    } else {
      console.error("Backend health request failed:", error);
    }

    throw new Error(`Could not reach backend at ${url}.`);
  }

  if (!response.ok) {
    throw new Error(
      `Backend health check returned HTTP ${response.status}.`,
    );
  }

  const data = (await response.json()) as HealthResponse;

  if (data?.status !== "ok") {
    throw new Error("Backend health response was not successful.");
  }

  return data;
}

/* ---------- Generic API client ---------- */

export async function api<T = unknown>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const url = apiUrl(path);
  const headers = new Headers(init.headers);
  const token = await getAuthToken();

  if (token && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const isFormData =
    typeof FormData !== "undefined" &&
    init.body instanceof FormData;

  if (
    init.body !== undefined &&
    !isFormData &&
    !headers.has("Content-Type")
  ) {
    headers.set("Content-Type", "application/json");
  }

  let response: Response;

  try {
    response = await fetch(url, {
      ...init,
      headers,
      cache: "no-store",
    });
  } catch (error) {
    // Preserve the original browser error for diagnosis.
    if (error instanceof Error) {
      console.error("API fetch failed:", {
        url,
        method: init.method || "GET",
        name: error.name,
        message: error.message,
        cause: error.cause,
      });
    } else {
      console.error("API fetch failed:", {
        url,
        method: init.method || "GET",
        error,
      });
    }

    throw new Error(
      `Could not reach ${url}. Check the browser Console for network or CORS errors.`,
    );
  }

  const raw = await response.text();
  let data: unknown = null;

  try {
    data = raw ? JSON.parse(raw) : null;
  } catch {
    data = raw;
  }

  if (!response.ok) {
    const detail =
      data &&
      typeof data === "object" &&
      "detail" in data
        ? String((data as { detail: unknown }).detail)
        : null;

    const message =
      data &&
      typeof data === "object" &&
      "message" in data
        ? String((data as { message: unknown }).message)
        : null;

    const error = new Error(
      detail ||
        message ||
        (typeof data === "string" ? data : "") ||
        response.statusText ||
        "Request failed.",
    ) as Error & { status?: number };

    error.status = response.status;
    throw error;
  }

  return data as T;
}

/* ---------- Response helpers ---------- */

export function rows<T = unknown>(value: unknown): T[] {
  if (Array.isArray(value)) {
    return value as T[];
  }

  if (value && typeof value === "object") {
    const object = value as Record<string, unknown>;

    for (const key of [
      "items",
      "runs",
      "results",
      "documents",
      "data",
    ]) {
      if (Array.isArray(object[key])) {
        return object[key] as T[];
      }
    }
  }

  return [];
}

export function dateLabel(value: unknown): string {
  if (!value) return "—";

  const date = new Date(String(value));

  return Number.isNaN(date.getTime())
    ? String(value)
    : date.toLocaleString();
}

export function relativeTime(value: unknown): string {
  if (!value) return "—";

  const date = new Date(String(value));

  if (Number.isNaN(date.getTime())) {
    return String(value);
  }

  const difference = Date.now() - date.getTime();
  const minutes = Math.floor(difference / 60000);

  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes}m ago`;

  const hours = Math.floor(minutes / 60);

  if (hours < 24) return `${hours}h ago`;

  const days = Math.floor(hours / 24);

  if (days < 30) return `${days}d ago`;

  return date.toLocaleDateString();
}

export function statusClass(
  status: string | null | undefined,
): string {
  if (!status) return "unknown";

  const value = status.toLowerCase();

  if (/complete|pass|success|done/i.test(value)) {
    return "completed";
  }

  if (/running|active|in_progress|stream/i.test(value)) {
    return "running";
  }

  if (/awaiting|pending|queued|plann|research|verif/i.test(value)) {
    return "awaiting_review";
  }

  if (/fail|error/i.test(value)) {
    return "failed";
  }

  return "unknown";
}

/* ---------- Typed API contracts ---------- */

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

/* ---------- Research streaming ---------- */

export async function streamResearch(
  request: ResearchRequest,
  onEvent: (event: StreamEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const headers = new Headers({
    "Content-Type": "application/json",
  });

  const token = await getAuthToken();

  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const url = apiUrl("/research/stream");

  let response: Response;

  try {
    response = await fetch(url, {
      method: "POST",
      headers,
      body: JSON.stringify(request),
      signal,
      cache: "no-store",
    });
  } catch (error) {
    console.error("Research streaming request failed:", {
      url,
      error:
        error instanceof Error
          ? {
              name: error.name,
              message: error.message,
              cause: error.cause,
            }
          : error,
    });

    throw new Error("Could not connect to the research streaming endpoint.");
  }

  if (!response.ok || !response.body) {
    const text = await response.text().catch(() => "");

    throw new Error(
      text || `Streaming failed with HTTP ${response.status}.`,
    );
  }

  const reader = response.body.getReader();
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
      let dataString = "";

      for (const line of lines) {
        if (line.startsWith("event:")) {
          eventName = line.slice(6).trim();
        } else if (line.startsWith("data:")) {
          dataString += line.slice(5).trim();
        }
      }

      if (!dataString) continue;

      try {
        const parsed = JSON.parse(dataString) as StreamEvent;

        onEvent({
          ...parsed,
          event: parsed.event || eventName,
        });
      } catch {
        onEvent({
          event: eventName,
          data: { raw: dataString },
        });
      }
    }
  }
}

/* ---------- Local run result cache ---------- */

export function storeRunResult(
  result: ResearchResponse,
): void {
  if (typeof window === "undefined") return;

  try {
    window.localStorage.setItem(
      `finthesara_run_${result.run_id}`,
      JSON.stringify(result),
    );
  } catch {
    // Ignore localStorage errors.
  }
}

export function getStoredRunResult(
  runId: string,
): ResearchResponse | null {
  if (typeof window === "undefined") return null;

  try {
    const raw = window.localStorage.getItem(
      `finthesara_run_${runId}`,
    );

    return raw
      ? (JSON.parse(raw) as ResearchResponse)
      : null;
  } catch {
    return null;
  }
}
