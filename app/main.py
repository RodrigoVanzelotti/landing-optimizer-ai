"""FastAPI application entrypoint for the Landing Optimizer AI service."""
from __future__ import annotations

import logging

from fastapi import FastAPI

from app.config import settings
from app.routers.internal import router as internal_router

logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="Landing Optimizer AI",
    version="0.1.0",
    description="CRO suggestion generation with an LLM provider abstraction.",
)

app.include_router(internal_router)


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    return {"status": "ok", "provider": settings.llm_provider}


def run() -> None:  # pragma: no cover - convenience entrypoint
    import uvicorn

    uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=True)


if __name__ == "__main__":  # pragma: no cover
    run()
