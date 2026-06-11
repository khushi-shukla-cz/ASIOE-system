"""Simple input validators used by API endpoints and tests."""
from __future__ import annotations

from typing import Optional


def validate_jd_text(jd: Optional[str]) -> bool:
    if jd is None:
        return False
    s = jd.strip()
    return len(s) >= 10


def sanitize_filename(name: str) -> str:
    return name.replace("..", "").replace('/', '_')
