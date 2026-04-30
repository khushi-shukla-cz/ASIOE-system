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


if not _has_module("opentelemetry"):
	opentelemetry_stub = types.ModuleType("opentelemetry")
	opentelemetry_trace_stub = types.ModuleType("opentelemetry.trace")
	opentelemetry_metrics_stub = types.ModuleType("opentelemetry.metrics")
	opentelemetry_exporter_stub = types.ModuleType("opentelemetry.exporter")
	opentelemetry_exporter_jaeger_stub = types.ModuleType("opentelemetry.exporter.jaeger")
	opentelemetry_exporter_jaeger_thrift_stub = types.ModuleType("opentelemetry.exporter.jaeger.thrift")
	opentelemetry_exporter_prometheus_stub = types.ModuleType("opentelemetry.exporter.prometheus")
	opentelemetry_sdk_stub = types.ModuleType("opentelemetry.sdk")
	opentelemetry_sdk_trace_stub = types.ModuleType("opentelemetry.sdk.trace")
	opentelemetry_sdk_trace_export_stub = types.ModuleType("opentelemetry.sdk.trace.export")
	opentelemetry_sdk_metrics_stub = types.ModuleType("opentelemetry.sdk.metrics")
	opentelemetry_sdk_resources_stub = types.ModuleType("opentelemetry.sdk.resources")
	opentelemetry_instrumentation_stub = types.ModuleType("opentelemetry.instrumentation")
	opentelemetry_instrumentation_fastapi_stub = types.ModuleType("opentelemetry.instrumentation.fastapi")
	opentelemetry_instrumentation_sqlalchemy_stub = types.ModuleType("opentelemetry.instrumentation.sqlalchemy")
	opentelemetry_instrumentation_redis_stub = types.ModuleType("opentelemetry.instrumentation.redis")
	opentelemetry_instrumentation_requests_stub = types.ModuleType("opentelemetry.instrumentation.requests")

	class _NoOpSpan:
		def __init__(self, *args, **kwargs):
			self.attributes = {}

		def __enter__(self):
			return self

		def __exit__(self, exc_type, exc_val, exc_tb):
			return False

		def set_attribute(self, key, value):
			self.attributes[key] = value

	class _NoOpTracer:
		def start_span(self, *args, **kwargs):
			return _NoOpSpan()

	class _NoOpTracerProvider:
		def __init__(self, *args, **kwargs):
			return None

		def add_span_processor(self, *args, **kwargs):
			return None

	class _NoOpMetricProvider:
		def __init__(self, *args, **kwargs):
			return None

	class _NoOpResource:
		@staticmethod
		def create(*args, **kwargs):
			return _NoOpResource()

	class _NoOpFastAPIInstrumentor:
		@staticmethod
		def instrument_app(*args, **kwargs):
			return None

		@staticmethod
		def uninstrument_app(*args, **kwargs):
			return None

	class _NoOpInstrumentor:
		def instrument(self, *args, **kwargs):
			return None

	class _NoOpExporter:
		def __init__(self, *args, **kwargs):
			return None

	class _NoOpBatchProcessor:
		def __init__(self, *args, **kwargs):
			return None

	def _set_tracer_provider(*args, **kwargs):
		return None

	def _get_tracer(*args, **kwargs):
		return _NoOpTracer()

	def _set_meter_provider(*args, **kwargs):
		return None

	opentelemetry_trace_stub.get_tracer = _get_tracer
	opentelemetry_trace_stub.set_tracer_provider = _set_tracer_provider
	opentelemetry_metrics_stub.set_meter_provider = _set_meter_provider
	opentelemetry_exporter_jaeger_thrift_stub.JaegerExporter = _NoOpExporter
	opentelemetry_exporter_prometheus_stub.PrometheusMetricReader = _NoOpExporter
	opentelemetry_sdk_trace_stub.TracerProvider = _NoOpTracerProvider
	opentelemetry_sdk_trace_export_stub.BatchSpanProcessor = _NoOpBatchProcessor
	opentelemetry_sdk_metrics_stub.MeterProvider = _NoOpMetricProvider
	opentelemetry_sdk_resources_stub.Resource = _NoOpResource
	opentelemetry_instrumentation_fastapi_stub.FastAPIInstrumentor = _NoOpFastAPIInstrumentor
	opentelemetry_instrumentation_sqlalchemy_stub.SQLAlchemyInstrumentor = _NoOpInstrumentor
	opentelemetry_instrumentation_redis_stub.RedisInstrumentor = _NoOpInstrumentor
	opentelemetry_instrumentation_requests_stub.RequestsInstrumentor = _NoOpInstrumentor

	opentelemetry_stub.trace = opentelemetry_trace_stub
	opentelemetry_stub.metrics = opentelemetry_metrics_stub
	opentelemetry_stub.exporter = opentelemetry_exporter_stub
	opentelemetry_stub.sdk = opentelemetry_sdk_stub
	opentelemetry_stub.instrumentation = opentelemetry_instrumentation_stub

	opentelemetry_exporter_stub.jaeger = opentelemetry_exporter_jaeger_stub
	opentelemetry_exporter_jaeger_stub.thrift = opentelemetry_exporter_jaeger_thrift_stub

	opentelemetry_sdk_stub.trace = opentelemetry_sdk_trace_stub
	opentelemetry_sdk_stub.metrics = opentelemetry_sdk_metrics_stub
	opentelemetry_sdk_stub.resources = opentelemetry_sdk_resources_stub
	opentelemetry_sdk_trace_stub.export = opentelemetry_sdk_trace_export_stub

	opentelemetry_instrumentation_stub.fastapi = opentelemetry_instrumentation_fastapi_stub
	opentelemetry_instrumentation_stub.sqlalchemy = opentelemetry_instrumentation_sqlalchemy_stub
	opentelemetry_instrumentation_stub.redis = opentelemetry_instrumentation_redis_stub
	opentelemetry_instrumentation_stub.requests = opentelemetry_instrumentation_requests_stub

	sys.modules["opentelemetry"] = opentelemetry_stub
	sys.modules["opentelemetry.trace"] = opentelemetry_trace_stub
	sys.modules["opentelemetry.metrics"] = opentelemetry_metrics_stub
	sys.modules["opentelemetry.exporter"] = opentelemetry_exporter_stub
	sys.modules["opentelemetry.exporter.jaeger"] = opentelemetry_exporter_jaeger_stub
	sys.modules["opentelemetry.exporter.jaeger.thrift"] = opentelemetry_exporter_jaeger_thrift_stub
	sys.modules["opentelemetry.exporter.prometheus"] = opentelemetry_exporter_prometheus_stub
	sys.modules["opentelemetry.sdk"] = opentelemetry_sdk_stub
	sys.modules["opentelemetry.sdk.trace"] = opentelemetry_sdk_trace_stub
	sys.modules["opentelemetry.sdk.trace.export"] = opentelemetry_sdk_trace_export_stub
	sys.modules["opentelemetry.sdk.metrics"] = opentelemetry_sdk_metrics_stub
	sys.modules["opentelemetry.sdk.resources"] = opentelemetry_sdk_resources_stub
	sys.modules["opentelemetry.instrumentation"] = opentelemetry_instrumentation_stub
	sys.modules["opentelemetry.instrumentation.fastapi"] = opentelemetry_instrumentation_fastapi_stub
	sys.modules["opentelemetry.instrumentation.sqlalchemy"] = opentelemetry_instrumentation_sqlalchemy_stub
	sys.modules["opentelemetry.instrumentation.redis"] = opentelemetry_instrumentation_redis_stub
	sys.modules["opentelemetry.instrumentation.requests"] = opentelemetry_instrumentation_requests_stub


# Allow imports like `core.*`, `engines.*`, and `backend.*` during tests.
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))
