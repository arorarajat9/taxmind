"use client";

import { useState } from "react";
import {
  Analysis,
  API_BASE,
  analyzeFiles,
  inr,
  queryKB,
  runDemo,
} from "@/lib/api";
import { CitationCard } from "./CitationCard";
import { ITCDonut, ReconBars, VendorBars } from "./Charts";

const STATUS_STYLES: Record<string, string> = {
  matched: "bg-emerald-500/20 text-emerald-300",
  mismatched: "bg-amber-500/20 text-amber-300",
  missing_in_2a: "bg-red-500/20 text-red-300",
  missing_in_books: "bg-slate-500/20 text-slate-300",
};

const SEVERITY_STYLES: Record<string, string> = {
  critical: "bg-red-500/20 text-red-300",
  warning: "bg-amber-500/20 text-amber-300",
  info: "bg-slate-500/20 text-slate-300",
};

function Kpi({ label, value, accent }: { label: string; value: string; accent: string }) {
  return (
    <div className="card">
      <div className="text-xs uppercase tracking-wide text-slate-400">{label}</div>
      <div className={`mt-2 text-2xl font-bold ${accent}`}>{value}</div>
    </div>
  );
}

function Panel({ title, children, right }: { title: string; children: React.ReactNode; right?: React.ReactNode }) {
  return (
    <section className="card">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-slate-200">{title}</h3>
        {right}
      </div>
      {children}
    </section>
  );
}

