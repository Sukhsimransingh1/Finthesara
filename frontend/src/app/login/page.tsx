"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Activity,
  ShieldCheck,
  ArrowRight,
  LoaderCircle,
  Info,
} from "lucide-react";
import { getSupabaseBrowserClient } from "@/lib/supabase";

export default function Login() {
  const [mode, setMode] = useState<"signin" | "signup">("signin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const router = useRouter();

  const configured = Boolean(
    process.env.NEXT_PUBLIC_SUPABASE_URL &&
      process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY,
  );

  async function submit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setMessage("");

    const client = getSupabaseBrowserClient();

    if (!client) {
      setError(
        "Supabase Auth is not configured. Set NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY in frontend/.env.local, then restart Next.js.",
      );
      return;
    }

    setBusy(true);

    try {
      if (mode === "signin") {
        const { error: authError } =
          await client.auth.signInWithPassword({
            email: email.trim(),
            password,
          });

        if (authError) throw authError;

        router.replace("/dashboard");
      } else {
        const { data, error: authError } =
          await client.auth.signUp({
            email: email.trim(),
            password,
          });

        if (authError) throw authError;

        if (data.session) {
          router.replace("/dashboard");
        } else {
          setMessage(
            "Account created. Check your email to confirm the account, then sign in.",
          );
        }
      }
    } catch (e: unknown) {
      setError(
        e instanceof Error
          ? e.message
          : "Authentication failed.",
      );
    } finally {
      setBusy(false);
    }
  }

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
        <ShieldCheck
          size={26}
          style={{ color: "var(--teal)" }}
        />

        <div className="eyebrow">SECURE WORKSPACE</div>

        <h1>
          {mode === "signin"
            ? "Sign in to Finthesara"
            : "Create your account"}
        </h1>

        <p>
          Use your configured Supabase account to access private
          research projects and protected backend operations.
        </p>

        {!configured && (
          <div
            className="notice info"
            style={{ marginTop: 14 }}
          >
            <Info size={16} />
            <span>
              Supabase Auth is not configured yet. Add the public
              URL and anon key to{" "}
              <code>frontend/.env.local</code>.
            </span>
          </div>
        )}

        <form
          className="research-form"
          onSubmit={submit}
          style={{ marginTop: 18 }}
        >
          <label>
            Email
            <input
              type="email"
              required
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              disabled={busy}
            />
          </label>

          <label>
            Password
            <input
              type="password"
              required
              minLength={6}
              autoComplete={
                mode === "signin"
                  ? "current-password"
                  : "new-password"
              }
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              disabled={busy}
            />
          </label>

          {error && (
            <div className="error-box">
              <b>Authentication failed</b>
              <p>{error}</p>
            </div>
          )}

          {message && (
            <div className="notice">
              <Info size={16} />
              <span>{message}</span>
            </div>
          )}

          <button
            className="btn primary"
            type="submit"
            disabled={busy || !configured}
          >
            {busy ? (
              <LoaderCircle size={15} className="spin" />
            ) : (
              <ArrowRight size={15} />
            )}

            {mode === "signin"
              ? "Sign in"
              : "Create account"}
          </button>
        </form>

        <button
          type="button"
          className="table-link"
          style={{
            marginTop: 14,
            background: "none",
            border: 0,
          }}
          onClick={() => {
            setMode(
              mode === "signin" ? "signup" : "signin",
            );
            setError("");
            setMessage("");
          }}
        >
          {mode === "signin"
            ? "Need an account? Sign up"
            : "Already registered? Sign in"}
        </button>

        <p
          className="muted"
          style={{ marginTop: 14, fontSize: 11 }}
        >
          Your user must own the project selected in
          NEXT_PUBLIC_PROJECT_ID to use project-scoped endpoints.
        </p>
      </section>

      <small className="muted">
        Research support only · Not investment advice
      </small>
    </main>
  );
}