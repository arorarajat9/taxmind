import { Citation } from "@/lib/api";

export function CitationCard({ citation }: { citation: Citation | null }) {
  if (!citation) return null;
  return (
    <div className="mt-3 rounded-xl border border-emerald-500/30 bg-emerald-500/[0.07] p-3">
      <div className="flex items-center justify-between">
        <span className="chip bg-emerald-500/20 text-emerald-300">
          📑 {citation.section}
        </span>
        <span className="text-[11px] uppercase tracking-wide text-emerald-400/70">
          grounded · {(citation.confidence * 100).toFixed(0)}% conf
        </span>
      </div>
      <p className="mt-2 text-sm leading-relaxed text-slate-200">
        “{citation.snippet}”
      </p>
      <p className="mt-1.5 text-xs text-slate-400">
        Source: {citation.source}
      </p>
    </div>
  );
}
