import asyncio
import sys
import types
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

if "services.analysis_service" not in sys.modules:
    analysis_service_stub = types.ModuleType("services.analysis_service")

    def _stub_get_analysis_service():
        raise RuntimeError("analysis service should be monkeypatched in tests")

    analysis_service_stub.get_analysis_service = _stub_get_analysis_service
    sys.modules["services.analysis_service"] = analysis_service_stub

from api.routes import analysis as analysis_route


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
    def __init__(self, values):
        self._values = values

    async def execute(self, _stmt):
        return _FakeScalarsResult(self._values)


def test_get_metrics_returns_percentiles_and_distribution():
    logs = [
        SimpleNamespace(
            engine="parser",
            operation="parse.resume",
            duration_ms=100.0,
            success=True,
            input_tokens=10,
            output_tokens=5,
        ),
        SimpleNamespace(
            engine="parser",
            operation="parse.jd",
            duration_ms=200.0,
            success=True,
            input_tokens=8,
            output_tokens=7,
        ),
        SimpleNamespace(
            engine="gap",
            operation="gap.compute",
            duration_ms=300.0,
            success=False,
            input_tokens=0,
            output_tokens=0,
        ),
        SimpleNamespace(
            engine="path",
            operation="path.generate",
            duration_ms=400.0,
            success=True,
            input_tokens=0,
            output_tokens=0,
        ),
    ]

    analysis_route.get_cache_metrics = lambda: {
        "hits": 7,
        "misses": 3,
        "total_requests": 10,
        "hit_rate_percent": 70.0,
        "sets": 4,
        "deletes": 1,
        "estimated_saved_processing_ms": 2400.0,
    }

    response = asyncio.run(analysis_route.get_metrics("s1", db=_FakeDB(logs)))

    assert response["session_id"] == "s1"
    assert response["total_processing_ms"] == 1000.0
    assert response["total_tokens_used"] == 30
    assert response["all_engines_succeeded"] is False

    assert response["latency_ms"]["p50"] == 250.0
    assert response["latency_ms"]["p95"] == 385.0
    assert response["latency_ms"]["min"] == 100.0
    assert response["latency_ms"]["max"] == 400.0

    parser_stats = response["engine_distribution"]["parser"]
    assert parser_stats["count"] == 2
    assert parser_stats["total_duration_ms"] == 300.0
    assert parser_stats["avg_duration_ms"] == 150.0
    assert parser_stats["failures"] == 0

    gap_stats = response["engine_distribution"]["gap"]
    assert gap_stats["failures"] == 1

    assert response["cache"]["hits"] == 7
    assert response["cache"]["misses"] == 3
    assert response["cache"]["hit_rate_percent"] == 70.0
    assert response["cache"]["estimated_saved_processing_ms"] == 2400.0


def test_get_metrics_404_when_no_logs():
    with pytest.raises(HTTPException) as exc:
        asyncio.run(analysis_route.get_metrics("missing", db=_FakeDB([])))

    assert exc.value.status_code == 404
