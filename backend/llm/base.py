"""LLM client interface.

The only LLM-shaped task in TaxMind's critical path is mapping arbitrary, messy
spreadsheet headers onto the Fabric IQ ontology fields. The Azure path uses
GPT-4o; the local path uses a deterministic synonym matcher so the demo is
reproducible and key-free. Both return the same ``{ontology_field: source_header}``
mapping.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class LLMClient(ABC):
    name: str = "llm"

    @abstractmethod
    def map_columns(
        self,
        headers: list[str],
        sample_rows: list[dict],
        target_fields: dict[str, str],
    ) -> dict[str, str | None]:
        """Map each ontology field -> best matching source header (or None).

        ``target_fields`` is ``{ontology_field: human description}``.
        """
        raise NotImplementedError
