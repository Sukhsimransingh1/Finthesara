"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import {
  ArrowRight,
  Plus,
  RefreshCw,
  Activity,
  FileSearch,
  CheckCircle2,
  Clock,
} from "lucide-react";
import {
  api,
  rows,
  dateLabel,
  statusClass,
  DEFAULT_PROJECT_ID,
  type ResearchRun,
  type ResearchResponse,
} from "@/lib/api";
import { Heading, Panel, Empty, ErrorBox } from "@/components/ui";

function getStoredRuns(): ResearchRun[] {
  if (typeof window === "undefined") return [];
  const runs: ResearchRun[] = [];
  try {
    for (let i = 0; i < window.localStorage.length; i++) {
      const key = window.localStorage.key(i);
      if (key && key.startsWith("finthesara_run_")) {
        const raw = window.localStorage.getItem(key);
        if (raw) {
          const r = JSON.parse(raw) as ResearchResponse;
          runs.push({
            id: r.run_id,
            question: (r.state?.original_question as string) || "Research run",
            status: r.status,
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
          });
        }
      }
    }
  } catch {
    /* ignore */
  }
  return runs.sort((a, b) =>
    new Date(b.updated_at || 0).getTime() - new Date(a.updated_at || 0).getTime(),
  );
}

export default function Dashboard() {
  const [items, setItems] = useState<ResearchRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [source, setSource] = useState<"api" | "local" | "none">("none");

  async function load() {
    try {
      const data = await api(`/research-runs?project_id=${DEFAULT_PROJECT_ID}`);
      const list = rows<ResearchRun>(data);
      setItems(list);
      setSource(list.length > 0 ? "api" : "none");
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Request failed";
      const stored = getStoredRuns();
      if (stored.length > 0) {
        setItems(stored);
        setSource("local");
        setError(
          `${msg} — showing locally stored runs from this browser.`,
        );
      } else {
        setError(msg);
        setSource("none");
      }
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const data = await api(`/research-runs?project_id=${DEFAULT_PROJECT_ID}`);
        if (!active) return;
        const list = rows<ResearchRun>(data);
        setItems(list);
        setSource(list.length > 0 ? "api" : "none");
      } catch (e: unknown) {
        if (!active) return;
        const msg = e instanceof Error ? e.message : "Request failed";
        const stored = getStoredRuns();
        if (stored.length > 0) {
          setItems(stored);
          setSource("local");
          setError(`${msg} — showing locally stored runs from this browser.`);
        } else {
          setError(msg);
          setSource("none");
        }
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  const recent = items.slice(0, 6);
  const completed = items.filter((x) =>
    /complete|pass|success|done/i.test(x.status || ""),
  ).length;
  const active = items.filter((x) =>
    /running|pending|review|queued|plann|research|verif/i.test(x.status || ""),
  ).length;

  return (
    <>
      <Heading
        eyebrow="WORKSPACE / OVERVIEW"
        title="Research overview"
        description="A live view of investigations and research activity."
        action={
          <Link className="btn primary" href="/research/new">
            <Plus size={15} /> New investigation
          </Link>
        }
      />

      <div className="metrics">
        {[
          { t: "Research runs", v: loading ? "—" : items.length, I: FileSearch },
          { t: "Completed", v: loading ? "—" : completed, I: CheckCircle2 },
          { t: "Active / review", v: loading ? "—" : active, I: Activity },
        ].map((m) => (
          <div className="metric" key={m.t}>
            <span>
              {m.t} <m.I size={17} />
            </span>
            <b>{m.v}</b>
            <small>
              {source === "local" ? "From local storage" : "From backend API"}
            </small>
          </div>
        ))}
      </div>

      <Panel
        title="Recent investigations"
        description="Most recent runs returned by the backend"
        action={
          <button
            className="icon-btn"
            onClick={() => {
              setLoading(true);
              setError("");
              load();
            }}
            aria-label="Refresh"
            disabled={loading}
          >
            <RefreshCw size={15} className={loading ? "spin" : ""} />
          </button>
        }
      >
        {error && <ErrorBox message={error} />}
        {loading ? (
          <p className="muted">Loading research runs…</p>
        ) : recent.length === 0 ? (
          <Empty
            title="No investigations yet"
            description="Start a research run. Results will appear here when the backend returns them."
            action={
              <Link className="btn primary" href="/research/new">
                Start research <ArrowRight size={15} />
              </Link>
            }
          />
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Question / title</th>
                  <th>Status</th>
                  <th>Updated</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {recent.map((r, i) => (
                  <tr key={r.id || i}>
                    <td>
                      <b>{r.question || "Research run"}</b>
                      <small>{r.id || "ID unavailable"}</small>
                    </td>
                    <td>
                      <span className={`pill ${statusClass(r.status)}`}>
                        {r.status || "Unknown"}
                      </span>
                    </td>
                    <td>{dateLabel(r.updated_at || r.created_at)}</td>
                    <td>
                      <Link
                        className="table-link"
                        href={`/research/${r.id}`}
                      >
                        Open <ArrowRight size={13} />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Panel>

      <div className="notice">
        <Clock size={17} />
        <span>
          <b>Evidence-first workflow.</b> Data is loaded from your backend;
          unavailable metrics are not fabricated. Configure Supabase Auth to
          persist runs across sessions.
        </span>
      </div>
    </>
  );
}
