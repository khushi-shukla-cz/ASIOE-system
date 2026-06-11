"""Small utility to check required environment variables for local dev/tests."""
from __future__ import annotations

import os
import sys

REQUIRED = [
    "SECRET_KEY",
    "POSTGRES_PASSWORD",
    "NEO4J_PASSWORD",
]


def check_env() -> int:
    missing = [k for k in REQUIRED if not os.environ.get(k)]
    if missing:
        print("Missing environment variables:", ", ".join(missing))
        return 1
    print("All required environment variables set.")
    return 0


if __name__ == "__main__":
    sys.exit(check_env())
