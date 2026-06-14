"""Foundry IQ knowledge base adapter (Azure mode).

Primary path uses the official ``azure-search-documents`` Foundry IQ client
(``KnowledgeBaseRetrievalClient`` — agentic retrieval) against a knowledge base you
create in the Foundry portal. Maps the response onto the same
:class:`KnowledgeResult` shape the rest of TaxMind expects, so nothing upstream
changes between local and Azure modes.

Resilience: if the SDK isn't importable or a live call fails, it degrades to the
local knowledge base rather than guessing — keeping a live demo robust.
"""

from __future__ import annotations

from backend.config import Settings
from backend.foundry_iq.base import KnowledgeBase, KnowledgeResult
from backend.foundry_iq.local import LocalKnowledgeBase
from backend.ontology.entities import Citation


class FoundryIQKnowledgeBase(KnowledgeBase):
    name = "foundry-iq"

    def __init__(self, settings: Settings) -> None:
        self._s = settings
        self._fallback = LocalKnowledgeBase()
        self._client = None
        self._models = None
        try:
            from azure.core.credentials import AzureKeyCredential
            from azure.search.documents.knowledgebases import (
                KnowledgeBaseRetrievalClient,
            )
            from azure.search.documents.knowledgebases import models as kb_models

            endpoint = settings.foundry_iq_endpoint or settings.search_endpoint
            if endpoint and settings.search_key:
                self._client = KnowledgeBaseRetrievalClient(
                    endpoint=endpoint,
                    knowledge_base_name=settings.foundry_iq_kb,
                    credential=AzureKeyCredential(settings.search_key),
                )
                self._models = kb_models
        except Exception:
            self._client = None

    def query(self, question: str, top_k: int = 3) -> KnowledgeResult:
        if self._client is None:
            res = self._fallback.query(question, top_k=top_k)
            res.backend = "foundry_iq(fallback:local)"
            return res
        try:
            return self._retrieve(question, top_k)
        except Exception:
            res = self._fallback.query(question, top_k=top_k)
            res.backend = "foundry_iq(fallback:local)"
            return res

    def _retrieve(self, question: str, top_k: int) -> KnowledgeResult:
        m = self._models
        request = m.KnowledgeBaseRetrievalRequest(
            messages=[
                m.KnowledgeBaseMessage(
                    role="user",
                    content=[m.KnowledgeBaseMessageTextContent(text=question)],
                )
            ],
            include_activity=True,
        )
        resp = self._client.retrieve(retrieval_request=request)
        answer = _extract_answer(resp)
        citations = _extract_citations(resp, top_k)
        confidence = max((c.confidence for c in citations), default=0.5 if answer else 0.0)
        return KnowledgeResult(
            question=question,
            answer=answer or "No grounded answer returned by Foundry IQ.",
            citations=citations,
            confidence=min(1.0, confidence),
            backend="foundry_iq",
        )


def _extract_answer(resp) -> str:
    parts: list[str] = []
    for msg in getattr(resp, "response", None) or []:
        content = getattr(msg, "content", None)
        if isinstance(content, str):
            parts.append(content)
        elif isinstance(content, list):
            for item in content:
                txt = getattr(item, "text", None)
                if txt:
                    parts.append(txt)
    return "\n".join(parts).strip()


def _extract_citations(resp, top_k: int) -> list[Citation]:
    citations: list[Citation] = []
    for ref in (getattr(resp, "references", None) or [])[:top_k]:
        data = getattr(ref, "source_data", None) or {}
        if not isinstance(data, dict):
            data = {}
        snippet = data.get("content") or data.get("text") or data.get("chunk") or ""
        section = (
            data.get("section")
            or data.get("title")
            or data.get("source")
            or "GST reference"
        )
        score = getattr(ref, "reranker_score", None) or 0.0
        citations.append(
            Citation(
                section=str(section),
                snippet=str(snippet)[:320],
                source=str(data.get("source") or data.get("filepath") or "Foundry IQ"),
                confidence=min(1.0, float(score) / 4.0) if score else 0.5,
            )
        )
    return citations
