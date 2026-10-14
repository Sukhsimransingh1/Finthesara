
import Link from "next/link";
import {
  Activity,
  ArrowLeft,
  ArrowRight,
  BarChart3,
  BookOpen,
  CheckCircle2,
  FileSearch,
  ShieldCheck,
  GitBranch,
} from "lucide-react";

const metrics = [
  { label: "Revenue growth", value: "+8.2%", note: "Illustrative sample" },
  { label: "Operating margin", value: "27.4%", note: "Illustrative sample" },
  { label: "Evidence items", value: "18", note: "Demo dataset" },
  { label: "Claims reviewed", value: "12 / 12", note: "Example workflow only" },
];

const evidence = [
  {
    id: "E-01",
    title: "Annual filing — revenue discussion",
    type: "Source document",
    status: "Included in demo",
  },
  {
    id: "E-02",
    title: "Segment performance summary",
    type: "Financial evidence",
    status: "Illustrative excerpt",
  },
  {
    id: "E-03",
    title: "Risk factors and forward-looking statements",
    type: "Risk disclosure",
    status: "Illustrative excerpt",
  },
];

const agents = [
  {
    n: "01",
    title: "Planner",
    desc: "Breaks the research question into verifiable tasks",
    I: GitBranch,
  },
  {
    n: "02",
    title: "Financial analyst",
    desc: "Organizes reported metrics and deterministic calculations",
    I: BarChart3,
  },
  {
    n: "03",
    title: "Research & retrieval",
    desc: "Finds relevant passages from the available corpus",
    I: BookOpen,
  },
  {
    n: "04",
    title: "Verifier & synthesis",
    desc: "Checks support and assembles a traceable report",
    I: ShieldCheck,
  },
];

export default function PublicDemoPage() {
  return (
    <main className="landing" style={{ minHeight: "100vh" }}>
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

        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 16,
          }}
        >
          <Link href="/">Home</Link>
          <Link href="/login" className="btn secondary">
            Sign in
          </Link>
        </div>
      </header>

      <section className="hero" style={{ paddingBottom: 24 }}>
        <div>
          <div className="eyebrow">
            PUBLIC RECRUITER DEMO · NO SIGN-IN REQUIRED
          </div>

          <h1>
            Explore the research workflow.
            <br />
            <em>Follow the evidence.</em>
          </h1>

          <p className="hero-sub">
            This showcase uses clearly labelled illustrative sample data
            to demonstrate how Finthesara organizes financial metrics,
            evidence, verification, and multi-agent research. It does
            not represent a live analysis or investment recommendation.
          </p>

          <div className="hero-actions">
            <a
              href="#sample-report"
              className="btn primary large"
            >
              View sample report <ArrowRight size={16} />
            </a>

            <Link
              href="/login"
              className="btn secondary large"
            >
              Sign in to your workspace
            </Link>
          </div>

          <div className="trust">
            <span>
              <ShieldCheck size={15} /> Evidence-first design
            </span>
            <span>
              <CheckCircle2 size={15} /> Verification workflow
            </span>
            <span>
              <FileSearch size={15} /> Traceable structure
            </span>
          </div>
        </div>

        <div className="pipeline">
          <div className="pipeline-head">
            <span>DEMO WORKFLOW</span>
            <b>
              <i /> SAMPLE
            </b>
          </div>

          {agents.map((agent) => (
            <div className="pipe-row" key={agent.n}>
              <span className="pipe-icon">
                <agent.I size={17} />
              </span>

              <div>
                <b>{agent.title}</b>
                <small>{agent.desc}</small>
              </div>

              <span className="pipe-num">{agent.n}</span>
            </div>
          ))}

          <div className="pipeline-foot">
            <BookOpen size={15} />
            Sample workflow — not live agent execution.
          </div>
        </div>
      </section>

      <section
        id="sample-report"
        className="features"
        style={{ paddingTop: 24 }}
      >
        <div className="eyebrow">SAMPLE REPORT</div>

        <h2>Illustrative company fundamentals review</h2>

        <p>
          All values below are fictional demonstration values, not
          actual financial data. They demonstrate the interface and
          evidence workflow.
        </p>

        <div className="metrics">
          {metrics.map((metric) => (
            <div className="metric" key={metric.label}>
              <span>{metric.label}</span>
              <b>{metric.value}</b>
              <small>{metric.note}</small>
            </div>
          ))}
        </div>

        <div
          className="feature-grid"
          style={{ marginTop: 24 }}
        >
          <article>
            <span>
              <BarChart3 size={20} />
            </span>
            <b>Executive summary</b>
            <p>
              The sample company shows positive illustrative revenue
              growth and a stable operating margin. In a real run,
              conclusions must link to source evidence and the
              relevant reporting period.
            </p>
          </article>

          <article>
            <span>
              <ShieldCheck size={20} />
            </span>
            <b>Verification notes</b>
            <p>
              Example checks include whether a metric has a source,
              whether reporting periods align, and whether a
              conclusion exceeds what the evidence supports.
            </p>
          </article>

          <article>
            <span>
              <Activity size={20} />
            </span>
            <b>Limitations</b>
            <p>
              This public demo does not query current filings, call
              the LLM, or claim that agents ran. Authenticated
              features remain in the workspace.
            </p>
          </article>
        </div>
      </section>

      <section className="features" style={{ paddingTop: 8 }}>
        <div className="eyebrow">EVIDENCE EXPLORER PREVIEW</div>

        <h2>Inspect the evidence structure</h2>

        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Evidence item</th>
                <th>Type</th>
                <th>Demo status</th>
              </tr>
            </thead>

            <tbody>
              {evidence.map((item) => (
                <tr key={item.id}>
                  <td>
                    <b>{item.id}</b>
                  </td>
                  <td>{item.title}</td>
                  <td>{item.type}</td>
                  <td>
                    <span className="pill completed">
                      {item.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="notice" style={{ marginTop: 18 }}>
          <ShieldCheck size={17} />
          <span>
            <b>Responsible use.</b> Finthesara is a financial
            research support tool, not investment advice. All
            figures and evidence labels on this page are
            illustrative.
          </span>
        </div>

        <div className="hero-actions" style={{ marginTop: 24 }}>
          <Link href="/login" className="btn primary large">
            Access authenticated workspace
            <ArrowRight size={16} />
          </Link>

          <Link href="/" className="btn secondary large">
            <ArrowLeft size={16} /> Back to home
          </Link>
        </div>
      </section>

      <footer className="landing-footer">
        Finthesara · Public product demo · Illustrative data only ·
        Not investment advice
      </footer>
    </main>
  );
}
