"""Central configuration + provider-mode auto-detection for TaxMind.

TaxMind runs in one of two modes:

* ``azure``  — uses real Azure OpenAI + Foundry IQ (Azure AI Search) + Blob.
* ``local``  — uses bundled GST Act text + deterministic rule-based reasoning,
               so the whole pipeline runs with **no keys** for development and
               the deadline-day demo.

The mode is taken from ``TAXMIND_MODE`` if set, otherwise auto-detected from the
presence of the Azure OpenAI credentials. This single switch is what lets the
exact same agent/orchestration code light up the real Foundry IQ path the moment
a ``.env`` is filled in.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

try:  # optional dependency — local mode must work even if it is missing
    from dotenv import load_dotenv

    load_dotenv()
except Exception:  # pragma: no cover - dotenv is in requirements but be defensive
    pass


# Repo paths -------------------------------------------------------------------
ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
GST_SOURCES_DIR = DATA_DIR / "gst-sources"
SYNTHETIC_DIR = DATA_DIR / "synthetic"
OUTPUT_DIR = ROOT_DIR / "output"


def _has_azure_openai() -> bool:
    return bool(os.getenv("AZURE_OPENAI_ENDPOINT") and os.getenv("AZURE_OPENAI_KEY"))


def _has_foundry_iq() -> bool:
    # Foundry IQ retrieval is served by Azure AI Search; either endpoint works.
    return bool(
        os.getenv("AZURE_SEARCH_ENDPOINT") and os.getenv("AZURE_SEARCH_KEY")
    ) or bool(os.getenv("FOUNDRY_IQ_ENDPOINT"))


@dataclass(frozen=True)
class Settings:
    mode: str  # "azure" | "local"

    # Azure OpenAI
    azure_openai_endpoint: str | None
    azure_openai_key: str | None
    azure_openai_api_version: str
    azure_openai_deployment: str

    # Azure AI Search / Foundry IQ
    search_endpoint: str | None
    search_key: str | None
    search_index: str
    foundry_iq_endpoint: str | None
    foundry_iq_kb: str
    foundry_iq_api_version: str

    # Blob
    storage_connection_string: str | None
    uploads_container: str
    knowledge_container: str

    @property
    def use_azure_llm(self) -> bool:
        return self.mode == "azure" and _has_azure_openai()

    @property
    def use_foundry_iq(self) -> bool:
        return self.mode == "azure" and _has_foundry_iq()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    forced = (os.getenv("TAXMIND_MODE") or "").strip().lower()
    if forced in {"azure", "local"}:
        mode = forced
    else:
        mode = "azure" if _has_azure_openai() else "local"

    return Settings(
        mode=mode,
        azure_openai_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        azure_openai_key=os.getenv("AZURE_OPENAI_KEY"),
        azure_openai_api_version=os.getenv(
            "AZURE_OPENAI_API_VERSION", "2024-08-01-preview"
        ),
        azure_openai_deployment=os.getenv(
            "AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini-dev"
        ),
        search_endpoint=os.getenv("AZURE_SEARCH_ENDPOINT"),
        search_key=os.getenv("AZURE_SEARCH_KEY"),
        search_index=os.getenv("AZURE_SEARCH_INDEX", "gst-knowledge"),
        foundry_iq_endpoint=os.getenv("FOUNDRY_IQ_ENDPOINT"),
        foundry_iq_kb=os.getenv("FOUNDRY_IQ_KNOWLEDGE_BASE", "taxmind-gst-kb"),
        foundry_iq_api_version=os.getenv(
            "FOUNDRY_IQ_API_VERSION", "2026-05-01-preview"
        ),
        storage_connection_string=os.getenv("AZURE_STORAGE_CONNECTION_STRING"),
        uploads_container=os.getenv("AZURE_STORAGE_UPLOADS_CONTAINER", "uploads"),
        knowledge_container=os.getenv(
            "AZURE_STORAGE_KNOWLEDGE_CONTAINER", "gst-knowledge"
        ),
    )
