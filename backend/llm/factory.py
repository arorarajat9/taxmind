"""Selects the LLM client based on runtime mode."""

from __future__ import annotations

from functools import lru_cache

from backend.config import get_settings
from backend.llm.base import LLMClient


@lru_cache(maxsize=1)
def get_llm_client() -> LLMClient:
    settings = get_settings()
    if settings.use_azure_llm:
        from backend.llm.azure_openai import AzureOpenAIChat

        return AzureOpenAIChat(settings)
    from backend.llm.rule_based import RuleBasedLLM

    return RuleBasedLLM()
