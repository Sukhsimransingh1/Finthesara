
"use client";

import {
  ChangeEvent,
  FormEvent,
  useCallback,
  useEffect,
  useState,
} from "react";
import {
  FileUp,
  RefreshCw,
  CheckCircle2,
  FileText,
  Trash2,
  LoaderCircle,
} from "lucide-react";

import { api, rows, dateLabel, type UploadResponse } from "@/lib/api";
import { useProjects } from "@/components/projects/ProjectProvider";
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

interface DocumentRecord {
  id: string;
  title?: string;
  filename?: string;
  name?: string;
  company?: string;
  document_type?: string;
  status?: string;
  created_at?: string;
  publication_date?: string;
  source_url?: string;
  metadata?: Record<string, unknown>;
  [key: string]: unknown;
}

function getErrorMessage(error: unknown): string {
  return error instanceof Error
    ? error.message
    : "The document request failed.";
}

export default function Documents() {
  const {
    selectedProjectId,
    selectedProject,
    loading: projectsLoading,
  } = useProjects();

  const [documents, setDocuments] = useState<DocumentRecord[]>([]);
  const [file, setFile] = useState<File | null>(null);
  const [company, setCompany] = useState("");
  const [docType, setDocType] =
    useState<(typeof DOC_TYPES)[number]>("unknown");

  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [uploadResult, setUploadResult] =
    useState<UploadResponse | null>(null);

  const loadDocuments = useCallback(async () => {
    if (!selectedProjectId) {
      setDocuments([]);
      setLoading(false);
      return;
    }

    setLoading(true);
    setError("");

    try {
      const response = await api<unknown>(
        `/documents?project_id=${encodeURIComponent(selectedProjectId)}`,
      );

      setDocuments(rows<DocumentRecord>(response));
    } catch (err) {
      setDocuments([]);
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, [selectedProjectId]);

  useEffect(() => {
    void loadDocuments();
  }, [loadDocuments]);

  useEffect(() => {
    setMessage("");
    setError("");
    setUploadResult(null);
    setFile(null);
  }, [selectedProjectId]);

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    setFile(event.target.files?.[0] ?? null);
    setMessage("");
    setError("");
    setUploadResult(null);
  }

  async function handleUpload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!selectedProjectId) {
      setError("Select a project before uploading a document.");
      return;
    }

    if (!file) {
      setError("Choose a document to upload.");
      return;
    }

    setUploading(true);
    setError("");
    setMessage("");
    setUploadResult(null);

    try {
      const form = new FormData();
      form.append("file", file);
      form.append("project_id", selectedProjectId);
      form.append("document_type", docType);
      form.append("company", company.trim() || "unknown");

      const response = await api<UploadResponse>("/documents/upload", {
        method: "POST",
        body: form,
      });

      setUploadResult(response);
      setMessage(
        response.message || "Document submitted for ingestion.",
      );
      setFile(null);

      const input = document.getElementById(
        "document-file-input",
      ) as HTMLInputElement | null;

      if (input) input.value = "";

      await loadDocuments();
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setUploading(false);
    }
  }

  async function handleDelete(document: DocumentRecord) {
    if (!selectedProjectId || !document.id) {
      setError("The document ID or active project is missing.");
      return;
    }

    const title =
      document.filename ||
      document.title ||
      document.name ||
      "this document";

    const confirmed = window.confirm(
      `Permanently delete "${title}" and its indexed chunks?\n\n` +
        "Evidence that relies only on these chunks will also be removed. " +
        "This action cannot be undone.",
    );

    if (!confirmed) return;

    setDeletingId(document.id);
    setError("");
    setMessage("");

    try {
      const path =
        `/documents/${encodeURIComponent(document.id)}` +
        `?project_id=${encodeURIComponent(selectedProjectId)}`;

      await api<{ message?: string }>(path, {
        method: "DELETE",
      });

      setMessage(`Deleted "${title}". You can now upload it again.`);
      await loadDocuments();
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setDeletingId(null);
    }
  }

  const controlsDisabled =
    projectsLoading || uploading || deletingId !== null;

  return (
    <>
      <Heading
        eyebrow="INTELLIGENCE / KNOWLEDGE BASE"
        title="Document library"
        description="Upload financial documents, manage indexed sources, and inspect records for your active project."
      />

      <Panel
        title="Add a source document"
        description={
          selectedProject
            ? `Documents will be added to ${selectedProject.name}.`
            : "Select a project before uploading documents."
        }
      >
        <form className="document-upload-form" onSubmit={handleUpload}>
          <label className="upload" htmlFor="document-file-input">
            <FileUp size={22} />
            <b>
              {uploading
                ? "Uploading document..."
                : file
                  ? file.name
                  : "Choose a document to upload"}
            </b>
            <span>
              PDF, TXT, Markdown, DOCX, CSV or HTML, depending on backend
              support.
            </span>
            <input
              id="document-file-input"
              type="file"
              accept=".pdf,.txt,.md,.docx,.csv,.html,.htm"
              onChange={handleFileChange}
              disabled={controlsDisabled || !selectedProjectId}
            />
          </label>

          <div className="form-row">
            <label>
              Company
              <input
                value={company}
                onChange={(event) => setCompany(event.target.value)}
                placeholder="e.g. Microsoft"
                maxLength={200}
                disabled={controlsDisabled || !selectedProjectId}
              />
            </label>

            <label>
              Document type
              <select
                value={docType}
                onChange={(event) =>
                  setDocType(
                    event.target.value as (typeof DOC_TYPES)[number],
                  )
                }
                disabled={controlsDisabled || !selectedProjectId}
              >
                {DOC_TYPES.map((type) => (
                  <option key={type} value={type}>
                    {type}
                  </option>
                ))}
              </select>
            </label>
          </div>

          <button
            className="btn primary"
            type="submit"
            disabled={
              uploading ||
              deletingId !== null ||
              projectsLoading ||
              !selectedProjectId ||
              !file
            }
          >
            {uploading ? (
              <LoaderCircle size={15} className="spin" />
            ) : (
              <FileUp size={15} />
            )}
            {uploading ? "Uploading..." : "Upload and index"}
          </button>
        </form>

        {projectsLoading && (
          <p className="muted">Loading projects...</p>
        )}

        {!projectsLoading && !selectedProjectId && (
          <p className="muted">
            Create or select a project in the sidebar before uploading.
          </p>
        )}

        {message && (
          <p className="success">
            <CheckCircle2 size={15} />
            {message}
          </p>
        )}

        {error && <ErrorBox message={error} />}

        {uploadResult && (
          <details>
            <summary>Upload details</summary>
            <pre className="json">
              {JSON.stringify(uploadResult, null, 2)}
            </pre>
          </details>
        )}
      </Panel>

      <Panel
        title="Indexed documents"
        description={
          selectedProject
            ? `Showing documents for ${selectedProject.name}.`
            : "Select a project to view its documents."
        }
        action={
          <button
            type="button"
            className="icon-btn"
            onClick={() => void loadDocuments()}
            disabled={
              loading || projectsLoading || !selectedProjectId || deletingId !== null
            }
            aria-label="Refresh documents"
            title="Refresh documents"
          >
            <RefreshCw size={15} className={loading ? "spin" : ""} />
          </button>
        }
      >
        {projectsLoading || loading ? (
          <p className="muted">Loading documents...</p>
        ) : !selectedProjectId ? (
          <Empty
            title="No project selected"
            description="Select a project to see its indexed documents."
          />
        ) : documents.length === 0 ? (
          <Empty
            title="No documents found"
            description="Upload a source document to start building this project's knowledge base."
          />
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Document</th>
                  <th>Company</th>
                  <th>Type</th>
                  <th>Status</th>
                  <th>Created</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {documents.map((document, index) => (
                  <tr key={document.id || index}>
                    <td>
                      <div className="document-name">
                        <FileText size={16} />
                        <span>
                          <b>
                            {document.filename ||
                              document.title ||
                              document.name ||
                              "Untitled document"}
                          </b>
                          <small>{document.id || ""}</small>
                        </span>
                      </div>
                    </td>
                    <td>{document.company || "—"}</td>
                    <td>{document.document_type || "—"}</td>
                    <td>
                      <span className="pill">
                        {document.status || "Unknown"}
                      </span>
                    </td>
                    <td>{dateLabel(document.created_at)}</td>
                    <td>
                      <button
                        type="button"
                        className="icon-btn document-delete-button"
                        onClick={() => void handleDelete(document)}
                        disabled={
                          !document.id ||
                          deletingId !== null ||
                          uploading
                        }
                        aria-label={`Delete ${document.title || document.filename || "document"}`}
                        title="Delete document"
                      >
                        {deletingId === document.id ? (
                          <LoaderCircle size={15} className="spin" />
                        ) : (
                          <Trash2 size={15} />
                        )}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {error && <ErrorBox message={error} />}
      </Panel>
    </>
  );
}
