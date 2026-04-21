import asyncio

from db import cache as cache_module


class _FakeRedisClient:
    def __init__(self):
        self._store = {}

    async def get(self, key):
        return self._store.get(key)

    async def setex(self, key, _ttl, value):
        self._store[key] = value
        return True

    async def delete(self, key):
        self._store.pop(key, None)
        return 1

    async def exists(self, key):
        return 1 if key in self._store else 0


async def _run_cache_flow():
    fake = _FakeRedisClient()

    async def _fake_get_redis():
        return fake

    cache_module.reset_cache_metrics()
    cache_module.get_redis = _fake_get_redis

    key = cache_module.build_cache_key("analysis", "s1")
    await cache_module.cache_set(key, {"processing_time_ms": 300.0}, ttl=10)

    hit_payload = await cache_module.cache_get(key)
    miss_payload = await cache_module.cache_get("asioe:analysis:missing")

    metrics = cache_module.get_cache_metrics()
    return hit_payload, miss_payload, metrics


def test_cache_metrics_track_hits_misses_and_estimated_savings():
    hit_payload, miss_payload, metrics = asyncio.run(_run_cache_flow())

    assert hit_payload["processing_time_ms"] == 300.0
    assert miss_payload is None

    assert metrics["hits"] == 1
    assert metrics["misses"] == 1
    assert metrics["total_requests"] == 2
    assert metrics["hit_rate_percent"] == 50.0
    assert metrics["sets"] == 1
    assert metrics["estimated_saved_processing_ms"] == 300.0
