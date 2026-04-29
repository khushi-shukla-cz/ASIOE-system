"""
ASIOE — Distributed Tracing & Observability Infrastructure
Production-grade OpenTelemetry setup with per-engine spans, metrics, and status collection.

Features:
- Distributed tracing via OTLP/Jaeger
- Per-engine span tracking (parsing, normalization, gap, path, RAG, explainability)
- Latency, failure rate, and throughput metrics
- Request-scoped trace context propagation
- Performance profiles for bottleneck identification
"""
from __future__ import annotations

import contextvars
import functools
import time
from typing import Any, Callable, Dict, List, Optional

import structlog
from opentelemetry import trace, metrics
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.resources import Resource
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from prometheus_client import Counter, Histogram, Gauge

from core.config import settings

logger = structlog.get_logger(__name__)

# Distributed tracing context
_trace_id_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "trace_id", default=""
)
_span_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("span_id", default="")


# ── Prometheus Metrics (First-Class) ────────────────────────────────────────

# Latency histogram per engine (percentiles: p50, p90, p95, p99)
engine_latency_histogram = Histogram(
    "engine_latency_seconds",
    "Engine processing time in seconds",
    ["engine_name"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

# Failure rate counter per engine
engine_failures_counter = Counter(
    "engine_failures_total",
    "Total failures per engine",
    ["engine_name", "error_type"],
)

# Throughput counter per engine
engine_invocations_counter = Counter(
    "engine_invocations_total",
    "Total invocations per engine",
    ["engine_name"],
)

# Cache hit/miss rate
cache_hits_counter = Counter(
    "cache_hits_total",
    "Total cache hits",
    ["cache_layer"],
)

cache_misses_counter = Counter(
    "cache_misses_total",
    "Total cache misses",
    ["cache_layer"],
)

# Cache hit rate gauge
cache_hit_rate_gauge = Gauge(
    "cache_hit_rate",
    "Cache hit rate as percentage",
    ["cache_layer"],
)

# Queue depth gauge (for async job tracking)
queue_depth_gauge = Gauge(
    "queue_depth",
    "Number of pending jobs in queue",
    ["queue_name"],
)

# Per-engine request count (cumulative)
requests_per_engine_counter = Counter(
    "requests_per_engine_total",
    "Cumulative requests per engine",
    ["engine_name"],
)

# Per-engine error count
errors_per_engine_counter = Counter(
    "errors_per_engine_total",
    "Cumulative errors per engine",
    ["engine_name", "error_classification"],
)


class EngineMetricsCollector:
    """Collects latency, failure rate, and throughput metrics per engine."""

    def __init__(self) -> None:
        self._lock_free_stats: Dict[str, Dict[str, Any]] = {
            "parsing": {"invocations": 0, "failures": 0, "total_ms": 0, "error_types": {}},
            "normalization": {
                "invocations": 0,
                "failures": 0,
                "total_ms": 0,
                "error_types": {},
            },
            "gap": {"invocations": 0, "failures": 0, "total_ms": 0, "error_types": {}},
            "path": {"invocations": 0, "failures": 0, "total_ms": 0, "error_types": {}},
            "rag": {"invocations": 0, "failures": 0, "total_ms": 0, "error_types": {}},
            "explainability": {
                "invocations": 0,
                "failures": 0,
                "total_ms": 0,
                "error_types": {},
            },
        }

    def record_latency(
        self, engine_name: str, latency_seconds: float, success: bool = True
    ) -> None:
        """Record latency and success/failure for an engine."""
        if engine_name not in self._lock_free_stats:
            return

        stats = self._lock_free_stats[engine_name]
        stats["invocations"] += 1
        stats["total_ms"] += latency_seconds * 1000

        if not success:
            stats["failures"] += 1

        engine_latency_histogram.labels(engine_name=engine_name).observe(
            latency_seconds
        )
        engine_invocations_counter.labels(engine_name=engine_name).inc()

    def record_error(self, engine_name: str, error_type: str) -> None:
        """Record an error classification for an engine."""
        if engine_name not in self._lock_free_stats:
            return

        stats = self._lock_free_stats[engine_name]
        stats["error_types"][error_type] = stats["error_types"].get(error_type, 0) + 1

        engine_failures_counter.labels(engine_name=engine_name, error_type=error_type).inc()
        errors_per_engine_counter.labels(
            engine_name=engine_name, error_classification=error_type
        ).inc()

    def get_snapshot(self) -> Dict[str, Any]:
        """Return a point-in-time snapshot of all metrics."""
        snapshot: Dict[str, Any] = {}
        for engine_name, stats in self._lock_free_stats.items():
            avg_ms = (
                stats["total_ms"] / stats["invocations"]
                if stats["invocations"] > 0
                else 0
            )
            failure_rate = (
                (stats["failures"] / stats["invocations"] * 100)
                if stats["invocations"] > 0
                else 0
            )
            snapshot[engine_name] = {
                "invocations": stats["invocations"],
                "failures": stats["failures"],
                "failure_rate_pct": failure_rate,
                "avg_latency_ms": avg_ms,
                "total_latency_ms": stats["total_ms"],
                "error_types": stats["error_types"],
            }
        return snapshot


# Global metrics collector
_metrics_collector = EngineMetricsCollector()


def get_metrics_collector() -> EngineMetricsCollector:
    """Get the global metrics collector instance."""
    return _metrics_collector


class EngineSpan:
    """Context manager for per-engine distributed tracing spans."""

    def __init__(self, engine_name: str, operation: str, context_dict: Optional[Dict] = None):
        self.engine_name = engine_name
        self.operation = operation
        self.context_dict = context_dict or {}
        self.tracer = trace.get_tracer(__name__)
        self.span = None
        self.start_time = 0.0

    def __enter__(self) -> EngineSpan:
        self.start_time = time.time()
        self.span = self.tracer.start_span(
            name=f"{self.engine_name}.{self.operation}",
            attributes={
                "engine": self.engine_name,
                "operation": self.operation,
                "trace_id": _trace_id_var.get(),
                **self.context_dict,
            },
        )
        self.span.__enter__()
        logger.info(
            f"engine.{self.engine_name}.start",
            operation=self.operation,
            trace_id=_trace_id_var.get(),
        )
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        elapsed = time.time() - self.start_time
        success = exc_type is None

        if self.span:
            self.span.set_attribute("success", success)
            self.span.set_attribute("duration_seconds", elapsed)
            if exc_type:
                self.span.set_attribute("error_type", exc_type.__name__)
            self.span.__exit__(exc_type, exc_val, exc_tb)

        _metrics_collector.record_latency(
            self.engine_name, elapsed, success=success
        )

        if exc_type:
            _metrics_collector.record_error(self.engine_name, exc_type.__name__)
            logger.warning(
                f"engine.{self.engine_name}.failure",
                operation=self.operation,
                error=exc_type.__name__,
                latency_ms=elapsed * 1000,
                trace_id=_trace_id_var.get(),
            )
        else:
            logger.info(
                f"engine.{self.engine_name}.complete",
                operation=self.operation,
                latency_ms=elapsed * 1000,
                trace_id=_trace_id_var.get(),
            )


def engine_span_decorator(engine_name: str):
    """Decorator for automatic engine span tracking."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            context_dict = {
                "input_keys": str(list(kwargs.keys())[:3]),  # First 3 kwargs
                "async": True,
            }
            with EngineSpan(engine_name, func.__name__, context_dict):
                return await func(*args, **kwargs)

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            context_dict = {
                "input_keys": str(list(kwargs.keys())[:3]),
                "async": False,
            }
            with EngineSpan(engine_name, func.__name__, context_dict):
                return func(*args, **kwargs)

        # Return appropriate wrapper based on function type
        if hasattr(func, "__await__"):
            return async_wrapper
        return async_wrapper if "async" in str(func) else sync_wrapper

    return decorator


def set_trace_id(trace_id: str) -> None:
    """Set the request-scoped trace ID."""
    _trace_id_var.set(trace_id)


def get_trace_id() -> str:
    """Get the current trace ID."""
    return _trace_id_var.get()


def init_tracing() -> None:
    """Initialize OpenTelemetry tracing infrastructure."""
    # Resource description
    resource = Resource.create(
        {
            "service.name": "asioe",
            "service.version": settings.APP_VERSION,
            "service.environment": settings.APP_ENV,
        }
    )

    # Jaeger exporter for distributed tracing
    jaeger_exporter = JaegerExporter(
        agent_host_name=settings.JAEGER_HOST,
        agent_port=settings.JAEGER_PORT,
    )

    # Trace provider
    trace_provider = TracerProvider(resource=resource)
    trace_provider.add_span_processor(BatchSpanProcessor(jaeger_exporter))
    trace.set_tracer_provider(trace_provider)

    # Prometheus metrics reader
    prometheus_reader = PrometheusMetricReader()

    # Metrics provider
    meter_provider = MeterProvider(resource=resource, metric_readers=[prometheus_reader])
    metrics.set_meter_provider(meter_provider)

    # Instrument FastAPI, SQLAlchemy, Redis, Requests
    FastAPIInstrumentor.instrument_app(None)  # Will be called on the app later
    SQLAlchemyInstrumentor().instrument()
    RedisInstrumentor().instrument()
    RequestsInstrumentor().instrument()

    logger.info(
        "observability.initialized",
        tracing_backend="jaeger",
        metrics_backend="prometheus",
        jaeger_host=settings.JAEGER_HOST,
        jaeger_port=settings.JAEGER_PORT,
    )


def init_tracing_middleware() -> Callable:
    """
    Middleware to extract/inject trace context from HTTP headers.
    Sets up request-scoped trace ID for logging and span correlation.
    """

    async def middleware(request: Any, call_next: Callable) -> Any:
        import uuid

        # Extract or generate trace ID
        trace_id = request.headers.get("X-Trace-ID", str(uuid.uuid4()))
        set_trace_id(trace_id)

        # Add trace ID to response headers
        response = await call_next(request)
        response.headers["X-Trace-ID"] = trace_id
        return response

    return middleware
