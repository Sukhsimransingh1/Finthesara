
"use client";

import { useMemo, useState, type FormEvent } from "react";
import {
  BarChart3,
  LoaderCircle,
  Info,
  ExternalLink,
  FileText,
  ChevronDown,
  Search,
} from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { api } from "@/lib/api";
import { useProjects } from "@/components/projects/ProjectProvider";
import { Heading, Panel, Empty, ErrorBox } from "@/components/ui";

type JsonRecord = Record<string, unknown>;

interface FinancialValue {
  company?: string;
  metric?: string;
  period?: { label?: string; start_date?: string; end_date?: string };
  value?: number | string;
  currency?: string | null;
  unit?: string | null;
  source_id?: string | null;
  source_url?: string | null;
}

interface MetricGroup {
  company?: string;
  metric?: string;
  values?: FinancialValue[];
  source_count?: number;
}

interface FinancialAnalysisResponse extends JsonRecord {
  company?: string;
  ticker?: string;
  period?: string;
  metrics?: MetricGroup[];
}

interface DocumentEvidence {
  evidence_id?: string;
  chunk_id?: string;
  document_id?: string;
  content?: string;
  company?: string | null;
  document_type?: string | null;
  publication_date?: string | null;
  page_number?: number | null;
  source_url?: string | null;
}

interface DocumentAnalysisResponse {
  project_id?: string;
  question?: string;
  answer?: string;
  evidence?: DocumentEvidence[];
  result_count?: number;
}

interface MetricCard {
  company: string;
  metric: string;
  period: string;
  value: number;
  currency: string;
  unit: string;
  sourceId: string;
  sourceUrl: string;
}

const METRIC_LABELS: Record<string, string> = {
  revenue: "Revenue",
  operating_expense: "Operating expenses",
  operating_income: "Operating income",
  net_income: "Net income",
  gross_profit: "Gross profit",
  eps: "Earnings per share",
};

