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
  storeRunResult,
  DEFAULT_PROJECT_ID,
  type ResearchResponse,
} from "@/lib/api";
import { Heading, Panel } from "@/components/ui";

const STAGES = [
  { label: "Planning", I: GitBranch },
  { label: "Financial analysis", I: BarChart3 },
  { label: "Retrieval", I: Search },
  { label: "Evidence fusion", I: ShieldCheck },
  { label: "Verification", I: CheckCircle2 },
  { label: "Synthesis", I: FileText },
] as const;

export default function NewResearch() {
  const [q, setQ] = useState("");
  const [entity, setEntity] = useState("");
  const [focus, setFocus] = useState(
    "financial fundamentals",
  );
  const [period, setPeriod] = useState(
    "latest available",
  );
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const abortRef = useRef<AbortController | null>(null);
  const router = useRouter();

  async function submit(e: FormEvent) {
    e.preventDefault();

    if (busy) return;

    setError("");
    setMessage("");

    if (!DEFAULT_PROJECT_ID) {
      setError(
        "NEXT_PUBLIC_PROJECT_ID is missing. Add the UUID of a project owned by your Supabase user to frontend/.env.local, then restart Next.js.",
      );
      return;
    }

    const uuidPattern =
      /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

    if (!uuidPattern.test(DEFAULT_PROJECT_ID)) {
      setError(
        "NEXT_PUBLIC_PROJECT_ID must be a valid project UUID, not your Supabase project reference or URL.",
      );
      return;
    }

    setBusy(true);

    setMessage(
      "Submitting one research request. The current backend runs this workflow synchronously; live node updates are not exposed by this endpoint.",
    );

    const question = [
      q.trim(),
      entity.trim()
        ? `Company/entity: ${entity.trim()}`
        : "",
      `Research focus: ${focus}`,
      `Reporting period: ${period}`,
    ]
      .filter(Boolean)
      .join("\n");

    const runId = crypto.randomUUID();
    const controller = new AbortController();
    abortRef.current = controller;

    try {
      const result = await api<ResearchResponse>(
        "/research",
        {
          method: "POST",
          body: JSON.stringify({
            question,
            project_id: DEFAULT_PROJECT_ID,
            run_id: runId,
          }),
          signal: controller.signal,
        },
      );

      const normalized = {
        ...result,
        run_id: result.run_id || runId,
      };

      storeRunResult(normalized);

      if (!normalized.run_id) {
        throw new Error(
          "The backend returned no run ID, so this result cannot be opened.",
        );
      }

      router.push(
        `/research/${encodeURIComponent(normalized.run_id)}`,
      );
    } catch (e: unknown) {
      if (e instanceof Error && e.name === "AbortError") {
        setError(
          "Request cancelled. The backend may already have started processing; check research history before retrying.",
        );
      } else {
        setError(
          e instanceof Error
            ? e.message
            : "Research request failed.",
        );
      }
    } finally {
      setBusy(false);
      abortRef.current = null;
    }
  }

  function cancel() {
    abortRef.current?.abort();
  }

  return (
    <>
      <Heading
        eyebrow="WORKSPACE / NEW RUN"
        title="Start an investigation"
        description="Describe the question. The backend handles retrieval, financial analysis, and verification."
      />

      <div className="research-layout">
        <Panel
          title="Investigation brief"
          description="Specify the entity, scope, and reporting period."
        >
          <form
            className="research-form"
            onSubmit={submit}
          >
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

            {message && (
              <div className="notice">
                <InfoIcon />
                <span>{message}</span>
              </div>
            )}

            {error && (
              <div className="error-box">
                <b>Investigation failed</b>
                <p>{error}</p>
              </div>
            )}

            <div
              style={{
                display: "flex",
                gap: 10,
                flexWrap: "wrap",
              }}
            >
              <button
                className="btn primary large"
                disabled={busy || q.trim().length < 8}
              >
                {busy ? (
                  <>
                    <LoaderCircle
                      className="spin"
                      size={16}
                    />
                    Running…
                  </>
                ) : (
                  <>
                    Launch investigation
                    <ArrowRight size={16} />
                  </>
                )}
              </button>

              {busy && (
                <button
                  type="button"
                  className="btn secondary large"
                  onClick={cancel}
                >
                  <X size={16} />
                  Cancel request
                </button>
              )}
            </div>

            <small className="form-foot">
              <ShieldCheck size={14} />
              Findings should be traceable to sources and may
              require human review.
            </small>
          </form>
        </Panel>

        <aside className="aside">
          <div className="aside-card">
            <span className="feature-icon">
              <Sparkles size={18} />
            </span>

            <h3>Research workflow</h3>

            {STAGES.map((stage, i) => (
              <div className="step" key={stage.label}>
                <span>0{i + 1}</span>
                <b
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 8,
                  }}
                >
                  <stage.I
                    size={14}
                    style={{ color: "var(--teal)" }}
                  />
                  {stage.label}
                </b>
              </div>
            ))}

            <p
              className="muted"
              style={{ marginTop: 12 }}
            >
              These are workflow stages, not live progress
              indicators. Live node events require the backend
              streaming endpoint to return a single complete
              result.
            </p>
          </div>

          <div className="aside-card">
            <h3>Research principles</h3>
            <p>
              Source-grounded results, transparent limitations,
              and explicit review states. This workspace is not
              investment advice.
            </p>

            <Link className="table-link" href="/research">
              View research history
              <ArrowRight size={13} />
            </Link>
          </div>
        </aside>
      </div>
    </>
  );
}

function InfoIcon() {
  return <ShieldCheck size={17} aria-hidden="true" />;
}