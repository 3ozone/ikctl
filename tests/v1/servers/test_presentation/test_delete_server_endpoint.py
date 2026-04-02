"""Tests de presentación — DELETE /api/v1/servers/{id} (T-54).

Verifica que el endpoint de eliminación de servidor:
1. Devuelve 204 sin body al eliminar correctamente
2. Devuelve 404 cuando el servidor no existe o no pertenece al usuario
3. Devuelve 409 cuando el servidor tiene operaciones activas (ServerInUseError)
"""

import pytest
from fastapi.testclient import TestClient

from app.v1.servers.application.exceptions import ServerInUseError
from app.v1.servers.domain.exceptions.server import ServerNotFoundError
from app.v1.servers.infrastructure.presentation.deps import (
    get_current_user_id,
    get_delete_server,
)
from main import app, jwt_provider

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

_USER_ID = "user-delete-server"
_SERVER_ID = "srv-del-001"


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


class FakeDeleteServerOk:
    """Fake que simula eliminación exitosa."""

    async def execute(self, **kwargs) -> None:
        pass


class FakeDeleteServerNotFound:
    """Fake que lanza ServerNotFoundError."""

    async def execute(self, **kwargs) -> None:
        raise ServerNotFoundError("Servidor no encontrado.")


class FakeDeleteServerInUse:
    """Fake que lanza ServerInUseError."""

    async def execute(self, **kwargs) -> None:
        raise ServerInUseError("El servidor tiene operaciones activas.")


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
    app.dependency_overrides[get_delete_server] = lambda: FakeDeleteServerOk()
    app.dependency_overrides[get_current_user_id] = lambda: _USER_ID
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def client_not_found():
    app.dependency_overrides[get_delete_server] = lambda: FakeDeleteServerNotFound(
    )
    app.dependency_overrides[get_current_user_id] = lambda: _USER_ID
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def client_in_use():
    app.dependency_overrides[get_delete_server] = lambda: FakeDeleteServerInUse(
    )
    app.dependency_overrides[get_current_user_id] = lambda: _USER_ID
    yield TestClient(app)
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_delete_server_returns_204(client_ok: TestClient) -> None:
    """DELETE /servers/{id} devuelve 204 sin body al eliminar correctamente."""
    resp = client_ok.delete(
        f"/api/v1/servers/{_SERVER_ID}", headers=_auth_headers())
    assert resp.status_code == 204
    assert resp.content == b""


def test_delete_server_not_found_returns_404(client_not_found: TestClient) -> None:
    """DELETE /servers/{id} devuelve 404 cuando el servidor no existe."""
    resp = client_not_found.delete(
        f"/api/v1/servers/{_SERVER_ID}", headers=_auth_headers())
    assert resp.status_code == 404
    assert "detail" in resp.json()


def test_delete_server_in_use_returns_409(client_in_use: TestClient) -> None:
    """DELETE /servers/{id} devuelve 409 cuando el servidor tiene operaciones activas."""
    resp = client_in_use.delete(
        f"/api/v1/servers/{_SERVER_ID}", headers=_auth_headers())
    assert resp.status_code == 409
    assert "detail" in resp.json()
