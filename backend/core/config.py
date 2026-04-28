"""
ASIOE — Core Configuration
Production-grade settings management via Pydantic BaseSettings.
All secrets are injected via environment variables — never hardcoded.
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import List, Optional

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ────────────────────────────────────────────────────────────
    APP_NAME: str = "ASIOE — Adaptive Skill Intelligence & Optimization Engine"
    APP_VERSION: str = "1.0.0"
    APP_ENV: str = Field(default="production", pattern="^(development|staging|production)$")
    DEBUG: bool = False
    SECRET_KEY: str = Field(..., min_length=32)
    ALLOWED_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:80"]

    # ── Database — PostgreSQL ──────────────────────────────────────────────────
    POSTGRES_HOST: str = "postgres"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "asioe"
    POSTGRES_USER: str = "asioe_user"
    POSTGRES_PASSWORD: str = Field(...)
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 40

    @property
    def DATABASE_URL(self) -> str:  # noqa: N802
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def DATABASE_URL_SYNC(self) -> str:  # noqa: N802
        return (
            f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # ── Database — Neo4j ──────────────────────────────────────────────────────
    NEO4J_URI: str = "bolt://neo4j:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = Field(...)

    # ── Cache — Redis ─────────────────────────────────────────────────────────
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None
    CACHE_TTL_SECONDS: int = 3600

    @property
    def REDIS_URL(self) -> str:  # noqa: N802
        auth = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
        return f"redis://{auth}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    # ── LLM — Groq ────────────────────────────────────────────────────────────
    GROQ_API_KEY: str = Field(...)
    GROQ_PRIMARY_MODEL: str = "llama-3.3-70b-versatile"
    GROQ_FALLBACK_MODEL: str = "mixtral-8x7b-32768"
    GROQ_MAX_TOKENS: int = 4096
    GROQ_TEMPERATURE: float = 0.1   # Low temperature → deterministic extraction
    GROQ_TIMEOUT_SECONDS: int = 30
    GROQ_MAX_RETRIES: int = 3

    # ── Embeddings ────────────────────────────────────────────────────────────
    EMBEDDING_MODEL: str = "sentence-transformers/all-mpnet-base-v2"
    EMBEDDING_DIMENSION: int = 768
    EMBEDDING_BATCH_SIZE: int = 64

    # ── Data Paths ────────────────────────────────────────────────────────────
    DATA_DIR: Path = Path(__file__).resolve().parents[1] / "data"

    @property
    def PROCESSED_DATA_DIR(self) -> Path:  # noqa: N802
        return self.DATA_DIR / "processed"

    @property
    def SKILL_ONTOLOGY_PATH(self) -> Path:  # noqa: N802
        return self.PROCESSED_DATA_DIR / "skill_ontology.json"

    @property
    def COURSE_CATALOG_PATH(self) -> Path:  # noqa: N802
        return self.PROCESSED_DATA_DIR / "course_catalog.json"

    @property
    def ONTOLOGY_EMBEDDINGS_CACHE_PATH(self) -> Path:  # noqa: N802
        return self.PROCESSED_DATA_DIR / "ontology_embeddings.pkl"

    @property
    def FAISS_INDEX_PATH(self) -> Path:  # noqa: N802
        return self.PROCESSED_DATA_DIR / "faiss_index"

    # ── Skill Graph ───────────────────────────────────────────────────────────
    SKILL_SIMILARITY_THRESHOLD: float = 0.82
    MAX_PATH_DEPTH: int = 15
    MAX_RECOMMENDATIONS: int = 20
    MIN_CONFIDENCE_SCORE: float = 0.65

    # ── File Upload ───────────────────────────────────────────────────────────
    MAX_UPLOAD_SIZE_MB: int = 10
    ALLOWED_EXTENSIONS: List[str] = ["pdf", "docx", "txt"]
    UPLOAD_DIR: str = "/tmp/asioe_uploads"

    # ── Observability ─────────────────────────────────────────────────────────
    LOG_LEVEL: str = "INFO"
    ENABLE_METRICS: bool = True
    SENTRY_DSN: Optional[str] = None
    CORRELATION_HEADER_NAME: str = "X-Correlation-ID"

    # -- API Security --
    SECURITY_HEADERS_ENABLED: bool = True
    SECURITY_ENABLE_HSTS: bool = True
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_MAX_REQUESTS: int = 120
    RATE_LIMIT_WINDOW_SECONDS: int = 60
    RATE_LIMIT_PATH_PREFIX: str = "/api/v1"
    RATE_LIMIT_TRUST_PROXY_HEADERS: bool = False

    # -- Authentication / Authorization --
    AUTH_ENABLED: bool = False
    API_AUTH_KEYS: str = ""
    DEFAULT_AUTH_USER: str = "anonymous"
    SESSION_TOKEN_TTL_SECONDS: int = 86400

    # ── Reliability / Resilience ──────────────────────────────────────────────
    ENGINE_DEFAULT_TIMEOUT_SECONDS: int = 30
    ENGINE_DEFAULT_RETRY_ATTEMPTS: int = 2
    ENGINE_CIRCUIT_BREAKER_FAILURE_THRESHOLD: int = 5
    ENGINE_CIRCUIT_BREAKER_RECOVERY_SECONDS: int = 30

    @field_validator("APP_ENV", mode="before")
    @classmethod
    def validate_env(cls, v: str) -> str:
        allowed = {"development", "staging", "production"}
        if v not in allowed:
            raise ValueError(f"APP_ENV must be one of {allowed}")
        return v

    @model_validator(mode="after")
    def validate_auth_configuration(self):
        if self.AUTH_ENABLED and not self.API_AUTH_KEYS.strip():
            raise ValueError("API_AUTH_KEYS must be configured when AUTH_ENABLED is true")
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached singleton settings instance."""
    return Settings()


settings = get_settings()
