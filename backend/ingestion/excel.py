"""Excel ingestion — turns a messy SME register into ontology entities.

Handles the three messy realities called out in the build plan:

1. **Misaligned columns / junk header rows** — auto-detects the real header row
   by scoring each row against the ontology vocabulary.
2. **Mixed date formats** — dd/mm/yyyy, yyyy-mm-dd, Excel serials, etc.
3. **Hindi or English headers** — handled by the column mapper's synonym sets.
"""

from __future__ import annotations

import math
from datetime import date, datetime
from pathlib import Path
from typing import Literal

import pandas as pd

from backend.llm.factory import get_llm_client
from backend.llm.rule_based import SYNONYMS, _norm
from backend.ontology.entities import PurchaseEntry, SalesEntry, SupplyType

RegisterKind = Literal["sales", "purchase"]

ONTOLOGY_FIELDS: dict[str, str] = {
    "invoice_number": "unique invoice/bill number",
    "invoice_date": "date the invoice was issued",
    "gstin": "15-char GSTIN of the counterparty",
    "legal_name": "name of the supplier/customer",
    "taxable_value": "taxable value before tax",
    "cgst": "central GST amount",
    "sgst": "state GST amount",
    "igst": "integrated GST amount",
    "hsn_code": "HSN or SAC code",
    "place_of_supply": "state / place of supply",
    "description": "description of goods or services",
}

_ALL_SYNONYM_TOKENS = {
    tok
    for syns in SYNONYMS.values()
    for syn in syns
    for tok in _norm(syn).split()
}


def _detect_header_row(raw: pd.DataFrame, max_scan: int = 10) -> int:
    """Pick the row whose cells best resemble known column headers."""
    best_row, best_score = 0, -1.0
    for i in range(min(max_scan, len(raw))):
        cells = [str(c) for c in raw.iloc[i].tolist() if pd.notna(c)]
        if not cells:
            continue
        score = sum(
            1
            for cell in cells
            for tok in _norm(cell).split()
            if tok in _ALL_SYNONYM_TOKENS
        )
        if score > best_score:
            best_row, best_score = i, score
    return best_row


def parse_amount(value) -> float:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return 0.0
    if isinstance(value, (int, float)):
        return round(float(value), 2)
    s = str(value).strip().replace(",", "").replace("₹", "").replace("Rs", "")
    s = s.replace("INR", "").replace("(", "-").replace(")", "").strip()
    if not s or s in {"-", "nan", "NA", "N/A"}:
        return 0.0
    try:
        return round(float(s), 2)
    except ValueError:
        return 0.0


_DATE_FORMATS = [
    "%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d/%m/%y", "%d-%b-%Y",
    "%d %b %Y", "%d.%m.%Y", "%m/%d/%Y", "%d-%b-%y", "%Y/%m/%d",
]


def parse_date(value) -> date | None:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    # Excel serial date
    if isinstance(value, (int, float)):
        try:
            return (datetime(1899, 12, 30) + pd.to_timedelta(int(value), "D")).date()
        except Exception:
            return None
    s = str(value).strip()
    if not s:
        return None
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    try:  # last resort: let pandas guess (day-first for Indian data)
        return pd.to_datetime(s, dayfirst=True, errors="raise").date()
    except Exception:
        return None


def _clean_str(value) -> str | None:
    """Return a trimmed string, or None for NaN / empty / nan-like values."""
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    s = str(value).strip()
    if s.lower() in {"", "nan", "none", "n/a", "na", "null"}:
        return None
    return s


def ingest_register(path: str | Path, kind: RegisterKind) -> list:
    """Read a sales or purchase register Excel into normalized ontology entities."""
    raw = pd.read_excel(path, header=None, dtype=object)
    header_row = _detect_header_row(raw)
    df = pd.read_excel(path, header=header_row, dtype=object)
    df = df.dropna(how="all")

    headers = [str(c) for c in df.columns]
    sample_rows = df.head(3).to_dict(orient="records")

    mapper = get_llm_client()
    mapping = mapper.map_columns(headers, sample_rows, ONTOLOGY_FIELDS)

    entities = []
    for _, row in df.iterrows():
        def get(field):
            col = mapping.get(field)
            return row.get(col) if col else None

        invoice_number = _clean_str(get("invoice_number"))
        if invoice_number is None:
            continue  # skip blank/total rows

        gstin = _clean_str(get("gstin"))
        common = dict(
            invoice_number=invoice_number,
            invoice_date=parse_date(get("invoice_date")),
            gstin=gstin.upper() if gstin else None,
            legal_name=_clean_str(get("legal_name")),
            taxable_value=parse_amount(get("taxable_value")),
            cgst=parse_amount(get("cgst")),
            sgst=parse_amount(get("sgst")),
            igst=parse_amount(get("igst")),
            hsn_code=_clean_str(get("hsn_code")),
            place_of_supply=_clean_str(get("place_of_supply")),
            description=_clean_str(get("description")),
        )

        if kind == "sales":
            supply = SupplyType.B2B if common["gstin"] else SupplyType.B2C
            entities.append(SalesEntry(supply_type=supply, **common))
        else:
            entities.append(PurchaseEntry(**common))

    return entities


def ingestion_report(entities: list, mapping_meta: dict | None = None) -> dict:
    return {
        "rows_ingested": len(entities),
        "total_taxable_value": round(sum(e.taxable_value for e in entities), 2),
        "total_tax": round(sum(e.total_tax for e in entities), 2),
    }
