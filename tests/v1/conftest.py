"""Fixtures for v1 tests."""
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def test_client():
    """FastAPI test client."""
    from app.main import app
    return TestClient(app)


@pytest.fixture
def auth_headers(test_client):
    """Headers with valid JWT token for authenticated requests."""
    # Register and login a test user
    test_client.post("/api/v1/register", json={
        "name": "Test User",
        "email": "test@example.com",
        "password": "TestPass123!"
    })

    response = test_client.post("/api/v1/login", data={
        "username": "test@example.com",
        "password": "TestPass123!"
    })

    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
