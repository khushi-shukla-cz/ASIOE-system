"""
ASIOE — FastAPI Application Entry Point
Production configuration with:
- Structured logging
- CORS
- Request ID middleware
- Prometheus metrics
- Database lifespan management
- OpenAPI documentation
"""
from __future__ import annotations

import time
import uuid
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator

from api.routes import analysis, health, simulation
from core.config import settings
from core.logging import configure_logging
from db.cache import close_redis, get_redis
from db.database import close_db, init_db
from db.neo4j_manager import neo4j_manager

# Configure logging before anything else
configure_logging()
logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """Application startup and shutdown lifecycle."""
    logger.info("asioe.startup", version=settings.APP_VERSION, env=settings.APP_ENV)

    # Initialize databases
    await init_db()
    logger.info("db.postgres.ready")

    await neo4j_manager.connect()
    await neo4j_manager.create_constraints()
    logger.info("db.neo4j.ready")

    await get_redis()
    logger.info("db.redis.ready")

    # Initialize RAG engine (build FAISS index if needed)
    from engines.rag.rag_engine import get_rag_engine
    rag = get_rag_engine()
    await rag.initialize()
    logger.info("rag.engine.ready")

    # Seed skill graph from ontology
    from engines.skill_graph.skill_graph_engine import get_skill_graph_engine
    from pathlib import Path
    graph_engine = get_skill_graph_engine()
    ontology_path = Path("/app/data/processed/skill_ontology.json")
    if ontology_path.exists():
        count = await graph_engine.initialize_graph(ontology_path)
        logger.info("skill.graph.seeded", skills=count)

    logger.info("asioe.ready")
    yield

    # Shutdown
    logger.info("asioe.shutdown")
    await close_db()
    await neo4j_manager.close()
    await close_redis()
    logger.info("asioe.stopped")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description=(
            "Production-grade AI-adaptive onboarding engine that parses candidate capabilities "
            "and dynamically generates personalized learning pathways using graph-based algorithms."
        ),
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )

    # ── Middleware ─────────────────────────────────────────────────────────────

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_middleware(GZipMiddleware, minimum_size=1024)

    # Request ID middleware for distributed tracing
    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        start_time = time.perf_counter()
        response: Response = await call_next(request)
        duration_ms = (time.perf_counter() - start_time) * 1000

        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"

        logger.info(
            "http.request",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration_ms=round(duration_ms, 2),
        )
        return response

    # ── Prometheus Metrics ─────────────────────────────────────────────────────
    if settings.ENABLE_METRICS:
        Instrumentator().instrument(app).expose(app, endpoint="/metrics")

    # ── Routers ────────────────────────────────────────────────────────────────
    app.include_router(health.router, prefix="/api", tags=["Health"])
    app.include_router(analysis.router, prefix="/api/v1", tags=["Analysis"])
    app.include_router(simulation.router, prefix="/api/v1", tags=["Simulation"])

    # ── Exception Handlers ─────────────────────────────────────────────────────
    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError):
        return JSONResponse(
            status_code=422,
            content={"detail": str(exc), "type": "validation_error"},
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        logger.error("unhandled.exception", error=str(exc), exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "detail": "Internal server error",
                "type": "internal_error",
                "request_id": structlog.contextvars.get_contextvars().get("request_id"),
            },
        )

    return app


app = create_app()
