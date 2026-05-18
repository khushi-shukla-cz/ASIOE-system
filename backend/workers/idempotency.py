import os
from typing import Optional

import redis

_REDIS = redis.from_url(os.getenv('REDIS_URL', 'redis://localhost:6379/0'))


def acquire_idempotency_key(key: str, ttl_seconds: int = 60 * 60) -> bool:
    """Try to acquire an idempotency key in Redis.

    Returns True if this caller acquired the key (meaning work should proceed).
    Returns False if a key already exists (work should be skipped).
    """
    # SET key NX EX ttl
    return _REDIS.set(name=key, value='1', nx=True, ex=ttl_seconds)


def release_idempotency_key(key: str) -> None:
    try:
        _REDIS.delete(key)
    except Exception:
        pass


def get_idempotency_value(key: str) -> Optional[str]:
    try:
        return _REDIS.get(key)
    except Exception:
        return None
