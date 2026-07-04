"""Request/response schemas for the AI service (mirrors API AiClient types)."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

SuggestionKind = Literal[
    "hypothesis", "headline", "cta", "friction", "section", "score", "plan"
]
RiskLevel = Literal["low", "medium", "high"]


class AnalyzeInput(BaseModel):
    site_id: str = Field(alias="siteId")
    page_map: dict[str, Any] = Field(default_factory=dict, alias="pageMap")
    metrics: dict[str, Any] = Field(default_factory=dict)
    guardrails: dict[str, Any] = Field(default_factory=dict)

    model_config = {"populate_by_name": True}


class Suggestion(BaseModel):
    kind: SuggestionKind
    title: str
    detail: str
    selector: str | None = None
    proposed_value: str | None = Field(default=None, serialization_alias="proposedValue")
    original_value: str | None = Field(default=None, serialization_alias="originalValue")
    expected_impact: str | None = Field(default=None, serialization_alias="expectedImpact")
    risk_level: RiskLevel = Field(default="low", serialization_alias="riskLevel")

    model_config = {"populate_by_name": True}


class AnalyzeResult(BaseModel):
    model: str
    score: int
    suggestions: list[Suggestion]


class ScoreInput(BaseModel):
    page_map: dict[str, Any] = Field(default_factory=dict, alias="pageMap")
    metrics: dict[str, Any] = Field(default_factory=dict)

    model_config = {"populate_by_name": True}


class ScoreResult(BaseModel):
    score: int
    factors: dict[str, Any]
