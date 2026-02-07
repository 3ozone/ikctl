"""Configuración compartida para tests."""
import pytest
from fastapi.testclient import TestClient
from main import app


@pytest.fixture
def client():
    """Fixture para cliente de test de FastAPI."""
    return TestClient(app)


@pytest.fixture
def authenticated_client():
    """Fixture para cliente autenticado."""
    test_client = TestClient(app)

    # Registrar usuario de test
    test_client.post(
        "/register",
        json={
            "name": "Test User",
            "email": "fixture@example.com",
            "password": "testpass123"
        }
    )

    # Hacer login
    login_response = test_client.post(
        "/login",
        json={
            "email": "fixture@example.com",
            "password": "testpass123"
        }
    )

    token = login_response.json()["access_token"]
    test_client.headers = {"Authorization": f"Bearer {token}"}

    return test_client


@pytest.fixture(autouse=True)
def reset_database():
    """Fixture para resetear la base de datos entre tests."""
    # TODO: Implementar reset de base de datos
    # Por ahora, cada test usa emails únicos para evitar conflictos
    yield
    # Cleanup después del test si es necesario
