import os
import sys
from pathlib import Path


# Ensure required settings can load in test environments without real secrets.
os.environ.setdefault("SECRET_KEY", "test_secret_key_123456789012345678901234")
os.environ.setdefault("POSTGRES_PASSWORD", "test_postgres_password")
os.environ.setdefault("NEO4J_PASSWORD", "test_neo4j_password")
os.environ.setdefault("GROQ_API_KEY", "gsk_test_key")


# Allow imports like `core.*`, `engines.*`, and `backend.*` during tests.
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
	sys.path.insert(0, str(BACKEND_ROOT))
