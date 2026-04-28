"""
ASIOE — Structured Logging
Production-grade structured logging using structlog.
Outputs JSON in production, colored console in development.
"""
from __future__ import annotations

import re
import logging
import sys
from typing import Any, Mapping

import structlog
from structlog.types import EventDict, Processor

from core.config import settings

_SENSITIVE_KEY_PATTERNS = (
    "password",
    "secret",
    "token",
    "api_key",
    "apikey",
    "authorization",
    "email",
    "candidate_name",
    "resume_filename",
    "jd_text",
)

_EMAIL_PATTERN = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.IGNORECASE)


def _is_sensitive_key(key: str) -> bool:
    normalized = key.lower()
    return any(pattern in normalized for pattern in _SENSITIVE_KEY_PATTERNS)


def _sanitize_value(key: str | None, value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            nested_key: _sanitize_value(nested_key, nested_value)
            for nested_key, nested_value in value.items()
        }

    if isinstance(value, list):
        return [_sanitize_value(key, item) for item in value]

    if key and _is_sensitive_key(key):
        return "[REDACTED]"

    if isinstance(value, str):
        return _EMAIL_PATTERN.sub("[REDACTED_EMAIL]", value)

    return value


def sanitize_log_event(event_dict: EventDict) -> EventDict:
    """Redact PII and secret-like values before they reach the log sink."""
    return {
        key: _sanitize_value(key, value)
        for key, value in event_dict.items()
    }


def _add_app_context(
    logger: Any, method_name: str, event_dict: EventDict
) -> EventDict:
    event_dict["app"] = "asioe"
    event_dict["version"] = settings.APP_VERSION
    event_dict["env"] = settings.APP_ENV
    return event_dict


def _drop_color_message_key(
    logger: Any, method_name: str, event_dict: EventDict
) -> EventDict:
    event_dict.pop("color_message", None)
    return event_dict


def configure_logging() -> None:
    """Configure structlog for the application."""
    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        sanitize_log_event,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        _add_app_context,
        _drop_color_message_key,
    ]

    if settings.APP_ENV == "production":
        processors: list[Processor] = [
            *shared_processors,
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ]
    else:
        processors = [
            *shared_processors,
            structlog.dev.ConsoleRenderer(colors=True),
        ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(sys.stdout),
        cache_logger_on_first_use=True,
    )

    # Also configure stdlib logging to route through structlog
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    )


def get_logger(name: str) -> structlog.BoundLogger:
    """Get a bound logger for a specific module."""
    return structlog.get_logger(name)
