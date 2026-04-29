"""
ASIOE — Metrics Collection & Exposure
Aggregates engine performance, cache efficiency, and system health metrics.
Exposes as first-class observability surface for dashboards and alerts.
"""
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Tuple

import structlog

from core.config import settings
from core.observability import (
    get_metrics_collector,
    cache_hit_rate_gauge,
    queue_depth_gauge,
    cache_hits_counter,
    cache_misses_counter,
)
from db.cache import get_cache_stats

logger = structlog.get_logger(__name__)


class MetricsAggregator:
    """Aggregates all observability metrics into a single view."""

    @staticmethod
    async def get_engine_metrics() -> Dict[str, Any]:
        """Get per-engine performance metrics."""
        collector = get_metrics_collector()
        return collector.get_snapshot()

    @staticmethod
    async def get_cache_metrics() -> Dict[str, Any]:
        """Get Redis cache efficiency metrics."""
        cache_stats = get_cache_stats()

        total_requests = (
            cache_stats.get("hits", 0) + cache_stats.get("misses", 0)
        )
        hit_rate = (
            (cache_stats.get("hits", 0) / total_requests * 100)
            if total_requests > 0
            else 0
        )

        # Update Prometheus gauge
        cache_hit_rate_gauge.labels(cache_layer="redis").set(hit_rate)

        return {
            "total_hits": int(cache_stats.get("hits", 0)),
            "total_misses": int(cache_stats.get("misses", 0)),
            "total_requests": total_requests,
            "hit_rate_pct": hit_rate,
            "sets": int(cache_stats.get("sets", 0)),
            "deletes": int(cache_stats.get("deletes", 0)),
            "estimated_saved_processing_ms": cache_stats.get(
                "estimated_saved_processing_ms", 0
            ),
        }

    @staticmethod
    async def get_full_metrics_view() -> Dict[str, Any]:
        """Get comprehensive metrics view for dashboards."""
        engines = await MetricsAggregator.get_engine_metrics()
        cache = await MetricsAggregator.get_cache_metrics()

        # Compute aggregated stats across all engines
        total_invocations = sum(e.get("invocations", 0) for e in engines.values())
        total_failures = sum(e.get("failures", 0) for e in engines.values())
        total_latency_ms = sum(e.get("total_latency_ms", 0) for e in engines.values())

        system_failure_rate = (
            (total_failures / total_invocations * 100)
            if total_invocations > 0
            else 0
        )
        system_avg_latency_ms = (
            (total_latency_ms / total_invocations)
            if total_invocations > 0
            else 0
        )

        return {
            "timestamp": time.time(),
            "system": {
                "total_invocations": total_invocations,
                "total_failures": total_failures,
                "failure_rate_pct": system_failure_rate,
                "avg_latency_ms": system_avg_latency_ms,
                "cache_hit_rate_pct": cache["hit_rate_pct"],
                "estimated_time_saved_ms": cache["estimated_saved_processing_ms"],
            },
            "engines": engines,
            "cache": cache,
        }


class LatencyBuckets:
    """Compute latency percentiles from histogram data."""

    @staticmethod
    def compute_percentiles(
        latencies: List[float], percentiles: Optional[List[int]] = None
    ) -> Dict[int, float]:
        """Compute latency percentiles (p50, p90, p95, p99, etc.)."""
        if not percentiles:
            percentiles = [50, 90, 95, 99]

        if not latencies:
            return {p: 0.0 for p in percentiles}

        sorted_latencies = sorted(latencies)
        result = {}
        for p in percentiles:
            idx = int(len(sorted_latencies) * (p / 100))
            idx = min(idx, len(sorted_latencies) - 1)
            result[p] = sorted_latencies[idx]
        return result


class CacheEfficiencyAnalyzer:
    """Analyzes cache hit rate trends and predicts savings."""

    @staticmethod
    def compute_cache_efficiency(
        total_hits: int, total_misses: int, avg_processing_ms: float
    ) -> Dict[str, Any]:
        """Compute cache efficiency metrics."""
        total = total_hits + total_misses
        hit_rate = (total_hits / total * 100) if total > 0 else 0

        # Estimate time saved by cache hits
        time_saved_ms = total_hits * avg_processing_ms

        return {
            "hit_rate_pct": hit_rate,
            "total_requests": total,
            "time_saved_ms": time_saved_ms,
            "cache_efficiency_ratio": hit_rate / 100,  # 0.0 to 1.0
        }


class HealthCheck:
    """System health indicators."""

    @staticmethod
    async def compute_health_status() -> Dict[str, Any]:
        """Compute overall system health."""
        metrics = await MetricsAggregator.get_full_metrics_view()

        system = metrics.get("system", {})
        failure_rate = system.get("failure_rate_pct", 0)

        # Health classification
        if failure_rate == 0:
            health = "excellent"
        elif failure_rate < 1:
            health = "good"
        elif failure_rate < 5:
            health = "fair"
        else:
            health = "poor"

        return {
            "health": health,
            "failure_rate_pct": failure_rate,
            "avg_latency_ms": system.get("avg_latency_ms", 0),
            "cache_hit_rate_pct": system.get("cache_hit_rate_pct", 0),
            "total_invocations": system.get("total_invocations", 0),
        }
