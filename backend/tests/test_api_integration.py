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
from schemas.schemas import SessionStatus

# Clean up import-time stubs so other test modules can import real engines.
sys.modules.pop("engines.path.path_engine", None)
sys.modules.pop("engines.rag.rag_engine", None)


class _DummyDB:
    async def execute(self, _stmt):
        return None


class _DummyModule:
    def __init__(self, module_id: str):
        self.module_id = module_id


class _DummyPathResult:
    def __init__(self):
        self.phases = [SimpleNamespace(modules=[_DummyModule('m1')])]
        self.total_modules = 1
        self.total_hours = 8.0

    def model_dump(self):
        return {
            'phases': [{'modules': [{'module_id': 'm1'}]}],
            'total_modules': self.total_modules,
            'total_hours': self.total_hours,
        }


def _analysis_payload(session_id: str = 's1') -> dict:
    now = datetime.now(timezone.utc).isoformat()
    return {
        'session_id': session_id,
        'status': SessionStatus.COMPLETED,
        'skill_profile': {
            'candidate_name': 'Test User',
            'current_role': 'Student',
            'years_of_experience': 1,
            'education_level': 'BTech',
            'skills': [],
            'certifications': [],
            'parsing_confidence': 0.9,
            'target_role': 'Backend Engineer',
            'jd_required_skills': [],
        },
        'gap_analysis': {
            'session_id': session_id,
            'overall_readiness_score': 0.55,
            'readiness_label': 'Partial',
            'critical_gaps': [],
            'major_gaps': [],
            'minor_gaps': [],
            'strength_areas': [],
            'domain_coverage': [],
            'reasoning_trace': 'trace',
            'analysis_timestamp': now,
        },
        'learning_path': {
            'session_id': session_id,
            'path_id': 'path-1',
            'target_role': 'Backend Engineer',
            'phases': [],
            'total_modules': 0,
            'total_hours': 0.0,
            'total_weeks': 0.0,
            'path_graph': {'nodes': [], 'edges': []},
            'efficiency_score': 0.9,
            'redundancy_eliminated': 0,
            'path_algorithm': 'topological_dfs',
            'path_version': 1,
            'reasoning_trace': 'trace',
            'generated_at': now,
        },
        'reasoning_trace': None,
        'processing_time_ms': 25.0,
    }


def _build_app() -> FastAPI:
    app = FastAPI()
    app.include_router(analysis_route.router, prefix='/api/v1')
    app.include_router(simulation_route.router, prefix='/api/v1')

    async def _override_db():
        yield _DummyDB()

    app.dependency_overrides[analysis_route.get_db] = _override_db
    app.dependency_overrides[analysis_route.get_current_principal] = lambda: AuthenticatedPrincipal(user_id='test-user')
    app.dependency_overrides[analysis_route.require_session_access] = lambda: AuthenticatedPrincipal(user_id='test-user')
    app.dependency_overrides[simulation_route.get_current_principal] = lambda: AuthenticatedPrincipal(user_id='test-user')

    return app


def test_post_analyze_happy_path(monkeypatch):
    class _FakeService:
        async def create_session(self, **kwargs):
            return SimpleNamespace(id='s1')

        async def run_analysis(self, **kwargs):
            return _analysis_payload('s1')

    monkeypatch.setattr(analysis_route, 'get_analysis_service', lambda: _FakeService())

    app = _build_app()
    with TestClient(app) as client:
        response = client.post(
            '/api/v1/analyze',
            files={'resume': ('resume.txt', b'x' * 220, 'text/plain')},
            data={
                'jd_text': 'Senior backend engineer with strong Python, SQL, API design, and Docker expertise.',
            },
        )

    assert response.status_code == 200
    assert response.json()['session_id'] == 's1'
    assert 'x-session-token' in response.headers


def test_post_analyze_rejects_invalid_upload_type(monkeypatch):
    class _FakeService:
        async def create_session(self, **kwargs):
            return SimpleNamespace(id='s1')

        async def run_analysis(self, **kwargs):
            return _analysis_payload('s1')

    monkeypatch.setattr(analysis_route, 'get_analysis_service', lambda: _FakeService())

    app = _build_app()
    with TestClient(app) as client:
        response = client.post(
            '/api/v1/analyze',
            files={'resume': ('malware.exe', b'bad', 'application/octet-stream')},
            data={
                'jd_text': 'Senior backend engineer with strong Python, SQL, API design, and Docker expertise.',
            },
        )

    assert response.status_code == 422
    assert 'Unsupported file type' in response.json()['detail']


