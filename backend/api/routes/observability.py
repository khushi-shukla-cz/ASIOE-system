"""
ASIOE — Observability Routes
Exposes metrics, health, and tracing information as first-class API surfaces.
"""
from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends, HTTPException

from core.metrics import MetricsAggregator, HealthCheck
from core.security import require_session_access

logger = structlog.get_logger(__name__)

router = APIRouter()


@router.get("/metrics/health", tags=["Observability"])
async def get_health_status() -> dict:
    """
    Get overall system health status.
    
    Returns:
    - health: excellent | good | fair | poor
    - failure_rate_pct: percentage of failed operations
    - avg_latency_ms: average request latency
    - cache_hit_rate_pct: Redis cache efficiency
    - total_invocations: cumulative engine calls
    """
    try:
        health = await HealthCheck.compute_health_status()
        logger.info("metrics.health.retrieved", health_status=health.get("health"))
        return {"status": "ok", "data": health}
    except Exception as exc:
        logger.error("metrics.health.failed", error=str(exc), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to compute health status")


@router.get("/metrics/engines", tags=["Observability"])
async def get_engine_metrics() -> dict:
    """
    Get per-engine performance metrics:
    - invocations: total calls to each engine
    - failures: total failures per engine
    - failure_rate_pct: percentage failures
    - avg_latency_ms: mean time per engine
    - error_types: classification of failures (e.g., TimeoutError, ValidationError)
    """
    try:
        metrics = await MetricsAggregator.get_engine_metrics()
        logger.info("metrics.engines.retrieved", engine_count=len(metrics))
        return {"status": "ok", "data": metrics}
    except Exception as exc:
        logger.error("metrics.engines.failed", error=str(exc), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve engine metrics")


@router.get("/metrics/cache", tags=["Observability"])
async def get_cache_metrics() -> dict:
    """
    Get Redis cache efficiency metrics:
    - total_hits: cache hits
    - total_misses: cache misses
    - hit_rate_pct: hit rate percentage
    - sets: total items cached
    - deletes: total items evicted
    - estimated_saved_processing_ms: time saved by caching
    """
    try:
        metrics = await MetricsAggregator.get_cache_metrics()
        hit_rate = metrics.get("hit_rate_pct", 0)
        logger.info("metrics.cache.retrieved", hit_rate_pct=hit_rate)
        return {"status": "ok", "data": metrics}
    except Exception as exc:
        logger.error("metrics.cache.failed", error=str(exc), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve cache metrics")


@router.get("/metrics/full", tags=["Observability"])
async def get_full_metrics() -> dict:
    """
    Get comprehensive observability view:
    - system-level aggregates (latency, failure rate, cache efficiency)
    - per-engine breakdowns
    - cache layer statistics
    
    Use this for dashboards, SLO calculations, and capacity planning.
    """
    try:
        metrics = await MetricsAggregator.get_full_metrics_view()
        logger.info(
            "metrics.full.retrieved",
            total_invocations=metrics.get("system", {}).get("total_invocations"),
        )
        return {"status": "ok", "data": metrics}
    except Exception as exc:
        logger.error("metrics.full.failed", error=str(exc), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve full metrics")


@router.get("/metrics/trace/{session_id}", tags=["Observability"])
async def get_session_trace(session_id: str, _=Depends(require_session_access)) -> dict:
    """
    Retrieve the distributed trace for a specific analysis session.
    Requires valid session token.
    
    Returns:
    - session_id: analysis session identifier
    - span_tree: hierarchical spans (parse → normalize → gap → path → RAG → explain)
    - total_latency_ms: end-to-end duration
    - per_engine_latencies: breakdown by engine
    - error_details: if any engine failed
    """
    try:
        # In production, traces are persisted in Jaeger/OpenTelemetry backend
        # This endpoint would fetch from that store via the trace ID
        logger.info("metrics.trace.retrieved", session_id=session_id)
        return {
            "status": "ok",
            "message": "Trace retrieval requires integration with Jaeger backend",
            "data": {
                "session_id": session_id,
                "jaeger_url": "http://jaeger:16686/search?service=asioe&traceID={trace_id}",
            },
        }
    except Exception as exc:
        logger.error("metrics.trace.failed", session_id=session_id, error=str(exc), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve trace")
