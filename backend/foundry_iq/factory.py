"""Selects the knowledge-base backend based on runtime mode."""

from __future__ import annotations

from functools import lru_cache

from backend.config import get_settings
from backend.foundry_iq.base import KnowledgeBase


@lru_cache(maxsize=1)
def get_knowledge_base() -> KnowledgeBase:
    settings = get_settings()
    if settings.use_foundry_iq:
        from backend.foundry_iq.foundry import FoundryIQKnowledgeBase

        return FoundryIQKnowledgeBase(settings)
    from backend.foundry_iq.local import LocalKnowledgeBase

    return LocalKnowledgeBase()
