"""
ASIOE — Redis Cache Manager
Handles caching of expensive computations:
- Skill embeddings
- Gap analysis results
- Learning path outputs
"""
from __future__ import annotations

import json
from typing import Any, Optional

import redis.asyncio as aioredis

from core.config import settings
from core.logging import get_logger

logger = get_logger(__name__)

_redis_client: Optional[aioredis.Redis] = None


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
        return json.loads(value)
    return None


async def cache_set(key: str, value: Any, ttl: int = settings.CACHE_TTL_SECONDS) -> None:
    client = await get_redis()
    await client.setex(key, ttl, json.dumps(value, default=str))


async def cache_delete(key: str) -> None:
    client = await get_redis()
    await client.delete(key)


async def cache_exists(key: str) -> bool:
    client = await get_redis()
    return bool(await client.exists(key))


def build_cache_key(*parts: str) -> str:
    return "asioe:" + ":".join(str(p) for p in parts)
