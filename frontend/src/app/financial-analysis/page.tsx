"use client";

import { useState } from "react";
import { BarChart3, LoaderCircle, AlertCircle } from "lucide-react";
import { Heading, Panel, Empty, ErrorBox } from "@/components/ui";

export default function FinancialAnalysis() {
  const [ticker, setTicker] = useState("AAPL");
  const [period, setPeriod] = useState("Latest");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  async function go(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setErr("");
    try {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000"}${
          process.env.NEXT_PUBLIC_API_PREFIX || "/api/v1"
        }/financial-analysis`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ ticker, period }),
        },
      );
      if (!res.ok) {
        const text = await res.text().catch(() => "");
        throw new Error(
          `Financial analysis endpoint returned ${res.status}. ${text}`,
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
        eyebrow="INTELLIGENCE / FUNDAMENTALS"
        title="Financial analysis"
        description="Request structured analysis. Values are displayed only when returned by the API."
      />

      <Panel title="Analysis request">
        <form className="inline-form" onSubmit={go}>
          <label style={{ display: "flex", flexDirection: "column", gap: 6, fontSize: 12, fontWeight: 600 }}>
            Ticker
            <input
              required
              value={ticker}
              onChange={(e) => setTicker(e.target.value.toUpperCase())}
              disabled={busy}
            />
          </label>
          <label style={{ display: "flex", flexDirection: "column", gap: 6, fontSize: 12, fontWeight: 600 }}>
            Reporting period
            <select
              value={period}
              onChange={(e) => setPeriod(e.target.value)}
              disabled={busy}
            >
              <option>Latest</option>
              <option>FY2024</option>
              <option>FY2023</option>
              <option>FY2022</option>
              <option>Quarterly</option>
            </select>
          </label>
          <button className="btn primary" disabled={busy} type="submit">
            {busy ? (
              <LoaderCircle size={15} className="spin" />
            ) : (
              <BarChart3 size={15} />
            )}{" "}
            Run analysis
          </button>
        </form>
        {err && <ErrorBox message={err} />}
      </Panel>

      <Panel title="Analysis output">
        <Empty
          title="Financial analysis endpoint not available"
          description="The backend does not currently expose a POST /api/v1/financial-analysis endpoint. Financial analysis runs as part of the multi-agent research workflow (financial_analysis node). Submit a request above to confirm availability."
        />
      </Panel>

      <div className="notice">
        <AlertCircle size={17} />
        <span>
          <b>Deterministic calculations.</b> Financial metrics (YoY/QoQ growth,
          margins, CAGR, ratios) are computed by deterministic backend tools,
          not by the LLM. A standalone analysis endpoint is not yet exposed.
        </span>
      </div>
    </>
  );
}
