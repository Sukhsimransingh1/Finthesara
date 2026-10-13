"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  ArrowRight,
  Plus,
  Search,
  RefreshCw,
} from "lucide-react";
import {
  api,
  rows,
  dateLabel,
  statusClass,
  DEFAULT_PROJECT_ID,
  type ResearchRun,
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
          const r = JSON.parse(raw);
          runs.push({
            id: r.run_id,
            question: r.state?.original_question || "Research run",
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

export default function History() {
  const [data, setData] = useState<ResearchRun[]>([]);
  const [q, setQ] = useState("");
  const [busy, setBusy] = useState(true);
  const [err, setErr] = useState("");
  const [source, setSource] = useState<"api" | "local">("api");

  async function load() {
    try {
      const res = await api(`/research-runs?project_id=${DEFAULT_PROJECT_ID}`);
      const list = rows<ResearchRun>(res);
      setData(list);
      setSource("api");
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Request failed";
      const stored = getStoredRuns();
      if (stored.length > 0) {
        setData(stored);
        setSource("local");
        setErr(`${msg} — showing locally stored runs.`);
      } else {
        setErr(msg);
        setData([]);
      }
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const res = await api(`/research-runs?project_id=${DEFAULT_PROJECT_ID}`);
        if (!active) return;
        const list = rows<ResearchRun>(res);
        setData(list);
        setSource("api");
      } catch (e: unknown) {
        if (!active) return;
        const msg = e instanceof Error ? e.message : "Request failed";
        const stored = getStoredRuns();
        if (stored.length > 0) {
          setData(stored);
          setSource("local");
          setErr(`${msg} — showing locally stored runs.`);
        } else {
          setErr(msg);
          setData([]);
        }
      } finally {
        if (active) setBusy(false);
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  const shown = data.filter((x) =>
    `${x.question || ""} ${x.status || ""} ${x.id || ""}`
      .toLowerCase()
      .includes(q.toLowerCase()),
  );

  return (
    <>
      <Heading
        eyebrow="WORKSPACE / HISTORY"
        title="Research history"
        description="Browse investigation runs returned by the backend."
        action={
          <Link className="btn primary" href="/research/new">
            <Plus size={15} /> New investigation
          </Link>
        }
      />

      <Panel
        title="All investigations"
        description={`${busy ? "Loading" : shown.length} run(s) · ${source === "local" ? "local storage" : "backend"}`}
        action={
          <button
            className="icon-btn"
            onClick={() => {
              setBusy(true);
              setErr("");
              load();
            }}
            aria-label="Refresh"
            disabled={busy}
          >
            <RefreshCw size={15} className={busy ? "spin" : ""} />
          </button>
        }
      >
        <div className="search">
          <Search size={16} />
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search question, status or run ID…"
          />
        </div>

        {err && <ErrorBox message={err} />}

        {busy ? (
          <p className="muted">Loading…</p>
        ) : !shown.length ? (
          <Empty
            title="No matching investigations"
            description="Launch an investigation or try another search term."
          />
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Question</th>
                  <th>Status</th>
                  <th>Created</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {shown.map((r, i) => (
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
                    <td>{dateLabel(r.created_at || r.updated_at)}</td>
                    <td>
                      <Link className="table-link" href={`/research/${r.id}`}>
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
    </>
  );
}
