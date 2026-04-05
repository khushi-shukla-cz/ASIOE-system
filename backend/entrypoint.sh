#!/bin/bash
set -e

echo "=== ASIOE Backend Starting ==="

# Seed data if not already seeded
if [ ! -f /app/data/processed/skill_ontology.json ]; then
    echo "Seeding skill ontology and course catalog..."
    cd /app && python /scripts/seed_data.py
fi

echo "Starting FastAPI server..."
exec uvicorn main:app --host 0.0.0.0 --port 8000 --workers 2 --loop asyncio
