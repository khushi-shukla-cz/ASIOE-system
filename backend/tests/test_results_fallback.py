import asyncio
import sys
import types
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.responses import JSONResponse

if "services.analysis_service" not in sys.modules:
    analysis_service_stub = types.ModuleType("services.analysis_service")

    def _stub_get_analysis_service():
        raise RuntimeError("analysis service should be monkeypatched in tests")

    analysis_service_stub.get_analysis_service = _stub_get_analysis_service
    sys.modules["services.analysis_service"] = analysis_service_stub

from api.routes import analysis as analysis_route
from schemas.schemas import SessionStatus


class _FakeScalarResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class _FakeScalars:
    def __init__(self, values):
        self._values = values

    def all(self):
        return self._values


class _FakeScalarsResult:
    def __init__(self, values):
        self._values = values

    def scalars(self):
        return _FakeScalars(self._values)


class _FakeDB:
    def __init__(self, results):
        self._results = list(results)

    async def execute(self, _stmt):
        return self._results.pop(0)


def test_get_results_returns_cached_payload(monkeypatch):
    cached_payload = {"session_id": "s1", "status": "completed", "processing_time_ms": 100}

    async def fake_cache_get(_key):
        return cached_payload

    monkeypatch.setattr(analysis_route, "cache_get", fake_cache_get)

    response = asyncio.run(analysis_route.get_results("s1", db=_FakeDB([])))

    assert isinstance(response, JSONResponse)
    assert response.status_code == 200


def test_get_results_reconstructs_from_database(monkeypatch):
    captured = {}

    async def fake_cache_get(_key):
        return None

    async def fake_cache_set(key, value, ttl):
        captured["key"] = key
        captured["value"] = value
        captured["ttl"] = ttl

    monkeypatch.setattr(analysis_route, "cache_get", fake_cache_get)
    monkeypatch.setattr(analysis_route, "cache_set", fake_cache_set)

    now = datetime.now(timezone.utc)
    session = SimpleNamespace(
        id="s1",
        status=SessionStatus.COMPLETED,
        target_role="Backend Engineer",
    )
    profile = SimpleNamespace(
        candidate_name="Khushi",
        current_role="Student",
        years_of_experience=1.5,
        education_level="BTech",
        extracted_skills={
            "python": {
                "skill_id": "python",
                "name": "Python",
                "domain": "technical",
                "proficiency_level": "intermediate",
                "proficiency_score": 0.7,
                "confidence": 0.9,
                "source": "resume",
            }
        },
        jd_required_skills={},
        parsing_confidence=0.89,
    )
    gap = SimpleNamespace(
        overall_readiness_score=0.62,
        critical_gaps=[],
        major_gaps=[],
        minor_gaps=[],
        strength_areas=[],
        domain_coverage=[],
        created_at=now,
    )
    path = SimpleNamespace(
        id="path-1",
        phases=[],
        total_modules=0,
        estimated_hours=0.0,
        estimated_weeks=0.0,
        path_graph={"nodes": [], "edges": []},
        efficiency_score=0.9,
        path_algorithm="topological_dfs",
        path_version=1,
        created_at=now,
    )
    audit_logs = [SimpleNamespace(duration_ms=1200), SimpleNamespace(duration_ms=800)]

    db = _FakeDB(
        [
            _FakeScalarResult(session),
            _FakeScalarResult(profile),
            _FakeScalarResult(gap),
            _FakeScalarResult(path),
            _FakeScalarsResult(audit_logs),
        ]
    )

    response = asyncio.run(analysis_route.get_results("s1", db=db))

    assert response.session_id == "s1"
    assert response.gap_analysis is not None
    assert response.gap_analysis.readiness_label == "Near Ready"
    assert response.processing_time_ms == 2000.0
    assert captured["key"].startswith("asioe:analysis:s1")


def test_get_results_404_when_session_missing(monkeypatch):
    async def fake_cache_get(_key):
        return None

    monkeypatch.setattr(analysis_route, "cache_get", fake_cache_get)

    db = _FakeDB([_FakeScalarResult(None)])

    with pytest.raises(HTTPException) as exc:
        asyncio.run(analysis_route.get_results("missing", db=db))

    assert exc.value.status_code == 404