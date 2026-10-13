"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import {
  RefreshCw,
  FileText,
  ShieldCheck,
  GitBranch,
  BarChart3,
  Search,
  CheckCircle2,
  XCircle,
  Clock,
  Info,
  Copy,
  Printer,
  ThumbsUp,
  ThumbsDown,
  RotateCcw,
} from "lucide-react";
import {
  api,
  statusClass,
  getStoredRunResult,
  type ResearchResponse,
  type ResearchRun,
  type HumanReviewRequest,
} from "@/lib/api";
import { Heading, Panel, Empty, ErrorBox, Tabs } from "@/components/ui";

const WF_NODES = [
  { id: "planner", label: "Planner", I: GitBranch },
  { id: "financial_analysis", label: "Financial", I: BarChart3 },
  { id: "research", label: "Retrieval", I: Search },
  { id: "evidence_fusion", label: "Fusion", I: ShieldCheck },
  { id: "verification", label: "Verify", I: CheckCircle2 },
  { id: "synthesis", label: "Synthesis", I: FileText },
] as const;

type View = "overview" | "report" | "evidence" | "trace";

export default function InvestigationDetail() {
  const { id } = useParams<{ id: string }>();
  const [run, setRun] = useState<ResearchResponse | ResearchRun | null>(null);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(true);
  const [view, setView] = useState<View>("overview");
  const [reviewMsg, setReviewMsg] = useState("");
  const [reviewComment, setReviewComment] = useState("");

  async function load() {
    try {
      const data = await api<ResearchRun>(`/research-runs/${encodeURIComponent(id)}`);
      setRun(data);
    } catch (e: unknown) {
      const stored = getStoredRunResult(id);
      if (stored) {
        setRun(stored);
        setErr(
          `${e instanceof Error ? e.message : "Request failed"} — showing locally stored result.`,
        );
      } else {
        setErr(e instanceof Error ? e.message : "Request failed");
        setRun(null);
      }
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const data = await api<ResearchRun>(`/research-runs/${encodeURIComponent(id)}`);
        if (!active) return;
        setRun(data);
      } catch (e: unknown) {
        if (!active) return;
        const stored = getStoredRunResult(id);
        if (stored) {
          setRun(stored);
          setErr(
            `${e instanceof Error ? e.message : "Request failed"} — showing locally stored result.`,
          );
        } else {
          setErr(e instanceof Error ? e.message : "Request failed");
          setRun(null);
        }
      } finally {
        if (active) setBusy(false);
      }
    })();
    return () => {
      active = false;
    };
  }, [id]);

  const state = useMemo<Record<string, unknown>>(() => {
    if (!run) return {};
    if ("state" in run && run.state) return run.state as Record<string, unknown>;
    if ("metadata" in run && (run as ResearchRun).metadata) {
      const meta = (run as ResearchRun).metadata as Record<string, unknown>;
      if (meta.state && typeof meta.state === "object") {
        return meta.state as Record<string, unknown>;
      }
      return meta;
    }
    return {};
  }, [run]);

  const question =
    (state.original_question as string) ||
    (state.normalized_question as string) ||
    (run && "question" in run ? (run as ResearchRun).question : undefined) ||
    "Research run";

  const status =
    (run && "status" in run ? run.status : undefined) ||
    (state.status as string) ||
    "unknown";

  const finalReport =
    (state.final_report as string) ||
    (run && "final_report" in run ? (run as ResearchResponse).final_report : null);
  const draftReport =
    (state.draft_report as string) ||
    (run && "draft_report" in run ? (run as ResearchResponse).draft_report : null);

  const financialResults = (state.financial_results as unknown[]) || [];
  const financialEvidence = (state.financial_evidence as unknown[]) || [];
  const evidence = (state.evidence as unknown[]) || [];
  const claims = (state.claims as unknown[]) || [];
  const verification = state.verification_result as
    | { status?: string; confidence?: number; issues?: string[] }
    | null;
  const companies = (state.companies as string[]) || [];
  const contradictions = (state.contradictions as string[]) || [];
  const errors = (state.errors as string[]) || [];
  const humanReviewRequired =
    (state.human_review_required as boolean) ||
    (run && "human_review_required" in run
      ? (run as ResearchResponse).human_review_required
      : false);

  const completedNodes = useMemo(() => {
    const done = new Set<string>();
    const agentResults = (state.agent_results as unknown[]) || [];
    for (const ar of agentResults) {
      if (ar && typeof ar === "object" && "agent" in ar) {
        done.add(String((ar as { agent: string }).agent));
      }
    }
    if (verification) done.add("verification");
    if (finalReport) done.add("synthesis");
    return done;
  }, [state, verification, finalReport]);

  async function submitReview(decision: HumanReviewRequest["decision"]) {
    setReviewMsg("");
    try {
      const res = await api(`/human-reviews/${encodeURIComponent(id)}`, {
        method: "POST",
        body: JSON.stringify({ decision, comment: reviewComment || null }),
      });
      setReviewMsg(`Review submitted: ${(res as { decision?: string }).decision || decision}`);
      setReviewComment("");
      await load();
    } catch (e: unknown) {
      setReviewMsg(e instanceof Error ? e.message : "Review failed");
    }
  }

  function copyReport() {
    if (finalReport) {
      navigator.clipboard.writeText(finalReport).catch(() => {});
    }
  }

  if (busy) {
    return (
      <>
        <Heading eyebrow="RESEARCH / RUN" title="Loading investigation…" />
        <Panel>
          <p className="muted">Fetching run {id}…</p>
        </Panel>
      </>
    );
  }

  if (!run) {
    return (
      <>
        <Heading eyebrow="RESEARCH / RUN" title="Investigation not found" />
        <ErrorBox message={err || "No data available for this run."} />
        <Panel>
          <Empty
            title="Run unavailable"
            description="This run could not be loaded from the backend or local storage."
            action={
              <Link className="btn primary" href="/research/new">
                Start a new investigation
              </Link>
            }
          />
        </Panel>
      </>
    );
  }

  return (
    <>
      <Heading
        eyebrow="RESEARCH / INVESTIGATION"
        title={question}
        description={`Run ID: ${id}`}
        action={
          <div style={{ display: "flex", gap: 8 }}>
            <button className="btn secondary" onClick={() => { setBusy(true); setErr(""); load(); }}>
              <RefreshCw size={14} /> Refresh
            </button>
            <Link className="btn primary" href="/research/new">
              New investigation
            </Link>
          </div>
        }
      />

      {err && <ErrorBox message={err} />}

      <div className="metrics">
        <div className="metric">
          <span>
            Status <Clock size={16} />
          </span>
          <b style={{ fontSize: 16 }}>
            <span className={`pill ${statusClass(status)}`}>{status}</span>
          </b>
          <small>
            {humanReviewRequired ? "Human review required" : "No review required"}
          </small>
        </div>
        <div className="metric">
          <span>
            Evidence <ShieldCheck size={16} />
          </span>
          <b>{evidence.length + financialEvidence.length}</b>
          <small>items retrieved</small>
        </div>
        <div className="metric">
          <span>
            Claims <CheckCircle2 size={16} />
          </span>
          <b>{claims.length}</b>
          <small>claims generated</small>
        </div>
      </div>

      <Panel title="Agent workflow" description="LangGraph execution stages">
        <div className="workflow-grid">
          {WF_NODES.map((n) => {
            const done = completedNodes.has(n.id);
            return (
              <div
                key={n.id}
                className={`wf-node ${done ? "done" : "pending"}`}
              >
                <n.I size={18} className="wf-ic" />
                <b>{n.label}</b>
                <small>{done ? "Completed" : "Pending"}</small>
              </div>
            );
          })}
        </div>
        {companies.length > 0 && (
          <div className="muted" style={{ marginTop: 8 }}>
            Companies: {companies.join(", ")}
          </div>
        )}
      </Panel>

      <Tabs
        tabs={[
          { id: "overview", label: "Overview" },
          { id: "report", label: "Report" },
          { id: "evidence", label: "Evidence" },
          { id: "trace", label: "Trace" },
        ]}
        active={view}
        onChange={(v) => setView(v as View)}
      />

      {view === "overview" && (
        <>
          {verification && (
            <Panel title="Verification result">
              <div className="notice">
                {verification.status === "PASS" ? (
                  <CheckCircle2 size={18} />
                ) : verification.status === "FAIL" ? (
                  <XCircle size={18} />
                ) : (
                  <Info size={18} />
                )}
                <span>
                  <b>Status: {verification.status || "unknown"}</b>
                  {verification.confidence != null &&
                    ` · Confidence: ${verification.confidence}`}
                </span>
              </div>
              {verification.issues && verification.issues.length > 0 && (
                <ul style={{ marginTop: 12, paddingLeft: 18 }}>
                  {verification.issues.map((issue, i) => (
                    <li key={i} className="muted" style={{ marginBottom: 4 }}>
                      {issue}
                    </li>
                  ))}
                </ul>
              )}
            </Panel>
          )}

          {financialResults.length > 0 && (
            <Panel title="Financial findings">
              {financialResults.map((fr, i) => {
                const f = fr as Record<string, unknown>;
                return (
                  <div key={i} className="evidence-item">
                    <h4>{String(f.company || "Financial analysis")}</h4>
                    {Array.isArray(f.findings) && f.findings.length > 0 && (
                      <ul style={{ paddingLeft: 18, marginTop: 6 }}>
                        {(f.findings as string[]).map((finding, j) => (
                          <li key={j} style={{ fontSize: 11, color: "var(--ink-soft)", marginBottom: 3 }}>
                            {finding}
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                );
              })}
            </Panel>
          )}

          {claims.length > 0 && (
            <Panel title="Claims">
              {claims.map((c, i) => {
                const claim = c as {
                  claim_id?: string;
                  statement?: string;
                  evidence_ids?: string[];
                  calculation_ids?: string[];
                };
                return (
                  <div key={i} className="claim-item verified">
                    <div className="claim-statement">{claim.statement}</div>
                    <div className="evidence-meta">
                      {claim.claim_id && <span>ID: {claim.claim_id}</span>}
                      {claim.evidence_ids && claim.evidence_ids.length > 0 && (
                        <span>Evidence: {claim.evidence_ids.length}</span>
                      )}
                      {claim.calculation_ids && claim.calculation_ids.length > 0 && (
                        <span>Calculations: {claim.calculation_ids.length}</span>
                      )}
                    </div>
                  </div>
                );
              })}
            </Panel>
          )}

          {contradictions.length > 0 && (
            <Panel title="Contradictions">
              {contradictions.map((c, i) => (
                <div key={i} className="error-box">
                  {c}
                </div>
              ))}
            </Panel>
          )}

          {errors.length > 0 && (
            <Panel title="Errors">
              {errors.map((e, i) => (
                <div key={i} className="error-box">
                  {e}
                </div>
              ))}
            </Panel>
          )}

          {!verification &&
            financialResults.length === 0 &&
            claims.length === 0 && (
              <Panel>
                <Empty
                  title="No findings yet"
                  description="This run has no structured findings to display."
                />
              </Panel>
            )}
        </>
      )}

      {view === "report" && (
        <Panel
          title="Research report"
          action={
            <div style={{ display: "flex", gap: 8 }}>
              <button className="icon-btn" onClick={copyReport} aria-label="Copy">
                <Copy size={15} />
              </button>
              <button
                className="icon-btn"
                onClick={() => window.print()}
                aria-label="Print"
              >
                <Printer size={15} />
              </button>
            </div>
          }
        >
          {finalReport || draftReport ? (
            <div className="report">
              <pre
                style={{
                  whiteSpace: "pre-wrap",
                  fontFamily: "inherit",
                  fontSize: 13,
                  lineHeight: 1.8,
                  color: "var(--ink-soft)",
                  margin: 0,
                }}
              >
                {finalReport || draftReport}
              </pre>
            </div>
          ) : (
            <Empty
              title="No report generated"
              description="The research workflow did not produce a final report."
            />
          )}
        </Panel>
      )}

      {view === "evidence" && (
        <Panel title="Evidence records">
          {(evidence.length + financialEvidence.length) === 0 ? (
            <Empty
              title="No evidence"
              description="No evidence items were retrieved for this run."
            />
          ) : (
            <>
              {financialEvidence.map((ev, i) => {
                const e = ev as Record<string, unknown>;
                return (
                  <div key={`fe-${i}`} className="evidence-item">
                    <h4>
                      {String(e.company || "Unknown")} — {String(e.metric || "metric")}
                    </h4>
                    <p>
                      {String(e.value ?? "N/A")} {String(e.unit || e.currency || "")}
                    </p>
                    <div className="evidence-meta">
                      {e.period_label != null && <span>{String(e.period_label)}</span>}
                      {e.source_id != null && <span>Source: {String(e.source_id)}</span>}
                      {e.source_url != null && (
                        <span>
                          <a
                            href={String(e.source_url)}
                            target="_blank"
                            rel="noopener noreferrer"
                            style={{ color: "var(--teal-dark)" }}
                          >
                            View source
                          </a>
                        </span>
                      )}
                    </div>
                  </div>
                );
              })}
              {evidence.map((ev, i) => {
                const e = ev as Record<string, unknown>;
                return (
                  <div key={`ev-${i}`} className="evidence-item">
                    <h4>{String(e.title || e.document_id || `Evidence ${i + 1}`)}</h4>
                    {e.excerpt != null && <p>{String(e.excerpt)}</p>}
                    <div className="evidence-meta">
                      {e.chunk_id != null && <span>Chunk: {String(e.chunk_id)}</span>}
                      {e.source_url != null && (
                        <span>
                          <a
                            href={String(e.source_url)}
                            target="_blank"
                            rel="noopener noreferrer"
                            style={{ color: "var(--teal-dark)" }}
                          >
                            Source
                          </a>
                        </span>
                      )}
                    </div>
                  </div>
                );
              })}
            </>
          )}
        </Panel>
      )}

      {view === "trace" && (
        <Panel title="Execution state">
          <pre className="json">{JSON.stringify(state, null, 2)}</pre>
        </Panel>
      )}

      {humanReviewRequired && (
        <Panel title="Human review" description="Approve, reject, or request additional research">
          {reviewMsg && (
            <div
              className={
                reviewMsg.toLowerCase().includes("fail") ||
                reviewMsg.toLowerCase().includes("error")
                  ? "error-box"
                  : "notice"
              }
            >
              {reviewMsg}
            </div>
          )}
          <div style={{ marginBottom: 12 }}>
            <label style={{ display: "flex", flexDirection: "column", gap: 6, fontSize: 12, fontWeight: 600 }}>
              Review comment (optional)
              <textarea
                rows={3}
                value={reviewComment}
                onChange={(e) => setReviewComment(e.target.value)}
                placeholder="Add context for the review decision…"
                style={{
                  width: "100%",
                  border: "1px solid var(--line)",
                  borderRadius: 7,
                  padding: 10,
                  fontSize: 12,
                  resize: "vertical",
                }}
              />
            </label>
          </div>
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
            <button
              className="btn primary"
              onClick={() => submitReview("approve")}
            >
              <ThumbsUp size={15} /> Approve
            </button>
            <button
              className="btn danger"
              onClick={() => submitReview("reject")}
            >
              <ThumbsDown size={15} /> Reject
            </button>
            <button
              className="btn secondary"
              onClick={() => submitReview("request_research")}
            >
              <RotateCcw size={15} /> Request more research
            </button>
          </div>
          <p className="muted" style={{ marginTop: 12 }}>
            Review actions require a valid Supabase access token. If
            authentication is not configured, these calls will return 401.
          </p>
        </Panel>
      )}
    </>
  );
}
