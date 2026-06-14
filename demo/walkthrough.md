# TaxMind — Walkthrough

A guided tour of what TaxMind does on the bundled kirana dataset.

## The dataset (`data/synthetic/`)
*Sharma Kirana Store*, Maharashtra (GSTIN `27AAQCS4455K1ZP`). Deliberately messy and
seeded with real issues:

- **Sales register** — English headers, a title row, mixed date formats; 6 invoices
  (B2C retail + a few B2B).
- **Purchase register** — **Hindi** headers, a junk title row; 9 invoices including
  a staff-catering bill, a shop-construction bill, a duplicate, a bad GSTIN, a
  future-dated invoice, and a missing-GSTIN row.
- **GSTR-2A** (JSON + Excel) — supplier-reported invoices with one amount mismatch,
  one purchase missing (ITC at risk), and one entry not in our books.

## What TaxMind finds

| Finding | Invoice | Result |
|---|---|---|
| ITC at risk | P-1003 (Britannia) + others | not in GSTR-2A → ₹8,640 total at risk |
| Amount mismatch | P-1002 (Nestlé) | books ₹5,400 vs 2A ₹5,040 |
| **Blocked ITC** | P-1004 (staff catering) | **Section 17(5)(b)(i)** — cited |
| **Blocked ITC** | P-1005 (construction) | **Section 17(5)(d)** — cited |
| Not blocked | P-1002 (packaged food for resale) | eligible — same-category proviso |
| Duplicate | P-1001 ×2 | critical anomaly |
| Invalid GSTIN | P-1007 (`27ABC123`) | critical anomaly |
| Future-dated | P-1008 (2026-12-01) | critical anomaly |
| Missing GSTIN | P-1009 | warning |

## Outputs
- **GSTR-1**: B2B invoice list, B2C rate-wise, HSN summary.
- **GSTR-3B**: gross ITC ₹50,580 − blocked ₹18,900 − at-risk ₹8,640 = net claimable
  ₹23,040; **net tax payable ₹3,300**.
- **Filing-ready Excel** (`output/taxmind_filing_summary.xlsx`): 5 sheets incl. a
  cited audit log.

## Try it
```bash
python scripts/run_full_pipeline.py          # CLI, prints everything above
pytest backend/tests                          # 11 acceptance tests
```
Or open the dashboard and hit **Run demo**.
