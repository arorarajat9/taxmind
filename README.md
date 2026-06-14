# TaxMind

**AI agent that reads messy Excel sheets, reconciles input tax credit, flags risky invoices with cited GST Act references, and generates GSTR-1 and GSTR-3B ready summaries for Indian small businesses.**

> Built for the Microsoft Agents League hackathon — Enterprise Agents track.
> Grounded on **Foundry IQ** (knowledge base + agentic retrieval) with a
> **Fabric IQ-style business ontology**.

Full documentation lands in this file as the build completes. See
[ARCHITECTURE.md](ARCHITECTURE.md) for the system design and
[the build plan](#) for the roadmap.

## ⚠️ Disclaimer
TaxMind **assists** with GST filing preparation. It does **not** auto-submit to
the GSTN portal — a human reviews and files. Every compliance flag is backed by a
cited GST Act reference. Verify against the latest CBIC bare act and consult a
qualified CA before filing.
