"""Generate the synthetic kirana-store demo dataset.

Persona: *Sharma Kirana Store* — a neighbourhood retail shop in Maharashtra
(state code 27). All data is fabricated for the demo; no real taxpayer data is
used. The files are deliberately messy (title/junk rows, Hindi headers, mixed
date formats) to exercise the ingestion layer, and contain planted issues so the
agents have something real to find:

* A **restaurant/catering bill** -> ITC blocked under Section 17(5)(b)(i).
* An **office construction bill** -> ITC blocked under Section 17(5)(d).
* A purchase **missing from GSTR-2A** -> ITC at risk.
* A purchase with an **amount mismatch** vs GSTR-2A.
* A **duplicate** invoice, an **invalid GSTIN**, a **future-dated** invoice, and a
  **missing GSTIN** -> anomalies.

Run:  python scripts/generate_demo_data.py
"""

from __future__ import annotations

import json
from pathlib import Path

from openpyxl import Workbook

OUT = Path(__file__).resolve().parent.parent / "data" / "synthetic"
OUT.mkdir(parents=True, exist_ok=True)

OWN_GSTIN = "27AAQCS4455K1ZP"  # Sharma Kirana Store

# ── Sales register (outward supplies) ────────────────────────────────────────
# English headers, a title row on top, mixed date formats.
SALES_HEADERS = [
    "Invoice No", "Date", "Customer Name", "GSTIN", "Taxable Value",
    "CGST", "SGST", "IGST", "HSN", "Place of Supply",
]
SALES_ROWS = [
    ["S-001", "05/04/2025", "Walk-in Customers", "", 80000, 2000, 2000, 0, "2106", "Maharashtra"],
    ["S-002", "08-04-2025", "Walk-in Customers", "", 50000, 4500, 4500, 0, "3401", "Maharashtra"],
    ["S-003", "2025-04-12", "Patel Provisions", "27AAHCP7777L1Z3", 40000, 1000, 1000, 0, "1006", "Maharashtra"],
    ["S-004", "15-Apr-2025", "Gupta General Store", "27AAICG8888M1Z6", 25000, 2250, 2250, 0, "3402", "Maharashtra"],
    ["S-005", "20/04/2025", "Walk-in Customers", "", 30000, 1800, 1800, 0, "1905", "Maharashtra"],
    ["S-006", "28/04/2025", "Mehta Traders", "29AAJCM9999N1Z4", 18000, 0, 0, 3240, "3401", "Karnataka"],
]

# ── Purchase register (inward supplies) ──────────────────────────────────────
# Hindi headers + a junk title row to test header detection.
PURCHASE_TITLE = "शर्मा किराना स्टोर - खरीद रजिस्टर (FY 2025-26)"
PURCHASE_HEADERS = [
    "बिल नंबर", "तारीख", "सप्लायर का नाम", "जीएसटीआईएन", "कर योग्य मूल्य",
    "सीजीएसटी", "एसजीएसटी", "आईजीएसटी", "एचएसएन", "विवरण",
]
PURCHASE_ROWS = [
    ["P-1001", "03/04/2025", "Hindustan Lever Distributors", "27AAACS1234F1Z5", 50000, 4500, 4500, 0, "3401", "Soaps and detergents"],
    ["P-1002", "06/04/2025", "Nestle India Distributor", "27AABCH5678G1Z2", 30000, 2700, 2700, 0, "2106", "Packaged food items"],
    ["P-1003", "10/04/2025", "Britannia Distributor", "27AALCS9012H1Z8", 20000, 1800, 1800, 0, "1905", "Biscuits and bakery"],
    ["P-1004", "12/04/2025", "Sharma Caterers (staff lunch)", "27AAFCS3333J1Z1", 5000, 450, 450, 0, "9963", "Food and beverages - staff party"],
    ["P-1005", "14/04/2025", "BuildWell Constructions", "27AAGCS4444K1Z9", 100000, 9000, 9000, 0, "9954", "Construction of new shop floor"],
    ["P-1001", "03/04/2025", "Hindustan Lever Distributors", "27AAACS1234F1Z5", 50000, 4500, 4500, 0, "3401", "Soaps and detergents"],  # duplicate
    ["P-1007", "18/04/2025", "Cash Wholesale Mart", "27ABC123", 8000, 720, 720, 0, "2106", "Misc grocery (bad GSTIN)"],
    ["P-1008", "01/12/2026", "Future Supplies Co", "27AAKCF2222P1Z7", 12000, 1080, 1080, 0, "3402", "Future-dated invoice"],
    ["P-1009", "22/04/2025", "Local Vendor", "", 6000, 540, 540, 0, "1006", "Missing GSTIN supplier"],
]

