"""Small input validators used by API routes and tests."""
from __future__ import annotations

from typing import Any


def is_non_empty_str(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())
