from celery_app import app, send_to_dlq
from idempotency import acquire_idempotency_key, release_idempotency_key
import time


@app.task(bind=True, max_retries=5, autoretry_for=(Exception,), retry_backoff=True)
def analyze_job(self, session_id: str, idempotency_key: str, payload: dict):
    """Example analysis worker task.

    - Uses an idempotency key to ensure at-most-once processing per job key.
    - On repeated failures, the payload is pushed to a simple DLQ.
    """
    key = f"idemp:analyze:{idempotency_key}"
    acquired = acquire_idempotency_key(key, ttl_seconds=60 * 60)
    if not acquired:
        # Another worker is processing or already processed this job
        return {'status': 'skipped', 'reason': 'duplicate'}

    try:
        # Placeholder for heavy analysis work
        # Replace with real engine orchestration calls
        time.sleep(2)

        # Simulate writing results to DB / emitting events
        result = {'session_id': session_id, 'status': 'completed'}
        return result

    except Exception as exc:
        try:
            # Let Celery retry according to configuration
            raise self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            # on final failure, push to DLQ for manual inspection
            send_to_dlq({'session_id': session_id, 'payload': payload})
            raise
    finally:
        # release key only after success or terminal failure
        release_idempotency_key(key)
