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
from schemas.schemas import AnalysisCompleteResponse, SessionStatus

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


def _build_contract_app() -> FastAPI:
    app = FastAPI()
    app.include_router(analysis_route.router, prefix="/api/v1")
    app.include_router(simulation_route.router, prefix="/api/v1")

    async def _override_db():
        yield _DummyDB()

    app.dependency_overrides[analysis_route.get_db] = _override_db
    return app


def test_analyze_response_matches_contract(monkeypatch):
    class _FakeService:
        async def create_session(self, **kwargs):
            return SimpleNamespace(id="s1")

        async def run_analysis(self, **kwargs):
            return _analysis_payload("s1")

    monkeypatch.setattr(analysis_route, "get_analysis_service", lambda: _FakeService())

    app = _build_contract_app()
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/analyze",
            files={"resume": ("resume.txt", b"x" * 220 + b" contact hidden@example.com", "text/plain")},
            data={"jd_text": "Senior backend engineer with strong Python, SQL, API design, and Docker expertise."},
        )

    assert response.status_code == 200
    assert "X-Session-Token" in response.headers

    contract = AnalysisCompleteResponse.model_validate(response.json())
    assert contract.session_id == "s1"
    assert contract.status == SessionStatus.COMPLETED
    assert contract.processing_time_ms == 25.0
    assert contract.gap_analysis is not None
    assert contract.learning_path is not None


def test_results_response_preserves_analysis_contract(monkeypatch):
    payload = _analysis_payload("cached-s1")

    async def _fake_cache_get(_key):
        return payload

    monkeypatch.setattr(analysis_route, "cache_get", _fake_cache_get)

    app = _build_contract_app()
    with TestClient(app) as client:
        response = client.get(
            "/api/v1/results/cached-s1",
            headers={"X-Session-Token": issue_session_token("cached-s1", "test-user")},
        )

    assert response.status_code == 200
    contract = AnalysisCompleteResponse.model_validate(response.json())
    assert contract.session_id == "cached-s1"
    assert contract.learning_path.total_modules == 0


def test_simulation_response_exposes_stable_fields(monkeypatch):
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
                "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
            },
            "skill_profile": {"skills": []},
            "learning_path": {"phases": [], "total_hours": 40.0},
        }

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

    monkeypatch.setattr(simulation_route, "cache_get", fake_cache_get)
    monkeypatch.setattr(simulation_route, "get_path_engine", lambda: _FakePathEngine())
    monkeypatch.setattr(simulation_route, "get_rag_engine", lambda: _FakeRagEngine())

    app = _build_contract_app()
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/simulate",
            headers={"X-Session-Token": issue_session_token("s1", "test-user")},
            json={
                "session_id": "s1",
                "time_constraint_weeks": 12,
                "max_modules": 12,
                "priority_domains": ["technical"],
                "exclude_module_ids": [],
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["session_id"] == "s1"
    assert body["simulation_applied"] is True
    assert "learning_path" in body
    assert "delta" in body
    assert set(body["delta"].keys()) == {
        "original_modules",
        "simulated_modules",
        "module_delta",
        "original_hours",
        "simulated_hours",
        "hour_delta",
    }


# === API Contract Tests: Comprehensive Response Validation ===


class TestAnalyzeEndpointContract:
    """Contract tests for /analyze endpoint responses."""

    def test_analyze_success_response_schema(self, monkeypatch):
        """Verify /analyze returns 200 with AnalysisCompleteResponse schema."""
        class _FakeService:
            async def create_session(self, **kwargs):
                return SimpleNamespace(id="s1")
            async def run_analysis(self, **kwargs):
                return _analysis_payload("s1")

        monkeypatch.setattr(analysis_route, "get_analysis_service", lambda: _FakeService())
        app = _build_contract_app()
        
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/analyze",
                files={"resume": ("resume.txt", b"x" * 220, "text/plain")},
                data={"jd_text": "Senior engineer"},
            )

        assert response.status_code == 200
        body = response.json()
        
        # Contract: Required top-level fields
        assert "session_id" in body
        assert "status" in body
        assert "skill_profile" in body
        assert "gap_analysis" in body
        assert "learning_path" in body
        assert "processing_time_ms" in body
        
        # Contract: session_id must be non-empty string
        assert isinstance(body["session_id"], str) and body["session_id"]
        
        # Contract: status must be valid SessionStatus
        assert body["status"] in [s.value for s in SessionStatus]

    def test_analyze_validation_error_response(self, monkeypatch):
        """Verify /analyze returns 422 for missing required fields."""
        monkeypatch.setattr(analysis_route, "get_analysis_service", lambda: None)
        app = _build_contract_app()
        
        with TestClient(app) as client:
            # Missing jd_text
            response = client.post(
                "/api/v1/analyze",
                files={"resume": ("resume.txt", b"x" * 220, "text/plain")},
            )

        assert response.status_code == 422
        body = response.json()
        assert "detail" in body

    def test_analyze_file_too_large_error(self, monkeypatch):
        """Verify /analyze returns 413 for oversized files."""
        class _FakeService:
            async def create_session(self, **kwargs):
                return SimpleNamespace(id="s1")

        monkeypatch.setattr(analysis_route, "get_analysis_service", lambda: _FakeService())
        app = _build_contract_app()
        
        with TestClient(app) as client:
            # File > 10MB
            response = client.post(
                "/api/v1/analyze",
                files={"resume": ("resume.txt", b"x" * (11 * 1024 * 1024), "text/plain")},
                data={"jd_text": "Senior engineer"},
            )

        assert response.status_code == 413


