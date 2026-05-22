"""Smoke tests for health endpoints — focus on shape, not infra."""

from fastapi.testclient import TestClient

from app.main import app


def test_liveness_does_not_touch_dependencies():
    # /live must work even before lifespan startup runs DB init.
    with TestClient(app) as client:
        resp = client.get("/live")
    assert resp.status_code == 200
    assert resp.json() == {"status": "alive"}


def test_root_endpoint_reports_service_info():
    with TestClient(app) as client:
        resp = client.get("/")
    assert resp.status_code == 200
    body = resp.json()
    assert body["service"] == "AlgoTrader Pro User API"
    assert body["status"] == "running"


def test_health_endpoint_returns_healthy_shape():
    with TestClient(app) as client:
        resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "healthy"
    assert body["service"] == "user-api"


def test_ready_reports_db_status_with_lifespan():
    """When lifespan runs, DB engines initialise — /ready should reflect them."""
    with TestClient(app) as client:
        resp = client.get("/ready")
    body = resp.json()
    assert set(body["checks"].keys()) == {"database_oltp", "database_timescaledb"}
    if resp.status_code == 200:
        assert body["status"] == "ready"
        assert body["checks"]["database_oltp"] is True
        assert body["checks"]["database_timescaledb"] is True
    else:
        # Acceptable in environments without a reachable DB; the shape still holds.
        assert resp.status_code == 503
        assert body["status"] == "not_ready"
