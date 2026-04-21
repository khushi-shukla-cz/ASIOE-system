"""
ASIOE — Redis Cache Manager
Handles caching of expensive computations:
- Skill embeddings
- Gap analysis results
- Learning path outputs
"""
from __future__ import annotations

import json
from typing import Any, Dict, Optional

import redis.asyncio as aioredis

from core.config import settings
from core.logging import get_logger

logger = get_logger(__name__)

_redis_client: Optional[aioredis.Redis] = None
_cache_stats: Dict[str, float] = {
    "hits": 0.0,
    "misses": 0.0,
    "sets": 0.0,
    "deletes": 0.0,
    "estimated_saved_processing_ms": 0.0,
}


async def get_redis() -> aioredis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            max_connections=20,
        )
        logger.info("redis.connected")
    return _redis_client


async def close_redis() -> None:
    global _redis_client
    if _redis_client:
        await _redis_client.aclose()
        _redis_client = None
        logger.info("redis.closed")


async def cache_get(key: str) -> Optional[Any]:
    client = await get_redis()
    value = await client.get(key)
    if value:
        _cache_stats["hits"] += 1
        parsed = json.loads(value)
        if isinstance(parsed, dict):
            maybe_saved_ms = parsed.get("processing_time_ms")
            if isinstance(maybe_saved_ms, (int, float)):
                _cache_stats["estimated_saved_processing_ms"] += float(maybe_saved_ms)
        return parsed

    _cache_stats["misses"] += 1
    return None


async def cache_set(key: str, value: Any, ttl: int = settings.CACHE_TTL_SECONDS) -> None:
    client = await get_redis()
    await client.setex(key, ttl, json.dumps(value, default=str))
    _cache_stats["sets"] += 1


async def cache_delete(key: str) -> None:
    client = await get_redis()
    await client.delete(key)
    _cache_stats["deletes"] += 1


async def cache_exists(key: str) -> bool:
    client = await get_redis()
    return bool(await client.exists(key))


def build_cache_key(*parts: str) -> str:
    return "asioe:" + ":".join(str(p) for p in parts)


def get_cache_metrics() -> Dict[str, float]:
    hits = int(_cache_stats["hits"])
    misses = int(_cache_stats["misses"])
    total = hits + misses
    hit_rate = (hits / total) if total else 0.0

    return {
        "hits": hits,
        "misses": misses,
        "total_requests": total,
        "hit_rate_percent": round(hit_rate * 100.0, 2),
        "sets": int(_cache_stats["sets"]),
        "deletes": int(_cache_stats["deletes"]),
        "estimated_saved_processing_ms": round(_cache_stats["estimated_saved_processing_ms"], 2),
    }


def reset_cache_metrics() -> None:
    for key in _cache_stats:
        _cache_stats[key] = 0.0
