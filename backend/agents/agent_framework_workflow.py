"""Microsoft Agent Framework workflow that wires the four TaxMind agents.

This expresses TaxMind's pipeline as a real Agent Framework sequential workflow
of custom :class:`Executor` steps:

    ingest -> reconcile -> itc_eligibility -> anomaly -> returns

Each step is a deterministic executor (the agents are tool-like and key-free), so
the workflow runs without an LLM. It is used by ``run_analysis_via_workflow`` when
the ``agent-framework`` package is installed; otherwise callers fall back to the
plain sequential orchestrator in :mod:`backend.agents.orchestrator`. Both produce
the identical analysis dict.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
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

try:  # the framework is optional — local installs may not have it
    from agent_framework import Executor, WorkflowBuilder, WorkflowContext, handler

    AGENT_FRAMEWORK_AVAILABLE = True
except Exception:  # pragma: no cover
    AGENT_FRAMEWORK_AVAILABLE = False


@dataclass
class PipelineState:
    """Shared message passed along the workflow edges."""

    sales_path: str
    purchase_path: str
    gstr2a_path: str | None
    today: date | None = None
    sales: list = field(default_factory=list)
    purchases: list = field(default_factory=list)
    gstr2a: list = field(default_factory=list)
    audit: AuditLog = field(default_factory=AuditLog)
    recon: object | None = None
    itc: dict = field(default_factory=dict)
    anomalies: list = field(default_factory=list)
    result: dict = field(default_factory=dict)


def _build_result(s: PipelineState) -> dict:
    settings = get_settings()
    kb = get_knowledge_base()
    gstr1 = build_gstr1(s.sales)
    liability, detail = build_gstr3b(s.sales, s.purchases, s.recon, s.itc)
    return {
        "mode": settings.mode,
        "knowledge_backend": kb.name,
        "orchestration": "agent-framework-workflow",
        "counts": {
            "sales_rows": len(s.sales),
            "purchase_rows": len(s.purchases),
            "gstr2a_rows": len(s.gstr2a),
            "anomalies": len(s.anomalies),
        },
        "itc_summary": s.itc,
        "reconciliation": {**s.recon.model_dump(mode="json"), "summary": s.recon.summary},
        "anomalies": [a.model_dump(mode="json") for a in s.anomalies],
        "blocked_itc": [
            {
                "invoice_number": p.invoice_number,
                "supplier": p.legal_name,
                "description": p.description,
                "tax": p.total_tax,
                "reason": p.itc_block_reason,
                "citation": p.citation.model_dump(mode="json") if p.citation else None,
            }
            for p in s.purchases
            if p.itc_eligible is False
        ],
        "gstr1": gstr1,
        "gstr3b": liability.model_dump(),
        "gstr3b_detail": detail,
        "audit_log": [e.model_dump(mode="json") for e in s.audit.entries],
        "audit_cited_count": s.audit.cited_count,
    }


if AGENT_FRAMEWORK_AVAILABLE:

    class IngestExecutor(Executor):
        @handler
        async def run(self, state: PipelineState, ctx: WorkflowContext[PipelineState]) -> None:
            state.sales = ingest_register(state.sales_path, "sales")
            state.purchases = ingest_register(state.purchase_path, "purchase")
            state.gstr2a = load_gstr2a(state.gstr2a_path) if state.gstr2a_path else []
            await ctx.send_message(state)

    class ReconcileExecutor(Executor):
        @handler
        async def run(self, state: PipelineState, ctx: WorkflowContext[PipelineState]) -> None:
            state.recon = reconcile(state.purchases, state.gstr2a)
            await ctx.send_message(state)

    class ITCExecutor(Executor):
        @handler
        async def run(self, state: PipelineState, ctx: WorkflowContext[PipelineState]) -> None:
            state.itc = assess_itc_eligibility(state.purchases, state.audit)
            await ctx.send_message(state)

    class AnomalyExecutor(Executor):
        @handler
        async def run(self, state: PipelineState, ctx: WorkflowContext[PipelineState]) -> None:
            state.anomalies = detect_anomalies(state.purchases, state.audit, today=state.today)
            await ctx.send_message(state)

    class ReturnsExecutor(Executor):
        @handler
        async def run(self, state: PipelineState, ctx: WorkflowContext[None, dict]) -> None:
            state.result = _build_result(state)
            await ctx.yield_output(state.result)

    def build_workflow():
        ingest = IngestExecutor(id="ingest")
        recon = ReconcileExecutor(id="reconcile")
        itc = ITCExecutor(id="itc_eligibility")
        anomaly = AnomalyExecutor(id="anomaly_detection")
        returns = ReturnsExecutor(id="return_generator")
        return (
            WorkflowBuilder(start_executor=ingest)
            .add_edge(ingest, recon)
            .add_edge(recon, itc)
            .add_edge(itc, anomaly)
            .add_edge(anomaly, returns)
            .build()
        )

    async def _run(state: PipelineState) -> dict:
        workflow = build_workflow()
        events = await workflow.run(state)
        outputs = events.get_outputs() if hasattr(events, "get_outputs") else []
        return outputs[0] if outputs else state.result


def run_analysis_via_workflow(
    sales_path: str | Path,
    purchase_path: str | Path,
    gstr2a_path: str | Path | None = None,
    today: date | None = None,
) -> dict:
    """Run the pipeline through the Agent Framework workflow if available."""
    from backend.agents.orchestrator import run_analysis

    if not AGENT_FRAMEWORK_AVAILABLE:
        return run_analysis(sales_path, purchase_path, gstr2a_path, today=today)

    try:
        state = PipelineState(
            sales_path=str(sales_path),
            purchase_path=str(purchase_path),
            gstr2a_path=str(gstr2a_path) if gstr2a_path else None,
            today=today,
        )
        result = asyncio.run(_run(state))
        if result:
            return result
    except Exception:
        pass
    # Resilient fallback: the deterministic pipeline always works.
    return run_analysis(sales_path, purchase_path, gstr2a_path, today=today)
