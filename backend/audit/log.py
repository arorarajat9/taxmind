"""Audit log — every compliance decision with its grounded source.

The build plan calls this out explicitly: judges (and CAs) want to see *why* each
flag was raised and the exact GST Act text behind it. Each entry carries the
decision, the agent that made it, and the citation returned by the knowledge base.
"""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field

from backend.ontology.entities import Citation


class AuditEntry(BaseModel):
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    agent: str
    entity_ref: str
    decision: str
    rationale: str = ""
    citation: Citation | None = None
    confident: bool = True


class AuditLog(BaseModel):
    entries: list[AuditEntry] = []

    def record(
        self,
        agent: str,
        entity_ref: str,
        decision: str,
        rationale: str = "",
        citation: Citation | None = None,
        confident: bool = True,
    ) -> None:
        self.entries.append(
            AuditEntry(
                agent=agent,
                entity_ref=entity_ref,
                decision=decision,
                rationale=rationale,
                citation=citation,
                confident=confident,
            )
        )

    @property
    def cited_count(self) -> int:
        return sum(1 for e in self.entries if e.citation is not None)
