from __future__ import annotations

import pytest

from db.cache import build_cache_key


def test_idempotency_key_format():
    key = build_cache_key("idempotency", "abc123")
    assert "idempotency" in key and "abc123" in key
