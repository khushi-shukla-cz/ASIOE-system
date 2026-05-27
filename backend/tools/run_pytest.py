import subprocess
import sys
from pathlib import Path

venv_python = sys.executable
log_path = Path(__file__).resolve().parents[1] / "pytest_run.log"

print(f"Running pytest with: {venv_python}")
proc = subprocess.run([venv_python, "-m", "pytest", "backend", "-q", "-x"], capture_output=True, text=True)
log_path.write_text(proc.stdout + '\n' + proc.stderr, encoding='utf-8')
print(proc.stdout)
print(proc.stderr, file=sys.stderr)
sys.exit(proc.returncode)
