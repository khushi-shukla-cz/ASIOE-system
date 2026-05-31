"""Utility to clean cached ontology embeddings for the normalization engine."""
from __future__ import annotations

from core.config import settings
from pathlib import Path
import logging


def clean_cache() -> bool:
    path: Path = settings.ONTOLOGY_EMBEDDINGS_CACHE_PATH
    if path.exists():
        path.unlink()
        logging.getLogger(__name__).info("Removed embeddings cache", path=str(path))
        return True
    logging.getLogger(__name__).info("No embeddings cache found", path=str(path))
    return False


if __name__ == "__main__":
    import sys

    ok = clean_cache()
    sys.exit(0 if ok else 0)
