"""Anomaly Detection Agent — deterministic data-quality checks.

Rules-based pass over purchases (and optionally sales) for the issues that most
commonly break a GST filing: duplicate invoices, missing or structurally invalid
GSTINs, and future-dated invoices. Fast, explainable, and key-free.
"""

from __future__ import annotations

import re
from datetime import date

from backend.audit.log import AuditLog
from backend.ontology.entities import Anomaly, Invoice, Severity

AGENT = "Anomaly Detection Agent"

# Structural GSTIN check: 2-digit state + 10-char PAN + entity + Z + checksum.
GSTIN_RE = re.compile(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$")


def detect_anomalies(
    entries: list[Invoice],
    audit: AuditLog,
    today: date | None = None,
) -> list[Anomaly]:
    today = today or date.today()
    anomalies: list[Anomaly] = []
    seen: dict[tuple, str] = {}

    def add(entry_ref, rule, message, severity):
        anomalies.append(
            Anomaly(entity_ref=entry_ref, rule=rule, message=message, severity=severity)
        )
        audit.record(agent=AGENT, entity_ref=entry_ref, decision=rule, rationale=message)

    for e in entries:
        ref = e.invoice_number

        # Duplicate (same invoice number + GSTIN seen already)
        key = (e.invoice_number.upper(), e.gstin)
        if key in seen:
            add(ref, "Duplicate invoice",
                f"Invoice {ref} from {e.gstin or 'unknown GSTIN'} appears more than once.",
                Severity.CRITICAL)
        else:
            seen[key] = ref

        # Missing GSTIN (only material for purchases / B2B — flag as warning)
        if not e.gstin:
            add(ref, "Missing GSTIN",
                f"Invoice {ref} has no GSTIN — ITC cannot be claimed without it.",
                Severity.WARNING)
        elif not GSTIN_RE.match(e.gstin):
            add(ref, "Invalid GSTIN format",
                f"GSTIN '{e.gstin}' on invoice {ref} is not a valid 15-character GSTIN.",
                Severity.CRITICAL)

        # Future-dated invoice
        if e.invoice_date and e.invoice_date > today:
            add(ref, "Future-dated invoice",
                f"Invoice {ref} is dated {e.invoice_date.isoformat()} (in the future).",
                Severity.CRITICAL)

    return anomalies
