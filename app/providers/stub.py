"""Deterministic, no-network provider.

Generates brand-safe CRO suggestions from the page map + metrics using simple
heuristics. Used for local development, tests, and as a fallback when a real
LLM provider is unavailable. Fully deterministic for a given input.
"""
from __future__ import annotations

from typing import Any

from app.providers.base import LLMProvider
from app.schemas import AnalyzeInput, AnalyzeResult, ScoreInput, ScoreResult, Suggestion


class StubProvider(LLMProvider):
    name = "stub-v1"

    async def suggest(self, data: AnalyzeInput) -> AnalyzeResult:
        suggestions: list[Suggestion] = []
        nodes: list[dict[str, Any]] = data.page_map.get("nodes", []) or []
        overview = _overview(data.metrics)

        headings = [n for n in nodes if n.get("role") == "heading"]
        ctas = [n for n in nodes if n.get("role") == "cta"]

        # Headline rewrite suggestion.
        if headings:
            h = headings[0]
            suggestions.append(
                Suggestion(
                    kind="headline",
                    title="Make the headline benefit-led",
                    detail=(
                        "The primary headline reads feature-first. Lead with the outcome "
                        "the visitor gets to increase relevance and comprehension."
                    ),
                    selector=h.get("selector"),
                    original_value=h.get("text"),
                    proposed_value="Ship your landing page changes faster — no code required",
                    expected_impact="+3-8% engagement",
                    risk_level="low",
                )
            )

        # CTA clarity suggestion.
        if ctas:
            c = ctas[0]
            suggestions.append(
                Suggestion(
                    kind="cta",
                    title="Use an action + value CTA label",
                    detail=(
                        "Generic CTA copy underperforms. A specific, value-oriented label "
                        "sets expectations and lifts click-through."
                    ),
                    selector=c.get("selector"),
                    original_value=c.get("text"),
                    proposed_value="Start free — no credit card",
                    expected_impact="+2-5% CTA CTR",
                    risk_level="low",
                )
            )

        # Friction analysis from conversion rate.
        conv_rate = overview.get("conversionRate", 0.0)
        if conv_rate < 0.02:
            suggestions.append(
                Suggestion(
                    kind="friction",
                    title="Reduce above-the-fold friction",
                    detail=(
                        "Conversion rate is low. Consider trimming form fields, adding a "
                        "single primary CTA, and moving social proof higher."
                    ),
                    expected_impact="Qualitative",
                    risk_level="medium",
                )
            )

        # Always include a hypothesis + plan for reviewer context.
        suggestions.append(
            Suggestion(
                kind="hypothesis",
                title="Benefit-led hero increases signups",
                detail=(
                    "If we lead with the primary outcome in the hero headline and CTA, "
                    "then signups increase because relevance improves."
                ),
                risk_level="low",
            )
        )

        return AnalyzeResult(
            model=self.name,
            score=self._score(nodes, overview),
            suggestions=suggestions,
        )

    async def score(self, data: ScoreInput) -> ScoreResult:
        nodes = data.page_map.get("nodes", []) or []
        overview = _overview(data.metrics)
        score = self._score(nodes, overview)
        return ScoreResult(
            score=score,
            factors={
                "hasHero": any(n.get("role") == "hero" for n in nodes),
                "hasCta": any(n.get("role") == "cta" for n in nodes),
                "hasSocialProof": any(n.get("role") == "testimonials" for n in nodes),
                "conversionRate": overview.get("conversionRate", 0.0),
            },
        )

    @staticmethod
    def _score(nodes: list[dict[str, Any]], overview: dict[str, Any]) -> int:
        roles = {n.get("role") for n in nodes}
        base = 40
        for role, pts in (("hero", 15), ("cta", 15), ("testimonials", 10), ("faq", 5)):
            if role in roles:
                base += pts
        if overview.get("conversionRate", 0.0) > 0.03:
            base += 10
        return max(0, min(100, base))


def _overview(metrics: dict[str, Any]) -> dict[str, Any]:
    ov = metrics.get("overview")
    return ov if isinstance(ov, dict) else {}
