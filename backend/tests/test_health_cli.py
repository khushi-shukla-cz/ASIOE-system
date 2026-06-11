from __future__ import annotations

from fastapi.testclient import TestClient

from api.routes import analysis as analysis_route
from api.routes import simulation as simulation_route


def test_health_endpoint_available():
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(analysis_route.router, prefix="/api/v1")
    app.include_router(simulation_route.router, prefix="/api/v1")

    with TestClient(app) as client:
        r = client.get("/api/v1/health")
        assert r.status_code == 200
