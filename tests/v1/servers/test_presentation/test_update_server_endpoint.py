"""Tests de presentación — PUT /api/v1/servers/{id} (T-53).

Verifica que el endpoint de actualización de servidor:
1. Devuelve 200 con ServerResponse actualizado cuando el servidor existe
2. Devuelve 404 cuando el servidor no existe o no pertenece al usuario
"""
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.v1.servers.application.dtos.server_result import ServerResult
from app.v1.servers.domain.exceptions.server import ServerNotFoundError
from app.v1.servers.infrastructure.presentation.deps import (
    get_current_user_id,
    get_update_server,
)
from main import app, jwt_provider

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

_USER_ID = "user-update-server"
_SERVER_ID = "srv-upd-001"
_NOW = datetime(2026, 4, 1, 12, 0, 0, tzinfo=timezone.utc)

_UPDATE_BODY = {
    "name": "web-01-updated",
    "host": "10.0.0.5",
    "port": 2222,
    "credential_id": "cred-new",
    "description": "Descripción actualizada",
}

_SERVER_RESULT = ServerResult(
    server_id=_SERVER_ID,
    user_id=_USER_ID,
    name="web-01-updated",
    server_type="remote",
    status="active",
    host="10.0.0.5",
    port=2222,
    credential_id="cred-new",
    description="Descripción actualizada",
    os_id=None,
    os_version=None,
    os_name=None,
    created_at=_NOW,
    updated_at=_NOW,
)


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


class FakeUpdateServerOk:
    """Fake que devuelve servidor actualizado."""

    async def execute(self, **kwargs) -> ServerResult:
        return _SERVER_RESULT


class FakeUpdateServerNotFound:
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
def client_ok():
    app.dependency_overrides[get_update_server] = lambda: FakeUpdateServerOk()
    app.dependency_overrides[get_current_user_id] = lambda: _USER_ID
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def client_not_found():
    app.dependency_overrides[get_update_server] = lambda: FakeUpdateServerNotFound(
    )
    app.dependency_overrides[get_current_user_id] = lambda: _USER_ID
    yield TestClient(app)
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_update_server_returns_200(client_ok: TestClient) -> None:
    """PUT /servers/{id} devuelve 200 con ServerResponse actualizado."""
    resp = client_ok.put(
        f"/api/v1/servers/{_SERVER_ID}", json=_UPDATE_BODY, headers=_auth_headers()
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["server_id"] == _SERVER_ID
    assert data["name"] == "web-01-updated"
    assert data["host"] == "10.0.0.5"
    assert data["port"] == 2222


def test_update_server_not_found_returns_404(client_not_found: TestClient) -> None:
    """PUT /servers/{id} devuelve 404 cuando el servidor no existe."""
    resp = client_not_found.put(
        f"/api/v1/servers/{_SERVER_ID}", json=_UPDATE_BODY, headers=_auth_headers()
    )
    assert resp.status_code == 404
    assert "detail" in resp.json()
