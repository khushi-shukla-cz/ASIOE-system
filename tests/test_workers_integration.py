import importlib


class FakeRedis:
    def __init__(self):
        self.store = {}
        self.lists = []

    def set(self, name, value, nx=False, ex=None):
        if nx:
            if name in self.store:
                return False
            self.store[name] = value
            return True
        self.store[name] = value
        return True

    def get(self, name):
        return self.store.get(name)

    def delete(self, name):
        self.store.pop(name, None)

    def rpush(self, key, value):
        self.lists.append((key, value))


def test_idempotency_acquire_release(monkeypatch):
    # Ensure backend.workers.idempotency uses our FakeRedis
    import redis as real_redis

    fake = FakeRedis()
    monkeypatch.setattr(real_redis, 'from_url', lambda url: fake)

    idemp = importlib.import_module('backend.workers.idempotency')
    importlib.reload(idemp)

    key = 'test:idemp:1'
    acquired = idemp.acquire_idempotency_key(key, ttl_seconds=10)
    assert acquired is True

    # second acquire should fail
    acquired2 = idemp.acquire_idempotency_key(key, ttl_seconds=10)
    assert acquired2 is False

    # release and acquire again
    idemp.release_idempotency_key(key)
    acquired3 = idemp.acquire_idempotency_key(key, ttl_seconds=10)
    assert acquired3 is True


def test_send_to_dlq_pushes(monkeypatch):
    import redis as real_redis
    fake = FakeRedis()
    monkeypatch.setattr(real_redis, 'from_url', lambda url: fake)

    celery_app = importlib.import_module('backend.workers.celery_app')
    importlib.reload(celery_app)

    # make serializer.dumps a simple identity
    class DummyBackend:
        class serializer:
            @staticmethod
            def dumps(x):
                return str(x)

    celery_app.app.backend = DummyBackend()

    payload = {'session_id': 's1', 'reason': 'test'}
    celery_app.send_to_dlq(payload, redis_url='redis://localhost:6379/0')

    # ensure something was pushed to list
    assert len(fake.lists) == 1
    key, value = fake.lists[0]
    assert key == 'dlq:list'
    assert "session_id'" in value or 'session_id' in value
