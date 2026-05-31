from __future__ import annotations

import re


def slugify_skill(name: str) -> str:
    """Create a normalized slug suitable for synthetic skill IDs."""
    name = name.strip().lower()
    name = re.sub(r"[^a-z0-9]+", "_", name)
    name = re.sub(r"_+", "_", name)
    return name.strip("_")
