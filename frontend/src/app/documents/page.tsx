"use client";

import { useState } from "react";
import { FileUp, RefreshCw, CheckCircle2 } from "lucide-react";
import { api, DEFAULT_PROJECT_ID, type UploadResponse } from "@/lib/api";
import { Heading, Panel, Empty, ErrorBox } from "@/components/ui";

const DOC_TYPES = [
  "10-K",
  "10-Q",
  "8-K",
  "Annual Report",
  "Earnings Call",
  "Press Release",
  "unknown",
] as const;

export default function Documents() {
  const [file, setFile] = useState<File | null>(null);
  const [company, setCompany] = useState("");
  const [docType, setDocType] = useState<string>("unknown");
  const [uploading, setUploading] = useState(false);
  const [msg, setMsg] = useState("");
  const [err, setErr] = useState("");
  const [result, setResult] = useState<UploadResponse | null>(null);

  async function handleUpload(e: React.FormEvent) {
    e.preventDefault();
    if (!file) return;
    setUploading(true);
    setErr("");
    setMsg("");
    setResult(null);
    try {
      const form = new FormData();
      form.append("file", file);
      form.append("project_id", DEFAULT_PROJECT_ID);
      form.append("document_type", docType);
      form.append("company", company.trim() || "unknown");
      const res = await api<UploadResponse>("/documents/upload", {
        method: "POST",
        body: form,
      });
      setResult(res);
      setMsg(res.message || "Document submitted for ingestion.");
    } catch (e: unknown) {
      setErr(e instanceof Error ? e.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  }

  return (
    <>
      <Heading
        eyebrow="INTELLIGENCE / KNOWLEDGE BASE"
        title="Document library"
        description="Upload source documents for ingestion and retrieval. Ingestion is asynchronous; a successful upload does not mean the document is fully indexed."
      />

      <Panel
        title="Upload a source document"
        description="Submit a document to the ingestion pipeline"
      >
        <form className="inline-form" onSubmit={handleUpload}>
          <label style={{ display: "flex", flexDirection: "column", gap: 6, fontSize: 12, fontWeight: 600 }}>
            File
            <input
              type="file"
              accept=".pdf,.txt,.md,.docx,.csv,.html"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              disabled={uploading}
              required
            />
          </label>
          <label style={{ display: "flex", flexDirection: "column", gap: 6, fontSize: 12, fontWeight: 600 }}>
            Company
            <input
              value={company}
              onChange={(e) => setCompany(e.target.value)}
              placeholder="e.g. Apple Inc."
              disabled={uploading}
            />
          </label>
          <label style={{ display: "flex", flexDirection: "column", gap: 6, fontSize: 12, fontWeight: 600 }}>
            Document type
            <select
              value={docType}
              onChange={(e) => setDocType(e.target.value)}
              disabled={uploading}
            >
              {DOC_TYPES.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          </label>
          <button className="btn primary" type="submit" disabled={uploading || !file}>
            <FileUp size={15} /> {uploading ? "Uploading…" : "Upload"}
          </button>
        </form>

        {msg && (
          <div className="notice">
            <CheckCircle2 size={17} />
            <span>{msg}</span>
          </div>
        )}
        {err && <ErrorBox message={err} />}

        {result && (
          <div className="muted" style={{ marginTop: 12 }}>
            <b>Ingestion response:</b>
            <pre className="json">{JSON.stringify(result, null, 2)}</pre>
          </div>
        )}
      </Panel>

      <Panel
        title="Indexed documents"
        description="The backend does not currently expose a document listing endpoint"
        action={
          <button
            className="icon-btn"
            onClick={() => {
              setErr("");
            }}
            aria-label="Refresh"
          >
            <RefreshCw size={15} />
          </button>
        }
      >
        <Empty
          title="Document listing not available"
          description="The backend ingestion endpoint accepts uploads, but no GET /documents listing endpoint is currently exposed. Uploaded documents are processed by the ingestion pipeline; check the backend logs for processing status."
        />
      </Panel>

      <div className="notice">
        <FileUp size={17} />
        <span>
          <b>Supported file types:</b> PDF (max 20MB). Other formats depend on
          backend parser availability. Uploads require a valid Supabase access
          token.
        </span>
      </div>
    </>
  );
}
