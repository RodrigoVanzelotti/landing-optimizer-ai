"""Internal AI endpoints consumed by the control-plane API."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.analyzer import analyze, get_provider
from app.auth import require_internal_token
from app.schemas import AnalyzeInput, AnalyzeResult, ScoreInput, ScoreResult

router = APIRouter(prefix="/internal", tags=["internal"])


@router.post(
    "/analyze",
    response_model=AnalyzeResult,
    dependencies=[Depends(require_internal_token)],
)
async def analyze_endpoint(payload: AnalyzeInput) -> AnalyzeResult:
    return await analyze(payload)


@router.post(
    "/score",
    response_model=ScoreResult,
    dependencies=[Depends(require_internal_token)],
)
async def score_endpoint(payload: ScoreInput) -> ScoreResult:
    return await get_provider().score(payload)
