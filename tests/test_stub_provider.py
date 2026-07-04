"""Tests for the deterministic stub provider and guardrail enforcement."""
from __future__ import annotations

import pytest

from app.analyzer import apply_guardrails
from app.providers.stub import StubProvider
from app.schemas import AnalyzeInput, Suggestion

PAGE_MAP = {
    "nodes": [
        {"role": "heading", "selector": "#hero h1", "text": "Our features"},
        {"role": "cta", "selector": "#cta", "text": "Submit"},
        {"role": "testimonials", "selector": ".reviews"},
    ]
}


@pytest.mark.asyncio
async def test_stub_generates_headline_and_cta_suggestions() -> None:
    provider = StubProvider()
    result = await provider.suggest(
        AnalyzeInput(siteId="s1", pageMap=PAGE_MAP, metrics={"overview": {"conversionRate": 0.01}})
    )
    kinds = {s.kind for s in result.suggestions}
    assert "headline" in kinds
    assert "cta" in kinds
    assert "friction" in kinds  # low conversion rate triggers friction analysis
    assert 0 <= result.score <= 100
    # Deterministic: same input -> same score.
    again = await provider.suggest(
        AnalyzeInput(siteId="s1", pageMap=PAGE_MAP, metrics={"overview": {"conversionRate": 0.01}})
    )
    assert again.score == result.score


def test_guardrails_drop_banned_words() -> None:
    s = Suggestion(
        kind="headline",
        title="t",
        detail="d",
        selector="#h",
        proposed_value="Cheap guaranteed miracle",
    )
    out = apply_guardrails(s, {"bannedWords": ["guaranteed"]})
    assert out is None


def test_guardrails_truncate_to_max_length() -> None:
    s = Suggestion(
        kind="headline",
        title="t",
        detail="d",
        selector="#h",
        proposed_value="x" * 100,
    )
    out = apply_guardrails(s, {"maxLength": 20})
    assert out is not None
    assert len(out.proposed_value or "") <= 20
