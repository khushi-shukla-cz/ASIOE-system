from __future__ import annotations

import os
import subprocess
import sys


def test_check_env_script_runs(monkeypatch):
    # Ensure script returns exit 0 when required vars present
    monkeypatch.setenv("SECRET_KEY", "x" * 32)
    monkeypatch.setenv("POSTGRES_PASSWORD", "pw")
    monkeypatch.setenv("NEO4J_PASSWORD", "pw")

    res = subprocess.run([sys.executable, "backend/tools/check_env.py"], capture_output=True)
    assert res.returncode == 0
