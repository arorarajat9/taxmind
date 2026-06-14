# GST knowledge sources

TaxMind grounds its compliance decisions in **public** Indian GST law. The
knowledge base is populated from the documents below.

## Bundled in this repo (`data/gst-sources/`)
Curated, public statutory text used by the **local** knowledge base so the demo is
key-free and reproducible:

| File | Covers |
|---|---|
| `section-17-5-blocked-credits.md` | Section 17(5) CGST Act — all blocked-credit clauses (a)–(i) |
| `section-16-itc-eligibility.md` | Section 16 — ITC eligibility, conditions, 16(2)(aa), Rule 36(4), time limits |
| `gstin-and-returns-reference.md` | GSTIN format, GSTR-1/2A/2B/3B structure, CGST-SGST vs IGST |

These are reproductions of public statute, included for grounding. Always verify
against the official current bare act before filing.

## Recommended full sources for Foundry IQ (Azure mode)
For a production knowledge base, ingest the full official PDFs into the Foundry IQ
knowledge source (Blob container `gst-knowledge`):

- **CGST Act, 2017** — CBIC: https://cbic-gst.gov.in (Acts)
- **CGST Rules, 2017** — CBIC: https://cbic-gst.gov.in (Rules)
- **CBIC notifications & circulars** — https://cbic-gst.gov.in (Notifications)
- **GST portal user manuals (GSTR-1/2B/3B)** — https://www.gst.gov.in

`scripts/setup_foundry_iq.py` uploads whatever is in `data/gst-sources/` to Blob;
add the official PDFs there before running it for a richer knowledge base.

## Data hygiene
- No confidential or client data is used anywhere in this project.
- Demo invoice data is synthetic (`scripts/generate_demo_data.py`).