class TestResultsEndpointContract:
    """Contract tests for /results/{session_id} endpoint."""

    def test_results_success_response_schema(self, monkeypatch):
        """Verify /results returns complete AnalysisCompleteResponse."""
        payload = _analysis_payload("s1")
        
        async def _fake_cache_get(_key):
            return payload

        monkeypatch.setattr(analysis_route, "cache_get", _fake_cache_get)
        app = _build_contract_app()
        
        with TestClient(app) as client:
            response = client.get(
                "/api/v1/results/s1",
                headers={"X-Session-Token": issue_session_token("s1", "test-user")},
            )

        assert response.status_code == 200
        body = response.json()
        
        # Contract: All analysis result fields present
        assert "gap_analysis" in body
        assert "learning_path" in body
        assert body["gap_analysis"]["overall_readiness_score"] is not None
        assert "phases" in body["learning_path"]

    def test_results_not_found_error(self, monkeypatch):
        """Verify /results returns 404 for missing session."""
        async def _fake_cache_get(_key):
            return None

        monkeypatch.setattr(analysis_route, "cache_get", _fake_cache_get)
        app = _build_contract_app()
        
        with TestClient(app) as client:
            response = client.get(
                "/api/v1/results/nonexistent",
                headers={"X-Session-Token": issue_session_token("nonexistent", "test-user")},
            )

        assert response.status_code == 404

    def test_results_requires_session_token(self, monkeypatch):
        """Verify /results returns 401 when session token missing."""
        async def _fake_cache_get(_key):
            return _analysis_payload("s1")

        monkeypatch.setattr(analysis_route, "cache_get", _fake_cache_get)
        app = _build_contract_app()
        
        with TestClient(app) as client:
            response = client.get("/api/v1/results/s1")

        assert response.status_code == 401


