"""Foundry IQ knowledge base adapter (Azure mode).

Calls Foundry IQ agentic retrieval (served by Azure AI Search) and maps the
response onto the same :class:`KnowledgeResult` shape the rest of TaxMind expects.
Uses only the standard library for the HTTP call so the local-mode install stays
dependency-light; the request shape follows the ``2026-05-01-preview`` agentic
retrieval contract.

This path activates automatically when ``TAXMIND_MODE=azure`` and search creds are
present. If a call fails it degrades to the local KB rather than guessing, which
keeps the demo resilient.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request

from backend.config import Settings
from backend.foundry_iq.base import KnowledgeBase, KnowledgeResult
from backend.foundry_iq.local import LocalKnowledgeBase
from backend.ontology.entities import Citation


class FoundryIQKnowledgeBase(KnowledgeBase):
    name = "foundry-iq"

    def __init__(self, settings: Settings) -> None:
        self._s = settings
        # Local KB is the graceful fallback if a live call fails mid-demo.
        self._fallback = LocalKnowledgeBase()

    def _endpoint(self) -> str:
        base = (self._s.foundry_iq_endpoint or self._s.search_endpoint or "").rstrip("/")
        return (
            f"{base}/knowledgeBases/{self._s.foundry_iq_kb}/retrieve"
            f"?api-version={self._s.foundry_iq_api_version}"
        )

    def query(self, question: str, top_k: int = 3) -> KnowledgeResult:
        payload = {
            "messages": [
                {"role": "user", "content": [{"type": "text", "text": question}]}
            ],
            "knowledgeSourceParams": [
                {"knowledgeSourceName": self._s.search_index, "kind": "searchIndex"}
            ],
            "rerankerThreshold": 1.5,
        }
        req = urllib.request.Request(
            self._endpoint(),
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "api-key": self._s.search_key or "",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            return self._parse(question, data)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, KeyError):
            # Resilience over silence: fall back to local grounding.
            result = self._fallback.query(question, top_k=top_k)
            result.backend = "foundry_iq(fallback:local)"
            return result

    def _parse(self, question: str, data: dict) -> KnowledgeResult:
        # Agentic retrieval returns a grounded "response" plus "references".
        answer = ""
        resp = data.get("response")
        if isinstance(resp, list) and resp:
            content = resp[0].get("content")
            if isinstance(content, list) and content:
                answer = content[0].get("text", "")
            elif isinstance(content, str):
                answer = content

        citations: list[Citation] = []
        for ref in data.get("references", [])[:5]:
            src = ref.get("sourceData", {}) if isinstance(ref, dict) else {}
            citations.append(
                Citation(
                    section=src.get("section") or src.get("title") or "GST reference",
                    snippet=(src.get("content") or src.get("text") or "")[:320],
                    source=src.get("source") or "Foundry IQ",
                    confidence=float(ref.get("rerankerScore", 0) or 0) / 4.0,
                )
            )
        confidence = max((c.confidence for c in citations), default=0.5 if answer else 0.0)
        return KnowledgeResult(
            question=question,
            answer=answer or "No grounded answer returned by Foundry IQ.",
            citations=citations,
            confidence=min(1.0, confidence),
            backend="foundry_iq",
        )
