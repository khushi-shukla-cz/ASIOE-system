import os
from celery import Celery

# Broker and backend (Redis)
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

app = Celery(
    'backend_workers',
    broker=REDIS_URL,
    backend=REDIS_URL,
)

# Recommended default config for reliability
app.conf.update(
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_publish_retry=True,
    task_time_limit=60 * 60,  # 1 hour default
    task_soft_time_limit=60 * 50,
)


def send_to_dlq(payload: dict, redis_url: str = REDIS_URL):
    """Push a failing job payload to a simple Redis-backed DLQ list.

    This is a small, robust fallback in absence of a broker-level DLQ.
    Consumers can inspect the `dlq:list` key for failed items.
    """
    try:
        import redis

        r = redis.from_url(redis_url)
        r.rpush('dlq:list', app.backend.serializer.dumps(payload))
    except Exception:
        # Best-effort only; don't raise inside failure handlers
        pass
