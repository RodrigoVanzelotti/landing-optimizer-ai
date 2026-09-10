"""FastAPI application entrypoint for the Landing Optimizer AI service."""
from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException
from starlette.middleware.base import RequestResponseEndpoint
from starlette.responses import Response

from app.config import settings
from app.logging_utils import (
    Logger,
    clean_log_value,
    configure_json_logging,
    normalize_request_id,
    request_id,
)
from app.routers.internal import router as internal_router

log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
configure_json_logging(log_level)
logger = Logger(__name__)

app = FastAPI(
    title="Landing Optimizer AI",
    version="0.1.0",
    description="CRO suggestion generation with an LLM provider abstraction.",
)

app.include_router(internal_router)


@app.middleware("http")
async def correlate_request(request: Request, call_next: RequestResponseEndpoint) -> Response:
    request.state.request_id = normalize_request_id(request.headers.get("x-request-id"))
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id(request)
    return response


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, error: RequestValidationError) -> JSONResponse:
    correlation_id = request_id(request)
    fields = ",".join(
        ".".join(str(part) for part in item["loc"])
        for item in error.errors()[:5]
    )
    logger.warn(
        "request_failed",
        method=request.method,
        path=clean_log_value(request.url.path),
        status=422,
        reason="validation_error",
        fields=fields,
        request_id=correlation_id,
    )
    return JSONResponse(
        status_code=422,
        content={"error": {"code": "validation_error", "message": "Request validation failed"}},
        headers={"X-Request-ID": correlation_id},
    )


@app.exception_handler(HTTPException)
async def http_error(request: Request, error: HTTPException) -> JSONResponse:
    correlation_id = request_id(request)
    reason = clean_log_value(str(error.detail))
    logger.warn(
        "request_failed",
        method=request.method,
        path=clean_log_value(request.url.path),
        status=error.status_code,
        reason=reason,
        request_id=correlation_id,
    )
    return JSONResponse(
        status_code=error.status_code,
        content={"error": {"code": _error_code(error.status_code), "message": str(error.detail)}},
        headers={**(error.headers or {}), "X-Request-ID": correlation_id},
    )


@app.exception_handler(Exception)
async def unhandled_error(request: Request, error: Exception) -> JSONResponse:
    correlation_id = request_id(request)
    logger.exception(
        "request_failed",
        error,
        method=request.method,
        path=clean_log_value(request.url.path),
        status=500,
        request_id=correlation_id,
    )
    return JSONResponse(
        status_code=500,
        content={"error": {"code": "internal_error", "message": "Internal server error"}},
        headers={"X-Request-ID": correlation_id},
    )


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    return {"status": "ok", "provider": settings.llm_provider}


def _error_code(status_code: int) -> str:
    return {
        401: "unauthenticated",
        403: "forbidden",
        404: "not_found",
        429: "rate_limited",
    }.get(status_code, "request_error")


def run() -> None:  # pragma: no cover - convenience entrypoint
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=True,
        access_log=False,
        log_config="logging.json",
    )


if __name__ == "__main__":  # pragma: no cover
    run()
