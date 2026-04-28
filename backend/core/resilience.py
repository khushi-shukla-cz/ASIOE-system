from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Dict, Optional, Tuple, Type

import structlog
from tenacity import AsyncRetrying, RetryCallState, retry_if_exception_type, stop_after_attempt, stop_after_delay, wait_exponential_jitter

from core.config import settings
from core.errors import (
    AppError,
    EngineExecutionError,
    EngineValidationError,
    RequestTimeoutError,
    UpstreamDependencyError,
)

logger = structlog.get_logger(__name__)


class CircuitOpenError(Exception):
    pass


class _RetryableOperationFailure(Exception):
    def __init__(self, app_error: AppError) -> None:
        super().__init__(app_error.message)
        self.app_error = app_error


class _PermanentOperationFailure(Exception):
    def __init__(self, app_error: AppError) -> None:
        super().__init__(app_error.message)
        self.app_error = app_error


@dataclass
class _BreakerState:
    failure_count: int = 0
    opened_at: float = 0.0
    open: bool = False


@dataclass(frozen=True, slots=True)
class ResiliencePolicy:
    operation_name: str
    timeout_seconds: int
    retry_attempts: int
    retry_budget_seconds: int
    idempotent: bool = True


_PERMANENT_FAILURE_TYPES: Tuple[Type[Exception], ...] = (
    ValueError,
    TypeError,
    KeyError,
    FileNotFoundError,
    json.JSONDecodeError,
)


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

    async def _record_success(self) -> bool:
        async with self._lock:
            was_open = self._state.open
            self._state.failure_count = 0
            self._state.open = False
            self._state.opened_at = 0.0
            return was_open

    async def _record_failure(self) -> None:
        async with self._lock:
            self._state.failure_count += 1
            if self._state.failure_count >= self._threshold:
                self._state.open = True
                self._state.opened_at = time.monotonic()
                logger.warning(
                    "engine.circuit.opened",
                    engine=self._name,
                    threshold=self._threshold,
                    recovery_seconds=self._recovery_seconds,
                )

    async def _record_open_recovery(self) -> None:
        logger.info("engine.circuit.recovered", engine=self._name)

    async def call(self, fn: Callable[[], Awaitable[Any]]) -> Any:
        if await self._is_open():
            raise CircuitOpenError(f"Circuit is open for {self._name}")
        try:
            result = await fn()
            recovered = await self._record_success()
            if recovered:
                await self._record_open_recovery()
            return result
        except _PermanentOperationFailure:
            raise
        except _RetryableOperationFailure:
            await self._record_failure()
            raise
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


def _engine_key(operation_name: str) -> str:
    if operation_name.startswith("simulation.path"):
        return "path"
    if operation_name.startswith("simulation.rag"):
        return "rag"
    return operation_name.split(".", 1)[0]


def _build_policy(
    operation_name: str,
    timeout_seconds: Optional[int],
    retries: Optional[int],
    retry_budget_seconds: Optional[int],
    idempotent: Optional[bool],
) -> ResiliencePolicy:
    engine_key = _engine_key(operation_name)
    timeout_lookup = {
        "parsing": settings.PARSING_ENGINE_TIMEOUT_SECONDS,
        "gap": settings.GAP_ENGINE_TIMEOUT_SECONDS,
        "path": settings.PATH_ENGINE_TIMEOUT_SECONDS,
        "rag": settings.RAG_ENGINE_TIMEOUT_SECONDS,
        "explainability": settings.EXPLAINABILITY_ENGINE_TIMEOUT_SECONDS,
    }
    retry_lookup = {
        "parsing": settings.PARSING_ENGINE_RETRY_ATTEMPTS,
        "gap": settings.GAP_ENGINE_RETRY_ATTEMPTS,
        "path": settings.PATH_ENGINE_RETRY_ATTEMPTS,
        "rag": settings.RAG_ENGINE_RETRY_ATTEMPTS,
        "explainability": settings.EXPLAINABILITY_ENGINE_RETRY_ATTEMPTS,
    }
    budget_lookup = {
        "parsing": settings.PARSING_ENGINE_RETRY_BUDGET_SECONDS,
        "gap": settings.GAP_ENGINE_RETRY_BUDGET_SECONDS,
        "path": settings.PATH_ENGINE_RETRY_BUDGET_SECONDS,
        "rag": settings.RAG_ENGINE_RETRY_BUDGET_SECONDS,
        "explainability": settings.EXPLAINABILITY_ENGINE_RETRY_BUDGET_SECONDS,
    }

    resolved_timeout = timeout_seconds or timeout_lookup.get(engine_key, settings.ENGINE_DEFAULT_TIMEOUT_SECONDS)
    resolved_retries = retries or retry_lookup.get(engine_key, settings.ENGINE_DEFAULT_RETRY_ATTEMPTS)
    resolved_budget = retry_budget_seconds or budget_lookup.get(engine_key, settings.ENGINE_DEFAULT_RETRY_BUDGET_SECONDS)
    resolved_idempotent = settings.ENGINE_IDEMPOTENT_DEFAULT if idempotent is None else idempotent

    if not resolved_idempotent:
        resolved_retries = 1
        resolved_budget = min(resolved_budget, resolved_timeout)

    return ResiliencePolicy(
        operation_name=operation_name,
        timeout_seconds=resolved_timeout,
        retry_attempts=resolved_retries,
        retry_budget_seconds=resolved_budget,
        idempotent=resolved_idempotent,
    )


