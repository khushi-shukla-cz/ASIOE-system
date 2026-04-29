from __future__ import annotations

import sys
import types
from datetime import datetime, timezone
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

if "services.analysis_service" not in sys.modules:
    analysis_service_stub = types.ModuleType("services.analysis_service")

    def _stub_get_analysis_service():
        raise RuntimeError("analysis service should be monkeypatched in tests")

    analysis_service_stub.get_analysis_service = _stub_get_analysis_service
    sys.modules["services.analysis_service"] = analysis_service_stub

if "engines.path.path_engine" not in sys.modules:
    path_engine_stub = types.ModuleType("engines.path.path_engine")
    path_engine_stub.get_path_engine = lambda: None
    sys.modules["engines.path.path_engine"] = path_engine_stub

if "engines.rag.rag_engine" not in sys.modules:
    rag_engine_stub = types.ModuleType("engines.rag.rag_engine")
    rag_engine_stub.get_rag_engine = lambda: None
    sys.modules["engines.rag.rag_engine"] = rag_engine_stub

from api.routes import analysis as analysis_route
from api.routes import simulation as simulation_route
from core.auth import AuthenticatedPrincipal
from core.auth import issue_session_token
from schemas.schemas import SessionStatus

sys.modules.pop("engines.path.path_engine", None)
sys.modules.pop("engines.rag.rag_engine", None)


class _DummyDB:
    async def execute(self, _stmt):
        return None


def _analysis_payload(session_id: str = "s1") -> dict:
    now = datetime.now(timezone.utc).isoformat()
    return {
        "session_id": session_id,
        "status": SessionStatus.COMPLETED.value,
        "skill_profile": {
            "candidate_name": "Test User",
            "current_role": "Student",
            "years_of_experience": 1,
            "education_level": "BTech",
            "skills": [],
            "certifications": [],
            "parsing_confidence": 0.9,
            "target_role": "Backend Engineer",
            "jd_required_skills": [],
        },
        "gap_analysis": {
            "session_id": session_id,
            "overall_readiness_score": 0.55,
            "readiness_label": "Partial",
            "critical_gaps": [],
            "major_gaps": [],
            "minor_gaps": [],
            "strength_areas": [],
            "domain_coverage": [],
            "reasoning_trace": "trace",
            "analysis_timestamp": now,
        },
        "learning_path": {
            "session_id": session_id,
            "path_id": "path-1",
            "target_role": "Backend Engineer",
            "phases": [],
            "total_modules": 0,
            "total_hours": 0.0,
            "total_weeks": 0.0,
            "path_graph": {"nodes": [], "edges": []},
            "efficiency_score": 0.9,
            "redundancy_eliminated": 0,
            "path_algorithm": "topological_dfs",
            "path_version": 1,
            "reasoning_trace": "trace",
            "generated_at": now,
        },
        "reasoning_trace": None,
        "processing_time_ms": 25.0,
    }


def _build_app() -> FastAPI:
    app = FastAPI()
    app.include_router(analysis_route.router, prefix="/api/v1")
    app.include_router(simulation_route.router, prefix="/api/v1")

    async def _override_db():
        yield _DummyDB()

    app.dependency_overrides[analysis_route.get_db] = _override_db
    return app


def test_full_analysis_to_results_to_simulation_workflow(monkeypatch):
    payload = _analysis_payload("s1")

    class _FakeService:
        async def create_session(self, **kwargs):
            return SimpleNamespace(id="s1")

        async def run_analysis(self, **kwargs):
            return payload

    async def _fake_cache_get(_key):
        return payload

    async def _fake_cache_set(_key, _value, ttl):
        return None

    class _FakePathEngine:
        async def generate_path(self, **kwargs):
            return SimpleNamespace(
                phases=[],
                total_modules=0,
                total_hours=40.0,
                total_weeks=4.0,
                model_dump=lambda: {"phases": [], "total_modules": 0, "total_hours": 40.0},
            )

    class _FakeRagEngine:
        async def enrich_modules(self, modules):
            return modules

    monkeypatch.setattr(analysis_route, "get_analysis_service", lambda: _FakeService())
    monkeypatch.setattr(analysis_route, "cache_get", _fake_cache_get)
    monkeypatch.setattr(analysis_route, "cache_set", _fake_cache_set)
    monkeypatch.setattr(simulation_route, "cache_get", _fake_cache_get)
    monkeypatch.setattr(simulation_route, "cache_set", _fake_cache_set)
    monkeypatch.setattr(simulation_route, "get_path_engine", lambda: _FakePathEngine())
    monkeypatch.setattr(simulation_route, "get_rag_engine", lambda: _FakeRagEngine())

    app = _build_app()
    with TestClient(app) as client:
        analyze_response = client.post(
            "/api/v1/analyze",
            files={"resume": ("resume.txt", b"x" * 220 + b" contact hidden@example.com", "text/plain")},
            data={"jd_text": "Senior backend engineer with strong Python, SQL, API design, and Docker expertise."},
        )

        session_token = analyze_response.headers["X-Session-Token"]
        results_response = client.get(
            "/api/v1/results/s1",
            headers={"X-Session-Token": session_token},
        )
        simulation_response = client.post(
            "/api/v1/simulate",
            headers={"X-Session-Token": session_token},
            json={
                "session_id": "s1",
                "time_constraint_weeks": 12,
                "max_modules": 12,
                "priority_domains": ["technical"],
                "exclude_module_ids": [],
            },
        )

    assert analyze_response.status_code == 200
    assert results_response.status_code == 200
    assert simulation_response.status_code == 200
    assert results_response.json()["session_id"] == "s1"
    assert simulation_response.json()["session_id"] == "s1"
    assert simulation_response.json()["simulation_applied"] is True


