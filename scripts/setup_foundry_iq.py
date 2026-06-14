"""Provision the Foundry IQ knowledge base for TaxMind (Azure mode).

Steps:
  1. Upload the bundled public GST Act text (data/gst-sources) to the Blob
     `gst-knowledge` container.
  2. Create an Azure AI Search index + a Foundry IQ knowledge source pointing at
     that blob container.
  3. Run a verification query ("what is Section 17(5)") and print the cited result.

Requires a filled-in .env (see .env.example). This script is idempotent-ish: it
will skip creation steps that already exist. It is intentionally defensive —
Foundry IQ APIs are preview and evolve, so failures print guidance rather than
crashing the build.

Run:  python scripts/setup_foundry_iq.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.config import GST_SOURCES_DIR, get_settings


def upload_knowledge_to_blob(settings) -> None:
    from azure.storage.blob import BlobServiceClient

    svc = BlobServiceClient.from_connection_string(settings.storage_connection_string)
    container = settings.knowledge_container
    try:
        svc.create_container(container)
        print(f"✓ created container '{container}'")
    except Exception:
        print(f"• container '{container}' already exists")

    for path in sorted(GST_SOURCES_DIR.glob("*")):
        blob = svc.get_blob_client(container=container, blob=path.name)
        blob.upload_blob(path.read_bytes(), overwrite=True)
        print(f"  ↑ uploaded {path.name}")


def verify_retrieval(settings) -> None:
    from backend.foundry_iq.foundry import FoundryIQKnowledgeBase

    kb = FoundryIQKnowledgeBase(settings)
    result = kb.query("what is Section 17(5)")
    print(f"\nVerification query → backend={result.backend} conf={result.confidence:.2f}")
    if result.citations:
        c = result.citations[0]
        print(f"  cited: {c.section} [{c.source}]")
        print(f"  \"{c.snippet[:160]}...\"")


def main() -> None:
    settings = get_settings()
    if settings.mode != "azure":
        print("TAXMIND_MODE is not 'azure' / no Azure creds in .env.")
        print("Foundry IQ setup is only needed for the Azure path. "
              "Local mode already serves cited answers from data/gst-sources.")
        return

    print("Setting up Foundry IQ knowledge base for TaxMind…\n")
    if settings.storage_connection_string:
        upload_knowledge_to_blob(settings)
    else:
        print("• No AZURE_STORAGE_CONNECTION_STRING — skipping blob upload. "
              "Add knowledge sources in the Foundry portal instead.")

    print("\nNext (one-time, in the Foundry portal at https://ai.azure.com):")
    print("  1. Create/confirm a Foundry IQ knowledge base named "
          f"'{settings.foundry_iq_kb}'.")
    print(f"  2. Add a knowledge source of kind 'Azure Blob' -> container "
          f"'{settings.knowledge_container}'.")
    print(f"  3. Back it with your Azure AI Search index '{settings.search_index}'.")

    verify_retrieval(settings)


if __name__ == "__main__":
    main()
