"""Return generation — GSTR-1 (outward) and GSTR-3B (summary).

Builds filing-ready summaries from the normalized entities + reconciliation +
ITC eligibility results. Figures follow standard GST return structure; the human
reviews and files (TaxMind never auto-submits).
"""

from __future__ import annotations

from collections import defaultdict

from backend.agents.reconciliation import ReconReport
from backend.ontology.entities import PurchaseEntry, SalesEntry, SupplyType, TaxLiability


def _rate_of(taxable: float, tax: float) -> int:
    if taxable <= 0:
        return 0
    return int(round(tax / taxable * 100))


def build_gstr1(sales: list[SalesEntry]) -> dict:
    b2b, b2c_rate = [], defaultdict(lambda: {"taxable_value": 0.0, "tax": 0.0, "count": 0})
    rate_wise = defaultdict(lambda: {"taxable_value": 0.0, "tax": 0.0, "count": 0})
    hsn = defaultdict(lambda: {"taxable_value": 0.0, "tax": 0.0, "count": 0})

    b2b_total = {"taxable_value": 0.0, "tax": 0.0, "count": 0}
    b2c_total = {"taxable_value": 0.0, "tax": 0.0, "count": 0}

    for s in sales:
        rate = _rate_of(s.taxable_value, s.total_tax)
        rate_wise[rate]["taxable_value"] += s.taxable_value
        rate_wise[rate]["tax"] += s.total_tax
        rate_wise[rate]["count"] += 1

        key = s.hsn_code or "UNSPECIFIED"
        hsn[key]["taxable_value"] += s.taxable_value
        hsn[key]["tax"] += s.total_tax
        hsn[key]["count"] += 1

        if s.supply_type == SupplyType.B2B and s.gstin:
            b2b.append({
                "gstin": s.gstin,
                "recipient": s.legal_name,
                "invoice_number": s.invoice_number,
                "invoice_date": s.invoice_date.isoformat() if s.invoice_date else None,
                "taxable_value": round(s.taxable_value, 2),
                "cgst": round(s.cgst, 2),
                "sgst": round(s.sgst, 2),
                "igst": round(s.igst, 2),
                "rate": rate,
            })
            b2b_total["taxable_value"] += s.taxable_value
            b2b_total["tax"] += s.total_tax
            b2b_total["count"] += 1
        else:
            b2c_rate[rate]["taxable_value"] += s.taxable_value
            b2c_rate[rate]["tax"] += s.total_tax
            b2c_rate[rate]["count"] += 1
            b2c_total["taxable_value"] += s.taxable_value
            b2c_total["tax"] += s.total_tax
            b2c_total["count"] += 1

    def _round(d):
        return {k: {kk: round(vv, 2) for kk, vv in v.items()} for k, v in d.items()}

    return {
        "b2b_invoices": b2b,
        "b2b_total": {k: round(v, 2) for k, v in b2b_total.items()},
        "b2c_total": {k: round(v, 2) for k, v in b2c_total.items()},
        "b2c_rate_wise": _round(b2c_rate),
        "rate_wise": _round(rate_wise),
        "hsn_summary": _round(hsn),
    }


def build_gstr3b(
    sales: list[SalesEntry],
    purchases: list[PurchaseEntry],
    recon: ReconReport,
    itc: dict,
) -> tuple[TaxLiability, dict]:
    outward_taxable = sum(s.taxable_value for s in sales)
    outward_tax = sum(s.total_tax for s in sales)

    gross_itc = round(sum(p.total_tax for p in purchases), 2)
    itc_blocked = round(itc.get("itc_blocked_value", 0.0), 2)
    itc_at_risk = round(recon.total_itc_at_risk, 2)

    # Conservative claimable ITC: drop blocked (17(5)) and at-risk (not in 2A).
    itc_reversed = round(itc_blocked + itc_at_risk, 2)
    itc_available = round(gross_itc - itc_reversed, 2)
    net_payable = round(max(0.0, outward_tax - itc_available), 2)

    liability = TaxLiability(
        outward_taxable_value=round(outward_taxable, 2),
        outward_tax=round(outward_tax, 2),
        itc_available=itc_available,
        itc_reversed=itc_reversed,
        net_tax_payable=net_payable,
    )
    detail = {
        "gross_itc_in_books": gross_itc,
        "itc_blocked_17_5": itc_blocked,
        "itc_at_risk_2a_mismatch": itc_at_risk,
        "net_itc_claimable": itc_available,
        "net_tax_payable": net_payable,
    }
    return liability, detail
