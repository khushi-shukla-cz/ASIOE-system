import os
import sys
import types
from importlib import import_module
from pathlib import Path


# Ensure required settings can load in test environments without real secrets.
os.environ.setdefault("SECRET_KEY", "test_secret_key_123456789012345678901234")
os.environ.setdefault("POSTGRES_PASSWORD", "test_postgres_password")
os.environ.setdefault("NEO4J_PASSWORD", "test_neo4j_password")
os.environ.setdefault("GROQ_API_KEY", "gsk_test_key")


# Provide lightweight fallbacks so unit tests can run even when optional
# production dependencies are not installed in the active local environment.
def _has_module(name: str) -> bool:
	try:
		import_module(name)
		return True
	except ModuleNotFoundError:
		return False


if not _has_module("structlog"):
	structlog_stub = types.ModuleType("structlog")

	class _NoOpLogger:
		def debug(self, *args, **kwargs):
			return None

		def info(self, *args, **kwargs):
			return None

		def warning(self, *args, **kwargs):
			return None

		def error(self, *args, **kwargs):
			return None

		def exception(self, *args, **kwargs):
			return None

	structlog_stub.get_logger = lambda *args, **kwargs: _NoOpLogger()
	structlog_stub.configure = lambda *args, **kwargs: None
	structlog_stub.make_filtering_bound_logger = lambda *args, **kwargs: _NoOpLogger
	structlog_stub.PrintLoggerFactory = lambda *args, **kwargs: object()
	structlog_stub.BoundLogger = _NoOpLogger

	structlog_contextvars = types.ModuleType("structlog.contextvars")
	structlog_contextvars.merge_contextvars = lambda logger, method_name, event_dict: event_dict

	structlog_stdlib = types.ModuleType("structlog.stdlib")
	structlog_stdlib.add_log_level = lambda logger, method_name, event_dict: event_dict
	structlog_stdlib.add_logger_name = lambda logger, method_name, event_dict: event_dict

	structlog_processors = types.ModuleType("structlog.processors")

	class _TimeStamper:
		def __init__(self, *args, **kwargs):
			return None

		def __call__(self, logger, method_name, event_dict):
			return event_dict

	structlog_processors.TimeStamper = _TimeStamper
	structlog_processors.dict_tracebacks = lambda logger, method_name, event_dict: event_dict
	structlog_processors.JSONRenderer = lambda *args, **kwargs: (lambda logger, method_name, event_dict: event_dict)

	structlog_dev = types.ModuleType("structlog.dev")
	structlog_dev.ConsoleRenderer = lambda *args, **kwargs: (lambda logger, method_name, event_dict: event_dict)

	structlog_types = types.ModuleType("structlog.types")
	structlog_types.EventDict = dict
	structlog_types.Processor = object

	structlog_stub.contextvars = structlog_contextvars
	structlog_stub.stdlib = structlog_stdlib
	structlog_stub.processors = structlog_processors
	structlog_stub.dev = structlog_dev

	sys.modules["structlog"] = structlog_stub
	sys.modules["structlog.contextvars"] = structlog_contextvars
	sys.modules["structlog.stdlib"] = structlog_stdlib
	sys.modules["structlog.processors"] = structlog_processors
	sys.modules["structlog.dev"] = structlog_dev
	sys.modules["structlog.types"] = structlog_types

if not _has_module("fitz"):
	fitz_stub = types.ModuleType("fitz")
	fitz_stub.open = lambda *args, **kwargs: None
	sys.modules["fitz"] = fitz_stub

if not _has_module("pdfplumber"):
	pdfplumber_stub = types.ModuleType("pdfplumber")
	pdfplumber_stub.open = lambda *args, **kwargs: None
	sys.modules["pdfplumber"] = pdfplumber_stub

if not _has_module("groq"):
	groq_stub = types.ModuleType("groq")

	class _AsyncGroq:
		def __init__(self, *args, **kwargs):
			return None

	groq_stub.AsyncGroq = _AsyncGroq
	sys.modules["groq"] = groq_stub

if not _has_module("redis"):
	redis_stub = types.ModuleType("redis")
	redis_asyncio_stub = types.ModuleType("redis.asyncio")

	class _FakeRedisClient:
		async def get(self, *args, **kwargs):
			return None

		async def setex(self, *args, **kwargs):
			return True

		async def delete(self, *args, **kwargs):
			return 1

		async def exists(self, *args, **kwargs):
			return 0

		async def aclose(self):
			return None

	class _RedisFactory:
		@staticmethod
		def from_url(*args, **kwargs):
			return _FakeRedisClient()

	redis_asyncio_stub.from_url = _RedisFactory.from_url
	redis_asyncio_stub.Redis = _FakeRedisClient
	redis_stub.asyncio = redis_asyncio_stub

	sys.modules["redis"] = redis_stub
	sys.modules["redis.asyncio"] = redis_asyncio_stub

if not _has_module("sentence_transformers"):
	st_stub = types.ModuleType("sentence_transformers")

	class _SentenceTransformer:
		def __init__(self, *args, **kwargs):
			return None

		def encode(self, *args, **kwargs):
			return []

	st_stub.SentenceTransformer = _SentenceTransformer
	sys.modules["sentence_transformers"] = st_stub


# Allow imports like `core.*`, `engines.*`, and `backend.*` during tests.
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))
