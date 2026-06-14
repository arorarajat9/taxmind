# TaxMind — Demo video script (target 3:00–3:30)

Record at 1280×720+. Captions recommended (some judges watch muted). Have the API
(`uvicorn backend.api.main:app --port 8000`) and frontend (`npm run dev`) running,
browser at the dashboard, and a terminal ready.

---

### 0:00–0:20 — The problem
> "Meet Sharma Kirana Store — a small shop in Mumbai. Every month its owner loses
> days reconciling GST invoices in Excel and pays a CA thousands of rupees to file
> GSTR-1 and GSTR-3B. One wrong input-tax-credit claim can mean penalties."

Show the messy `purchase_register.xlsx` (Hindi headers, junk title row) on screen.

### 0:20–0:45 — Upload the mess
> "TaxMind ingests that messy Excel directly — misaligned columns, mixed date
> formats, Hindi or English headers."

Hit **Run demo (kirana store)**. The dashboard populates.

### 0:45–1:30 — Reconcile + the cited flag (the hero)
> "It reconciles every purchase against GSTR-2A and finds ₹8,640 of ITC at risk.
> Then the ITC Eligibility Agent catches a staff catering bill and a shop
> construction bill — and look: it doesn't just say 'blocked'. It cites
> **Section 17(5)(b)(i)** and **17(5)(d)** with the exact GST Act text, retrieved
> live from the Foundry IQ knowledge base."

Zoom into the **Blocked ITC** panel — the green citation cards. Let the
`section + snippet + source` show clearly on screen.

### 1:30–2:30 — Dashboard + output
> "Tax liability, ITC composition, vendor exposure, four anomalies — duplicates, a
> bad GSTIN, a future-dated invoice. Every decision is in an audit trail with its
> citation. One click downloads a filing-ready GSTR-1/3B Excel."

Scroll the reconciliation table, anomalies, audit log. Click **Download filing Excel**
and open it briefly.

### 2:30–3:00 — Before vs after (grounding vs hallucination)
> "Why does the citation matter? A raw LLM will happily invent a fake GST rule.
> TaxMind never asserts a rule without a retrieved citation — and when it's unsure,
> it tells you to consult a CA instead of guessing."

In the **Ask the GST knowledge base** box, ask:
"Can I claim ITC on a staff lunch / catering bill?" → show the cited answer.

### 3:00–3:30 — Architecture + IQ call-out
> "Under the hood: a Fabric IQ–style ontology, four agents orchestrated with the
> Microsoft Agent Framework, all grounded on Foundry IQ. It runs locally today and
> upgrades to full Azure with one config file. TaxMind prepares — a human files. No
> auto-submission, full audit trail. That's enterprise-ready, grounded AI for GST."

Show the diagram in ARCHITECTURE.md and the `mode: AZURE / knowledge: foundry-iq`
chips.

---

**Checklist before recording**
- [ ] `python scripts/generate_demo_data.py` has been run
- [ ] API + frontend running; dashboard loads
- [ ] Citation cards visible and legible
- [ ] Filing Excel downloads and opens
- [ ] Mention: GitHub Copilot used in development
