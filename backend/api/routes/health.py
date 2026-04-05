"""
ASIOE — Health Check Routes
Liveness and readiness probes for Kubernetes/cloud deployment.
"""
from __future__ import annotations

from datetime import datetime

import structlog
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from db.cache import get_redis
from db.database import get_db
from db.neo4j_manager import neo4j_manager
from schemas.schemas import HealthResponse
from core.config import settings

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.get("/health", response_model=HealthResponse, summary="System Health Check")
async def health_check(db: AsyncSession = Depends(get_db)) -> HealthResponse:
    services = {}

    # PostgreSQL
    try:
        await db.execute(text("SELECT 1"))
        services["postgres"] = True
    except Exception:
        services["postgres"] = False

    # Neo4j
    try:
        await neo4j_manager.run_query("RETURN 1 AS ok")
        services["neo4j"] = True
    except Exception:
        services["neo4j"] = False

    # Redis
    try:
        redis = await get_redis()
        await redis.ping()
        services["redis"] = True
    except Exception:
        services["redis"] = False

    overall = "healthy" if all(services.values()) else "degraded"
    return HealthResponse(
        status=overall,
        version=settings.APP_VERSION,
        timestamp=datetime.utcnow(),
        services=services,
    )


@router.get("/health/live", summary="Liveness Probe")
async def liveness() -> dict:
    return {"status": "alive", "timestamp": datetime.utcnow().isoformat()}


@router.get("/health/ready", summary="Readiness Probe")
async def readiness() -> dict:
    return {"status": "ready", "timestamp": datetime.utcnow().isoformat()}
