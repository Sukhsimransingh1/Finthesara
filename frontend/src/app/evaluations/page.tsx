"use client";

import { useState } from "react";
import { RefreshCw, AlertCircle } from "lucide-react";
import { api } from "@/lib/api";
import { Heading, Panel, Empty, ErrorBox } from "@/components/ui";

export default function Evaluations() {
  const [data, setData] = useState<unknown>(null);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  async function load() {
    setBusy(true);
    setErr("");
    try {
      const res = await api("/evaluations");
      setData(res);
    } catch (e: unknown) {
      setErr(e instanceof Error ? e.message : "Request failed");
      setData(null);
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <Heading
        eyebrow="QUALITY / OBSERVABILITY"
        title="Evaluation lab"
        description="Inspect evaluation records from the backend; no benchmark scores are fabricated."
      />

      <Panel
        title="Evaluation runs"
        action={
          <button
            className="icon-btn"
            onClick={load}
            aria-label="Refresh"
            disabled={busy}
          >
            <RefreshCw size={15} className={busy ? "spin" : ""} />
          </button>
        }
      >
        {err ? (
          <ErrorBox message={err} />
        ) : data ? (
          <pre className="json">{JSON.stringify(data, null, 2)}</pre>
        ) : (
          <Empty
            title="Evaluation endpoint not available"
            description="The backend does not currently expose a GET /api/v1/evaluations endpoint. Evaluation runs, datasets, retrieval quality, claim verification, groundedness, latency, and cost metrics will appear here once the endpoint is available. Click refresh to probe the endpoint."
          />
        )}
      </Panel>

      <div className="notice">
        <AlertCircle size={17} />
        <span>
          <b>No fabricated metrics.</b> All evaluation results shown here come
          from actual backend executions. If the endpoint is unavailable, no
          scores are invented.
        </span>
      </div>
    </>
  );
}
