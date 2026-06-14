"""Knowledge base interface — the seam between local retrieval and Foundry IQ.

Both implementations return the identical :class:`KnowledgeResult` shape so that
agents, the audit log, and the frontend never need to know which backend served
the answer. Swapping ``local`` → ``azure`` lights up real Foundry IQ agentic
retrieval with zero changes upstream.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from pydantic import BaseModel

from backend.ontology.entities import Citation

# Below this retrieval confidence the agents must defer to a human ("consult a
# CA") instead of asserting a compliance decision. This is the Reliability/Safety
# guardrail called out in the build plan.
CONFIDENCE_FLOOR = 0.35


class KnowledgeResult(BaseModel):
    question: str
    answer: str
    citations: list[Citation] = []
    confidence: float = 0.0
    backend: str = "local"  # "local" | "foundry_iq"

    @property
    def is_confident(self) -> bool:
        return self.confidence >= CONFIDENCE_FLOOR


class KnowledgeBase(ABC):
    """A grounded GST knowledge source."""

    name: str = "knowledge-base"

    @abstractmethod
    def query(self, question: str, top_k: int = 3) -> KnowledgeResult:
        """Return a grounded, cited answer for a GST compliance question."""
        raise NotImplementedError
