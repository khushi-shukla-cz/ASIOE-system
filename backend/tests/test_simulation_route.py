import asyncio
import sys
import types
from types import SimpleNamespace

import pytest

if "engines.path.path_engine" not in sys.modules:
    path_engine_stub = types.ModuleType("engines.path.path_engine")
    path_engine_stub.get_path_engine = lambda: None
    sys.modules["engines.path.path_engine"] = path_engine_stub

if "engines.rag.rag_engine" not in sys.modules:
    rag_engine_stub = types.ModuleType("engines.rag.rag_engine")
    rag_engine_stub.get_rag_engine = lambda: None
    sys.modules["engines.rag.rag_engine"] = rag_engine_stub

from api.routes import simulation as simulation_route
from core.auth import AuthenticatedPrincipal
from core.config import settings
from schemas.schemas import SimulationRequest

# Clean up import-time stubs so other test modules can import real engines.
sys.modules.pop("engines.path.path_engine", None)
sys.modules.pop("engines.rag.rag_engine", None)


class _DummyModule:
    def __init__(self, module_id: str):
        self.module_id = module_id


class _DummyPathResult:
    def __init__(self):
        self.phases = [
            SimpleNamespace(modules=[_DummyModule("m1"), _DummyModule("m2")]),
            SimpleNamespace(modules=[_DummyModule("m3")]),
        ]
        self.total_modules = 3
        self.total_hours = 24.0

    def model_dump(self):
        return {
            "phases": [
                {"modules": [{"module_id": "m1"}, {"module_id": "m2"}]},
                {"modules": [{"module_id": "m3"}]},
            ],
            "total_modules": self.total_modules,
            "total_hours": self.total_hours,
        }


def test_simulation_honors_max_modules(monkeypatch):
    captured = {}

    async def fake_cache_get(_key):
        return {
            "gap_analysis": {
                "session_id": "s1",
                "overall_readiness_score": 0.5,
                "readiness_label": "Partial",
                "critical_gaps": [],
                "major_gaps": [],
                "minor_gaps": [],
                "strength_areas": [],
                "domain_coverage": [],
                "reasoning_trace": "trace",
                "analysis_timestamp": "2026-04-07T00:00:00",
            },
            "skill_profile": {
                "skills": [],
            },
            "learning_path": {
                "phases": [
                    {"modules": [{"module_id": "a"}, {"module_id": "b"}]},
                    {"modules": [{"module_id": "c"}]},
                ],
                "total_hours": 40.0,
            },
        }

    async def fake_cache_set(_key, _value, ttl):
        captured["ttl"] = ttl

    class _FakePathEngine:
        async def generate_path(self, **kwargs):
            captured["max_modules"] = kwargs["max_modules"]
            return _DummyPathResult()

    class _FakeRagEngine:
        async def enrich_modules(self, modules):
            return modules

    monkeypatch.setattr(simulation_route, "cache_get", fake_cache_get)
    monkeypatch.setattr(simulation_route, "cache_set", fake_cache_set)
    monkeypatch.setattr(simulation_route, "get_path_engine", lambda: _FakePathEngine())
    monkeypatch.setattr(simulation_route, "get_rag_engine", lambda: _FakeRagEngine())

    request = SimulationRequest(
        session_id="s1",
        time_constraint_weeks=12,
        max_modules=12,
        priority_domains=["technical"],
        exclude_module_ids=[],
    )

    response = asyncio.run(simulation_route.simulate(request))

    assert captured["max_modules"] == 12
    assert response["max_modules"] == 12
    assert response["delta"]["original_modules"] == 3
    assert response["delta"]["simulated_modules"] == 3
    assert response["delta"]["module_delta"] == 0


def test_simulation_requires_session_token_when_auth_enabled(monkeypatch):
    monkeypatch.setattr(settings, "AUTH_ENABLED", True)

    request = SimulationRequest(
        session_id="s1",
        time_constraint_weeks=12,
        max_modules=12,
        priority_domains=["technical"],
        exclude_module_ids=[],
    )

    with pytest.raises(simulation_route.HTTPException) as exc:
        asyncio.run(
            simulation_route.simulate(
                request,
                principal=AuthenticatedPrincipal(user_id="test-user"),
                x_session_token=None,
            )
        )

    assert exc.value.status_code == 401
    assert "X-Session-Token header is required" in str(exc.value.detail)


def test_simulation_ignores_invalid_token_when_auth_disabled(monkeypatch):
    monkeypatch.setattr(settings, "AUTH_ENABLED", False)

    captured = {}

    async def fake_cache_get(_key):
        return {
            "gap_analysis": {
                "session_id": "s1",
                "overall_readiness_score": 0.5,
                "readiness_label": "Partial",
                "critical_gaps": [],
                "major_gaps": [],
                "minor_gaps": [],
                "strength_areas": [],
                "domain_coverage": [],
                "reasoning_trace": "trace",
                "analysis_timestamp": "2026-04-07T00:00:00",
            },
            "skill_profile": {
                "skills": [],
            },
            "learning_path": {
                "phases": [
                    {"modules": [{"module_id": "a"}, {"module_id": "b"}]},
                    {"modules": [{"module_id": "c"}]},
                ],
                "total_hours": 40.0,
            },
        }

    async def fake_cache_set(_key, _value, ttl):
        captured["ttl"] = ttl

    class _FakePathEngine:
        async def generate_path(self, **kwargs):
            captured["max_modules"] = kwargs["max_modules"]
            return _DummyPathResult()

    class _FakeRagEngine:
        async def enrich_modules(self, modules):
            return modules

    monkeypatch.setattr(simulation_route, "cache_get", fake_cache_get)
    monkeypatch.setattr(simulation_route, "cache_set", fake_cache_set)
    monkeypatch.setattr(simulation_route, "get_path_engine", lambda: _FakePathEngine())
    monkeypatch.setattr(simulation_route, "get_rag_engine", lambda: _FakeRagEngine())

    request = SimulationRequest(
        session_id="s1",
        time_constraint_weeks=12,
        max_modules=12,
        priority_domains=["technical"],
        exclude_module_ids=[],
    )

    response = asyncio.run(
        simulation_route.simulate(
            request,
            principal=AuthenticatedPrincipal(user_id="test-user"),
            x_session_token="invalid-token",
        )
    )

    assert response["session_id"] == "s1"
    assert captured["max_modules"] == 12
