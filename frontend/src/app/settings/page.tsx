"use client";

import { useEffect, useState } from "react";
import {
  Settings as SettingsIcon,
  Shield,
  Info,
  CheckCircle2,
  XCircle,
  LoaderCircle,
} from "lucide-react";
import { api, type HealthResponse } from "@/lib/api";
import { Heading, Panel, ErrorBox } from "@/components/ui";

type ConnState = "checking" | "ok" | "fail";

export default function Settings() {
  const [conn, setConn] = useState<ConnState>("checking");
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [err, setErr] = useState("");

  const baseUrl =
    process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";
  const prefix = process.env.NEXT_PUBLIC_API_PREFIX || "/api/v1";
  const projectId = process.env.NEXT_PUBLIC_PROJECT_ID || "";
  const hasSupabase =
    !!process.env.NEXT_PUBLIC_SUPABASE_URL &&
    !!process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

  async function checkConnection() {
    try {
      const res = await api<HealthResponse>("/health");
      setHealth(res);
      setConn("ok");
    } catch (e: unknown) {
      setErr(e instanceof Error ? e.message : "Connection failed");
      setConn("fail");
    }
  }

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const res = await api<HealthResponse>("/health");
        if (!active) return;
        setHealth(res);
        setConn("ok");
      } catch (e: unknown) {
        if (!active) return;
        setErr(e instanceof Error ? e.message : "Connection failed");
        setConn("fail");
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  return (
    <>
      <Heading
        eyebrow="SYSTEM / CONFIGURATION"
        title="Settings"
        description="Frontend environment, backend connection status, and security configuration."
        action={
          <button className="btn secondary" onClick={() => { setConn("checking"); setErr(""); checkConnection(); }}>
            <SettingsIcon size={15} /> Re-check connection
          </button>
        }
      />

      <Panel title="Backend connection" description="Live status of the FastAPI backend">
        <div className="setting">
          <b>Connection status</b>
          <p>
            {conn === "checking" && (
              <span className="pill awaiting_review">
                <LoaderCircle size={13} className="spin" /> Checking…
              </span>
            )}
            {conn === "ok" && (
              <span className="pill completed">
                <CheckCircle2 size={13} /> Connected
              </span>
            )}
            {conn === "fail" && (
              <span className="pill failed">
                <XCircle size={13} /> Disconnected
              </span>
            )}
          </p>
          {health && (
            <div className="muted" style={{ marginTop: 8 }}>
              <p>
                <b>Service:</b> {health.service} · <b>Version:</b> {health.version} ·{" "}
                <b>Environment:</b> {health.environment}
              </p>
            </div>
          )}
          {err && <ErrorBox message={err} />}
        </div>

        <div className="setting">
          <b>Backend base URL</b>
          <p>
            Set <code>NEXT_PUBLIC_API_BASE_URL</code> in <code>.env.local</code>.
          </p>
          <code>{baseUrl}</code>
        </div>

        <div className="setting">
          <b>API prefix</b>
          <p>Default API prefix used by the frontend.</p>
          <code>{prefix}</code>
        </div>

        <div className="setting">
          <b>Default project ID</b>
          <p>
            Set <code>NEXT_PUBLIC_PROJECT_ID</code> in <code>.env.local</code>.
          </p>
          <code>{projectId || "— (using fallback UUID)"}</code>
        </div>
      </Panel>

      <Panel title="Authentication" description="Supabase Auth configuration">
        <div className="setting">
          <b>Supabase Auth</b>
          <p>
            {hasSupabase
              ? "Supabase URL and anon key are configured."
              : "Supabase Auth is not configured. Protected endpoints (research runs, documents, human reviews) will return 401."}
          </p>
          <p className="muted">
            {hasSupabase
              ? "Status: Configured"
              : "Status: Not configured"}
          </p>
        </div>
      </Panel>

      <Panel title="Production security">
        <ul className="security">
          <li>
            <Shield size={16} /> Connect Supabase Auth and attach the user&apos;s
            access token to protected API calls.
          </li>
          <li>
            <Shield size={16} /> Never expose service-role keys or provider API
            keys in client-side code.
          </li>
          <li>
            <Shield size={16} /> Configure FastAPI CORS for the frontend origin.
          </li>
          <li>
            <Shield size={16} /> Use a deployed API URL outside local
            development.
          </li>
        </ul>
      </Panel>

      <div className="notice">
        <Info size={17} />
        <span>
          <b>Application:</b> Finthesara — AI Financial Research & Intelligence.
          This platform is for financial research and decision support only. It
          is not a trading platform, brokerage, stock-prediction tool, or
          personalized investment-advisory service.
        </span>
      </div>
    </>
  );
}
