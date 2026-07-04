"""Provider selection and brand-guardrail enforcement."""
from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any

from app.config import settings
from app.providers.base import LLMProvider
from app.providers.openai_provider import OpenAIProvider
from app.providers.stub import StubProvider
from app.schemas import AnalyzeInput, AnalyzeResult, Suggestion

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_provider() -> LLMProvider:
    if settings.llm_provider == "openai" and settings.openai_api_key:
        logger.info("Using OpenAI provider model=%s", settings.openai_model)
        return OpenAIProvider(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
            model=settings.openai_model,
        )
    logger.info("Using stub provider")
    return StubProvider()


async def analyze(data: AnalyzeInput) -> AnalyzeResult:
    provider = get_provider()
    result = await provider.suggest(data)
    result.suggestions = [
        s for s in (apply_guardrails(s, data.guardrails) for s in result.suggestions) if s
    ]
    return result


def apply_guardrails(suggestion: Suggestion, guardrails: dict[str, Any]) -> Suggestion | None:
    """Enforce brand guardrails. Drops suggestions that violate hard rules and
    trims proposed copy to configured limits."""
    if not guardrails:
        return suggestion

    banned = {w.lower() for w in guardrails.get("bannedWords", []) if isinstance(w, str)}
    max_len = guardrails.get("maxLength")

    if suggestion.proposed_value:
        lowered = suggestion.proposed_value.lower()
        if any(word in lowered for word in banned):
            logger.info("Dropping suggestion violating banned-words guardrail")
            return None
        if isinstance(max_len, int) and len(suggestion.proposed_value) > max_len:
            suggestion.proposed_value = suggestion.proposed_value[:max_len].rstrip()

    return suggestion
