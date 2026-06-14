"""End-to-end TaxMind pipeline from the command line (no frontend needed).

Usage:
    python scripts/run_full_pipeline.py \
        --sales data/synthetic/sales_register.xlsx \
        --purchase data/synthetic/purchase_register.xlsx \
        --gstr2a data/synthetic/gstr2a.json

With no arguments it runs against the bundled synthetic kirana dataset.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.agents.agent_framework_workflow import run_analysis_via_workflow as run_analysis
from backend.config import OUTPUT_DIR, SYNTHETIC_DIR, get_settings
from backend.returns.excel_writer import write_filing_excel


def _fmt(n) -> str:
    return f"₹{n:,.2f}"


def main() -> None:
    ap = argparse.ArgumentParser(description="Run the full TaxMind pipeline.")
    ap.add_argument("--sales", default=str(SYNTHETIC_DIR / "sales_register.xlsx"))
    ap.add_argument("--purchase", default=str(SYNTHETIC_DIR / "purchase_register.xlsx"))
    ap.add_argument("--gstr2a", default=str(SYNTHETIC_DIR / "gstr2a.json"))
    ap.add_argument("--out", default=str(OUTPUT_DIR / "taxmind_filing_summary.xlsx"))
    args = ap.parse_args()

    settings = get_settings()
    print("=" * 70)
    print(f"  TaxMind pipeline  |  mode: {settings.mode.upper()}")
    print("=" * 70)

    result = run_analysis(args.sales, args.purchase, args.gstr2a)

    c = result["counts"]
    print(f"\nIngested: {c['sales_rows']} sales, {c['purchase_rows']} purchases, "
          f"{c['gstr2a_rows']} GSTR-2A rows")
    print(f"Knowledge backend: {result['knowledge_backend']}")

    print("\n── Reconciliation ──")
    print(json.dumps(result["reconciliation"]["summary"], indent=2))

    print("\n── Blocked ITC (cited GST Act references) ──")
    for b in result["blocked_itc"]:
        cite = b["citation"]
        print(f"  • {b['invoice_number']} ({b['supplier']}): {b['reason']}  —  {_fmt(b['tax'])}")
        if cite:
            print(f"      ↳ {cite['section']} [{cite['source']}]")
            print(f"        \"{cite['snippet'][:140]}...\"")

    print("\n── Anomalies ──")
    for a in result["anomalies"]:
        print(f"  [{a['severity']:8}] {a['entity_ref']}: {a['rule']} — {a['message']}")

    print("\n── GSTR-3B ──")
    for k, v in result["gstr3b_detail"].items():
        print(f"  {k:32} {_fmt(v)}")

    print("\n── GSTR-1 ──")
    g1 = result["gstr1"]
    print(f"  B2B invoices: {g1['b2b_total']['count']}  ({_fmt(g1['b2b_total']['taxable_value'])} taxable)")
    print(f"  B2C value:    {_fmt(g1['b2c_total']['taxable_value'])} taxable")
    print(f"  HSN codes:    {len(g1['hsn_summary'])}")

    out = write_filing_excel(args.out, result)
    print(f"\nAudit log: {len(result['audit_log'])} decisions, "
          f"{result['audit_cited_count']} with citations")
    print(f"Filing-ready Excel written to: {out}")
    print("\nReminder: TaxMind assists preparation — a human reviews and files. "
          "It does NOT auto-submit to GSTN.")


if __name__ == "__main__":
    main()