function isRecord(value: unknown): value is JsonRecord {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function asString(value: unknown, fallback = ""): string {
  return typeof value === "string" ? value : fallback;
}

function collectMetricGroups(response: unknown): MetricGroup[] {
  if (!isRecord(response)) return [];

  const groups: MetricGroup[] = [];
  const visited = new Set<unknown>();

  function visit(value: unknown, depth = 0) {
    if (depth > 6 || !value || visited.has(value)) return;

    if (typeof value === "object") visited.add(value);

    if (Array.isArray(value)) {
      for (const item of value) visit(item, depth + 1);
      return;
    }

    if (!isRecord(value)) return;

    if (typeof value.metric === "string" && Array.isArray(value.values)) {
      groups.push(value as unknown as MetricGroup);
    }

    for (const [key, child] of Object.entries(value)) {
      if (["values", "period", "metadata", "retrieval_config"].includes(key)) {
        continue;
      }
      if (Array.isArray(child) || isRecord(child)) visit(child, depth + 1);
    }
  }

  visit(response);
  return groups;
}

function toMetricCards(response: unknown): MetricCard[] {
  const cards: MetricCard[] = [];

  for (const group of collectMetricGroups(response)) {
    for (const item of group.values ?? []) {
      if (item.value === null || item.value === undefined || item.value === "") {
        continue;
      }

      const numericValue = Number(item.value);
      if (!Number.isFinite(numericValue)) continue;

      cards.push({
        company: item.company || group.company || "Company",
        metric: item.metric || group.metric || "Financial metric",
        period: item.period?.label || "Reported period",
        value: numericValue,
        currency: item.currency || "",
        unit: item.unit || "",
        sourceId: item.source_id || "",
        sourceUrl: item.source_url || "",
      });
    }
  }

  return cards;
}

function labelMetric(metric: string): string {
  return (
    METRIC_LABELS[metric.toLowerCase()] ||
    metric.replace(/[_-]+/g, " ").replace(/\b\w/g, (char) => char.toUpperCase())
  );
}

function formatValue(card: MetricCard): string {
  const isPerShare = card.metric.toLowerCase() === "eps";
  const isCurrency = Boolean(card.currency) || card.unit === "USD";
  const formatted = new Intl.NumberFormat("en-US", {
    maximumFractionDigits: isPerShare ? 4 : 2,
  }).format(card.value);

  if (isCurrency || isPerShare) {
    const currencyCode = card.currency || (isPerShare ? "USD" : "");
    if (currencyCode) {
      try {
        return new Intl.NumberFormat("en-US", {
          style: "currency",
          currency: currencyCode,
          maximumFractionDigits: isPerShare ? 4 : 2,
        }).format(card.value);
      } catch {
        return `${currencyCode} ${formatted}`;
      }
    }
  }

  return card.unit ? `${formatted} ${card.unit}` : formatted;
}

function getErrorMessage(error: unknown): string {
  return error instanceof Error
    ? error.message
    : "The financial analysis request failed.";
}

function getCompany(response: FinancialAnalysisResponse): string {
  if (typeof response.company === "string") return response.company;
  return toMetricCards(response)[0]?.company || asString(response.ticker, "");
}

export default function FinancialAnalysis() {
  const {
    projects,
    selectedProjectId,
    selectedProject,
    setSelectedProjectId,
    loading: projectsLoading,
  } = useProjects();

  const [mode, setMode] = useState<"ticker" | "documents">("ticker");
  const [ticker, setTicker] = useState("");
  const [question, setQuestion] = useState("");
  const [documentData, setDocumentData] =
    useState<DocumentAnalysisResponse | null>(null);
  const [period, setPeriod] = useState("Latest");
  const [data, setData] = useState<FinancialAnalysisResponse | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  function changeMode(nextMode: "ticker" | "documents") {
    setMode(nextMode);
    setData(null);
    setDocumentData(null);
    setError("");
  }

  async function runAnalysis(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (mode === "documents") {
      const cleanQuestion = question.trim();

      if (!selectedProjectId) {
        setError("Select a project before analyzing indexed documents.");
        return;
      }

      if (cleanQuestion.length < 5) {
        setError("Enter a financial analysis question (at least 5 characters).");
        return;
      }

      setBusy(true);
      setError("");
      setData(null);
      setDocumentData(null);

      try {
        const response = await api<DocumentAnalysisResponse>(
          "/financial-analysis/documents",
          {
            method: "POST",
            body: JSON.stringify({
              project_id: selectedProjectId,
              question: cleanQuestion,
              top_k: 10,
            }),
          },
        );
        setDocumentData(response);
      } catch (err) {
        setError(getErrorMessage(err));
      } finally {
        setBusy(false);
      }
      return;
    }

    const normalizedTicker = ticker.trim().toUpperCase();

    if (!normalizedTicker) {
      setError("Enter a ticker symbol before running the analysis.");
      return;
    }

    setBusy(true);
    setError("");
    setData(null);
    setDocumentData(null);

    try {
      const response = await api<FinancialAnalysisResponse>(
        "/financial-analysis",
        {
          method: "POST",
          body: JSON.stringify({ ticker: normalizedTicker, period }),
        },
      );
      setData(response);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  const cards = useMemo(() => toMetricCards(data), [data]);
  const company = data ? getCompany(data) : "";

  const sources = useMemo(() => {
    const unique = new Map<string, MetricCard>();
    for (const card of cards) {
      if (card.sourceUrl) unique.set(card.sourceUrl, card);
    }
    return Array.from(unique.values());
  }, [cards]);

  return (
    <>
      <Heading
        eyebrow="INTELLIGENCE / FUNDAMENTALS"
        title="Financial analysis"
        description="Explore reported company financials and deterministic calculations sourced from SEC filings."
      />

      <Panel
        title="Analysis request"
        description="Choose SEC company fundamentals or analysis grounded in your indexed financial documents."
      >
        <div className="financial-mode-selector" role="group" aria-label="Analysis source">
          <button
            className={`btn ${mode === "ticker" ? "primary" : "secondary"}`}
            type="button"
            onClick={() => changeMode("ticker")}
            disabled={busy}
            aria-pressed={mode === "ticker"}
          >
            <BarChart3 size={15} /> Ticker
          </button>
          <button
            className={`btn ${mode === "documents" ? "primary" : "secondary"}`}
            type="button"
            onClick={() => changeMode("documents")}
            disabled={busy}
            aria-pressed={mode === "documents"}
          >
            <FileText size={15} /> Indexed Documents
          </button>
        </div>

        <form className="financial-request-form" onSubmit={runAnalysis}>
          <div className="financial-request-fields">
            {mode === "ticker" ? (
              <>
                <label>
                  Ticker
                  <input
                    required
                    value={ticker}
                    onChange={(event) => setTicker(event.target.value.toUpperCase())}
                    placeholder="Enter a ticker, e.g. AAPL"
                    autoComplete="off"
                    disabled={busy}
                  />
                  <small>
                    Enter a ticker symbol. Company names or unsupported formats
                    may be rejected by the backend.
                  </small>
                </label>

                <label>
                  Reporting period
                  <select
                    value={period}
                    onChange={(event) => setPeriod(event.target.value)}
                    disabled={busy}
                  >
                    <option value="Latest">Latest</option>
                    <option value="FY2024">FY2024</option>
                    <option value="FY2023">FY2023</option>
                    <option value="FY2022">FY2022</option>
                    <option value="Quarterly">Quarterly</option>
                  </select>
                </label>
              </>
            ) : (
              <>
                <label>
                  Project
                  <select
                    value={selectedProjectId}
                    onChange={(event) => {
                      setSelectedProjectId(event.target.value);
                      setDocumentData(null);
                      setData(null);
                      setError("");
                    }}
                    disabled={busy || projectsLoading || projects.length === 0}
                    required
                  >
                    <option value="">Select a project</option>
                    {projects.map((project) => (
                      <option key={project.id} value={project.id}>
                        {project.name}
                      </option>
                    ))}
                  </select>
                  <small>
                    Searches indexed documents in the selected project
                    {selectedProject ? `: ${selectedProject.name}` : "."}
                  </small>
                </label>

                <label>
                  Financial question
                  <textarea
                    required
                    rows={4}
                    minLength={5}
                    maxLength={5000}
                    value={question}
                    onChange={(event) => setQuestion(event.target.value)}
                    placeholder="Enter your financial question..."
                    disabled={busy || projectsLoading || !selectedProjectId}
                  />
                  <small>
                    Answers use indexed evidence and include references when
                    available.
                  </small>
                </label>
              </>
            )}
          </div>

          <button
            className="btn primary financial-submit-button"
            type="submit"
            disabled={
              busy ||
              (mode === "ticker"
                ? !ticker.trim()
                : projectsLoading ||
                  !selectedProjectId ||
                  question.trim().length < 5)
            }
          >
            {busy ? (
              <LoaderCircle size={15} className="spin" />
            ) : mode === "ticker" ? (
              <BarChart3 size={15} />
            ) : (
              <Search size={15} />
            )}
            {busy
              ? "Analyzing..."
              : mode === "ticker"
                ? "Run analysis"
                : "Analyze indexed documents"}
          </button>
        </form>

        {error && <ErrorBox message={error} />}

        <div className="financial-notice">
          <Info size={17} />
          <p>
            {mode === "ticker"
              ? "Financial data availability depends on the SEC backend source and reporting periods. Metrics are displayed only when returned by the API."
              : "Indexed-document analysis is limited to evidence retrieved from the selected project. It does not fetch external SEC data in this mode."}
          </p>
        </div>
      </Panel>

      <Panel
        title="Analysis output"
        description={
          documentData
            ? `${selectedProject?.name || "Selected project"} · Indexed document analysis`
            : data
              ? `${company || ticker} · ${period}`
              : "Your financial results will appear here."
        }
      >
        {busy ? (
          <div className="financial-loading">
            <LoaderCircle size={22} className="spin" />
            <p>Retrieving financial data and processing results...</p>
          </div>
        ) : documentData ? (
          <div className="financial-results">
            <div className="financial-results-heading">
              <div>
                <span className="financial-eyebrow">INDEXED DOCUMENTS</span>
                <h2>{selectedProject?.name || "Project analysis"}</h2>
                <p>
                  {documentData.result_count ?? documentData.evidence?.length ?? 0}{" "}
                  evidence item(s) retrieved
                </p>
              </div>
              <span className="financial-source-count">
                <FileText size={14} /> {documentData.evidence?.length ?? 0} evidence items
              </span>
            </div>

            {documentData.answer ? (
              <div className="markdown-content financial-document-answer">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {documentData.answer}
                </ReactMarkdown>
              </div>
            ) : (
              <Empty
                title="No analysis answer returned"
                description="The backend returned no generated answer. Inspect the raw response below."
              />
            )}

            {(documentData.evidence?.length ?? 0) > 0 && (
              <section className="financial-sources">
                <h3>Retrieved evidence</h3>
                <div className="financial-source-list">
                  {documentData.evidence?.map((item, index) => (
                    <article
                      className="financial-source-item"
                      key={
                        item.evidence_id ||
                        item.chunk_id ||
                        `${item.document_id || "doc"}-${index}`
                      }
                    >
                      <FileText size={16} />
                      <span>
                        <b>
                          Evidence [E{index + 1}] · {item.company || "Company not specified"}
                        </b>
                        <small>
                          {[
                            item.document_type,
                            item.page_number ? `Page ${item.page_number}` : null,
                            item.document_id ? `Document ${item.document_id}` : null,
                          ]
                            .filter(Boolean)
                            .join(" · ")}
                        </small>
                        {item.content && <small>{item.content}</small>}
                        {item.source_url && (
                          <a href={item.source_url} target="_blank" rel="noopener noreferrer">
                            Open source <ExternalLink size={12} />
                          </a>
                        )}
                      </span>
                    </article>
                  ))}
                </div>
              </section>
            )}

            <details className="financial-raw-response">
              <summary><ChevronDown size={14} /> Inspect raw API response</summary>
              <pre className="json">{JSON.stringify(documentData, null, 2)}</pre>
            </details>
          </div>
        ) : data && cards.length > 0 ? (
          <div className="financial-results">
            <div className="financial-results-heading">
              <div>
                <span className="financial-eyebrow">COMPANY</span>
                <h2>{company || ticker}</h2>
                <p>{period} · SEC-sourced financial data</p>
              </div>
              <span className="financial-source-count">
                <FileText size={14} />
                {sources.length} source{sources.length === 1 ? "" : "s"}
              </span>
            </div>

            <div className="financial-metric-grid">
              {cards.map((card, index) => (
                <article
                  className="financial-metric-card"
                  key={`${card.metric}-${card.period}-${index}`}
                >
                  <span>{labelMetric(card.metric)}</span>
                  <strong>{formatValue(card)}</strong>
                  <small>{card.period}</small>
                  {card.sourceUrl && (
                    <a href={card.sourceUrl} target="_blank" rel="noopener noreferrer">
                      View SEC source <ExternalLink size={12} />
                    </a>
                  )}
                </article>
              ))}
            </div>

            {sources.length > 0 && (
              <section className="financial-sources">
                <h3>Source evidence</h3>
                <div className="financial-source-list">
                  {sources.map((source) => (
                    <a
                      className="financial-source-item"
                      key={source.sourceUrl}
                      href={source.sourceUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      <FileText size={16} />
                      <span>
                        <b>{labelMetric(source.metric)} · {source.period}</b>
                        <small>{source.sourceId || source.sourceUrl}</small>
                      </span>
                      <ExternalLink size={14} />
                    </a>
                  ))}
                </div>
              </section>
            )}

            <details className="financial-raw-response">
              <summary><ChevronDown size={14} /> Inspect raw API response</summary>
              <pre className="json">{JSON.stringify(data, null, 2)}</pre>
            </details>
          </div>
        ) : data ? (
          <div className="financial-empty-results">
            <Empty
              title="No financial metrics returned"
              description="The request succeeded, but the response did not contain recognized metric values. Inspect the raw response."
            />
            <details className="financial-raw-response" open>
              <summary>Raw API response</summary>
              <pre className="json">{JSON.stringify(data, null, 2)}</pre>
            </details>
          </div>
        ) : (
          <Empty
            title="No analysis requested"
            description={
              mode === "ticker"
                ? "Enter a ticker and run an analysis to view reported metrics and SEC source links."
                : "Select a project and enter a financial question to analyze its indexed documents."
            }
          />
        )}
      </Panel>

      <div className="financial-notice">
        <Info size={17} />
        <p>
          Financial figures depend on available reported data. Calculations
          should use compatible periods and units. This page is for research
          and is not personalized investment advice.
        </p>
      </div>

      <style jsx>{`
        .financial-mode-selector {
          display: flex;
          flex-wrap: wrap;
          gap: 0.5rem;
          margin-bottom: 1.25rem;
        }

        .financial-request-form {
          display: flex;
          flex-direction: column;
          align-items: stretch;
          gap: 1rem;
          min-width: 0;
        }

        .financial-request-fields {
          display: grid;
          grid-template-columns: repeat(2, minmax(0, 1fr));
          align-items: start;
          gap: 1rem 1.25rem;
          min-width: 0;
        }

        .financial-request-fields > label {
          display: flex;
          flex-direction: column;
          align-items: stretch;
          gap: 0.55rem;
          width: 100%;
          min-width: 0;
        }

        .financial-request-fields input,
        .financial-request-fields select,
        .financial-request-fields textarea {
          box-sizing: border-box;
          width: 100%;
          max-width: 100%;
          min-width: 0;
        }

        .financial-request-fields textarea {
          resize: vertical;
        }

        .financial-request-fields small {
          display: block;
          line-height: 1.5;
        }

        .financial-submit-button {
          align-self: flex-start;
          max-width: 100%;
          white-space: normal;
        }

        @media (max-width: 760px) {
          .financial-request-fields {
            grid-template-columns: minmax(0, 1fr);
          }

          .financial-submit-button {
            align-self: stretch;
            justify-content: center;
          }
        }
      `}</style>
    </>
  );
}
