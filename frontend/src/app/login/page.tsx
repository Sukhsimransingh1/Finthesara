import Link from "next/link";
import { Activity, ShieldCheck, ArrowRight, Info } from "lucide-react";

export default function Login() {
  return (
    <main className="login-page">
      <Link href="/" className="brand">
        <span className="brand-mark">
          <Activity size={20} />
        </span>
        <span>
          <b>Finthesara</b>
          <small>FINANCIAL INTELLIGENCE</small>
        </span>
      </Link>

      <section className="login-card">
        <ShieldCheck size={26} style={{ color: "var(--teal)" }} />
        <div className="eyebrow">SECURE WORKSPACE</div>
        <h1>Sign in to continue</h1>
        <p>
          Finthesara is designed for Supabase Auth. Configure the public
          Supabase URL and anon key, then connect the sign-in flow before using
          private research data.
        </p>

        <div className="error-box" style={{ marginTop: 14 }}>
          <b>Authentication not configured</b>
          <p>
            This workspace does not pretend a user is authenticated. The
            research creation endpoint is available for evaluation, but
            persisted research runs, document upload, and human review require a
            valid Supabase access token.
          </p>
        </div>

        <div className="notice info" style={{ marginTop: 14 }}>
          <Info size={16} />
          <span>
            <b>Development mode:</b> You can continue to the workspace to test
            the research workflow. Set <code>NEXT_PUBLIC_PROJECT_ID</code> in{" "}
            <code>.env.local</code> to a valid project UUID.
          </span>
        </div>

        <Link href="/dashboard" className="btn primary" style={{ marginTop: 18 }}>
          Continue to workspace <ArrowRight size={15} />
        </Link>
        <Link href="/" className="table-link">
          Back to home
        </Link>
      </section>

      <small className="muted">Research support only · Not investment advice</small>
    </main>
  );
}
