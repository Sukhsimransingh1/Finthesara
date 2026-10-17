
"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  ArrowRight,
  Plus,
  Search,
  RefreshCw,
  Trash2,
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
    // Ignore malformed local-storage entries.
  }

  return runs.sort(
    (a, b) =>
      new Date(b.updated_at || 0).getTime() -
      new Date(a.updated_at || 0).getTime(),
  );
}

function isFailed(status: string | undefined): boolean {
  return (status || "").toLowerCase() === "failed";
}

export default function History() {
  const [data, setData] = useState<ResearchRun[]>([]);
  const [q, setQ] = useState("");
  const [busy, setBusy] = useState(true);
  const [err, setErr] = useState("");
  const [notice, setNotice] = useState("");
  const [source, setSource] = useState<"api" | "local">("api");
  const [deletingIds, setDeletingIds] = useState<string[]>([]);
  const [bulkDeleting, setBulkDeleting] = useState(false);

  const load = useCallback(async () => {
    setBusy(true);
    setErr("");

    try {
      const res = await api(
        `/research-runs?project_id=${DEFAULT_PROJECT_ID}`,
      );

      setData(rows<ResearchRun>(res));
      setSource("api");
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Request failed";
      const stored = getStoredRuns();

      if (stored.length > 0) {
        setData(stored);
        setSource("local");
        setErr(`${msg} — showing locally stored runs. Deletion is disabled.`);
      } else {
        setData([]);
        setSource("local");
        setErr(msg);
      }
    } finally {
      setBusy(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function deleteOne(run: ResearchRun) {
    if (source !== "api" || !run.id) return;

    const confirmed = window.confirm(
      `Delete this research run?\n\n${run.question || run.id}\n\nThis action cannot be undone.`,
    );

    if (!confirmed) return;

    setErr("");
    setNotice("");
    setDeletingIds((current) => [...current, run.id!]);

    try {
      await api(`/research-runs/${encodeURIComponent(run.id)}`, {
        method: "DELETE",
      });

      setData((current) => current.filter((item) => item.id !== run.id));
      setNotice("Research run deleted successfully.");
    } catch (e: unknown) {
      setErr(
        e instanceof Error
          ? `Could not delete research run: ${e.message}`
          : "Could not delete research run.",
      );
    } finally {
      setDeletingIds((current) =>
        current.filter((id) => id !== run.id),
      );
    }
  }

  async function deleteFailedRuns() {
    if (source !== "api" || bulkDeleting) return;

    const failedRuns = data.filter(
      (run) => isFailed(run.status) && Boolean(run.id),
    );

    if (failedRuns.length === 0) {
      setNotice("There are no failed runs to delete.");
      return;
    }

    const confirmed = window.confirm(
      `Delete all ${failedRuns.length} failed research run(s)?\n\nOnly runs marked "failed" will be selected. This action cannot be undone.`,
    );

    if (!confirmed) return;

    setBulkDeleting(true);
    setErr("");
    setNotice("");

    const deletedIds: string[] = [];
    const failures: string[] = [];

    try {
      for (const run of failedRuns) {
        try {
          await api(
            `/research-runs/${encodeURIComponent(run.id!)}`,
            { method: "DELETE" },
          );
          deletedIds.push(run.id!);
        } catch {
          failures.push(run.id!);
        }
      }

      if (deletedIds.length > 0) {
        setData((current) =>
          current.filter((run) => !deletedIds.includes(run.id || "")),
        );
      }

      if (failures.length > 0) {
        setErr(
          `${deletedIds.length} run(s) deleted. ${failures.length} could not be deleted. Refresh the list and check permissions or backend logs.`,
        );
      } else {
        setNotice(`${deletedIds.length} failed run(s) deleted successfully.`);
      }

      // Reconcile the UI with the database after bulk deletion.
      await load();
    } finally {
      setBulkDeleting(false);
    }
  }

  const shown = data.filter((run) =>
    `${run.question || ""} ${run.status || ""} ${run.id || ""}`
      .toLowerCase()
      .includes(q.toLowerCase()),
  );

  const failedCount = data.filter((run) => isFailed(run.status)).length;
  const canDelete = source === "api" && !busy;

  return (
    <>
      <Heading
        eyebrow="WORKSPACE / HISTORY"
        title="Research history"
        description="Browse, inspect, and manage investigation runs."
        action={
          <Link className="btn primary" href="/research/new">
            <Plus size={15} /> New investigation
          </Link>
        }
      />

      <Panel
        title="All investigations"
        description={`${busy ? "Loading" : shown.length} run(s) · ${
          source === "local" ? "local storage" : "backend"
        }`}
        action={
          <div className="flex items-center gap-2">
            {failedCount > 0 && (
              <button
                type="button"
                className="btn"
                onClick={deleteFailedRuns}
                disabled={!canDelete || bulkDeleting}
                title="Delete all failed runs"
              >
                <Trash2 size={15} />
                {bulkDeleting
                  ? "Deleting…"
                  : `Delete failed (${failedCount})`}
              </button>
            )}

            <button
              type="button"
              className="icon-btn"
              onClick={() => void load()}
              aria-label="Refresh research history"
              disabled={busy || bulkDeleting}
            >
              <RefreshCw size={15} className={busy ? "spin" : ""} />
            </button>
          </div>
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

        {notice && (
          <p className="muted" role="status">
            {notice}
          </p>
        )}

        {source === "local" && (
          <p className="muted">
            Showing locally stored entries. Connect to the backend to delete
            database records.
          </p>
        )}

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
                  <th>Actions</th>
                </tr>
              </thead>

              <tbody>
                {shown.map((run, index) => {
                  const deleting =
                    Boolean(run.id) && deletingIds.includes(run.id!);

                  return (
                    <tr key={run.id || index}>
                      <td>
                        <b>{run.question || "Research run"}</b>
                        <small>{run.id || "ID unavailable"}</small>
                      </td>

                      <td>
                        <span className={`pill ${statusClass(run.status)}`}>
                          {run.status || "Unknown"}
                        </span>
                      </td>

                      <td>{dateLabel(run.created_at || run.updated_at)}</td>

                      <td>
                        <div className="flex items-center gap-3">
                          {run.id && (
                            <Link
                              className="table-link"
                              href={`/research/${run.id}`}
                            >
                              Open <ArrowRight size={13} />
                            </Link>
                          )}

                          <button
                            type="button"
                            className="icon-btn"
                            aria-label={`Delete research run ${
                              run.question || run.id || ""
                            }`}
                            title="Delete research run"
                            disabled={
                              !canDelete ||
                              !run.id ||
                              deleting ||
                              bulkDeleting
                            }
                            onClick={() => void deleteOne(run)}
                          >
                            <Trash2
                              size={15}
                              className={deleting ? "spin" : ""}
                            />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Panel>
    </>
  );
}