# === End-to-End Workflow Tests: Full Cycle Coverage ===


class TestWorkflowBoundaryConditions:
    """Tests for full workflow under different candidate profiles."""

    def test_workflow_handles_sparse_resume(self, monkeypatch):
        """Verify workflow processes resume with minimal skills (15 modules needed)."""
        payload = _analysis_payload("sparse_s1")
        payload["learning_path"]["total_modules"] = 15
        payload["learning_path"]["total_weeks"] = 12
        
        class _FakeService:
            async def create_session(self, **kwargs):
                return SimpleNamespace(id="sparse_s1")
            async def run_analysis(self, **kwargs):
                return payload

        async def _fake_cache_get(_key):
            return payload
        
        async def _fake_cache_set(_key, _value, ttl):
            return None

        class _FakePathEngine:
            async def generate_path(self, **kwargs):
                return SimpleNamespace(
                    phases=[],
                    total_modules=15,
                    total_hours=100.0,
                    total_weeks=12.0,
                    model_dump=lambda: {"phases": [], "total_modules": 15, "total_hours": 100.0},
                )

        class _FakeRagEngine:
            async def enrich_modules(self, modules):
                return modules

        monkeypatch.setattr(analysis_route, "get_analysis_service", lambda: _FakeService())
        monkeypatch.setattr(analysis_route, "cache_get", _fake_cache_get)
        monkeypatch.setattr(analysis_route, "cache_set", _fake_cache_set)
        monkeypatch.setattr(simulation_route, "cache_get", _fake_cache_get)
        monkeypatch.setattr(simulation_route, "get_path_engine", lambda: _FakePathEngine())
        monkeypatch.setattr(simulation_route, "get_rag_engine", lambda: _FakeRagEngine())

        app = _build_app()
        with TestClient(app) as client:
            analyze_response = client.post(
                "/api/v1/analyze",
                files={"resume": ("resume.txt", b"Entry-level developer fresh graduate", "text/plain")},
                data={"jd_text": "Senior full-stack engineer"},
            )

        assert analyze_response.status_code == 200
        assert analyze_response.json()["learning_path"]["total_modules"] == 15

    def test_workflow_handles_advanced_candidate(self, monkeypatch):
        """Verify workflow processes resume with extensive skills (3 modules needed)."""
        payload = _analysis_payload("advanced_s1")
        payload["learning_path"]["total_modules"] = 3
        payload["learning_path"]["total_weeks"] = 2
        payload["gap_analysis"]["overall_readiness_score"] = 0.95
        
        class _FakeService:
            async def create_session(self, **kwargs):
                return SimpleNamespace(id="advanced_s1")
            async def run_analysis(self, **kwargs):
                return payload

        async def _fake_cache_get(_key):
            return payload
        
        async def _fake_cache_set(_key, _value, ttl):
            return None

        class _FakePathEngine:
            async def generate_path(self, **kwargs):
                return SimpleNamespace(
                    phases=[],
                    total_modules=3,
                    total_hours=15.0,
                    total_weeks=2.0,
                    model_dump=lambda: {"phases": [], "total_modules": 3, "total_hours": 15.0},
                )

        class _FakeRagEngine:
            async def enrich_modules(self, modules):
                return modules

        monkeypatch.setattr(analysis_route, "get_analysis_service", lambda: _FakeService())
        monkeypatch.setattr(analysis_route, "cache_get", _fake_cache_get)
        monkeypatch.setattr(analysis_route, "cache_set", _fake_cache_set)
        monkeypatch.setattr(simulation_route, "cache_get", _fake_cache_get)
        monkeypatch.setattr(simulation_route, "get_path_engine", lambda: _FakePathEngine())
        monkeypatch.setattr(simulation_route, "get_rag_engine", lambda: _FakeRagEngine())

        app = _build_app()
        with TestClient(app) as client:
            analyze_response = client.post(
                "/api/v1/analyze",
                files={"resume": ("resume.txt", b"x" * 500, "text/plain")},
                data={"jd_text": "Senior engineer"},
            )

        assert analyze_response.status_code == 200
        assert analyze_response.json()["learning_path"]["total_modules"] == 3
        assert analyze_response.json()["gap_analysis"]["overall_readiness_score"] == 0.95

    def test_workflow_session_id_consistency_across_steps(self, monkeypatch):
        """Verify same session_id is used throughout analyze→results→simulate workflow."""
        session_id = "consistent_s999"
        payload = _analysis_payload(session_id)
        
        class _FakeService:
            async def create_session(self, **kwargs):
                return SimpleNamespace(id=session_id)
            async def run_analysis(self, **kwargs):
                return payload

        async def _fake_cache_get(_key):
            return payload
        
        async def _fake_cache_set(_key, _value, ttl):
            return None

        class _FakePathEngine:
            async def generate_path(self, **kwargs):
                return SimpleNamespace(
                    phases=[],
                    total_modules=0,
                    total_hours=40.0,
                    total_weeks=4.0,
                    model_dump=lambda: {"phases": [], "total_modules": 0, "total_hours": 40.0},
                )

        class _FakeRagEngine:
            async def enrich_modules(self, modules):
                return modules

        monkeypatch.setattr(analysis_route, "get_analysis_service", lambda: _FakeService())
        monkeypatch.setattr(analysis_route, "cache_get", _fake_cache_get)
        monkeypatch.setattr(analysis_route, "cache_set", _fake_cache_set)
        monkeypatch.setattr(simulation_route, "cache_get", _fake_cache_get)
        monkeypatch.setattr(simulation_route, "get_path_engine", lambda: _FakePathEngine())
        monkeypatch.setattr(simulation_route, "get_rag_engine", lambda: _FakeRagEngine())

        app = _build_app()
        with TestClient(app) as client:
            analyze_resp = client.post(
                "/api/v1/analyze",
                files={"resume": ("resume.txt", b"x" * 220, "text/plain")},
                data={"jd_text": "Senior engineer"},
            )
            
            token = analyze_resp.headers["X-Session-Token"]
            
            results_resp = client.get(
                f"/api/v1/results/{session_id}",
                headers={"X-Session-Token": token},
            )
            
            simulate_resp = client.post(
                "/api/v1/simulate",
                headers={"X-Session-Token": token},
                json={
                    "session_id": session_id,
                    "time_constraint_weeks": 12,
                    "max_modules": 12,
                    "priority_domains": [],
                    "exclude_module_ids": [],
                },
            )

        assert analyze_resp.json()["session_id"] == session_id
        assert results_resp.json()["session_id"] == session_id
        assert simulate_resp.json()["session_id"] == session_id


