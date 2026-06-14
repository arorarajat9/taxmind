# GSTIN format & GST return reference

> Compiled from public GSTN / CBIC documentation for grounding TaxMind's anomaly
> and return-generation logic.

## GSTIN format (15 characters)
A GSTIN is a 15-character alphanumeric code:
- Characters 1–2: **State code** (e.g. 27 = Maharashtra, 07 = Delhi, 29 = Karnataka).
- Characters 3–12: **PAN** of the taxpayer (10 characters).
- Character 13: **entity number** of the same PAN holder in the state.
- Character 14: default letter **"Z"**.
- Character 15: **checksum** character.

Regex (structural): `^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$`

A value that does not match this structure is an **invalid GSTIN** and should be
flagged before filing.

## GSTR-1 (outward supplies)
Monthly/quarterly statement of outward supplies. Key tables:
- **B2B**: invoice-wise details of supplies to registered persons (recipient GSTIN
  required).
- **B2C (Large & Small)**: supplies to unregistered persons, reported rate-wise.
- **HSN summary**: quantity and value of supplies grouped by HSN code and rate.

## GSTR-2A / GSTR-2B (inward supplies — auto-drafted)
Auto-populated from suppliers' GSTR-1 filings. Used by the recipient to reconcile
purchases and determine eligible ITC. GSTR-2B is the static monthly version used
to claim ITC.

## GSTR-3B (summary return)
Monthly self-assessed summary return. Key figures:
- Outward taxable supplies and tax thereon.
- **ITC available** (eligible input tax credit).
- **ITC reversed** (e.g. blocked credits under Section 17(5), Rule 42/43).
- **Net tax payable** = output tax − net ITC available.

## Place of supply & CGST/SGST vs IGST
- **Intra-state** supply (supplier and place of supply in the same state): tax
  splits into **CGST + SGST**.
- **Inter-state** supply (different states): **IGST** applies.
Mismatched tax heads versus place of supply are a common data-entry anomaly.
