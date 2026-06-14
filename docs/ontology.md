# Fabric IQ Ontology

TaxMind maps every raw spreadsheet row onto a small set of GST business concepts so
the agents reason in domain language. Defined in
[`backend/ontology/entities.py`](../backend/ontology/entities.py).

## Entities

### Invoice (base)
| Field | Type | Notes |
|---|---|---|
| `invoice_number` | str | unique bill number |
| `invoice_date` | date? | normalized from mixed formats |
| `gstin` | str? | counterparty GSTIN (15-char) |
| `legal_name` | str? | supplier/customer name |
| `taxable_value` | float | value before tax |
| `cgst` / `sgst` / `igst` | float | tax heads |
| `hsn_code` | str? | HSN/SAC |
| `place_of_supply` | str? | drives intra/inter-state |
| derived: `total_tax`, `invoice_value` | float | |

### SalesEntry (outward) — extends Invoice
- `supply_type`: `B2B` (recipient has GSTIN) or `B2C`.

### PurchaseEntry (inward) — extends Invoice
- `itc_eligible`: `True | False | None` (None = uncertain → consult CA)
- `itc_block_reason`: human-readable reason
- `citation`: the grounded `Citation` behind a block
- `recon_status`: matched / mismatched / missing_in_2a / missing_in_books

### Supplier
- `gstin`, `legal_name`, `filing_status`.

### ITCClaim / TaxLiability
Aggregate figures that feed GSTR-3B: gross ITC, eligible, blocked, at-risk; outward
tax, ITC available/reversed, net payable.

### Citation (cross-cutting)
`section`, `snippet`, `source`, `confidence` — returned for every grounded
decision by **both** the local KB and Foundry IQ, so downstream code is
backend-agnostic.

### Anomaly
`entity_ref`, `rule`, `message`, `severity` (info/warning/critical).

## Why an ontology (not just columns)
Mapping `"कर योग्य मूल्य"` / `"Taxable Value"` / `"Basic Amount"` → a single
`taxable_value` concept means the agents, the reconciliation math, and the returns
generator never touch raw headers. New register formats only require an ingestion
mapping, not changes to business logic — exactly the reuse story Fabric IQ exists
for.
