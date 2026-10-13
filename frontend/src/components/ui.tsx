import { ReactNode } from "react";

export function Heading({
  title,
  description,
  eyebrow,
  action,
}: {
  title: string;
  description?: string;
  eyebrow?: string;
  action?: ReactNode;
}) {
  return (
    <div className="heading">
      <div>
        {eyebrow && <div className="eyebrow">{eyebrow}</div>}
        <h1>{title}</h1>
        {description && <p>{description}</p>}
      </div>
      {action}
    </div>
  );
}

export function Panel({
  title,
  description,
  action,
  children,
}: {
  title?: string;
  description?: string;
  action?: ReactNode;
  children: ReactNode;
}) {
  return (
    <section className="panel">
      {(title || description || action) && (
        <div className="panel-head">
          <div>
            {title && <h2>{title}</h2>}
            {description && <p>{description}</p>}
          </div>
          {action}
        </div>
      )}
      {children}
    </section>
  );
}

export function Empty({
  title,
  description,
  action,
}: {
  title: string;
  description: string;
  action?: ReactNode;
}) {
  return (
    <div className="empty">
      <div className="empty-icon">⌁</div>
      <b>{title}</b>
      <p>{description}</p>
      {action}
    </div>
  );
}

export function ErrorBox({ message }: { message: string }) {
  return (
    <div className="error-box">
      <b>Could not load data</b>
      <p>{message}</p>
      <small>
        Check the backend status and NEXT_PUBLIC_API_BASE_URL in .env.local.
      </small>
    </div>
  );
}

export function StatusBadge({ status }: { status: string | null | undefined }) {
  const cls = status
    ? status.toLowerCase()
    : "unknown";
  const map: Record<string, string> = {
    completed: "completed",
    pass: "completed",
    success: "completed",
    running: "running",
    active: "running",
    in_progress: "running",
    awaiting_review: "awaiting_review",
    pending: "awaiting_review",
    queued: "awaiting_review",
    planning: "awaiting_review",
    researching: "awaiting_review",
    verifying: "awaiting_review",
    failed: "failed",
    error: "failed",
    fail: "failed",
  };
  const resolved = map[cls] || "unknown";
  const label = status || "Unknown";
  return <span className={`pill ${resolved}`}>{label}</span>;
}

export function Tabs({
  tabs,
  active,
  onChange,
}: {
  tabs: readonly { id: string; label: string }[];
  active: string;
  onChange: (id: string) => void;
}) {
  return (
    <div className="tabs" role="tablist">
      {tabs.map((t) => (
        <button
          key={t.id}
          role="tab"
          aria-selected={active === t.id}
          className={`tab ${active === t.id ? "active" : ""}`}
          onClick={() => onChange(t.id)}
        >
          {t.label}
        </button>
      ))}
    </div>
  );
}
