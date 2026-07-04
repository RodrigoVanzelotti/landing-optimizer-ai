"""OpenAI-compatible LLM provider.

Works with any endpoint that implements the OpenAI Chat Completions API
(OpenAI, Azure OpenAI, local gateways, etc.). Requests a strict JSON response,
parses it into structured suggestions, and falls back to the stub provider on
any failure so the service degrades gracefully.
"""
from __future__ import annotations

import json
import logging

import httpx

from app.providers.base import LLMProvider
from app.providers.stub import StubProvider
from app.schemas import AnalyzeInput, AnalyzeResult, ScoreInput, ScoreResult, Suggestion

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a senior conversion-rate-optimization (CRO) expert. You analyze a "
    "sanitized landing page structure and aggregate metrics and propose safe, "
    "brand-consistent experiments. You NEVER invent PII. You respect the brand "
    "guardrails provided. Respond ONLY with strict JSON matching the requested "
    "schema. Do not auto-publish; these are suggestions for human review."
)


class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str, base_url: str, model: str) -> None:
        self.name = model
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._fallback = StubProvider()

    async def suggest(self, data: AnalyzeInput) -> AnalyzeResult:
        user_prompt = self._build_prompt(data)
        try:
            content = await self._complete(user_prompt)
            parsed = json.loads(content)
            suggestions = [Suggestion(**s) for s in parsed.get("suggestions", [])]
            if not suggestions:
                raise ValueError("no suggestions returned")
            return AnalyzeResult(
                model=self._model,
                score=int(parsed.get("score", 50)),
                suggestions=suggestions,
            )
        except Exception as exc:  # noqa: BLE001 - degrade gracefully
            logger.warning("OpenAI provider failed, using stub: %s", exc)
            return await self._fallback.suggest(data)

    async def score(self, data: ScoreInput) -> ScoreResult:
        # Scoring uses the deterministic heuristic to stay cheap and stable.
        return await self._fallback.score(data)

    async def _complete(self, user_prompt: str) -> str:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(
                f"{self._base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self._api_key}"},
                json={
                    "model": self._model,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt},
                    ],
                    "response_format": {"type": "json_object"},
                    "temperature": 0.4,
                },
            )
            resp.raise_for_status()
            body = resp.json()
            return body["choices"][0]["message"]["content"]

    @staticmethod
    def _build_prompt(data: AnalyzeInput) -> str:
        schema = {
            "score": "integer 0-100",
            "suggestions": [
                {
                    "kind": "headline|cta|hypothesis|friction|section|plan",
                    "title": "string",
                    "detail": "string",
                    "selector": "css selector or null",
                    "proposed_value": "string or null",
                    "original_value": "string or null",
                    "expected_impact": "string or null",
                    "risk_level": "low|medium|high",
                }
            ],
        }
        return (
            "Analyze this landing page and return CRO suggestions.\n\n"
            f"PAGE_MAP:\n{json.dumps(data.page_map)[:6000]}\n\n"
            f"METRICS:\n{json.dumps(data.metrics)[:3000]}\n\n"
            f"BRAND_GUARDRAILS:\n{json.dumps(data.guardrails)[:2000]}\n\n"
            f"Respond ONLY with JSON of this shape:\n{json.dumps(schema)}"
        )
