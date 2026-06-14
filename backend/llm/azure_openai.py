"""Azure OpenAI column mapper (Azure mode).

Feeds the messy headers + a few sample rows to GPT-4o and asks for a strict JSON
mapping onto the ontology fields. Falls back to the deterministic mapper if the
SDK is unavailable or the call fails, so the pipeline never hard-stops.
"""

from __future__ import annotations

import json

from backend.config import Settings
from backend.llm.base import LLMClient
from backend.llm.rule_based import RuleBasedLLM


class AzureOpenAIChat(LLMClient):
    name = "azure-openai"

    def __init__(self, settings: Settings) -> None:
        self._s = settings
        self._fallback = RuleBasedLLM()
        self._client = None
        try:
            from openai import AzureOpenAI

            self._client = AzureOpenAI(
                azure_endpoint=settings.azure_openai_endpoint,
                api_key=settings.azure_openai_key,
                api_version=settings.azure_openai_api_version,
            )
        except Exception:
            self._client = None

    def map_columns(
        self,
        headers: list[str],
        sample_rows: list[dict],
        target_fields: dict[str, str],
    ) -> dict[str, str | None]:
        if self._client is None:
            return self._fallback.map_columns(headers, sample_rows, target_fields)

        fields_desc = "\n".join(f"- {k}: {v}" for k, v in target_fields.items())
        prompt = (
            "You map messy spreadsheet columns (English or Hindi) from an Indian "
            "GST register onto a fixed business ontology. Return ONLY a JSON object "
            "mapping each ontology field to the exact source header that best fits, "
            "or null if none fits.\n\n"
            f"Ontology fields:\n{fields_desc}\n\n"
            f"Source headers: {json.dumps(headers, ensure_ascii=False)}\n\n"
            f"Sample rows: {json.dumps(sample_rows[:3], ensure_ascii=False, default=str)}"
        )
        try:
            resp = self._client.chat.completions.create(
                model=self._s.azure_openai_deployment,
                messages=[
                    {"role": "system", "content": "You output strict JSON only."},
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0,
            )
            raw = json.loads(resp.choices[0].message.content)
            # keep only known fields + headers that actually exist
            return {
                f: (raw.get(f) if raw.get(f) in headers else None)
                for f in target_fields
            }
        except Exception:
            return self._fallback.map_columns(headers, sample_rows, target_fields)
