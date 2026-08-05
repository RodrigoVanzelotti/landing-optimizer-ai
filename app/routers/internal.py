"""Internal AI endpoints consumed by the control-plane API."""
from __future__ import annotations

from time import perf_counter

from fastapi import APIRouter, Depends, Request

from app.analyzer import analyze, get_provider
from app.auth import require_internal_token
from app.schemas import AnalyzeInput, AnalyzeResult, ScoreInput, ScoreResult
from app.logging_utils import Logger, request_id, clean_log_value


router = APIRouter(prefix="/internal", tags=["internal"])
logger = Logger(__name__)

@router.post(
    "/analyze",
    response_model=AnalyzeResult,
    dependencies=[Depends(require_internal_token)],
)
async def analyze_endpoint(payload: AnalyzeInput, request: Request) -> AnalyzeResult:
    started = perf_counter()
    result = await analyze(payload)
    logger.info(
        "analyze_succeeded",
        site_id=payload.site_id,
        model=result.model,
        suggestions=len(result.suggestions),
        score=result.score,
        correlation_id=request_id(request),
        duration_ms=round((perf_counter() - started) * 1000),
    )
    return result


@router.post(
    "/score",
    response_model=ScoreResult,
    dependencies=[Depends(require_internal_token)],
)
async def score_endpoint(payload: ScoreInput, request: Request) -> ScoreResult:
    started = perf_counter()
    provider = get_provider()
    result = await provider.score(payload)

    logger.info(
        "score_succeeded",
        provider=provider.name,
        score=result.score,
        duration_ms=round((perf_counter() - started) * 1000),
        request_id=request_id(request),
    )

    return result   