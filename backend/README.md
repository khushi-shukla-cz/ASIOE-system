Backend worker & upload run instructions

1. Start Redis (local):

```bash
docker run -p 6379:6379 -d redis:7
```

2. Start Celery worker (from repo root):

```bash
cd backend
celery -A workers.celery_app.app worker --loglevel=info
```

3. API usage (async scheduling):
- POST `/api/v1/analyze` with form `idempotency_key` to schedule background work. Uploaded resume is saved under `backend/uploads/{session_id}/` and the worker receives a lightweight `blob_path` reference.
