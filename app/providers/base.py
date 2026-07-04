"""LLM provider abstraction.

The service is provider-agnostic: any OpenAI-compatible endpoint or a
deterministic stub can be swapped in via configuration. Providers return
already-structured suggestions so the rest of the service is uniform.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from app.schemas import AnalyzeInput, AnalyzeResult, ScoreInput, ScoreResult


class LLMProvider(ABC):
    name: str

    @abstractmethod
    async def suggest(self, data: AnalyzeInput) -> AnalyzeResult:
        """Generate CRO suggestions for a landing page."""

    @abstractmethod
    async def score(self, data: ScoreInput) -> ScoreResult:
        """Produce a landing page score with contributing factors."""
