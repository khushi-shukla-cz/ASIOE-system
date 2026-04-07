from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Dict, Optional, Tuple, Type

import structlog
from tenacity import AsyncRetrying, retry_if_exception_type, stop_after_attempt, wait_exponential_jitter

from core.config import settings
from core.errors import EngineExecutionError, RequestTimeoutError

logger = structlog.get_logger(__name__)


class CircuitOpenError(Exception):
    pass


@dataclass
class _BreakerState:
    failure_count: int = 0
    opened_at: float = 0.0
    open: bool = False


class AsyncCircuitBreaker:
    def __init__(self, name: str, threshold: int, recovery_seconds: int) -> None:
        self._name = name
        self._threshold = threshold
        self._recovery_seconds = recovery_seconds
        self._state = _BreakerState()
        self._lock = asyncio.Lock()

    async def _is_open(self) -> bool:
        async with self._lock:
            if not self._state.open:
                return False
            elapsed = time.monotonic() - self._state.opened_at
            if elapsed >= self._recovery_seconds:
                self._state.open = False
                self._state.failure_count = 0
                return False
            return True

    async def _record_success(self) -> None:
        async with self._lock:
            self._state.failure_count = 0
            self._state.open = False
            self._state.opened_at = 0.0

    async def _record_failure(self) -> None:
        async with self._lock:
            self._state.failure_count += 1
            if self._state.failure_count >= self._threshold:
                self._state.open = True
                self._state.opened_at = time.monotonic()

    async def call(self, fn: Callable[[], Awaitable[Any]]) -> Any:
        if await self._is_open():
            raise CircuitOpenError(f"Circuit is open for {self._name}")
        try:
            result = await fn()
            await self._record_success()
            return result
        except Exception:
            await self._record_failure()
            raise


_BREAKERS: Dict[str, AsyncCircuitBreaker] = {}


def _get_breaker(name: str) -> AsyncCircuitBreaker:
    if name not in _BREAKERS:
        _BREAKERS[name] = AsyncCircuitBreaker(
            name=name,
            threshold=settings.ENGINE_CIRCUIT_BREAKER_FAILURE_THRESHOLD,
            recovery_seconds=settings.ENGINE_CIRCUIT_BREAKER_RECOVERY_SECONDS,
        )
    return _BREAKERS[name]


async def run_with_resilience(
    operation_name: str,
    func: Callable[[], Awaitable[Any]],
    timeout_seconds: Optional[int] = None,
    retries: Optional[int] = None,
    retry_on: Tuple[Type[Exception], ...] = (Exception,),
) -> Any:
    timeout_value = timeout_seconds or settings.ENGINE_DEFAULT_TIMEOUT_SECONDS
    retry_attempts = retries or settings.ENGINE_DEFAULT_RETRY_ATTEMPTS
    breaker = _get_breaker(operation_name)

    async def wrapped_call() -> Any:
        try:
            return await asyncio.wait_for(func(), timeout=timeout_value)
        except asyncio.TimeoutError as exc:
            raise RequestTimeoutError(
                message=f"Operation '{operation_name}' timed out",
                details={"operation": operation_name, "timeout_seconds": timeout_value},
            ) from exc

    try:
        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(retry_attempts),
            wait=wait_exponential_jitter(initial=0.25, max=2.0),
            retry=retry_if_exception_type(retry_on),
            reraise=True,
        ):
            with attempt:
                return await breaker.call(wrapped_call)
    except (RequestTimeoutError, CircuitOpenError) as exc:
        logger.warning("engine.resilience.short_circuit", operation=operation_name, error=str(exc))
        raise
    except Exception as exc:
        logger.error("engine.resilience.failed", operation=operation_name, error=str(exc))
        raise EngineExecutionError(
            message=f"Operation '{operation_name}' failed",
            details={"operation": operation_name, "error": str(exc)},
        ) from exc
