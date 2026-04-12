from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from core.config import settings
from core.security import RateLimitMiddleware, SecurityHeadersMiddleware
import core.security as security_module


class _FakeRedis:
    def __init__(self):
        self._counts = {}

    async def incr(self, key: str) -> int:
        self._counts[key] = self._counts.get(key, 0) + 1
        return self._counts[key]

    async def expire(self, key: str, seconds: int) -> bool:
        return True

    async def ttl(self, key: str) -> int:
        return 60


def test_security_headers_added():
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware)

    @app.get("/ping")
    async def ping():
        return {"ok": True}

    with TestClient(app) as client:
        response = client.get("/ping")

    assert response.status_code == 200
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert "Permissions-Policy" in response.headers


def test_rate_limit_enforced_with_redis(monkeypatch):
    monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", True)
    monkeypatch.setattr(settings, "RATE_LIMIT_MAX_REQUESTS", 2)
    monkeypatch.setattr(settings, "RATE_LIMIT_WINDOW_SECONDS", 60)
    monkeypatch.setattr(settings, "RATE_LIMIT_PATH_PREFIX", "/api/v1")

    fake_redis = _FakeRedis()

    async def _fake_get_redis():
        return fake_redis

    monkeypatch.setattr(security_module, "get_redis", _fake_get_redis)

    app = FastAPI()
    app.add_middleware(RateLimitMiddleware)

    @app.get("/api/v1/ping")
    async def ping():
        return {"ok": True}

    with TestClient(app) as client:
        r1 = client.get("/api/v1/ping")
        r2 = client.get("/api/v1/ping")
        r3 = client.get("/api/v1/ping")

    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r3.status_code == 429
    assert r3.json()["code"] == "RATE_LIMITED"
    assert "Retry-After" in r3.headers


def test_rate_limit_memory_fallback_when_redis_unavailable(monkeypatch):
    monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", True)
    monkeypatch.setattr(settings, "RATE_LIMIT_MAX_REQUESTS", 1)
    monkeypatch.setattr(settings, "RATE_LIMIT_WINDOW_SECONDS", 60)
    monkeypatch.setattr(settings, "RATE_LIMIT_PATH_PREFIX", "/api/v1")

    async def _failing_get_redis():
        raise RuntimeError("redis unavailable")

    monkeypatch.setattr(security_module, "get_redis", _failing_get_redis)

    app = FastAPI()
    app.add_middleware(RateLimitMiddleware)

    @app.get("/api/v1/ping")
    async def ping():
        return {"ok": True}

    with TestClient(app) as client:
        r1 = client.get("/api/v1/ping")
        r2 = client.get("/api/v1/ping")

    assert r1.status_code == 200
    assert r2.status_code == 429