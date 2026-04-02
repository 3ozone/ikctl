"""Tests de presentación — GET /api/v1/servers/{id}/health (T-56).

Verifica que el endpoint de health check:
1. Devuelve 200 con HealthCheckResponse cuando el servidor está online
2. Devuelve 200 con HealthCheckResponse cuando el servidor está offline
3. Devuelve 404 cuando el servidor no existe o no pertenece al usuario
"""
import pytest
from fastapi.testclient import TestClient

from app.v1.servers.application.dtos.health_check_result import HealthCheckResult
from app.v1.servers.domain.exceptions.server import ServerNotFoundError
from app.v1.servers.infrastructure.presentation.deps import (
    get_check_server_health,
    get_current_user_id,
)
from main import app, jwt_provider

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

_USER_ID = "user-health-server"
_SERVER_ID = "srv-health-001"


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


class FakeCheckServerHealthOnline:
    """Fake que devuelve servidor online con OS info."""

    async def execute(self, **kwargs) -> HealthCheckResult:
        return HealthCheckResult(
            server_id=_SERVER_ID,
            status="online",
            latency_ms=12.5,
            os_id="ubuntu",
            os_version="22.04",
            os_name="Ubuntu 22.04 LTS",
        )


class FakeCheckServerHealthOffline:
    """Fake que devuelve servidor offline."""

    async def execute(self, **kwargs) -> HealthCheckResult:
        return HealthCheckResult(
            server_id=_SERVER_ID,
            status="offline",
            latency_ms=None,
            os_id=None,
            os_version=None,
            os_name=None,
        )


class FakeCheckServerHealthNotFound:
    """Fake que lanza ServerNotFoundError."""

    async def execute(self, **kwargs) -> HealthCheckResult:
        raise ServerNotFoundError("Servidor no encontrado.")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _auth_headers() -> dict:
    token = jwt_provider.create_access_token(user_id=_USER_ID).token
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def client_online():
    app.dependency_overrides[get_check_server_health] = lambda: FakeCheckServerHealthOnline()
    app.dependency_overrides[get_current_user_id] = lambda: _USER_ID
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def client_offline():
    app.dependency_overrides[get_check_server_health] = lambda: FakeCheckServerHealthOffline()
    app.dependency_overrides[get_current_user_id] = lambda: _USER_ID
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def client_not_found():
    app.dependency_overrides[get_check_server_health] = lambda: FakeCheckServerHealthNotFound()
    app.dependency_overrides[get_current_user_id] = lambda: _USER_ID
    yield TestClient(app)
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_health_check_online_returns_200(client_online: TestClient) -> None:
    """GET /servers/{id}/health devuelve 200 con status online y OS info."""
    resp = client_online.get(
        f"/api/v1/servers/{_SERVER_ID}/health",
        headers=_auth_headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["server_id"] == _SERVER_ID
    assert data["status"] == "online"
    assert data["latency_ms"] == 12.5
    assert data["os_id"] == "ubuntu"


def test_health_check_offline_returns_200(client_offline: TestClient) -> None:
    """GET /servers/{id}/health devuelve 200 con status offline y campos nulos."""
    resp = client_offline.get(
        f"/api/v1/servers/{_SERVER_ID}/health",
        headers=_auth_headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["server_id"] == _SERVER_ID
    assert data["status"] == "offline"
    assert data["latency_ms"] is None
    assert data["os_id"] is None


def test_health_check_not_found_returns_404(client_not_found: TestClient) -> None:
    """GET /servers/{id}/health devuelve 404 cuando el servidor no existe."""
    resp = client_not_found.get(
        f"/api/v1/servers/{_SERVER_ID}/health",
        headers=_auth_headers(),
    )
    assert resp.status_code == 404
    assert "detail" in resp.json()
