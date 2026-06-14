"""Reconciliation engine — purchase register vs GSTR-2A.

Matches each booked purchase against the supplier-reported GSTR-2A by
GSTIN + invoice number, then compares tax with a tolerance. The categories follow
standard GST practice:

* **matched**          — present in both, amounts agree.
* **mismatched**       — present in both, tax amount differs.
* **missing_in_2a**    — booked by us, supplier hasn't reported -> ITC at risk.
* **missing_in_books** — reported by supplier, not in our books.

``itc_at_risk`` is the total tax that may be denied: the full tax of
missing-in-2A purchases plus the shortfall on mismatched ones (Section 16(2)(aa) /
Rule 36(4)).
"""

from __future__ import annotations

import re

from pydantic import BaseModel

from backend.ontology.entities import Invoice, PurchaseEntry, ReconStatus

# Tax amounts within this absolute rupee tolerance are treated as a match.
AMOUNT_TOLERANCE = 1.0


def _norm_inv(num: str | None) -> str:
    return re.sub(r"[\s\-/]", "", (num or "")).upper()


class ReconLine(BaseModel):
    invoice_number: str
    gstin: str | None = None
    supplier: str | None = None
    status: ReconStatus
    book_tax: float = 0.0
    gstr2a_tax: float = 0.0
    tax_difference: float = 0.0
    itc_at_risk: float = 0.0
    note: str = ""


class ReconReport(BaseModel):
    lines: list[ReconLine] = []
    matched: int = 0
    mismatched: int = 0
    missing_in_2a: int = 0
    missing_in_books: int = 0
    total_itc_at_risk: float = 0.0
    total_book_itc: float = 0.0

    @property
    def summary(self) -> dict:
        return {
            "matched": self.matched,
            "mismatched": self.mismatched,
            "missing_in_2a": self.missing_in_2a,
            "missing_in_books": self.missing_in_books,
            "total_itc_at_risk": round(self.total_itc_at_risk, 2),
            "total_book_itc": round(self.total_book_itc, 2),
        }


def reconcile(
    purchases: list[PurchaseEntry], gstr2a: list[Invoice]
) -> ReconReport:
    # index 2A by (gstin, normalized invoice number)
    index: dict[tuple, Invoice] = {}
    for g in gstr2a:
        index[(g.gstin, _norm_inv(g.invoice_number))] = g
    matched_2a_keys: set[tuple] = set()

    report = ReconReport()
    for p in purchases:
        key = (p.gstin, _norm_inv(p.invoice_number))
        book_tax = p.total_tax
        report.total_book_itc += book_tax
        g = index.get(key)

        if g is None:
            line = ReconLine(
                invoice_number=p.invoice_number,
                gstin=p.gstin,
                supplier=p.legal_name,
                status=ReconStatus.MISSING_IN_2A,
                book_tax=book_tax,
                itc_at_risk=book_tax,
                note="Not reflected in GSTR-2A — supplier may not have filed.",
            )
            report.missing_in_2a += 1
            report.total_itc_at_risk += book_tax
            p.recon_status = ReconStatus.MISSING_IN_2A
        else:
            matched_2a_keys.add(key)
            diff = round(book_tax - g.total_tax, 2)
            if abs(diff) <= AMOUNT_TOLERANCE:
                line = ReconLine(
                    invoice_number=p.invoice_number,
                    gstin=p.gstin,
                    supplier=p.legal_name,
                    status=ReconStatus.MATCHED,
                    book_tax=book_tax,
                    gstr2a_tax=g.total_tax,
                    note="Matched with GSTR-2A.",
                )
                report.matched += 1
                p.recon_status = ReconStatus.MATCHED
            else:
                at_risk = max(0.0, diff)  # excess claimed in books is at risk
                line = ReconLine(
                    invoice_number=p.invoice_number,
                    gstin=p.gstin,
                    supplier=p.legal_name,
                    status=ReconStatus.MISMATCHED,
                    book_tax=book_tax,
                    gstr2a_tax=g.total_tax,
                    tax_difference=diff,
                    itc_at_risk=at_risk,
                    note=f"Tax differs by ₹{diff:,.2f} vs GSTR-2A.",
                )
                report.mismatched += 1
                report.total_itc_at_risk += at_risk
                p.recon_status = ReconStatus.MISMATCHED
        report.lines.append(line)

    # 2A entries never matched to a booked purchase
    for g in gstr2a:
        key = (g.gstin, _norm_inv(g.invoice_number))
        if key not in matched_2a_keys:
            report.lines.append(
                ReconLine(
                    invoice_number=g.invoice_number,
                    gstin=g.gstin,
                    supplier=g.legal_name,
                    status=ReconStatus.MISSING_IN_BOOKS,
                    gstr2a_tax=g.total_tax,
                    note="In GSTR-2A but not recorded in books — record it to claim ITC.",
                )
            )
            report.missing_in_books += 1

    report.total_itc_at_risk = round(report.total_itc_at_risk, 2)
    report.total_book_itc = round(report.total_book_itc, 2)
    return report
