from __future__ import annotations

import subprocess
import sys


def test_normalize_sample_runs():
    # Run the normalization CLI with python; ensure it exits 0
    res = subprocess.run([sys.executable, "backend/scripts/normalize_sample.py", "Python"], capture_output=True)
    assert res.returncode == 0
