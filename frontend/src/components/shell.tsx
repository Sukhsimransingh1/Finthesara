"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Activity,
  Home,
  Sparkles,
  FileSearch,
  BarChart3,
  BookOpen,
  Files,
  ShieldCheck,
  Settings,
  Menu,
} from "lucide-react";
import { Suspense, useEffect, useState } from "react";

type NavItem = readonly [string, string, typeof Home];

type NavGroup = {
  readonly group: string;
  readonly links: readonly NavItem[];
};

const nav: readonly NavGroup[] = [
  {
    group: "WORKSPACE",
    links: [
      ["/dashboard", "Overview", Home],
      ["/research/new", "New investigation", Sparkles],
      ["/research", "Research history", FileSearch],
    ],
  },
  {
    group: "INTELLIGENCE",
    links: [
      ["/financial-analysis", "Financial analysis", BarChart3],
      ["/rag", "Research copilot", BookOpen],
      ["/documents", "Documents", Files],
    ],
  },
  {
    group: "SYSTEM",
    links: [
      ["/evaluations", "Evaluation lab", ShieldCheck],
      ["/settings", "Settings", Settings],
    ],
  },
];

function useBackendStatus() {
  const [status, setStatus] = useState<"ok" | "err" | "checking">("checking");
  useEffect(() => {
    let cancelled = false;
    fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000"}/api/v1/health`)
      .then((r) => {
        if (!cancelled) setStatus(r.ok ? "ok" : "err");
      })
      .catch(() => {
        if (!cancelled) setStatus("err");
      });
    return () => {
      cancelled = true;
    };
  }, []);
  return status;
}

export function Shell({ children }: { children: React.ReactNode }) {
  return (
    <Suspense fallback={<div className="frame">Loading workspace…</div>}>
      <ShellContent>{children}</ShellContent>
    </Suspense>
  );
}

function ShellContent({ children }: { children: React.ReactNode }) {
  const path = usePathname();
  const [open, setOpen] = useState(false);
  const conn = useBackendStatus();

  if (path === "/" || path === "/login") {
    return <>{children}</>;
  }

  const navItems: NavItem[] = nav.flatMap((group) => [...group.links]);

  const title = path.startsWith("/research/new")
    ? "New investigation"
    : path.startsWith("/research/")
      ? "Investigation"
      : navItems.find(([href]) => href === path)?.[1] ?? "Workspace";

  return (
    <div className="frame">
      {open && (
        <button
          className="scrim"
          onClick={() => setOpen(false)}
          aria-label="Close menu"
        />
      )}

      <aside className={`sidebar ${open ? "side-open" : ""}`}>
        <Link href="/dashboard" className="brand">
          <span className="brand-mark">
            <Activity size={20} />
          </span>
          <span>
            <b>Finthesara</b>
            <small>FINANCIAL INTELLIGENCE</small>
          </span>
        </Link>

        <div className="workspace-label">
          <i />
          Research workspace
        </div>

        <nav>
          {nav.map((group) => (
            <section key={group.group}>
              <small className="nav-group">{group.group}</small>

              {group.links.map(([href, label, Icon]) => {
                const active =
                  path === href ||
                  (href === "/research" &&
                    path.startsWith("/research/") &&
                    path !== "/research/new");

                return (
                  <Link
                    key={href}
                    href={href}
                    onClick={() => setOpen(false)}
                    className={`nav-link ${active ? "active" : ""}`}
                  >
                    <Icon size={17} />
                    {label}
                  </Link>
                );
              })}
            </section>
          ))}
        </nav>

        <div className="side-note">
          <ShieldCheck size={18} />
          <b>Evidence first.</b>
          <p>Every conclusion stays traceable to its source.</p>
        </div>

        <div className="side-bottom">
          <i />
          Research support only · Not investment advice
        </div>
      </aside>

      <div className="main">
        <header className="topbar">
          <button
            className="mobile-menu"
            onClick={() => setOpen(true)}
            aria-label="Open navigation"
          >
            <Menu size={20} />
          </button>

          <div className="crumb">
            Workspace <span className="sep">/</span> <b>{title}</b>
          </div>

          <div className="topbar-actions">
            <span className={`conn-dot ${conn}`}>
              <i />
              {conn === "ok" ? "Backend connected" : conn === "err" ? "Backend offline" : "Checking…"}
            </span>
            <Link className="avatar" href="/settings" aria-label="Settings">
              F
            </Link>
          </div>
        </header>

        <main className="content">{children}</main>

        <footer className="footer">
          <span>FINTHESARA</span>
          <span>Evidence-led · Human-reviewed · Not investment advice</span>
        </footer>
      </div>
    </div>
  );
}
