#!/usr/bin/env bash
set -euo pipefail
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r backend/requirements.txt
pip install -r requirements-dev.txt
echo "Development environment set up. Activate with: source .venv/bin/activate"
