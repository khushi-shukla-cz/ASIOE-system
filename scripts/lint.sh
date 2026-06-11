#!/usr/bin/env bash
set -euo pipefail
echo "Running flake8..."
flake8 || true
echo "Running black check..."
black --check . || true
