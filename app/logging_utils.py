<<<<<<< HEAD
"""Small helpers for safe, correlated production logs."""
=======
>>>>>>> ba6f3864424e2937b072900aebb3e904e1bc5200
from __future__ import annotations

import json
import logging
import re
<<<<<<< HEAD
from datetime import UTC, datetime
from threading import Lock
from types import TracebackType
=======
from threading import Lock
from types import TracebackType
from datetime import UTC, datetime
>>>>>>> ba6f3864424e2937b072900aebb3e904e1bc5200
from typing import Any
from uuid import uuid4

from fastapi import Request

_REQUEST_ID = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
_STANDARD_RECORD_FIELDS = frozenset(
<<<<<<< HEAD
    logging.LogRecord("", 0, "", 0, "", (), None).__dict__
) | {"message", "asctime"}


class JsonFormatter(logging.Formatter):
    """Serialize every log record as one queryable JSON object."""

    def format(self, record: logging.LogRecord) -> str:
        output: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
            "level": record.levelname.lower(),
            "service": "landing-optimizer-ai",
            "logger": record.name,
        }
        event = getattr(record, "event", None)
        if event is not None:
            output["event"] = clean_log_value(str(event), 128)
        else:
            output["message"] = clean_log_value(record.getMessage(), 2000)

        for key, value in record.__dict__.items():
            if key in _STANDARD_RECORD_FIELDS or key == "event" or key.startswith("_"):
                continue
            output[key] = _json_value(value)

        if record.exc_info:
            output["exception"] = clean_log_value(
                self.formatException(record.exc_info),
                8000,
            )
        return json.dumps(output, ensure_ascii=False, separators=(",", ":"))


class Logger:
    """Cached module logger with structured JSON event methods."""
=======
    logging.LogRecord("", 0, "", 0, "", (), None).__dict__.keys()
) | {"message", "asctime"}


class Logger:
    """Singleton approach to logging with JSON formatting"""
>>>>>>> ba6f3864424e2937b072900aebb3e904e1bc5200

    _instances: dict[str, Logger] = {}
    _lock = Lock()

    def __new__(cls, name: str) -> Logger:
        with cls._lock:
            instance = cls._instances.get(name)
            if instance is None:
                instance = super().__new__(cls)
<<<<<<< HEAD
                instance._logger = logging.getLogger(name)
                cls._instances[name] = instance
            return instance

    def debug(self, event: str, **fields: object) -> None:
        self._emit(logging.DEBUG, event, fields)

    def info(self, event: str, **fields: object) -> None:
        self._emit(logging.INFO, event, fields)

    def warn(self, event: str, **fields: object) -> None:
        self._emit(logging.WARNING, event, fields)

    def warning(self, event: str, **fields: object) -> None:
        self.warn(event, **fields)

    def error(self, event: str, **fields: object) -> None:
        self._emit(logging.ERROR, event, fields)
=======
                instance.logger = logging.getLogger(name)
                cls._instances[name] = instance
            return instance

    def debug(self, event: str, **kwargs: Any) -> None:
        self._emit(logging.DEBUG, event, kwargs)

    def info(self, event: str, **kwargs: Any) -> None:
        self._emit(logging.INFO, event, kwargs)

    def warning(self, event: str, **kwargs: Any) -> None:
        self._emit(logging.WARNING, event, kwargs)

    def warn(self, event: str, **kwargs: Any) -> None:
        self.warning(event, **kwargs)
        
    def error(self, event: str, **kwargs: Any) -> None:
        self._emit(logging.ERROR, event, kwargs)
>>>>>>> ba6f3864424e2937b072900aebb3e904e1bc5200

    def exception(
        self,
        event: str,
        error: BaseException,
<<<<<<< HEAD
        **fields: object,
    ) -> None:
        fields.setdefault("reason", safe_reason(error))
        self._logger.error(
            event,
            extra={"event": event, **fields},
            exc_info=_exception_info(error),
        )

    def _emit(self, level: int, event: str, fields: dict[str, object]) -> None:
        self._logger.log(level, event, extra={"event": event, **fields})


def configure_json_logging(level: int) -> None:
    """Route application and framework logs through the JSON formatter."""
=======
        **fields: object
    ) -> None:
        fields.setdefault("reason", safe_reason(error))
        self._logger.error(
            event, extra={"event": event, **fields}, exc_info=_exception_info(error)
        )
    

    def _emit(self, level: int, event: str, fields: dict[str, object]) -> None:
        self.logger.log(level, event, extra={"event": event, **fields})

