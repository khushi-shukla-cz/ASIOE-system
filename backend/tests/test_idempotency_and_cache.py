from __future__ import annotations

from types import SimpleNamespace
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from api.routes import analysis as analysis_route
from core.auth import AuthenticatedPrincipal


def _build_app():
    # reuse builder from other tests by importing module-level _build_app
    from .test_api_integration import _build_app as builder
    return builder()


def _analysis_payload(session_id: str = "s1") -> dict:
    now = datetime.now(timezone.utc).isoformat()
    return {
        "session_id": session_id,
        "status": "completed",
        "skill_profile": {"candidate_name": "Test", "skills": []},
        "gap_analysis": {"session_id": session_id, "overall_readiness_score": 0.5, "reasoning_trace": "t", "analysis_timestamp": now},
        "learning_path": {"session_id": session_id, "path_id": "p1", "phases": [], "path_graph": {"nodes": [], "edges": []}, "generated_at": now},
        "processing_time_ms": 12.0,
    }


def test_post_analyze_with_existing_idempotency_mapping(monkeypatch):
    # Simulate existing mapping in cache
    async def _fake_cache_get(key):
        if "idempotency" in key:
            return {"session_id": "existing-s1"}
        return None

    monkeypatch.setattr(analysis_route, "cache_get", _fake_cache_get)

    # analysis service shouldn't be called when mapping exists
    class _FakeService:
        async def create_session(self, **kwargs):
            return SimpleNamespace(id="new-s1")

        async def run_analysis(self, **kwargs):
            return _analysis_payload("new-s1")

    monkeypatch.setattr(analysis_route, "get_analysis_service", lambda: _FakeService())

    app = _build_app()
    app.dependency_overrides[analysis_route.get_current_principal] = lambda: AuthenticatedPrincipal(user_id="tester")

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/analyze",
            files={"resume": ("resume.txt", b"x" * 220 + b" contact hidden@example.com", "text/plain")},
            data={"jd_text": "Senior backend engineer with strong Python and SQL." , "idempotency_key": "key-123"},
        )

    assert response.status_code == 200
    assert response.json()["session_id"] == "existing-s1"
    assert "x-session-token" in response.headers


def test_post_analyze_schedules_job_and_sets_mapping(monkeypatch):
    # No existing mapping
    async def _fake_cache_get(key):
        return None

    set_calls = {}

    async def _fake_cache_set(key, value, ttl):
        set_calls["key"] = key
        set_calls["value"] = value

    monkeypatch.setattr(analysis_route, "cache_get", _fake_cache_get)
    monkeypatch.setattr(analysis_route, "cache_set", _fake_cache_set)

    scheduled = {}

    class _FakeJob:
        def delay(self, *args, **kwargs):
            scheduled["called_with"] = (args, kwargs)

    monkeypatch.setattr(analysis_route, "analyze_job", _FakeJob())

    class _FakeService:
        async def create_session(self, **kwargs):
            return SimpleNamespace(id="sched-s1")

        async def run_analysis(self, **kwargs):
            return _analysis_payload("sched-s1")

    monkeypatch.setattr(analysis_route, "get_analysis_service", lambda: _FakeService())

    app = _build_app()
    app.dependency_overrides[analysis_route.get_current_principal] = lambda: AuthenticatedPrincipal(user_id="tester")

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/analyze",
            files={"resume": ("resume.txt", b"x" * 220 + b" contact hidden@example.com", "text/plain")},
            data={"jd_text": "Senior backend engineer with strong Python and SQL.", "idempotency_key": "key-456"},
        )

    assert response.status_code == 202
    assert scheduled.get("called_with") is not None
    assert set_calls.get("key") is not None
    assert "x-session-token" in response.headers
