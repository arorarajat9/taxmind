"""Deterministic column mapper — the key-free default.

Handles the three messy realities from the build plan: misaligned/oddly-named
columns, and Hindi *or* English headers. Matching is synonym + token-overlap
based, so it is transparent and reproducible for the demo.
"""

from __future__ import annotations

import re

from backend.llm.base import LLMClient

# Synonyms per ontology field, including common Hindi (romanised + Devanagari)
# headers seen in Indian SME registers.
SYNONYMS: dict[str, list[str]] = {
    "invoice_number": [
        "invoice number", "invoice no", "inv no", "invoice", "bill no",
        "bill number", "voucher no", "doc no", "चालान संख्या", "बिल नंबर", "invno",
    ],
    "invoice_date": [
        "invoice date", "date", "inv date", "bill date", "dated", "तारीख",
        "दिनांक", "txn date", "transaction date",
    ],
    "gstin": [
        "gstin", "gst no", "gst number", "gstin/uin", "party gstin",
        "supplier gstin", "recipient gstin", "जीएसटीआईएन", "gst",
    ],
    "legal_name": [
        "legal name", "party name", "name", "supplier", "supplier name",
        "vendor", "vendor name", "customer", "customer name", "party",
        "पार्टी का नाम", "नाम", "trade name",
    ],
    "taxable_value": [
        "taxable value", "taxable amount", "taxable", "amount", "value",
        "basic amount", "net amount", "assessable value", "कर योग्य मूल्य",
        "राशि", "base value",
    ],
    "cgst": ["cgst", "cgst amount", "central tax", "cgst amt", "सीजीएसटी"],
    "sgst": ["sgst", "sgst amount", "state tax", "sgst amt", "एसजीएसटी", "utgst"],
    "igst": ["igst", "igst amount", "integrated tax", "igst amt", "आईजीएसटी"],
    "hsn_code": ["hsn", "hsn code", "hsn/sac", "sac", "sac code", "एचएसएन"],
    "place_of_supply": [
        "place of supply", "pos", "state", "supply state", "आपूर्ति का स्थान",
    ],
    "description": [
        "description", "particulars", "item", "goods", "narration", "details",
        "description of goods", "विवरण",
    ],
}

_WORD = re.compile(r"[^\wऀ-ॿ]+")  # keep latin + Devanagari


def _norm(s: str) -> str:
    return _WORD.sub(" ", str(s).strip().lower()).strip()


def _tok(s: str) -> set[str]:
    return {t for t in _norm(s).split() if t}


class RuleBasedLLM(LLMClient):
    name = "rule-based"

    def map_columns(
        self,
        headers: list[str],
        sample_rows: list[dict],
        target_fields: dict[str, str],
    ) -> dict[str, str | None]:
        norm_headers = {h: _norm(h) for h in headers}
        mapping: dict[str, str | None] = {}
        used: set[str] = set()

        for field in target_fields:
            syns = SYNONYMS.get(field, [field.replace("_", " ")])
            best_header, best_score = None, 0.0
            for header, nh in norm_headers.items():
                if header in used:
                    continue
                score = self._score(nh, syns)
                if score > best_score:
                    best_header, best_score = header, score
            # require a minimum confidence to avoid spurious matches
            if best_header and best_score >= 0.5:
                mapping[field] = best_header
                used.add(best_header)
            else:
                mapping[field] = None
        return mapping

    @staticmethod
    def _score(norm_header: str, synonyms: list[str]) -> float:
        h_tokens = {t for t in norm_header.split() if t}
        best = 0.0
        for syn in synonyms:
            s = _norm(syn)
            if norm_header == s:
                return 1.0
            s_tokens = {t for t in s.split() if t}
            if not s_tokens:
                continue
            if s in norm_header or norm_header in s:
                best = max(best, 0.85)
            overlap = len(h_tokens & s_tokens)
            if overlap:
                best = max(best, overlap / max(len(h_tokens), len(s_tokens)))
        return best
