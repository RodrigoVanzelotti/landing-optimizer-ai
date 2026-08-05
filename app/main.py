"""FastAPI application entrypoint for the Landing Optimizer AI service."""
from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.middleware.exceptions import HTTPException
from starlette.middleware.base import RequestResponseEndpoint
from starlette.responses import Response

from app.config import settings
from app.logging_utils import (
    Logger,
    clean_log_value,
    configure_json_logging,
    normalize_request_id,
    request_id
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
    """Add a request ID to the request state and log the request."""
    request.state.request_id = normalize_request_id(request.headers.get("x-request-id"))
    response = await call_next(request)
    response.headers["X-Request-ID"] = request.state.request_id
    return response


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Return a JSON response for validation errors."""
    correlation_id = request_id(request)
    fields = ",".join(
        ".".join(str(part) for part in item["loc"]) for item in exc.errors()[:5]
    )
    logger.warning(
        "Request failed",
        method=request.method,
        path=request.url.path,
        status_code=422,
        correlation_id=correlation_id,
        fields=fields
    )

    return JSONResponse(
        status_code=422,
        content={"error": {"code": "validation_error", "message": "Request validation failed"}},
        headers={"X-Request-ID": correlation_id},
    )


@app.exception_handler(HTTPException)
async def http_exception(request: Request, exc: HTTPException) -> JSONResponse:
    """Return a JSON response for HTTP exceptions."""
    correlation_id = request_id(request)

    logger.warning(
        "Request failed",
        method=request.method,
        path=request.url.path,
        status_code=exc.status_code,
        correlation_id=correlation_id
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": _error_code(exc.status_code), "message": str(exc.detail)}},
        headers={**(exc.headers or {}), "X-Request-ID": correlation_id},
    )



@app.exception_handler(Exception)
async def unhandled_error(request: Request, exc: Exception) -> JSONResponse:
    """Return a JSON response for unhandled exceptions."""
    correlation_id = request_id(request)
    logger.exception(
        "Unhandled exception",
        method=request.method,
        path=request.url.path,
        status_code=500,
        correlation_id=correlation_id
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
        400: "bad_request",
        401: "unauthorized",
        403: "forbidden",
        404: "not_found",
        422: "validation_error",
        500: "internal_error",
    }.get(status_code, "unknown_error")


def run() -> None:  # pragma: no cover - convenience entrypoint
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        log_config="logging.json",
        log_level=settings.log_level.lower(),
        access_log=False
    )


if __name__ == "__main__":  # pragma: no cover
    run()
