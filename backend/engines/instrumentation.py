"""
ASIOE — Engine Instrumentation Helpers
Decorators and utilities for adding distributed tracing to engine methods.
"""
from __future__ import annotations

import functools
import time
from typing import Any, Callable, TypeVar, Optional, Dict

import structlog

from core.observability import EngineSpan, get_metrics_collector

logger = structlog.get_logger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


def trace_engine_operation(engine_name: str, operation_name: Optional[str] = None):
    """
    Decorator for tracing engine operations with automatic latency and error recording.
    
    Usage:
        @trace_engine_operation("parsing", "parse_resume")
        async def parse_resume(self, resume_bytes: bytes) -> Dict:
            ...
    """
    def decorator(func: Callable) -> Callable:
        actual_operation = operation_name or func.__name__

        @functools.wraps(func)
        async def async_wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
            context_dict = {
                "function": func.__name__,
                "engine": engine_name,
            }

            # Add first arg context if it looks like a meaningful ID
            if args and isinstance(args[0], (str, int)):
                context_dict["input_id"] = str(args[0])[:32]

            with EngineSpan(engine_name, actual_operation, context_dict):
                return await func(self, *args, **kwargs)

        @functools.wraps(func)
        def sync_wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
            context_dict = {
                "function": func.__name__,
                "engine": engine_name,
            }

            if args and isinstance(args[0], (str, int)):
                context_dict["input_id"] = str(args[0])[:32]

            with EngineSpan(engine_name, actual_operation, context_dict):
                return func(self, *args, **kwargs)

        # Return appropriate wrapper
        if hasattr(func, "__await__"):
            return async_wrapper
        
        # Check if it's an async function
        import inspect
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        
        return sync_wrapper

    return decorator


class MetricsRecorder:
    """Records and aggregates engine metrics for observability."""

    def __init__(self, engine_name: str):
        self.engine_name = engine_name
        self.collector = get_metrics_collector()

    def record_operation(
        self,
        operation: str,
        latency_ms: float,
        success: bool = True,
        error_type: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Record an operation's metrics."""
        metadata = metadata or {}

        self.collector.record_latency(
            self.engine_name,
            latency_ms / 1000.0,  # Convert to seconds
            success=success,
        )

        if error_type:
            self.collector.record_error(self.engine_name, error_type)

        if success:
            logger.info(
                f"engine.{self.engine_name}.operation",
                operation=operation,
                latency_ms=latency_ms,
                **metadata,
            )
        else:
            logger.warning(
                f"engine.{self.engine_name}.operation.failed",
                operation=operation,
                latency_ms=latency_ms,
                error_type=error_type,
                **metadata,
            )

    def record_batch(
        self,
        operation: str,
        count: int,
        total_latency_ms: float,
        success: bool = True,
        error_type: Optional[str] = None,
    ) -> None:
        """Record batch operation metrics."""
        avg_latency_ms = total_latency_ms / count if count > 0 else 0

        self.collector.record_latency(
            self.engine_name,
            total_latency_ms / 1000.0,
            success=success,
        )

        if error_type:
            self.collector.record_error(self.engine_name, error_type)

        logger.info(
            f"engine.{self.engine_name}.batch",
            operation=operation,
            batch_size=count,
            total_latency_ms=total_latency_ms,
            avg_latency_ms=avg_latency_ms,
        )
