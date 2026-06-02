"""Remove temporary upload folders older than N days."""
from __future__ import annotations

import shutil
from pathlib import Path
from datetime import datetime, timedelta

UPLOADS_DIR = Path(__file__).resolve().parents[2] / "uploads"


def clean(days: int = 7) -> int:
    if not UPLOADS_DIR.exists():
        return 0
    cutoff = datetime.now() - timedelta(days=days)
    removed = 0
    for p in UPLOADS_DIR.iterdir():
        try:
            if datetime.fromtimestamp(p.stat().st_mtime) < cutoff:
                if p.is_dir():
                    shutil.rmtree(p)
                else:
                    p.unlink()
                removed += 1
        except Exception:
            continue
    return removed


if __name__ == "__main__":
    print(f"Removed {clean()} uploads")
