"use client";

import { useState } from "react";
import { Search, LoaderCircle, AlertCircle } from "lucide-react";
import { Heading, Panel, Empty, ErrorBox } from "@/components/ui";

export default function Rag() {
  const [q, setQ] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  async function ask(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setErr("");
    try {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000"}${
          process.env.NEXT_PUBLIC_API_PREFIX || "/api/v1"
        }/rag/query`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ query: q }),
        },
      );
      if (!res.ok) {
        const text = await res.text().catch(() => "");
        throw new Error(
          `RAG query endpoint returned ${res.status}. ${text}`,
        );
      }
      const data = await res.json();
      setErr(JSON.stringify(data, null, 2));
    } catch (e: unknown) {
      setErr(e instanceof Error ? e.message : "Request failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <Heading
        eyebrow="INTELLIGENCE / RETRIEVAL"
        title="Research copilot"
        description="Query the connected knowledge base and inspect retrieved context."
      />

      <Panel title="Ask the knowledge base">
        <form className="query-form" onSubmit={ask}>
          <textarea
            required
            rows={3}
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Ask about a filing, a disclosed risk, a financial metric, or a source document…"
          />
          <button
            className="btn primary"
            disabled={busy || !q.trim()}
            type="submit"
          >
            {busy ? (
              <LoaderCircle size={15} className="spin" />
            ) : (
              <Search size={15} />
            )}{" "}
            Search sources
          </button>
        </form>
        {err && <ErrorBox message={err} />}
      </Panel>

      <Panel title="Response">
        <Empty
          title="RAG query endpoint not available"
          description="The backend does not currently expose a POST /api/v1/rag/query endpoint. Retrieval is performed internally by the multi-agent research workflow. Submit a query above to confirm availability."
        />
      </Panel>

      <div className="notice">
        <AlertCircle size={17} />
        <span>
          <b>Evidence-first retrieval.</b> The hybrid RAG pipeline (sparse +
          vector search with RRF) runs as part of the research workflow. A
          standalone RAG query endpoint is not yet exposed by the backend.
        </span>
      </div>
    </>
  );
}
