("""Utility helpers used across backend modules.

Expose commonly used functions for convenience imports, e.g.

from backend.utils import slugify_skill

""")

from .strings import slugify_skill

__all__ = ["slugify_skill"]

