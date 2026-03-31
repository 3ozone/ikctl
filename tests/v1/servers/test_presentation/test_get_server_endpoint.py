"""Tests de presentación — GET /api/v1/servers/{id} (T-52).

Verifica que el endpoint de obtención de servidor:
1. Devuelve 200 con ServerResponse cuando el servidor existe
2. Devuelve 404 cuando el servidor no existe o no pertenece al usuario
"""
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.v1.servers.application.dtos.server_result import ServerResult
from app.v1.servers.domain.exceptions.server import ServerNotFoundError
from app.v1.servers.infrastructure.presentation.deps import (
    get_current_user_id,
    get_get_server,
)
from main import app, jwt_provider

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

_USER_ID = "user-get-server"
_SERVER_ID = "srv-get-001"
_NOW = datetime(2026, 3, 31, 12, 0, 0, tzinfo=timezone.utc)

_SERVER_RESULT = ServerResult(
    server_id=_SERVER_ID,
    user_id=_USER_ID,
    name="web-01",
    server_type="remote",
    status="active",
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


class FakeGetServerOk:
    """Fake que devuelve el servidor correctamente."""

    async def execute(self, user_id: str, server_id: str) -> ServerResult:
        """Devuelve un ServerResult con los datos del servidor solicitado."""
        return _SERVER_RESULT


class FakeGetServerNotFound:
    """Fake que lanza ServerNotFoundError."""

    async def execute(self, user_id: str, server_id: str) -> ServerResult:
        """Simula que el servidor no existe o no pertenece al usuario lanzando ServerNotFoundError."""
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
    """Client con use case que devuelve el servidor solicitado."""
    app.dependency_overrides[get_get_server] = lambda: FakeGetServerOk()
    app.dependency_overrides[get_current_user_id] = lambda: _USER_ID
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def client_not_found():
    """Client con use case que lanza ServerNotFoundError."""
    app.dependency_overrides[get_get_server] = lambda: FakeGetServerNotFound()
    app.dependency_overrides[get_current_user_id] = lambda: _USER_ID
    yield TestClient(app)
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_get_server_returns_200(client_ok: TestClient) -> None:
    """GET /servers/{id} devuelve 200 con ServerResponse."""
    resp = client_ok.get(
        f"/api/v1/servers/{_SERVER_ID}", headers=_auth_headers())
    assert resp.status_code == 200
    data = resp.json()
    assert data["server_id"] == _SERVER_ID
    assert data["server_type"] == "remote"
    assert data["host"] == "192.168.1.10"


def test_get_server_not_found_returns_404(client_not_found: TestClient) -> None:
    """GET /servers/{id} devuelve 404 cuando el servidor no existe."""
    resp = client_not_found.get(
        f"/api/v1/servers/{_SERVER_ID}", headers=_auth_headers())
    assert resp.status_code == 404
    assert "detail" in resp.json()
