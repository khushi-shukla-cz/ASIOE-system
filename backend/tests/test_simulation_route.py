import asyncio
from types import SimpleNamespace

from api.routes import simulation as simulation_route
from schemas.schemas import SimulationRequest


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
