"""Load GSTR-2A (supplier-reported inward supplies).

Primary format is the GSTN-style JSON export; Excel is supported as a secondary
format. Both normalize to a list of :class:`Invoice` for reconciliation.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from backend.ingestion.excel import _clean_str, parse_amount, parse_date
from backend.ontology.entities import Invoice

_JSON_KEYS = {
    "invoice_number": ["invoice_number", "inum", "invoice_no"],
    "invoice_date": ["invoice_date", "idt", "date"],
    "gstin": ["gstin", "ctin"],
    "legal_name": ["supplier", "trdnm", "legal_name", "name"],
    "taxable_value": ["taxable_value", "txval", "taxable"],
    "cgst": ["cgst", "camt"],
    "sgst": ["sgst", "samt"],
    "igst": ["igst", "iamt"],
}


def _from_record(rec: dict) -> Invoice:
    def pick(field):
        for key in _JSON_KEYS[field]:
            if key in rec:
                return rec[key]
        return None

    gstin = _clean_str(pick("gstin"))
    return Invoice(
        invoice_number=_clean_str(pick("invoice_number")) or "",
        invoice_date=parse_date(pick("invoice_date")),
        gstin=gstin.upper() if gstin else None,
        legal_name=_clean_str(pick("legal_name")),
        taxable_value=parse_amount(pick("taxable_value")),
        cgst=parse_amount(pick("cgst")),
        sgst=parse_amount(pick("sgst")),
        igst=parse_amount(pick("igst")),
    )


def load_gstr2a(path: str | Path) -> list[Invoice]:
    path = Path(path)
    if path.suffix.lower() == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        records = data.get("b2b", data) if isinstance(data, dict) else data
        return [_from_record(r) for r in records if r.get("invoice_number") or r.get("inum")]

    # Excel fallback — reuse the register ingester's header detection
    from backend.ingestion.excel import _detect_header_row

    raw = pd.read_excel(path, header=None, dtype=object)
    df = pd.read_excel(path, header=_detect_header_row(raw), dtype=object).dropna(how="all")
    invoices = []
    for _, row in df.iterrows():
        rec = {str(k).strip().lower(): v for k, v in row.items()}
        inv = Invoice(
            invoice_number=_clean_str(rec.get("invoice number") or rec.get("invoice_number")) or "",
            invoice_date=parse_date(rec.get("invoice date") or rec.get("invoice_date")),
            gstin=(lambda g: g.upper() if g else None)(
                _clean_str(rec.get("gstin of supplier") or rec.get("gstin"))
            ),
            legal_name=_clean_str(rec.get("supplier name") or rec.get("supplier")),
            taxable_value=parse_amount(rec.get("taxable value")),
            cgst=parse_amount(rec.get("cgst")),
            sgst=parse_amount(rec.get("sgst")),
            igst=parse_amount(rec.get("igst")),
        )
        if inv.invoice_number:
            invoices.append(inv)
    return invoices
