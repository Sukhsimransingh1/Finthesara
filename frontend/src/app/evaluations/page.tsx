
"use client";

import { useCallback, useEffect, useState } from "react";
import {
  RefreshCw,
  LoaderCircle,
  ClipboardCheck,
  AlertCircle,
} from "lucide-react";

import { api } from "@/lib/api";
import { Heading, Panel, Empty, ErrorBox } from "@/components/ui";

interface EvaluationRun {
  id: string;
  evaluation_dataset_id: string;
  initiated_by?: string;
  status: string;
  configuration?: Record<string, unknown>;
  results?: Record<string, unknown>;
  created_at?: string;
  completed_at?: string | null;
  evaluation_datasets?: {
    name?: string;
    description?: string | null;
    project_id?: string | null;
  } | null;
}

interface EvaluationResponse {
  items: EvaluationRun[];
  count: number;
  message?: string;
}

function formatDate(value?: string | null): string {
  if (!value) return "Not available";

  const date = new Date(value);

  return Number.isNaN(date.getTime())
    ? value
    : date.toLocaleString();
}

function formatStatus(status: string): string {
  return status.replaceAll("_", " ");
}

export default function Evaluations() {
  const [runs, setRuns] = useState<EvaluationRun[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(true);
  const [lastUpdated, setLastUpdated] = useState("");

  const loadEvaluations = useCallback(async () => {
    setBusy(true);
    setError("");

    try {
      const response = await api<EvaluationResponse>(
        "/evaluations?limit=100",
      );

      setRuns(Array.isArray(response.items) ? response.items : []);
      setLastUpdated(new Date().toLocaleTimeString());
    } catch (caught: unknown) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Could not load evaluation runs.",
      );
    } finally {
      setBusy(false);
    }
  }, []);

  useEffect(() => {
    void loadEvaluations();
  }, [loadEvaluations]);

  return (
    <>
      <Heading
        eyebrow="QUALITY / OBSERVABILITY"
        title="Evaluation lab"
        description="Inspect persisted evaluation runs and their actual results. No benchmark scores are fabricated."
      />

      <Panel
        title={`Evaluation runs (${runs.length})`}
        description={
          lastUpdated
            ? `Last refreshed at ${lastUpdated}`
            : "Saved evaluation records from the backend."
        }
        action={
          <button
            type="button"
            className="icon-btn"
            onClick={() => void loadEvaluations()}
            disabled={busy}
            aria-label="Refresh evaluation runs"
            title="Refresh evaluation runs"
          >
            {busy ? (
              <LoaderCircle size={15} className="spin" />
            ) : (
              <RefreshCw size={15} />
            )}
          </button>
        }
      >
        {error && <ErrorBox message={error} />}

        {busy && runs.length === 0 && !error && (
          <div className="empty-state">
            <LoaderCircle size={28} className="spin" />
            <h3>Loading evaluation runs</h3>
            <p>Retrieving saved records from Supabase.</p>
          </div>
        )}

        {!busy && !error && runs.length === 0 && (
          <Empty
            title="No saved evaluation runs"
            description="The endpoint is available, but no evaluation runs have been saved for the configured local user yet."
          />
        )}

        {runs.length > 0 && (
          <div style={{ display: "grid", gap: 14 }}>
            {runs.map((run) => (
              <article
                key={run.id}
                style={{
                  border: "1px solid var(--border, #dbe3ec)",
                  borderRadius: 12,
                  padding: 16,
                  display: "grid",
                  gap: 10,
                  minWidth: 0,
                }}
              >
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "flex-start",
                    flexWrap: "wrap",
                    gap: 10,
                  }}
                >
                  <div style={{ display: "flex", gap: 10 }}>
                    <ClipboardCheck size={20} />
                    <div>
                      <h3>
                        {run.evaluation_datasets?.name ||
                          "Evaluation dataset"}
                      </h3>
                      <p style={{ fontSize: 12, overflowWrap: "anywhere" }}>
                        Run ID: {run.id}
                      </p>
                    </div>
                  </div>

                  <span className={`status ${run.status}`}>
                    {formatStatus(run.status)}
                  </span>
                </div>

                {run.evaluation_datasets?.description && (
                  <p>{run.evaluation_datasets.description}</p>
                )}

                <p style={{ fontSize: 13 }}>
                  <b>Created:</b> {formatDate(run.created_at)}
                </p>

                <p style={{ fontSize: 13 }}>
                  <b>Completed:</b> {formatDate(run.completed_at)}
                </p>

                <details>
                  <summary style={{ cursor: "pointer" }}>
                    View recorded configuration and results
                  </summary>

                  <h4 style={{ marginTop: 12 }}>Configuration</h4>
                  <pre className="json">
                    {JSON.stringify(run.configuration ?? {}, null, 2)}
                  </pre>

                  <h4 style={{ marginTop: 12 }}>Results</h4>
                  <pre className="json">
                    {JSON.stringify(run.results ?? {}, null, 2)}
                  </pre>
                </details>
              </article>
            ))}
          </div>
        )}
      </Panel>

      <div className="notice">
        <AlertCircle size={17} />
        <span>
          <b>Actual results only.</b> This page displays stored evaluation
          records. It does not automatically execute the evaluation runner
          or generate scores.
        </span>
      </div>
    </>
  );
}
