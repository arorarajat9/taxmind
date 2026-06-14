"""Fabric IQ-style business ontology for TaxMind.

This is the differentiator described in the build plan: instead of piping raw
spreadsheet columns into an LLM, TaxMind maps everything onto a small set of GST
business concepts and reasons in *GST language* ("ITC eligible amount", not
"column F"). These pydantic models are the canonical schema that ingestion maps
onto and that every agent consumes.
"""

from __future__ import annotations

from datetime import date
from enum import Enum

from pydantic import BaseModel, Field


class SupplyType(str, Enum):
    B2B = "B2B"  # recipient is GST-registered (has a GSTIN)
    B2C = "B2C"  # recipient is an unregistered consumer


class ReconStatus(str, Enum):
    MATCHED = "matched"
    MISMATCHED = "mismatched"  # found in 2A but amount differs
    MISSING_IN_2A = "missing_in_2a"  # in books, not reflected by supplier
    MISSING_IN_BOOKS = "missing_in_books"  # in 2A, not in our books


class Severity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class Citation(BaseModel):
    """A grounded reference returned for every compliance decision.

    The same shape is produced by both the local knowledge base and the real
    Foundry IQ retrieval path, so the "citation appears live on screen" demo
    works regardless of mode.
    """

    section: str = Field(..., description="e.g. 'Section 17(5)(b)(i)'")
    snippet: str = Field(..., description="Verbatim text supporting the decision")
    source: str = Field(..., description="Document the snippet came from")
    confidence: float = Field(0.0, ge=0.0, le=1.0)


class Invoice(BaseModel):
    invoice_number: str
    invoice_date: date | None = None
    gstin: str | None = Field(None, description="Counterparty GSTIN")
    legal_name: str | None = None
    taxable_value: float = 0.0
    cgst: float = 0.0
    sgst: float = 0.0
    igst: float = 0.0
    hsn_code: str | None = None
    place_of_supply: str | None = None
    description: str | None = None

    @property
    def total_tax(self) -> float:
        return round(self.cgst + self.sgst + self.igst, 2)

    @property
    def invoice_value(self) -> float:
        return round(self.taxable_value + self.total_tax, 2)


class SalesEntry(Invoice):
    supply_type: SupplyType = SupplyType.B2C


class PurchaseEntry(Invoice):
    """A purchase; ITC eligibility + reconciliation status are filled by agents."""

    itc_eligible: bool | None = None
    itc_block_reason: str | None = None
    citation: Citation | None = None
    recon_status: ReconStatus | None = None


class Supplier(BaseModel):
    gstin: str
    legal_name: str | None = None
    filing_status: str | None = None


class Anomaly(BaseModel):
    entity_ref: str = Field(..., description="invoice number or row reference")
    rule: str
    message: str
    severity: Severity = Severity.WARNING


class ITCClaim(BaseModel):
    total_itc_in_books: float = 0.0
    itc_eligible: float = 0.0
    itc_blocked: float = 0.0
    itc_at_risk: float = Field(
        0.0, description="ITC for purchases not reflected/mismatched in GSTR-2A"
    )


class TaxLiability(BaseModel):
    outward_taxable_value: float = 0.0
    outward_tax: float = 0.0
    itc_available: float = 0.0
    itc_reversed: float = 0.0
    net_tax_payable: float = 0.0