# ── GSTR-2A (supplier-reported, auto-drafted) ────────────────────────────────
# What suppliers actually reported. Drives reconciliation.
GSTR2A = [
    {"gstin": "27AAACS1234F1Z5", "supplier": "Hindustan Lever Distributors", "invoice_number": "P-1001", "invoice_date": "2025-04-03", "taxable_value": 50000, "cgst": 4500, "sgst": 4500, "igst": 0},
    {"gstin": "27AABCH5678G1Z2", "supplier": "Nestle India Distributor", "invoice_number": "P-1002", "invoice_date": "2025-04-06", "taxable_value": 28000, "cgst": 2520, "sgst": 2520, "igst": 0},  # mismatch
    {"gstin": "27AAFCS3333J1Z1", "supplier": "Sharma Caterers", "invoice_number": "P-1004", "invoice_date": "2025-04-12", "taxable_value": 5000, "cgst": 450, "sgst": 450, "igst": 0},
    {"gstin": "27AAGCS4444K1Z9", "supplier": "BuildWell Constructions", "invoice_number": "P-1005", "invoice_date": "2025-04-14", "taxable_value": 100000, "cgst": 9000, "sgst": 9000, "igst": 0},
    {"gstin": "27AAMCX1111Q1Z3", "supplier": "Surprise Supplier Pvt Ltd", "invoice_number": "P-2050", "invoice_date": "2025-04-19", "taxable_value": 15000, "cgst": 1350, "sgst": 1350, "igst": 0},  # missing in books
    # P-1003 (Britannia) intentionally ABSENT -> ITC at risk
]


def _write_sheet(path: Path, title: str | None, headers: list, rows: list) -> None:
    wb = Workbook()
    ws = wb.active
    ws.title = "Sheet1"
    if title:
        ws.append([title])
        ws.append([])  # blank spacer row -> tests header detection
    ws.append(headers)
    for r in rows:
        ws.append(r)
    wb.save(path)


def main() -> None:
    _write_sheet(OUT / "sales_register.xlsx", "Sharma Kirana Store - Sales Register FY 2025-26", SALES_HEADERS, SALES_ROWS)
    _write_sheet(OUT / "purchase_register.xlsx", PURCHASE_TITLE, PURCHASE_HEADERS, PURCHASE_ROWS)

    # GSTR-2A as both JSON (primary, GSTN-style) and Excel (secondary)
    (OUT / "gstr2a.json").write_text(
        json.dumps({"gstin": OWN_GSTIN, "period": "042025", "b2b": GSTR2A}, indent=2),
        encoding="utf-8",
    )
    g2a_headers = ["GSTIN of Supplier", "Supplier Name", "Invoice Number", "Invoice Date", "Taxable Value", "CGST", "SGST", "IGST"]
    g2a_rows = [
        [r["gstin"], r["supplier"], r["invoice_number"], r["invoice_date"], r["taxable_value"], r["cgst"], r["sgst"], r["igst"]]
        for r in GSTR2A
    ]
    _write_sheet(OUT / "gstr2a.xlsx", None, g2a_headers, g2a_rows)

    print(f"Demo data written to {OUT}")
    for p in sorted(OUT.glob("*")):
        print(f"  - {p.name}")


if __name__ == "__main__":
    main()
