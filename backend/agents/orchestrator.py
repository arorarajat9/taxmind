"""Agent orchestrator — the multi-step reasoning pipeline.

Runs the four specialist agents in sequence over the ingested data and assembles
a single analysis result plus a fully-cited audit log:

    ingest -> reconcile -> ITC eligibility (cited) -> anomalies -> returns

In Azure mode this same sequence is exposed through the Microsoft Agent Framework
workflow (see ``agent_framework_workflow.py``); the deterministic pipeline here is
always available so the demo runs with zero keys.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from backend.agents.anomaly_detection import detect_anomalies
from backend.agents.itc_eligibility import assess_itc_eligibility
from backend.agents.reconciliation import reconcile
from backend.audit.log import AuditLog
from backend.config import get_settings
from backend.foundry_iq.factory import get_knowledge_base
from backend.ingestion.excel import ingest_register
from backend.ingestion.gstr2a import load_gstr2a
from backend.returns.generator import build_gstr1, build_gstr3b


def run_analysis(
    sales_path: str | Path,
    purchase_path: str | Path,
    gstr2a_path: str | Path | None = None,
    today: date | None = None,
) -> dict:
    settings = get_settings()
    audit = AuditLog()
    kb = get_knowledge_base()

    # 1. Ingest
    sales = ingest_register(sales_path, "sales")
    purchases = ingest_register(purchase_path, "purchase")
    gstr2a = load_gstr2a(gstr2a_path) if gstr2a_path else []

    # 2. Reconcile purchases vs GSTR-2A
    recon = reconcile(purchases, gstr2a)

    # 3. ITC eligibility (grounded + cited)
    itc = assess_itc_eligibility(purchases, audit, kb=kb)

    # 4. Anomaly detection
    anomalies = detect_anomalies(purchases, audit, today=today)

    # 5. Return generation
    gstr1 = build_gstr1(sales)
    liability, gstr3b_detail = build_gstr3b(sales, purchases, recon, itc)

    return {
        "mode": settings.mode,
        "knowledge_backend": kb.name,
        "counts": {
            "sales_rows": len(sales),
            "purchase_rows": len(purchases),
            "gstr2a_rows": len(gstr2a),
            "anomalies": len(anomalies),
        },
        "itc_summary": itc,
        "reconciliation": {**recon.model_dump(mode="json"), "summary": recon.summary},
        "anomalies": [a.model_dump(mode="json") for a in anomalies],
        "blocked_itc": [
            {
                "invoice_number": p.invoice_number,
                "supplier": p.legal_name,
                "description": p.description,
                "tax": p.total_tax,
                "reason": p.itc_block_reason,
                "citation": p.citation.model_dump(mode="json") if p.citation else None,
            }
            for p in purchases
            if p.itc_eligible is False
        ],
        "gstr1": gstr1,
        "gstr3b": liability.model_dump(),
        "gstr3b_detail": gstr3b_detail,
        "audit_log": [e.model_dump(mode="json") for e in audit.entries],
        "audit_cited_count": audit.cited_count,
    }
