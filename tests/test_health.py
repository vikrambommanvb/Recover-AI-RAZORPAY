from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_root_endpoint():
    """Test that the GET / endpoint returns correct app metadata."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "RecoverAI"
    assert "version" in data
    assert "description" in data


def test_health_endpoint():
    """Test that the GET /health endpoint functions without crashing."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["ok", "degraded"]
    assert data["service"] == "RecoverAI"
    assert "environment" in data
