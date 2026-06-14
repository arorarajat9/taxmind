"""Azure stack smoke test — run after provisioning, before the build relies on it.

Proves Azure OpenAI + Azure AI Search are alive with your .env credentials.
Run:  python scripts/smoke_test.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv()


def test_openai() -> bool:
    try:
        from openai import AzureOpenAI

        client = AzureOpenAI(
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_key=os.getenv("AZURE_OPENAI_KEY"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-08-01-preview"),
        )
        resp = client.chat.completions.create(
            model=os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini-dev"),
            messages=[{"role": "user", "content": "Say 'TaxMind is ready' in exactly 4 words."}],
        )
        print("✓ Azure OpenAI:", resp.choices[0].message.content)
        return True
    except Exception as e:
        print("✗ Azure OpenAI failed:", e)
        return False


def test_search() -> bool:
    try:
        from azure.core.credentials import AzureKeyCredential
        from azure.search.documents.indexes import SearchIndexClient

        client = SearchIndexClient(
            endpoint=os.getenv("AZURE_SEARCH_ENDPOINT"),
            credential=AzureKeyCredential(os.getenv("AZURE_SEARCH_KEY")),
        )
        names = list(client.list_index_names())
        print(f"✓ Azure AI Search reachable — {len(names)} indexes: {names}")
        return True
    except Exception as e:
        print("✗ Azure AI Search failed:", e)
        return False


def main() -> None:
    if not os.getenv("AZURE_OPENAI_ENDPOINT"):
        print("No Azure credentials in .env — TaxMind will run in LOCAL mode. "
              "Fill .env (see .env.example) to test the Azure stack.")
        return
    ok = test_openai() & test_search()
    print("\nStack is alive ✅" if ok else "\nSome checks failed — see above.")


if __name__ == "__main__":
    main()
