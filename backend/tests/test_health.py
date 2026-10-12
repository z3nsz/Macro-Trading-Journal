from fastapi.testclient import TestClient

from app.api import health as health_module


def test_health_reports_ok_with_database(client: TestClient):
    response = client.get("/api/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["database"] == "connected"
    assert body["app"] == "Macro Trading Journal"
    assert "server_time" in body


def test_health_reports_degraded_when_database_down(client: TestClient, monkeypatch):
    # Simulate PostgreSQL being unreachable: the API must still answer, not crash.
    monkeypatch.setattr(health_module, "database_is_reachable", lambda db: False)

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["status"] == "degraded"
    assert response.json()["database"] == "unavailable"


def test_unknown_endpoint_returns_404(client: TestClient):
    assert client.get("/api/does-not-exist").status_code == 404