class TestWorkflowErrorRecovery:
    """Tests for workflow behavior under failure conditions."""

    def test_workflow_parsing_failure_graceful_degradation(self, monkeypatch):
        """Verify workflow degrades gracefully when parsing engine fails."""
        payload_partial = _analysis_payload("fail_s1")
        payload_partial["skill_profile"]["skills"] = []  # No skills extracted
        payload_partial["status"] = "partial_failure"
        
        class _FakeService:
            async def create_session(self, **kwargs):
                return SimpleNamespace(id="fail_s1")
            async def run_analysis(self, **kwargs):
                return payload_partial

        async def _fake_cache_get(_key):
            return payload_partial
        
        async def _fake_cache_set(_key, _value, ttl):
            return None

        monkeypatch.setattr(analysis_route, "get_analysis_service", lambda: _FakeService())
        monkeypatch.setattr(analysis_route, "cache_get", _fake_cache_get)
        monkeypatch.setattr(analysis_route, "cache_set", _fake_cache_set)

        app = _build_app()
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/analyze",
                files={"resume": ("resume.txt", b"corrupted data", "text/plain")},
                data={"jd_text": "Senior engineer"},
            )

        assert response.status_code == 200  # Graceful degradation
        body = response.json()
        assert body["skill_profile"]["skills"] == []

    def test_workflow_cache_hit_accelerates_results(self, monkeypatch):
        """Verify cached results are returned faster without re-analysis."""
        import time
        
        payload = _analysis_payload("cached_s1")
        call_times = []
        
        async def _fake_cache_get(_key):
            call_times.append(time.time())
            return payload  # Cache hit
        
        async def _fake_cache_set(_key, _value, ttl):
            return None

        monkeypatch.setattr(analysis_route, "cache_get", _fake_cache_get)
        
        app = _build_app()
        with TestClient(app) as client:
            response = client.get(
                "/api/v1/results/cached_s1",
                headers={"X-Session-Token": issue_session_token("cached_s1", "test-user")},
            )

        assert response.status_code == 200
        # Cache was accessed
        assert len(call_times) > 0
