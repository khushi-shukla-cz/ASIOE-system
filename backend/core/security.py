from __future__ import annotations

import asyncio
import time
from typing import Dict, Tuple

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from core.config import settings
from core.errors import ErrorCode, build_error_response
from core.logging import get_logger
from db.cache import get_redis

logger = get_logger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Attach baseline security headers to all responses."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault(
            "Permissions-Policy",
            "geolocation=(), camera=(), microphone=()",
        )

        if settings.SECURITY_ENABLE_HSTS and _is_https(request):
            response.headers.setdefault(
                "Strict-Transport-Security",
                "max-age=31536000; includeSubDomains",
            )

        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Fixed-window API rate limiting with Redis and memory fallback."""

    def __init__(self, app):
        super().__init__(app)
        self._window_seconds = settings.RATE_LIMIT_WINDOW_SECONDS
        self._max_requests = settings.RATE_LIMIT_MAX_REQUESTS
        self._memory_counters: Dict[str, Tuple[int, int]] = {}
        self._lock = asyncio.Lock()

    async def dispatch(self, request: Request, call_next):
        if not settings.RATE_LIMIT_ENABLED:
            return await call_next(request)

        if request.method == "OPTIONS":
            return await call_next(request)

        if not request.url.path.startswith(settings.RATE_LIMIT_PATH_PREFIX):
            return await call_next(request)

        client_ip = _resolve_client_ip(request)
        now = int(time.time())
        window_id = now // self._window_seconds
        counter_key = f"asioe:rate_limit:{client_ip}:{window_id}"

        allowed, remaining, retry_after = await self._consume(counter_key)
        if not allowed:
            response = build_error_response(
                request=request,
                status_code=429,
                code=ErrorCode.RATE_LIMITED,
                message="Rate limit exceeded",
                details={
                    "limit": self._max_requests,
                    "window_seconds": self._window_seconds,
                    "retry_after_seconds": retry_after,
                },
            )
            response.headers["Retry-After"] = str(retry_after)
            response.headers["X-RateLimit-Limit"] = str(self._max_requests)
            response.headers["X-RateLimit-Remaining"] = "0"
            response.headers["X-RateLimit-Reset"] = str(now + retry_after)
            return response

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self._max_requests)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(now + retry_after)
        return response

    async def _consume(self, key: str) -> Tuple[bool, int, int]:
        try:
            client = await get_redis()
            count = await client.incr(key)
            if count == 1:
                await client.expire(key, self._window_seconds)

            ttl = await client.ttl(key)
            ttl = ttl if ttl and ttl > 0 else self._window_seconds
            remaining = max(0, self._max_requests - int(count))

            if count > self._max_requests:
                return False, 0, ttl

            return True, remaining, ttl
        except Exception as exc:
            logger.warning("rate_limit.redis_fallback", error=str(exc))
            return await self._consume_memory(key)

    async def _consume_memory(self, key: str) -> Tuple[bool, int, int]:
        now = int(time.time())
        reset_at = now + self._window_seconds

        async with self._lock:
            count, existing_reset_at = self._memory_counters.get(key, (0, reset_at))

            if existing_reset_at <= now:
                count = 0
                existing_reset_at = reset_at

            count += 1
            self._memory_counters[key] = (count, existing_reset_at)

            retry_after = max(1, existing_reset_at - now)
            remaining = max(0, self._max_requests - count)

            if count > self._max_requests:
                return False, 0, retry_after

            return True, remaining, retry_after


def _resolve_client_ip(request: Request) -> str:
    if settings.RATE_LIMIT_TRUST_PROXY_HEADERS:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()

    if request.client and request.client.host:
        return request.client.host

    return "unknown"


def _is_https(request: Request) -> bool:
    forwarded_proto = request.headers.get("x-forwarded-proto", "")
    if forwarded_proto.lower() == "https":
        return True

    return request.url.scheme == "https"