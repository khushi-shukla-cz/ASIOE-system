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
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator

from api.routes import analysis, health, simulation, observability
from core.config import settings
from core.errors import (
    AppError,
    ErrorCode,
    build_error_response,
)
from core.logging import configure_logging
from core.observability import init_tracing, init_tracing_middleware, set_trace_id
from core.security import RateLimitMiddleware, SecurityHeadersMiddleware
from db.cache import close_redis, get_redis
from db.database import close_db, init_db
from db.neo4j_manager import neo4j_manager

# Configure logging before anything else
configure_logging()
logger = structlog.get_logger(__name__)

# Initialize distributed tracing
if settings.ENABLE_DISTRIBUTED_TRACING:
    init_tracing()
    logger.info("observability.tracing_enabled", backend="jaeger")


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
    graph_engine = get_skill_graph_engine()
    ontology_path = settings.SKILL_ONTOLOGY_PATH
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

    if settings.SECURITY_HEADERS_ENABLED:
        app.add_middleware(SecurityHeadersMiddleware)

    if settings.RATE_LIMIT_ENABLED:
        app.add_middleware(RateLimitMiddleware)

    # Correlation ID middleware for distributed tracing
    @app.middleware("http")
    async def correlation_middleware(request: Request, call_next):
        correlation_header = settings.CORRELATION_HEADER_NAME
        correlation_id = (
            request.headers.get(correlation_header)
            or request.headers.get("X-Request-ID")
            or str(uuid.uuid4())
        )
        
        # Also set trace ID for distributed tracing
        trace_id = request.headers.get(settings.TRACE_HEADER_NAME) or str(uuid.uuid4())
        set_trace_id(trace_id)

        request.state.correlation_id = correlation_id
        request.state.trace_id = trace_id
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            correlation_id=correlation_id,
            trace_id=trace_id
        )

        start_time = time.perf_counter()
        try:
            response: Response = await call_next(request)
        except Exception:
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.error(
                "http.request.failed",
                method=request.method,
                path=request.url.path,
                duration_ms=round(duration_ms, 2),
                exc_info=True,
            )
            raise

        duration_ms = (time.perf_counter() - start_time) * 1000
        response.headers[correlation_header] = correlation_id
        response.headers[settings.TRACE_HEADER_NAME] = trace_id
        response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"

        logger.info(
            "http.request",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration_ms=round(duration_ms, 2),
            correlation_id=correlation_id,
        )
        return response

    # ── Prometheus Metrics ─────────────────────────────────────────────────────
    if settings.ENABLE_METRICS:
        Instrumentator().instrument(app).expose(app, endpoint="/metrics")

    # ── Routers ────────────────────────────────────────────────────────────────
    app.include_router(health.router, prefix="/api", tags=["Health"])
    app.include_router(analysis.router, prefix="/api/v1", tags=["Analysis"])
    app.include_router(simulation.router, prefix="/api/v1", tags=["Simulation"])
    app.include_router(observability.router, prefix="/api/v1", tags=["Observability"])

    # ── Exception Handlers ─────────────────────────────────────────────────────
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        return build_error_response(
            request=request,
            status_code=422,
            code=ErrorCode.VALIDATION_ERROR,
            message="Request validation failed",
            details={"errors": exc.errors()},
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        code = ErrorCode.VALIDATION_ERROR if 400 <= exc.status_code < 500 else ErrorCode.INTERNAL_ERROR
        message = str(exc.detail) if exc.detail else "HTTP request failed"
        return build_error_response(
            request=request,
            status_code=exc.status_code,
            code=code,
            message=message,
            details={"status_code": exc.status_code},
        )

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError):
        return build_error_response(
            request=request,
            status_code=exc.status_code,
            code=exc.code,
            message=exc.message,
            details=exc.details,
        )

    @app.exception_handler(TimeoutError)
    async def timeout_exception_handler(request: Request, exc: TimeoutError):
        return build_error_response(
            request=request,
            status_code=504,
            code=ErrorCode.TIMEOUT_ERROR,
            message="Request timed out",
            details={"error": str(exc)},
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        logger.error("unhandled.exception", error=str(exc), exc_info=True)
        return build_error_response(
            request=request,
            status_code=500,
            code=ErrorCode.INTERNAL_ERROR,
            message="Internal server error",
            details={"error": str(exc)},
        )

    return app


app = create_app()