def _classify_failure(
    operation_name: str,
    exc: Exception,
    policy: ResiliencePolicy,
) -> AppError:
    details = {
        "operation": operation_name,
        "engine": _engine_key(operation_name),
        "idempotent": policy.idempotent,
    }

    if isinstance(exc, AppError):
        exc.details.update(details)
        return exc

    if isinstance(exc, _PermanentOperationFailure):
        return exc.app_error

    if isinstance(exc, _RetryableOperationFailure):
        return exc.app_error

    if isinstance(exc, asyncio.TimeoutError):
        return RequestTimeoutError(
            message=f"Operation '{operation_name}' timed out",
            details={**details, "timeout_seconds": policy.timeout_seconds},
        )

    if isinstance(exc, _PERMANENT_FAILURE_TYPES):
        return EngineValidationError(
            message=f"Operation '{operation_name}' received invalid input",
            details={**details, "error": str(exc), "error_type": type(exc).__name__},
        )

    if isinstance(exc, CircuitOpenError):
        return UpstreamDependencyError(
            message=str(exc),
            details={**details, "error": str(exc), "state": "open"},
        )

    return EngineExecutionError(
        message=f"Operation '{operation_name}' failed",
        details={**details, "error": str(exc), "error_type": type(exc).__name__},
    )


def _log_retry_attempt(retry_state: RetryCallState, operation_name: str, policy: ResiliencePolicy) -> None:
    exc = retry_state.outcome.exception() if retry_state.outcome else None
    logger.warning(
        "engine.resilience.retrying",
        operation=operation_name,
        engine=_engine_key(operation_name),
        attempt=retry_state.attempt_number,
        elapsed_seconds=round(retry_state.seconds_since_start or 0.0, 2),
        next_sleep_seconds=round(getattr(retry_state.next_action, "sleep", 0.0) or 0.0, 2),
        retry_budget_seconds=policy.retry_budget_seconds,
        idempotent=policy.idempotent,
        error=str(exc) if exc else None,
        error_type=type(exc).__name__ if exc else None,
    )


async def run_with_resilience(
    operation_name: str,
    func: Callable[[], Awaitable[Any]],
    timeout_seconds: Optional[int] = None,
    retries: Optional[int] = None,
    retry_budget_seconds: Optional[int] = None,
    idempotent: Optional[bool] = None,
    retry_on: Tuple[Type[Exception], ...] = (Exception,),
) -> Any:
    policy = _build_policy(
        operation_name=operation_name,
        timeout_seconds=timeout_seconds,
        retries=retries,
        retry_budget_seconds=retry_budget_seconds,
        idempotent=idempotent,
    )
    breaker = _get_breaker(operation_name)

    logger.info(
        "engine.resilience.start",
        operation=operation_name,
        engine=_engine_key(operation_name),
        timeout_seconds=policy.timeout_seconds,
        retry_attempts=policy.retry_attempts,
        retry_budget_seconds=policy.retry_budget_seconds,
        idempotent=policy.idempotent,
    )

    async def wrapped_call() -> Any:
        try:
            return await asyncio.wait_for(func(), timeout=policy.timeout_seconds)
        except asyncio.TimeoutError as exc:
            error = RequestTimeoutError(
                message=f"Operation '{operation_name}' timed out",
                details={"operation": operation_name, "timeout_seconds": policy.timeout_seconds},
            )
            if policy.idempotent and policy.retry_attempts > 1:
                raise _RetryableOperationFailure(error) from exc
            raise _PermanentOperationFailure(error) from exc
        except AppError as exc:
            raise _PermanentOperationFailure(
                _classify_failure(operation_name, exc, policy)
            ) from exc
        except _PERMANENT_FAILURE_TYPES as exc:
            raise _PermanentOperationFailure(
                _classify_failure(operation_name, exc, policy)
            ) from exc
        except retry_on as exc:
            classified = _classify_failure(operation_name, exc, policy)
            if policy.idempotent and policy.retry_attempts > 1:
                raise _RetryableOperationFailure(classified) from exc
            raise _PermanentOperationFailure(classified) from exc
        except Exception as exc:
            classified = _classify_failure(operation_name, exc, policy)
            raise _PermanentOperationFailure(classified) from exc

    try:
        stop_conditions = stop_after_attempt(policy.retry_attempts)
        if policy.retry_budget_seconds > 0:
            stop_conditions = stop_conditions | stop_after_delay(policy.retry_budget_seconds)

        async for attempt in AsyncRetrying(
            stop=stop_conditions,
            wait=wait_exponential_jitter(initial=0.25, max=2.0),
            retry=retry_if_exception_type(_RetryableOperationFailure),
            reraise=True,
            before_sleep=lambda retry_state: _log_retry_attempt(retry_state, operation_name, policy),
        ):
            with attempt:
                return await breaker.call(wrapped_call)
    except _PermanentOperationFailure as exc:
        logger.warning(
            "engine.resilience.permanent_failure",
            operation=operation_name,
            engine=_engine_key(operation_name),
            error=str(exc.app_error),
            code=exc.app_error.code.value,
        )
        raise exc.app_error
    except _RetryableOperationFailure as exc:
        logger.warning(
            "engine.resilience.retry_exhausted",
            operation=operation_name,
            engine=_engine_key(operation_name),
            error=str(exc.app_error),
            code=exc.app_error.code.value,
            retry_budget_seconds=policy.retry_budget_seconds,
            retry_attempts=policy.retry_attempts,
        )
        raise exc.app_error
    except (RequestTimeoutError, CircuitOpenError) as exc:
        logger.warning("engine.resilience.short_circuit", operation=operation_name, error=str(exc))
        raise _classify_failure(operation_name, exc, policy)
    except Exception as exc:
        app_error = _classify_failure(operation_name, exc, policy)
        logger.error(
            "engine.resilience.failed",
            operation=operation_name,
            engine=_engine_key(operation_name),
            error=str(app_error),
            code=app_error.code.value,
        )
        raise app_error