export default function Dashboard() {
  const [a, setA] = useState<Analysis | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [files, setFiles] = useState<{ sales?: File; purchase?: File; gstr2a?: File }>({});

  // GST KB ask box (the before/after demo)
  const [q, setQ] = useState("Can I claim ITC on a staff lunch / catering bill?");
  const [kb, setKb] = useState<Awaited<ReturnType<typeof queryKB>> | null>(null);
  const [kbLoading, setKbLoading] = useState(false);

  async function go(fn: () => Promise<Analysis>) {
    setLoading(true);
    setError(null);
    try {
      setA(await fn());
    } catch (e: any) {
      setError(e?.message || "Something went wrong. Is the API running on " + API_BASE + "?");
    } finally {
      setLoading(false);
    }
  }

  async function ask() {
    setKbLoading(true);
    try {
      setKb(await queryKB(q));
    } catch (e: any) {
      setError(e?.message || "KB query failed");
    } finally {
      setKbLoading(false);
    }
  }

  return (
    <main className="mx-auto max-w-6xl px-5 py-8">
      {/* Header */}
      <header className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">
            Tax<span className="text-blue-400">Mind</span>
          </h1>
          <p className="mt-1 max-w-xl text-sm text-slate-400">
            Reconciles input tax credit, flags blocked ITC with{" "}
            <span className="text-emerald-400">cited GST Act references</span>, and
            prepares GSTR-1 / GSTR-3B. Grounded on Foundry IQ.
          </p>
        </div>
        <div className="flex gap-2">
          <button className="btn-primary" disabled={loading} onClick={() => go(runDemo)}>
            {loading ? "Analyzing…" : "▶ Run demo (kirana store)"}
          </button>
          {a && (
            <a className="btn-ghost" href={`${API_BASE}${a.download_url}`}>
              ⬇ Download filing Excel
            </a>
          )}
        </div>
      </header>

      {/* Upload */}
      <section className="card mb-6">
        <div className="grid gap-3 md:grid-cols-4">
          {(["sales", "purchase", "gstr2a"] as const).map((k) => (
            <label key={k} className="text-xs text-slate-400">
              {k === "gstr2a" ? "GSTR-2A (.json/.xlsx)" : `${k} register (.xlsx)`}
              <input
                type="file"
                className="mt-1 block w-full rounded-lg border border-white/10 bg-black/20 p-2 text-xs text-slate-300 file:mr-2 file:rounded file:border-0 file:bg-blue-600 file:px-2 file:py-1 file:text-white"
                onChange={(e) => setFiles((f) => ({ ...f, [k]: e.target.files?.[0] }))}
              />
            </label>
          ))}
          <button
            className="btn-ghost self-end"
            disabled={loading}
            onClick={() => go(() => analyzeFiles(files))}
          >
            Analyze uploaded
          </button>
        </div>
        <p className="mt-2 text-[11px] text-slate-500">
          No files? Just hit “Run demo” — TaxMind ships with a messy synthetic kirana dataset.
        </p>
      </section>

      {error && (
        <div className="mb-6 rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-300">
          {error}
        </div>
      )}

      {!a && !loading && <EmptyState onAsk={ask} q={q} setQ={setQ} kb={kb} kbLoading={kbLoading} />}

      {a && (
        <>
          {/* mode banner */}
          <div className="mb-5 flex flex-wrap items-center gap-2 text-xs text-slate-400">
            <span className="chip bg-blue-500/20 text-blue-300">mode: {a.mode}</span>
            <span className="chip bg-violet-500/20 text-violet-300">
              knowledge: {a.knowledge_backend}
            </span>
            {a.orchestration && (
              <span className="chip bg-cyan-500/20 text-cyan-300">{a.orchestration}</span>
            )}
            <span className="chip bg-emerald-500/20 text-emerald-300">
              {a.audit_cited_count} cited decisions
            </span>
          </div>

          {/* KPIs */}
          <div className="mb-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Kpi label="Net tax payable" value={inr(a.gstr3b.net_tax_payable)} accent="text-blue-300" />
            <Kpi label="ITC at risk (2A)" value={inr(a.reconciliation.summary.total_itc_at_risk)} accent="text-amber-300" />
            <Kpi label="ITC blocked u/s 17(5)" value={inr(a.itc_summary.itc_blocked_value)} accent="text-red-300" />
            <Kpi label="Anomalies found" value={String(a.counts.anomalies)} accent="text-rose-300" />
          </div>

          {/* Charts */}
          <div className="mb-6 grid gap-4 lg:grid-cols-3">
            <Panel title="ITC composition">
              <ITCDonut a={a} />
            </Panel>
            <Panel title="Reconciliation status">
              <ReconBars a={a} />
            </Panel>
            <Panel title="Top vendors (ITC vs at-risk)">
              <VendorBars a={a} />
            </Panel>
          </div>

          {/* Hero: blocked ITC with citations */}
          <div className="mb-6 grid gap-4 lg:grid-cols-2">
            <Panel title="🚩 Blocked ITC — every flag cites the GST Act">
              {a.blocked_itc.length === 0 && (
                <p className="text-sm text-slate-400">No blocked credits detected.</p>
              )}
              {a.blocked_itc.map((b) => (
                <div key={b.invoice_number} className="mb-4 rounded-xl border border-white/10 bg-black/20 p-3">
                  <div className="flex items-center justify-between">
                    <div>
                      <span className="font-semibold">{b.invoice_number}</span>{" "}
                      <span className="text-slate-400">· {b.supplier}</span>
                    </div>
                    <span className="font-semibold text-red-300">{inr(b.tax)}</span>
                  </div>
                  <p className="text-xs text-slate-400">{b.description}</p>
                  <p className="mt-1 text-sm text-red-300">{b.reason}</p>
                  <CitationCard citation={b.citation} />
                </div>
              ))}
            </Panel>

            <Panel title="Ask the GST knowledge base">
              <div className="flex gap-2">
                <input
                  value={q}
                  onChange={(e) => setQ(e.target.value)}
                  className="w-full rounded-xl border border-white/10 bg-black/20 px-3 py-2 text-sm"
                  placeholder="e.g. Is ITC available on construction of a building?"
                />
                <button className="btn-primary" disabled={kbLoading} onClick={ask}>
                  {kbLoading ? "…" : "Ask"}
                </button>
              </div>
              {kb && (
                <div className="mt-3">
                  <p className="text-sm text-slate-200 whitespace-pre-wrap">{kb.answer.slice(0, 600)}</p>
                  {kb.citations[0] && <CitationCard citation={kb.citations[0]} />}
                </div>
              )}
              <p className="mt-3 text-[11px] text-slate-500">
                Compare this with a raw LLM: TaxMind never asserts a rule without a
                retrieved citation, and defers to a CA when retrieval is uncertain.
              </p>
            </Panel>
          </div>

          {/* Reconciliation table */}
          <Panel title="Purchase ↔ GSTR-2A reconciliation">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="text-xs uppercase text-slate-400">
                  <tr>
                    {["Invoice", "Supplier", "Status", "Book ITC", "2A ITC", "At risk", "Note"].map((h) => (
                      <th key={h} className="px-2 py-2">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {a.reconciliation.lines.map((l, i) => (
                    <tr key={i} className="border-t border-white/5">
                      <td className="px-2 py-2 font-medium">{l.invoice_number}</td>
                      <td className="px-2 py-2 text-slate-400">{l.supplier}</td>
                      <td className="px-2 py-2">
                        <span className={`chip ${STATUS_STYLES[l.status] || ""}`}>{l.status}</span>
                      </td>
                      <td className="px-2 py-2">{inr(l.book_tax)}</td>
                      <td className="px-2 py-2">{inr(l.gstr2a_tax)}</td>
                      <td className="px-2 py-2 text-amber-300">{l.itc_at_risk ? inr(l.itc_at_risk) : "—"}</td>
                      <td className="px-2 py-2 text-xs text-slate-400">{l.note}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Panel>

          {/* Anomalies + Audit */}
          <div className="mt-6 grid gap-4 lg:grid-cols-2">
            <Panel title="Anomalies">
              {a.anomalies.map((an, i) => (
                <div key={i} className="mb-2 flex items-start gap-2 text-sm">
                  <span className={`chip ${SEVERITY_STYLES[an.severity] || ""}`}>{an.severity}</span>
                  <div>
                    <span className="font-medium">{an.entity_ref}</span> · {an.rule}
                    <p className="text-xs text-slate-400">{an.message}</p>
                  </div>
                </div>
              ))}
            </Panel>
            <Panel title={`Audit trail (${a.audit_log.length} decisions)`}>
              <div className="max-h-72 space-y-2 overflow-y-auto">
                {a.audit_log.map((e, i) => (
                  <div key={i} className="rounded-lg border border-white/5 bg-black/20 p-2 text-xs">
                    <div className="flex justify-between">
                      <span className="font-medium text-slate-300">{e.agent}</span>
                      <span className={e.confident ? "text-emerald-400" : "text-amber-400"}>
                        {e.confident ? "confident" : "review"}
                      </span>
                    </div>
                    <p className="text-slate-300">{e.entity_ref}: {e.decision}</p>
                    {e.citation && (
                      <p className="text-emerald-400">📑 {e.citation.section}</p>
                    )}
                  </div>
                ))}
              </div>
            </Panel>
          </div>

          <footer className="mt-8 rounded-xl border border-amber-500/20 bg-amber-500/5 p-4 text-xs text-amber-200/80">
            ⚠ TaxMind assists preparation only. A human reviews and files — it does
            <b> not</b> auto-submit to the GSTN portal. Verify against the latest
            CBIC bare act and consult a qualified CA before filing.
          </footer>
        </>
      )}
    </main>
  );
}

function EmptyState({
  onAsk,
  q,
  setQ,
  kb,
  kbLoading,
}: {
  onAsk: () => void;
  q: string;
  setQ: (s: string) => void;
  kb: any;
  kbLoading: boolean;
}) {
  return (
    <div className="card text-center">
      <p className="text-lg font-semibold">Upload your registers, or run the demo.</p>
      <p className="mt-1 text-sm text-slate-400">
        TaxMind will reconcile ITC, flag blocked credits with citations, and prepare your returns.
      </p>
      <div className="mx-auto mt-5 max-w-xl text-left">
        <div className="flex gap-2">
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            className="w-full rounded-xl border border-white/10 bg-black/20 px-3 py-2 text-sm"
          />
          <button className="btn-primary" disabled={kbLoading} onClick={onAsk}>
            {kbLoading ? "…" : "Ask GST KB"}
          </button>
        </div>
        {kb?.citations?.[0] && <CitationCard citation={kb.citations[0]} />}
      </div>
    </div>
  );
}
