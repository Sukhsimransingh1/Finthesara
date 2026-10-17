"use client";

import { FormEvent, useEffect, useState } from "react";
import {
  Search,
  LoaderCircle,
  FileText,
  ExternalLink,
  RefreshCw,
} from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { api } from "@/lib/api";
import { useProjects } from "@/components/projects/ProjectProvider";
import { Heading, Panel, Empty, ErrorBox } from "@/components/ui";

interface Evidence {
  id?: string;
  document_id?: string;
  document_title?: string;
  title?: string;
  source?: string;
  source_url?: string;
  url?: string;
  content?: string;
  text?: string;
  snippet?: string;
  score?: number;
  metadata?: Record<string, unknown>;
}

interface RagResponse {
  query?: string;
  project_id?: string;
  answer?: string;
  result?: string;
  response?: string;
  evidence?: Evidence[];
  sources?: Evidence[];
  results?: Evidence[];
  result_count?: number;
  retrieval_config?: Record<string, unknown>;
  [key: string]: unknown;
}

function getAnswer(data: RagResponse): string {
  for (const value of [data.answer, data.result, data.response]) {
    if (typeof value === "string" && value.trim()) {
      return value;
    }
  }

  return "";
}

function getEvidence(data: RagResponse): Evidence[] {
  for (const value of [data.evidence, data.sources, data.results]) {
    if (Array.isArray(value)) {
      return value;
    }
  }

  return [];
}

function getErrorMessage(error: unknown): string {
  return error instanceof Error
    ? error.message
    : "The research query could not be completed.";
}

export default function Rag() {
  const {
    selectedProjectId,
    selectedProject,
    loading: projectsLoading,
  } = useProjects();

  const [query, setQuery] = useState("");
  const [result, setResult] = useState<RagResponse | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    setResult(null);
    setError("");
  }, [selectedProjectId]);

  async function ask(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const cleanQuery = query.trim();

    if (!selectedProjectId) {
      setError("Select a project before querying the knowledge base.");
      return;
    }

    if (!cleanQuery) {
      setError("Enter a question first.");
      return;
    }

    setBusy(true);
    setError("");
    setResult(null);

    try {
      const data = await api<RagResponse>("/rag/query", {
        method: "POST",
        body: JSON.stringify({
          query: cleanQuery,
          project_id: selectedProjectId,
          top_k: 10,
        }),
      });

      setResult(data);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  const answer = result ? getAnswer(result) : "";
  const evidence = result ? getEvidence(result) : [];

  return (
    <>
      <Heading
        eyebrow="INTELLIGENCE / RETRIEVAL"
        title="Research copilot"
        description="Ask questions about your indexed financial documents and inspect the supporting evidence."
      />

      <Panel
        title="Ask the knowledge base"
        description={
          selectedProject
            ? `Searching within ${selectedProject.name}.`
            : "Select a project from the sidebar to begin."
        }
      >
        <form className="query-form" onSubmit={ask}>
          <textarea
            required
            rows={4}
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Ask about revenue growth, disclosed risks, financial metrics, or a source document..."
            disabled={busy || projectsLoading || !selectedProjectId}
            aria-label="Research question"
          />

          <button
            className="btn primary"
            type="submit"
            disabled={
              busy ||
              projectsLoading ||
              !selectedProjectId ||
              !query.trim()
            }
          >
            {busy ? (
              <LoaderCircle size={15} className="spin" />
            ) : (
              <Search size={15} />
            )}
            {busy ? "Researching..." : "Search sources"}
          </button>
        </form>

        {projectsLoading && (
          <p className="muted">Loading projects...</p>
        )}

        {!projectsLoading && !selectedProjectId && (
          <p className="muted">
            No active project is selected. Create or select a project in the
            sidebar.
          </p>
        )}

        {error && <ErrorBox message={error} />}
      </Panel>

      {result && (
        <>
          <Panel
            title="Research answer"
            description="Generated from the response returned by your backend."
          >
            {answer ? (
              <div className="markdown-content">
                <ReactMarkdown
                  remarkPlugins={[remarkGfm]}
                  components={{
                    a: ({ children, href, ...props }) => (
                      <a
                        href={href}
                        target="_blank"
                        rel="noopener noreferrer"
                        {...props}
                      >
                        {children}
                      </a>
                    ),
                  }}
                >
                  {answer}
                </ReactMarkdown>
              </div>
            ) : (
              <>
                <Empty
                  title="No text answer returned"
                  description="The API returned a response, but no answer, result, or response text field was found."
                />
                <details>
                  <summary>Inspect complete API response</summary>
                  <pre className="json">
                    {JSON.stringify(result, null, 2)}
                  </pre>
                </details>
              </>
            )}
          </Panel>

          <Panel
            title="Supporting evidence"
            description={`${evidence.length} evidence item(s) returned by the API.`}
          >
            {evidence.length === 0 ? (
              <Empty
                title="No evidence items returned"
                description="The backend did not include a recognized evidence, sources, or results array for this query."
              />
            ) : (
              <div className="evidence-list">
                {evidence.map((item, index) => {
                  const title =
                    item.document_title ||
                    item.title ||
                    item.source ||
                    `Evidence ${index + 1}`;

                  const passage =
                    item.content || item.text || item.snippet || "";

                  const sourceUrl = item.source_url || item.url;

                  return (
                    <article
                      className="evidence-item"
                      key={`${item.id || item.document_id || title}-${index}`}
                    >
                      <div className="evidence-item-heading">
                        <FileText size={17} />
                        <b>{title}</b>
                      </div>

                      {passage && <p>{passage}</p>}

                      {typeof item.score === "number" && (
                        <small>
                          Retrieval score: {item.score.toFixed(4)}
                        </small>
                      )}

                      {sourceUrl && (
                        <a
                          href={sourceUrl}
                          target="_blank"
                          rel="noopener noreferrer"
                        >
                          View source <ExternalLink size={13} />
                        </a>
                      )}
                    </article>
                  );
                })}
              </div>
            )}
          </Panel>

          <details className="response-details">
            <summary>Inspect complete API response</summary>
            <pre className="json">
              {JSON.stringify(result, null, 2)}
            </pre>
          </details>
        </>
      )}

      {!result && !busy && (
        <Panel title="Response">
          <Empty
            title="No query submitted"
            description="Submit a question to see the generated answer and any supporting evidence returned by the backend."
          />
        </Panel>
      )}

      {busy && (
        <Panel title="Research in progress">
          <p className="muted">
            Retrieving relevant passages and generating an answer...
          </p>
        </Panel>
      )}

      <div className="rag-refresh">
        <button
          type="button"
          className="icon-btn"
          onClick={() => {
            setQuery("");
            setResult(null);
            setError("");
          }}
          disabled={busy}
        >
          <RefreshCw size={14} />
          Clear query
        </button>
      </div>
    </>
  );
}
