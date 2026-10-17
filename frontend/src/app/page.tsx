import Link from "next/link";
import {
  Activity,
  ArrowRight,
  BarChart3,
  BookOpen,
  GitBranch,
  ShieldCheck,
  FileSearch,
  CheckCircle2,
  Scale,
} from "lucide-react";

export default function Home() {
  return (
    <main className="landing">
      <header className="landing-nav">
        <Link href="/" className="brand">
          <span className="brand-mark">
            <Activity size={20} />
          </span>
          <span>
            <b>Finthesara</b>
            <small>FINANCIAL INTELLIGENCE</small>
          </span>
        </Link>
        <div>
          
          <Link href="/dashboard" className="btn primary">
            Open workspace <ArrowRight size={15} />
          </Link>
        </div>
      </header>

      <section className="hero">
        <div>
          <div className="eyebrow">MULTI-AGENT FINANCIAL INTELLIGENCE</div>
          <h1>
            Financial research.
            <br />
            <em>Reasoned and verified.</em>
          </h1>
          <p className="hero-sub">
            Finthesara orchestrates specialized AI agents to investigate
            companies, retrieve source documents, run deterministic financial
            analysis, verify claims against evidence, and produce auditable
            research reports — with human review built in.
          </p>
          <div className="hero-actions">
            <Link href="/research/new" className="btn primary large">
              Start an investigation <ArrowRight size={16} />
            </Link>
            <Link href="/dashboard" className="btn secondary large">
              Explore workspace
            </Link>
          </div>
          <div className="trust">
            <span>
              <ShieldCheck size={15} /> Source traceability
            </span>
            <span>
              <CheckCircle2 size={15} /> Claim verification
            </span>
            <span>
              <Scale size={15} /> Human review
            </span>
          </div>
        </div>

        <div className="pipeline">
          <div className="pipeline-head">
            <span>RESEARCH PIPELINE</span>
            <b>
              <i /> MULTI-AGENT
            </b>
          </div>
          <div className="query-card">
            <small>INVESTIGATION BRIEF</small>
            <b>Assess company fundamentals</b>
            <span>Structured filings · Source-backed claims</span>
          </div>
          {[
            { n: "01", title: "Plan investigation", sub: "Decompose the question", I: GitBranch },
            { n: "02", title: "Retrieve & analyze", sub: "Filings, metrics, evidence", I: BarChart3 },
            { n: "03", title: "Verify claims", sub: "Check source support", I: ShieldCheck },
            { n: "04", title: "Synthesize report", sub: "Findings with citations", I: FileSearch },
          ].map((x) => (
            <div className="pipe-row" key={x.n}>
              <span className="pipe-icon">
                <x.I size={17} />
              </span>
              <div>
                <b>{x.title}</b>
                <small>{x.sub}</small>
              </div>
              <span className="pipe-num">{x.n}</span>
            </div>
          ))}
          <div className="pipeline-foot">
            <BookOpen size={15} />
            Conclusions remain linked to their evidence.
          </div>
        </div>
      </section>

      <section className="features">
        <div className="eyebrow">BUILT FOR INVESTIGATIONS</div>
        <h2>From a research question to an auditable answer.</h2>
        <p>
          A connected workflow for exploring financial questions without losing
          sight of the underlying evidence.
        </p>
        <div className="feature-grid">
          {[
            {
              I: GitBranch,
              t: "Orchestrated research",
              d: "Specialized agents coordinate through a transparent LangGraph workflow.",
            },
            {
              I: BookOpen,
              t: "Hybrid retrieval",
              d: "Sparse and semantic search bring relevant documents into the research process.",
            },
            {
              I: BarChart3,
              t: "Financial analysis",
              d: "Deterministic tools compute growth, margins, and ratios with source identifiers.",
            },
            {
              I: ShieldCheck,
              t: "Claim verification",
              d: "Evidence support is checked before synthesis; unsupported claims are surfaced.",
            },
          ].map((f) => (
            <article key={f.t}>
              <span>
                <f.I size={20} />
              </span>
              <b>{f.t}</b>
              <p>{f.d}</p>
            </article>
          ))}
        </div>
      </section>

      <footer className="landing-footer">
        Finthesara · Financial research, reasoned and verified · Research
        support only · Not investment advice
      </footer>
    </main>
  );
}
