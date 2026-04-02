"""Tests de presentación — POST /api/v1/servers/{id}/toggle (T-55).

Verifica que el endpoint de toggle de estado:
1. Devuelve 200 con ServerResponse al activar el servidor
2. Devuelve 200 con ServerResponse al desactivar el servidor
3. Devuelve 404 cuando el servidor no existe o no pertenece al usuario
"""
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.v1.servers.application.dtos.server_result import ServerResult
from app.v1.servers.domain.exceptions.server import ServerNotFoundError
from app.v1.servers.infrastructure.presentation.deps import (
    get_current_user_id,
    get_toggle_server_status,
)
from main import app, jwt_provider

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

_USER_ID = "user-toggle-server"
_SERVER_ID = "srv-tog-001"
_NOW = datetime(2026, 4, 2, 12, 0, 0, tzinfo=timezone.utc)


def _make_result(status: str) -> ServerResult:
    return ServerResult(
        server_id=_SERVER_ID,
        user_id=_USER_ID,
        name="web-01",
        server_type="remote",
        status=status,
        host="192.168.1.10",
        port=22,
        credential_id="cred-abc",
        description=None,
        os_id=None,
        os_version=None,
        os_name=None,
        created_at=_NOW,
        updated_at=_NOW,
    )


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


class FakeToggleServerActive:
    """Fake que devuelve servidor activado."""

    async def execute(self, **kwargs) -> ServerResult:
        return _make_result("active")


class FakeToggleServerInactive:
    """Fake que devuelve servidor desactivado."""

    async def execute(self, **kwargs) -> ServerResult:
        return _make_result("inactive")


class FakeToggleServerNotFound:
    """Fake que lanza ServerNotFoundError."""

    async def execute(self, **kwargs) -> ServerResult:
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
def client_activate():
    app.dependency_overrides[get_toggle_server_status] = lambda: FakeToggleServerActive()
    app.dependency_overrides[get_current_user_id] = lambda: _USER_ID
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def client_deactivate():
    app.dependency_overrides[get_toggle_server_status] = lambda: FakeToggleServerInactive()
    app.dependency_overrides[get_current_user_id] = lambda: _USER_ID
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def client_not_found():
    app.dependency_overrides[get_toggle_server_status] = lambda: FakeToggleServerNotFound()
    app.dependency_overrides[get_current_user_id] = lambda: _USER_ID
    yield TestClient(app)
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_toggle_server_activate_returns_200(client_activate: TestClient) -> None:
    """POST /servers/{id}/toggle con active=true devuelve 200 con status active."""
    resp = client_activate.post(
        f"/api/v1/servers/{_SERVER_ID}/toggle",
        json={"active": True},
        headers=_auth_headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["server_id"] == _SERVER_ID
    assert data["status"] == "active"


def test_toggle_server_deactivate_returns_200(client_deactivate: TestClient) -> None:
    """POST /servers/{id}/toggle con active=false devuelve 200 con status inactive."""
    resp = client_deactivate.post(
        f"/api/v1/servers/{_SERVER_ID}/toggle",
        json={"active": False},
        headers=_auth_headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["server_id"] == _SERVER_ID
    assert data["status"] == "inactive"


def test_toggle_server_not_found_returns_404(client_not_found: TestClient) -> None:
    """POST /servers/{id}/toggle devuelve 404 cuando el servidor no existe."""
    resp = client_not_found.post(
        f"/api/v1/servers/{_SERVER_ID}/toggle",
        json={"active": True},
        headers=_auth_headers(),
    )
    assert resp.status_code == 404
    assert "detail" in resp.json()