def test_post_analyze_rejects_oversized_upload(monkeypatch):
    class _FakeService:
        async def create_session(self, **kwargs):
            return SimpleNamespace(id='s1')

        async def run_analysis(self, **kwargs):
            return _analysis_payload('s1')

    monkeypatch.setattr(analysis_route, 'get_analysis_service', lambda: _FakeService())
    monkeypatch.setattr(analysis_route, 'MAX_UPLOAD_BYTES', 120)

    app = _build_app()
    with TestClient(app) as client:
        response = client.post(
            '/api/v1/analyze',
            files={'resume': ('resume.txt', b'x' * 121, 'text/plain')},
            data={
                'jd_text': 'Senior backend engineer with strong Python, SQL, API design, and Docker expertise.',
            },
        )

    assert response.status_code == 413
    assert 'File too large' in response.json()['detail']


def test_post_analyze_rejects_near_empty_upload(monkeypatch):
    class _FakeService:
        async def create_session(self, **kwargs):
            return SimpleNamespace(id='s1')

        async def run_analysis(self, **kwargs):
            return _analysis_payload('s1')

    monkeypatch.setattr(analysis_route, 'get_analysis_service', lambda: _FakeService())

    app = _build_app()
    with TestClient(app) as client:
        response = client.post(
            '/api/v1/analyze',
            files={'resume': ('resume.txt', b'x' * 99, 'text/plain')},
            data={
                'jd_text': 'Senior backend engineer with strong Python, SQL, API design, and Docker expertise.',
            },
        )

    assert response.status_code == 422
    assert 'empty or corrupted' in response.json()['detail']


def test_get_results_uses_cached_payload(monkeypatch):
    payload = _analysis_payload('cached-s1')

    async def _fake_cache_get(_key):
        return payload

    monkeypatch.setattr(analysis_route, 'cache_get', _fake_cache_get)

    app = _build_app()
    with TestClient(app) as client:
        response = client.get('/api/v1/results/cached-s1')

    assert response.status_code == 200
    assert response.json()['session_id'] == 'cached-s1'


def test_post_simulate_recomputes_path(monkeypatch):
    async def _fake_cache_get(_key):
        return {
            'gap_analysis': {
                'session_id': 's1',
                'overall_readiness_score': 0.5,
                'readiness_label': 'Partial',
                'critical_gaps': [],
                'major_gaps': [],
                'minor_gaps': [],
                'strength_areas': [],
                'domain_coverage': [],
                'reasoning_trace': 'trace',
                'analysis_timestamp': '2026-04-14T00:00:00Z',
            },
            'skill_profile': {'skills': []},
            'learning_path': {
                'phases': [{'modules': [{'module_id': 'a'}, {'module_id': 'b'}]}],
                'total_hours': 12.0,
            },
        }

    async def _fake_cache_set(_key, _value, ttl):
        return None

    async def _fake_resilience(*, operation_name, func):
        del operation_name
        return await func()

    class _FakePathEngine:
        async def generate_path(self, **kwargs):
            return _DummyPathResult()

    class _FakeRagEngine:
        async def enrich_modules(self, modules):
            return modules

    monkeypatch.setattr(simulation_route, 'cache_get', _fake_cache_get)
    monkeypatch.setattr(simulation_route, 'cache_set', _fake_cache_set)
    monkeypatch.setattr(simulation_route, 'run_with_resilience', _fake_resilience)
    monkeypatch.setattr(simulation_route, 'get_path_engine', lambda: _FakePathEngine())
    monkeypatch.setattr(simulation_route, 'get_rag_engine', lambda: _FakeRagEngine())

    app = _build_app()
    with TestClient(app) as client:
        response = client.post(
            '/api/v1/simulate',
            json={
                'session_id': 's1',
                'time_constraint_weeks': 8,
                'max_modules': 10,
                'priority_domains': ['technical'],
                'exclude_module_ids': [],
            },
        )

    assert response.status_code == 200
    assert response.json()['simulation_applied'] is True
    assert response.json()['max_modules'] == 10
