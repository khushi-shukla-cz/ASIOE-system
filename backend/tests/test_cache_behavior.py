from __future__ import annotations

from db.cache import get_cache_stats, build_cache_key


def test_cache_stats_structure():
    stats = get_cache_stats()
    assert isinstance(stats, dict)
    assert "hits" in stats and "misses" in stats

def test_build_cache_key_consistent():
    k1 = build_cache_key("analysis", "s1")
    k2 = build_cache_key("analysis", "s1")
    assert k1 == k2
