"""Tests for the TaxMind pipeline — ingestion, reconciliation, agents, returns.

These run entirely in local mode (no Azure keys) against the synthetic kirana
dataset, so they double as the deadline-day acceptance gate.
"""

from datetime import date
from pathlib import Path

import pytest

from backend.agents.anomaly_detection import detect_anomalies
from backend.agents.itc_eligibility import assess_itc_eligibility
from backend.agents.orchestrator import run_analysis
from backend.agents.reconciliation import reconcile
from backend.audit.log import AuditLog
from backend.foundry_iq.factory import get_knowledge_base
from backend.ingestion.excel import ingest_register, parse_amount, parse_date
from backend.ingestion.gstr2a import load_gstr2a
from backend.ontology.entities import SupplyType
from backend.returns.generator import build_gstr1, build_gstr3b

DATA = Path(__file__).resolve().parent.parent.parent / "data" / "synthetic"


@pytest.fixture(scope="module", autouse=True)
def _ensure_data():
    if not (DATA / "purchase_register.xlsx").exists():
        import scripts.generate_demo_data as g  # type: ignore

        g.main()


# ── ingestion ───────────────────────────────────────────────────────────────
def test_parse_amount_handles_messy_values():
    assert parse_amount("₹1,50,000") == 150000.0
    assert parse_amount("(500)") == -500.0
    assert parse_amount("nan") == 0.0
    assert parse_amount(None) == 0.0


def test_parse_date_handles_multiple_formats():
    assert parse_date("05/04/2025") == date(2025, 4, 5)
    assert parse_date("2025-04-12") == date(2025, 4, 12)
    assert parse_date("15-Apr-2025") == date(2025, 4, 15)


def test_sales_b2b_b2c_classification():
    sales = ingest_register(DATA / "sales_register.xlsx", "sales")
    assert len(sales) >= 5
    b2c = [s for s in sales if s.supply_type == SupplyType.B2C]
    b2b = [s for s in sales if s.supply_type == SupplyType.B2B]
    assert all(s.gstin is None for s in b2c)
    assert all(s.gstin for s in b2b)


def test_hindi_headers_are_mapped():
    purch = ingest_register(DATA / "purchase_register.xlsx", "purchase")
    # Hindi headers + junk title row must still ingest 9 purchases with values
    assert len(purch) == 9
    assert sum(p.taxable_value for p in purch) > 0
    assert any(p.gstin and p.gstin.startswith("27") for p in purch)


# ── reconciliation ──────────────────────────────────────────────────────────
def test_reconciliation_categories():
    purch = ingest_register(DATA / "purchase_register.xlsx", "purchase")
    g2a = load_gstr2a(DATA / "gstr2a.json")
    rep = reconcile(purch, g2a)
    s = rep.summary
    assert s["matched"] >= 3
    assert s["mismatched"] == 1  # Nestlé amount differs
    assert s["missing_in_2a"] >= 1  # Britannia not filed
    assert s["missing_in_books"] >= 1  # Surprise Supplier
    assert s["total_itc_at_risk"] > 0


# ── ITC eligibility (cited) ─────────────────────────────────────────────────
def test_blocked_itc_is_cited_with_correct_sections():
    purch = ingest_register(DATA / "purchase_register.xlsx", "purchase")
    audit = AuditLog()
    assess_itc_eligibility(purch, audit)
    blocked = {p.invoice_number: p for p in purch if p.itc_eligible is False}
    # catering -> 17(5)(b)(i); construction -> 17(5)(d)
    assert blocked["P-1004"].citation.section.startswith("Section 17(5)(b)(i)")
    assert blocked["P-1005"].citation.section.startswith("Section 17(5)(d)")
    # every blocked flag must carry a citation
    assert all(p.citation is not None for p in blocked.values())


def test_resale_food_inventory_is_not_blocked():
    """Packaged food bought for resale keeps ITC (same-category proviso)."""
    purch = ingest_register(DATA / "purchase_register.xlsx", "purchase")
    audit = AuditLog()
    assess_itc_eligibility(purch, audit)
    nestle = next(p for p in purch if p.invoice_number == "P-1002")
    assert nestle.itc_eligible is True


# ── anomalies ───────────────────────────────────────────────────────────────
def test_anomaly_rules():
    purch = ingest_register(DATA / "purchase_register.xlsx", "purchase")
    audit = AuditLog()
    anoms = detect_anomalies(purch, audit, today=date(2026, 6, 14))
    rules = {a.rule for a in anoms}
    assert "Duplicate invoice" in rules
    assert "Invalid GSTIN format" in rules
    assert "Future-dated invoice" in rules
    assert "Missing GSTIN" in rules


# ── knowledge base ──────────────────────────────────────────────────────────
def test_kb_returns_cited_answer():
    kb = get_knowledge_base()
    res = kb.query("input tax credit on food and beverages outdoor catering")
    assert res.citations
    assert res.citations[0].section.startswith("Section 17(5)")
    assert res.is_confident


# ── returns ─────────────────────────────────────────────────────────────────
def test_gstr1_and_gstr3b_math():
    sales = ingest_register(DATA / "sales_register.xlsx", "sales")
    purch = ingest_register(DATA / "purchase_register.xlsx", "purchase")
    g2a = load_gstr2a(DATA / "gstr2a.json")
    recon = reconcile(purch, g2a)
    audit = AuditLog()
    itc = assess_itc_eligibility(purch, audit)

    g1 = build_gstr1(sales)
    assert g1["b2b_total"]["count"] >= 1
    assert g1["b2c_total"]["taxable_value"] > 0
    assert g1["hsn_summary"]

    liability, detail = build_gstr3b(sales, purch, recon, itc)
    # net ITC claimable = gross - blocked - at risk
    assert detail["net_itc_claimable"] == pytest.approx(
        detail["gross_itc_in_books"]
        - detail["itc_blocked_17_5"]
        - detail["itc_at_risk_2a_mismatch"]
    )
    assert liability.net_tax_payable >= 0


# ── end to end ──────────────────────────────────────────────────────────────
def test_full_analysis_runs():
    result = run_analysis(
        DATA / "sales_register.xlsx",
        DATA / "purchase_register.xlsx",
        DATA / "gstr2a.json",
    )
    assert result["mode"] in {"local", "azure"}
    assert len(result["blocked_itc"]) == 2
    assert result["audit_cited_count"] >= 2
    assert result["gstr3b"]["net_tax_payable"] >= 0