class JsonFormatter(logging.Formatter):
    """Serialize every log record as one queryable JSON object."""

    def format(self, record: logging.LogRecord) -> str:
        output: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
            "level": record.levelname.lower(),
            "service": "landing-optimizer-ai",
            "logger": record.name
        }

        event = getattr(record, "event", None)

        if event is not None:
            output["event"] = clean_log_value(str(event), 128)
        else:
            output["message"] = clean_log_value(record.getMessage(), 2000)

        for key, value in record.__dict__.items():
            if key in _STANDARD_RECORD_FIELDS or key == "event" or key.startswith("_"):
                continue
            else:
                output[key] = _json_value(value)

        if record.exc_info:
            output["exception"] = clean_log_value(self.formatException(record.exc_info), 8000)

        return json.dumps(output, ensure_ascii=False, separators=(",", ":"))


def configure_json_logging(level: str | int = logging.INFO) -> None:
    """Configure the root logger to emit JSON-formatted logs to stdout."""

>>>>>>> ba6f3864424e2937b072900aebb3e904e1bc5200
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)
<<<<<<< HEAD
=======

>>>>>>> ba6f3864424e2937b072900aebb3e904e1bc5200
    for name in ("app", "uvicorn", "uvicorn.error", "uvicorn.access"):
        target = logging.getLogger(name)
        target.handlers = []
        target.setLevel(level)
        target.propagate = True

<<<<<<< HEAD

def request_id(request: Request) -> str:
    """Return the request ID assigned by middleware."""
    value = getattr(request.state, "request_id", None)
    return value if isinstance(value, str) else "unknown"


def normalize_request_id(value: str | None) -> str:
    """Accept safe upstream IDs; replace malformed values to prevent log injection."""
    return value if value and _REQUEST_ID.fullmatch(value) else uuid4().hex


def clean_log_value(value: str, max_length: int = 300) -> str:
    """Collapse control characters and cap untrusted log fields."""
    return re.sub(r"[\x00-\x1f\x7f]+", " ", value).strip()[:max_length]


def safe_reason(error: BaseException) -> str:
    """Return a short single-line error reason without payload data."""
    message = clean_log_value(str(error))
    return f"{type(error).__name__}:{message}" if message else type(error).__name__


def _json_value(value: object) -> object:
    if value is None or isinstance(value, (bool, int, float)):
=======
    return



def request_id(request: Request) -> str:
    """Get or generate a request ID for logging."""
    value = getattr(request.state, "request_id", None)
    return value if isinstance(value, str) else "unknown"

def normalize_request_id(value: str | None) -> str:
    """Normalize a request ID to a valid format, generating a new one if necessary."""
    if value and _REQUEST_ID.fullmatch(value):
        return value
    return uuid4().hex

def clean_log_value(value: str, max_length: int = 2000) -> str:
    return re.sub(r"[\x00-\x1F\x7F]", " ", value).strip()[:max_length]

def safe_reason(error: BaseException) -> str:
    """Get a safe string representation of an exception for logging."""
    message = clean_log_value(str(error))
    return f"{type(error).__name__}: {message}" if message else type(error).__name__

def _json_value(value: object) -> object:
    if value is None or isinstance(value, (int, float, bool)):
>>>>>>> ba6f3864424e2937b072900aebb3e904e1bc5200
        return value
    if isinstance(value, str):
        return clean_log_value(value, 2000)
    if isinstance(value, (list, tuple)):
<<<<<<< HEAD
        return [_json_value(item) for item in value[:50]]
    if isinstance(value, dict):
        return {
            clean_log_value(str(key), 128): _json_value(item)
            for key, item in list(value.items())[:50]
        }
    return clean_log_value(str(value), 2000)


def _exception_info(
    error: BaseException,
) -> tuple[type[BaseException], BaseException, TracebackType | None]:
    return type(error), error, error.__traceback__
=======
        return [_json_value(v) for v in value[:50]]
    if isinstance(value, dict):
        return {
            clean_log_value(str(k), 128): _json_value(v) for k, v in list(value.items())[:50]
        }
    return clean_log_value(str(value), 2000)

def _exception_info(error: BaseException) -> tuple[type[BaseException], BaseException, TracebackType | None]:
    """Return a tuple suitable for exc_info from an exception."""
    return type(error), error, error.__traceback__
>>>>>>> ba6f3864424e2937b072900aebb3e904e1bc5200
