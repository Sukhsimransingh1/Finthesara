"use client";

import { FormEvent, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  ArrowRight,
  LoaderCircle,
  ShieldCheck,
  Sparkles,
  GitBranch,
  BarChart3,
  Search,
  CheckCircle2,
  FileText,
  X,
} from "lucide-react";
import {
  api,
  streamResearch,
  storeRunResult,
  DEFAULT_PROJECT_ID,
  type ResearchResponse,
  type StreamEvent,
} from "@/lib/api";
import { Heading, Panel } from "@/components/ui";

const STAGES = [
  { id: "planner", label: "Planning", I: GitBranch },
  { id: "financial_analysis", label: "Financial analysis", I: BarChart3 },
  { id: "research", label: "Retrieval", I: Search },
  { id: "evidence_fusion", label: "Evidence fusion", I: ShieldCheck },
  { id: "verification", label: "Verification", I: CheckCircle2 },
  { id: "synthesis", label: "Synthesis", I: FileText },
] as const;

export default function NewResearch() {
  const [q, setQ] = useState("");
  const [entity, setEntity] = useState("");
  const [focus, setFocus] = useState("financial fundamentals");
  const [period, setPeriod] = useState("latest available");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [activeStage, setActiveStage] = useState<string | null>(null);
  const [completed, setCompleted] = useState<string[]>([]);
  const [log, setLog] = useState<string[]>([]);
  const router = useRouter();
  const abortRef = useRef<AbortController | null>(null);

  function appendLog(line: string) {
    setLog((prev) => [...prev.slice(-40), line]);
  }

  function onEvent(evt: StreamEvent) {
    if (evt.node) {
      setActiveStage(evt.node);
      setCompleted((prev) =>
        prev.includes(evt.node!) ? prev : [...prev, evt.node!],
      );
    }
    if (evt.event === "research_started") {
      appendLog("Research workflow started.");
    } else if (evt.event === "research_completed") {
      appendLog("Research workflow completed.");
    } else if (evt.event === "research_error") {
      appendLog(`Error: ${String(evt.data?.error || "unknown")}`);
    } else if (evt.event === "node_update") {
      appendLog(`Node "${evt.node}" updated.`);
    }
  }

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (busy) return;
    setBusy(true);
    setError("");
    setCompleted([]);
    setActiveStage(null);
    setLog([]);

    const question = [
      q.trim(),
      entity.trim() ? `Company/entity: ${entity.trim()}` : "",
      `Research focus: ${focus}`,
      `Reporting period: ${period}`,
    ]
      .filter(Boolean)
      .join("\n");

    abortRef.current = new AbortController();

    try {
      try {
        await streamResearch(
          { question, project_id: DEFAULT_PROJECT_ID },
          onEvent,
          abortRef.current.signal,
        );
      } catch (streamErr) {
        appendLog(
          `Stream ended: ${streamErr instanceof Error ? streamErr.message : "unknown"}`,
        );
      }

      const result = await api<ResearchResponse>("/research", {
        method: "POST",
        body: JSON.stringify({ question, project_id: DEFAULT_PROJECT_ID }),
      });
      storeRunResult(result);

      const id = result.run_id;
      if (id) {
        router.push(`/research/${id}`);
      } else {
        setError(
          "The API responded, but no run identifier was present: " +
            JSON.stringify(result),
        );
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Request failed");
    } finally {
      setBusy(false);
      abortRef.current = null;
    }
  }

  function cancel() {
    abortRef.current?.abort();
    setBusy(false);
    setActiveStage(null);
  }

  return (
    <>
      <Heading
        eyebrow="WORKSPACE / NEW RUN"
        title="Start an investigation"
        description="Describe the question. Your backend handles retrieval, financial analysis, and verification."
      />

      <div className="research-layout">
        <Panel
          title="Investigation brief"
          description="Specify the entity, scope, and reporting period."
        >
          <form className="research-form" onSubmit={submit}>
            <label>
              Research question <em>REQUIRED</em>
              <textarea
                rows={5}
                minLength={8}
                required
                value={q}
                onChange={(e) => setQ(e.target.value)}
                placeholder="Assess the company's recent financial performance, key revenue and profitability drivers, and risks disclosed in its filings."
                disabled={busy}
              />
            </label>

            <label>
              Company or entity <small>Optional context</small>
              <input
                value={entity}
                onChange={(e) => setEntity(e.target.value)}
                placeholder="e.g. Apple Inc. (AAPL)"
                disabled={busy}
              />
            </label>

            <div className="form-row">
              <label>
                Research focus
                <select
                  value={focus}
                  onChange={(e) => setFocus(e.target.value)}
                  disabled={busy}
                >
                  <option>financial fundamentals</option>
                  <option>earnings and performance</option>
                  <option>risk and disclosures</option>
                  <option>competitive landscape</option>
                  <option>general research</option>
                </select>
              </label>
              <label>
                Reporting period
                <select
                  value={period}
                  onChange={(e) => setPeriod(e.target.value)}
                  disabled={busy}
                >
                  <option>latest available</option>
                  <option>last fiscal year</option>
                  <option>multi-year trend</option>
                  <option>specify in question</option>
                </select>
              </label>
            </div>

            {error && (
              <div className="error-box">
                <b>Investigation failed</b>
                <p>{error}</p>
              </div>
            )}

            <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
              <button
                className="btn primary large"
                disabled={busy || q.trim().length < 8}
              >
                {busy ? (
                  <>
                    <LoaderCircle className="spin" size={16} /> Running…
                  </>
                ) : (
                  <>
                    Launch investigation <ArrowRight size={16} />
                  </>
                )}
              </button>
              {busy && (
                <button
                  type="button"
                  className="btn secondary large"
                  onClick={cancel}
                >
                  <X size={16} /> Cancel
                </button>
              )}
            </div>

            <small className="form-foot">
              <ShieldCheck size={14} /> Findings remain traceable to sources and
              may require human review.
            </small>
          </form>
        </Panel>

        <aside className="aside">
          <div className="aside-card">
            <span className="feature-icon">
              <Sparkles size={18} />
            </span>
            <h3>What happens next?</h3>
            {STAGES.map((s, i) => {
              const isDone = completed.includes(s.id);
              const isActive = activeStage === s.id;
              return (
                <div className="step" key={s.id}>
                  <span>0{i + 1}</span>
                  <b style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <s.I
                      size={14}
                      style={{
                        color: isDone
                          ? "var(--teal)"
                          : isActive
                            ? "var(--teal)"
                            : "var(--muted)",
                      }}
                    />
                    {s.label}
                  </b>
                </div>
              );
            })}
          </div>

          {busy && (
            <div className="aside-card">
              <h3>Execution log</h3>
              <pre
                className="json"
                style={{ maxHeight: 220, margin: 0, fontSize: 10 }}
              >
                {log.join("\n") || "Waiting for events…"}
              </pre>
            </div>
          )}

          <div className="aside-card">
            <h3>Research principles</h3>
            <p>
              Source-grounded results, transparent limitations, and explicit
              review states. This workspace is not investment advice.
            </p>
            <Link className="table-link" href="/research">
              View research history <ArrowRight size={13} />
            </Link>
          </div>
        </aside>
      </div>
    </>
  );
}