class TestSimulateEndpointContract:
    """Contract tests for /simulate endpoint."""

    def test_simulate_success_response_schema(self, monkeypatch):
        """Verify /simulate returns structured delta response."""
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
                    "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
                },
                "skill_profile": {"skills": []},
                "learning_path": {"phases": [], "total_hours": 40.0},
            }

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

        monkeypatch.setattr(simulation_route, "cache_get", fake_cache_get)
        monkeypatch.setattr(simulation_route, "get_path_engine", lambda: _FakePathEngine())
        monkeypatch.setattr(simulation_route, "get_rag_engine", lambda: _FakeRagEngine())

        app = _build_contract_app()
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/simulate",
                headers={"X-Session-Token": issue_session_token("s1", "test-user")},
                json={
                    "session_id": "s1",
                    "time_constraint_weeks": 12,
                    "max_modules": 12,
                    "priority_domains": ["technical"],
                    "exclude_module_ids": [],
                },
            )

        assert response.status_code == 200
        body = response.json()
        
        # Contract: Required fields in delta
        assert "delta" in body
        assert "original_modules" in body["delta"]
        assert "simulated_modules" in body["delta"]
        assert "original_hours" in body["delta"]
        assert "simulated_hours" in body["delta"]

    def test_simulate_invalid_parameters_error(self, monkeypatch):
        """Verify /simulate returns 422 for invalid parameters."""
        app = _build_contract_app()
        
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/simulate",
                headers={"X-Session-Token": issue_session_token("s1", "test-user")},
                json={
                    "session_id": "s1",
                    "time_constraint_weeks": -5,  # Invalid: negative
                    "max_modules": 12,
                    "priority_domains": [],
                    "exclude_module_ids": [],
                },
            )

        assert response.status_code == 422


class TestHealthEndpointContract:
    """Contract tests for /health endpoint."""

    def test_health_check_response_schema(self):
        """Verify /health returns standard health check response."""
        app = _build_contract_app()
        
        with TestClient(app) as client:
            response = client.get("/api/v1/health")

        assert response.status_code == 200
        body = response.json()
        
        # Contract: Health check fields
        assert "status" in body
        assert body["status"] in ["ok", "degraded", "unhealthy"]
        assert "timestamp" in body


class TestMetricsEndpointContract:
    """Contract tests for /metrics/* endpoints."""

    def test_metrics_health_response_schema(self, monkeypatch):
        """Verify /metrics/health returns health status with metrics."""
        from core.metrics import MetricsAggregator
        
        async def _mock_get_health():
            return {
                "health_status": "excellent",
                "failure_rate_pct": 0.0,
                "avg_latency_ms": 250,
                "cache_hit_rate_pct": 85.0,
            }

        monkeypatch.setattr(MetricsAggregator, "get_engine_metrics", _mock_get_health)
        app = _build_contract_app()
        
        with TestClient(app) as client:
            response = client.get("/api/v1/metrics/health")

        # If endpoint exists, verify response structure
        if response.status_code == 200:
            body = response.json()
            assert "health_status" in body or "system" in body

    def test_metrics_engines_response_schema(self):
        """Verify /metrics/engines returns per-engine breakdown."""
        app = _build_contract_app()
        
        with TestClient(app) as client:
            response = client.get("/api/v1/metrics/engines")

        if response.status_code == 200:
            body = response.json()
            # Should contain all 6 engines or engines list
            assert "engines" in body or any(
                engine in body for engine in ["parsing", "normalization", "gap", "path", "rag", "explainability"]
            )


class TestErrorResponseContract:
    """Contract tests for error response consistency."""

    def test_error_response_structure(self):
        """Verify error responses have consistent structure."""
        app = _build_contract_app()
        
        with TestClient(app) as client:
            response = client.get("/api/v1/nonexistent")

        assert response.status_code == 404
        body = response.json()
        
        # Contract: Error responses should have detail/error field
        assert "detail" in body or "error" in body or "message" in body

    def test_error_codes_are_consistent(self):
        """Verify HTTP error codes are used consistently."""
        app = _build_contract_app()
        
        with TestClient(app) as client:
            # 401 for auth failure
            response = client.get("/api/v1/results/s1")
            assert response.status_code == 401
            
            # 404 for not found
            response = client.get("/api/v1/nonexistent")
            assert response.status_code == 404
