"""Simple CLI to demonstrate normalization engine usage.

Usage:
    python backend/scripts/normalize_sample.py "Python" "JS" "machine learning"
"""
from __future__ import annotations

import sys
from pprint import pprint

from engines.normalization import get_normalization_engine


def main(args: list[str]) -> None:
    engine = get_normalization_engine()
    skills = [{"name": s} for s in args or ["Python", "JS", "Machine Learning"]]
    result = engine.normalize_skill_list(skills)
    pprint(result)


if __name__ == "__main__":
    main(sys.argv[1:])
#!/usr/bin/env python3
"""Run a quick normalization sample using the fallback ontology.

Usage:
    python backend/scripts/normalize_sample.py "Python" "MySQL" "Go"
"""
from __future__ import annotations

import sys
from engines.normalization.normalization_engine import get_normalization_engine
from core.config import settings


def main(argv: list[str] | None = None) -> None:
    argv = argv or sys.argv[1:]
    if not argv:
        print("Provide skill names as arguments")
        return

    # Prefer debug mode when running locally
    settings.NORMALIZATION_DEBUG_MODE = True  # type: ignore[attr-defined]

    engine = get_normalization_engine()
    results = engine.normalize_skill_list([{"name": s} for s in argv])
    for r in results:
        print(f"{r['name']} -> {r['canonical_skill_id']} (conf={r['normalization_confidence']})")


if __name__ == "__main__":
    main()
