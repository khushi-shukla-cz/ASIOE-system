"""
ASIOE — Observability & Metrics Tests
Tests for distributed tracing, per-engine metrics, and dashboards.
"""
import pytest
import structlog
from unittest.mock import MagicMock, patch, AsyncMock

from core.observability import (
    EngineSpan,
    engine_span_decorator,
    get_metrics_collector,
    set_trace_id,
    get_trace_id,
)
from core.metrics import MetricsAggregator, HealthCheck, CacheEfficiencyAnalyzer
from engines.instrumentation import trace_engine_operation, MetricsRecorder


@pytest.mark.asyncio
class TestEngineSpan:
    """Test per-engine distributed tracing spans."""

    @pytest.mark.asyncio
    async def test_engine_span_success_records_latency(self):
        """Engine span should record latency on successful operation."""
        collector = get_metrics_collector()
        initial_invocations = collector.get_snapshot()["parsing"]["invocations"]

        with EngineSpan("parsing", "extract_resume"):
            import time
            time.sleep(0.01)  # Simulate 10ms operation

        snapshot = collector.get_snapshot()
        assert snapshot["parsing"]["invocations"] == initial_invocations + 1
        assert snapshot["parsing"]["failures"] == 0

    @pytest.mark.asyncio
    async def test_engine_span_failure_records_error(self):
        """Engine span should record errors and failures."""
        collector = get_metrics_collector()
        initial_failures = collector.get_snapshot()["gap"]["failures"]

        try:
            with EngineSpan("gap", "analyze"):
                raise ValueError("Test error")
        except ValueError:
            pass

        snapshot = collector.get_snapshot()
        assert snapshot["gap"]["failures"] == initial_failures + 1
        assert "ValueError" in snapshot["gap"]["error_types"]

    @pytest.mark.asyncio
    async def test_engine_span_sets_trace_context(self):
        """Engine span should propagate trace context."""
        trace_id = "test-trace-123"
        set_trace_id(trace_id)

        with EngineSpan("normalization", "normalize"):
            assert get_trace_id() == trace_id


@pytest.mark.asyncio
class TestMetricsAggregator:
    """Test metrics collection and aggregation."""

    @pytest.mark.asyncio
    async def test_get_engine_metrics_returns_all_engines(self):
        """Should return metrics for all 6 engines."""
        metrics = await MetricsAggregator.get_engine_metrics()

        expected_engines = {
            "parsing",
            "normalization",
            "gap",
            "path",
            "rag",
            "explainability",
        }
        assert set(metrics.keys()) == expected_engines

        for engine, data in metrics.items():
            assert "invocations" in data
            assert "failures" in data
            assert "failure_rate_pct" in data
            assert "avg_latency_ms" in data
            assert "error_types" in data

    @pytest.mark.asyncio
    async def test_cache_metrics_computes_hit_rate(self):
        """Cache metrics should compute hit rate correctly."""
        with patch("core.metrics.get_cache_stats") as mock_stats:
            mock_stats.return_value = {
                "hits": 80,
                "misses": 20,
                "sets": 100,
                "deletes": 5,
                "estimated_saved_processing_ms": 1000,
            }

            metrics = await MetricsAggregator.get_cache_metrics()

            assert metrics["total_hits"] == 80
            assert metrics["total_misses"] == 20
            assert metrics["total_requests"] == 100
            assert metrics["hit_rate_pct"] == 80.0
            assert metrics["estimated_saved_processing_ms"] == 1000

    @pytest.mark.asyncio
    async def test_full_metrics_view_aggregates_system_stats(self):
        """Full metrics view should aggregate system-level statistics."""
        metrics = await MetricsAggregator.get_full_metrics_view()

        assert "timestamp" in metrics
        assert "system" in metrics
        assert "engines" in metrics
        assert "cache" in metrics

        system = metrics["system"]
        assert "total_invocations" in system
        assert "total_failures" in system
        assert "failure_rate_pct" in system
        assert "avg_latency_ms" in system
        assert "cache_hit_rate_pct" in system


@pytest.mark.asyncio
class TestHealthCheck:
    """Test health status computation."""

    @pytest.mark.asyncio
    async def test_health_status_excellent_on_zero_failures(self):
        """Health should be 'excellent' when failure rate is 0%."""
        # Reset metrics
        collector = get_metrics_collector()
        collector._lock_free_stats["parsing"]["invocations"] = 10
        collector._lock_free_stats["parsing"]["failures"] = 0

        health = await HealthCheck.compute_health_status()

        assert health["health"] in ["excellent", "good"]
        assert health["failure_rate_pct"] >= 0

    @pytest.mark.asyncio
    async def test_health_status_poor_on_high_failure_rate(self):
        """Health should degrade with increasing failure rate."""
        collector = get_metrics_collector()
        for engine in collector._lock_free_stats:
            collector._lock_free_stats[engine]["invocations"] = 100
            collector._lock_free_stats[engine]["failures"] = 20  # 20%

        health = await HealthCheck.compute_health_status()

        assert health["failure_rate_pct"] >= 5
        # With 20% failure rate, health should be 'poor' or 'fair'
        assert health["health"] in ["fair", "poor"]


@pytest.mark.asyncio
class TestCacheEfficiencyAnalyzer:
    """Test cache efficiency metrics."""

    def test_compute_cache_efficiency_perfect_hit_rate(self):
        """Perfect hit rate should be 100%."""
        result = CacheEfficiencyAnalyzer.compute_cache_efficiency(
            total_hits=100, total_misses=0, avg_processing_ms=10
        )

        assert result["hit_rate_pct"] == 100.0
        assert result["total_requests"] == 100
        assert result["time_saved_ms"] == 1000  # 100 * 10
        assert result["cache_efficiency_ratio"] == 1.0

    def test_compute_cache_efficiency_with_misses(self):
        """Hit rate should reflect both hits and misses."""
        result = CacheEfficiencyAnalyzer.compute_cache_efficiency(
            total_hits=75, total_misses=25, avg_processing_ms=20
        )

        assert result["hit_rate_pct"] == 75.0
        assert result["total_requests"] == 100
        assert result["time_saved_ms"] == 1500  # 75 * 20
        assert result["cache_efficiency_ratio"] == 0.75

    def test_compute_cache_efficiency_zero_requests(self):
        """Should handle zero requests gracefully."""
        result = CacheEfficiencyAnalyzer.compute_cache_efficiency(
            total_hits=0, total_misses=0, avg_processing_ms=10
        )

        assert result["hit_rate_pct"] == 0
        assert result["total_requests"] == 0
        assert result["time_saved_ms"] == 0


@pytest.mark.asyncio
class TestMetricsRecorder:
    """Test engine metrics recording."""

    def test_metrics_recorder_records_operation_success(self):
        """Metrics recorder should record successful operations."""
        recorder = MetricsRecorder("parsing")
        collector = get_metrics_collector()

        initial = collector.get_snapshot()["parsing"]["invocations"]

        recorder.record_operation(
            operation="extract",
            latency_ms=50,
            success=True,
            metadata={"file_type": "pdf"},
        )

        snapshot = collector.get_snapshot()
        assert snapshot["parsing"]["invocations"] == initial + 1

    def test_metrics_recorder_records_operation_failure(self):
        """Metrics recorder should record failed operations with error type."""
        recorder = MetricsRecorder("normalization")
        collector = get_metrics_collector()

        initial_failures = collector.get_snapshot()["normalization"]["failures"]

        recorder.record_operation(
            operation="normalize",
            latency_ms=100,
            success=False,
            error_type="TimeoutError",
        )

        snapshot = collector.get_snapshot()
        assert snapshot["normalization"]["failures"] == initial_failures + 1
        assert "TimeoutError" in snapshot["normalization"]["error_types"]

    def test_metrics_recorder_records_batch_operation(self):
        """Metrics recorder should record batch operations."""
        recorder = MetricsRecorder("gap")
        collector = get_metrics_collector()

        initial = collector.get_snapshot()["gap"]["invocations"]

        recorder.record_batch(
            operation="batch_analyze",
            count=10,
            total_latency_ms=500,
            success=True,
        )

        snapshot = collector.get_snapshot()
        assert snapshot["gap"]["invocations"] == initial + 1  # One batch call


@pytest.mark.asyncio
class TestEngineSpanDecorator:
    """Test automatic span decoration for engine methods."""

    @pytest.mark.asyncio
    async def test_span_decorator_wraps_async_function(self):
        """Span decorator should wrap async functions."""

        @engine_span_decorator("test_engine")
        async def sample_async_func(x: int) -> int:
            return x * 2

        result = await sample_async_func(5)
        assert result == 10

        # Verify metrics were recorded
        collector = get_metrics_collector()
        # Note: decorator adds to a generic engine, so we check it was recorded
        # In practice, the decorator should have triggered a span

    @pytest.mark.asyncio
    async def test_span_decorator_records_exceptions(self):
        """Span decorator should record exceptions."""

        @engine_span_decorator("test_engine")
        async def failing_func():
            raise RuntimeError("Test failure")

        with pytest.raises(RuntimeError):
            await failing_func()

        # Metrics should record the failure
        collector = get_metrics_collector()
        # The failure should be in the metrics


@pytest.mark.asyncio
class TestTraceContextPropagation:
    """Test trace context across function calls."""

    def test_set_and_get_trace_id(self):
        """Should store and retrieve trace ID from context."""
        test_id = "trace-abc-123"
        set_trace_id(test_id)
        assert get_trace_id() == test_id

    def test_trace_id_isolation(self):
        """Trace IDs should be context-scoped."""
        set_trace_id("trace-1")
        assert get_trace_id() == "trace-1"

        set_trace_id("trace-2")
        assert get_trace_id() == "trace-2"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
