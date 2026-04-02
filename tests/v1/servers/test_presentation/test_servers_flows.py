"""Tests de integración presentación — flujos servers (T-64).

Escenarios:
1. Registrar servidor remoto OK → 201
2. Registrar servidor local OK → 201
3. Segundo servidor local → 409 (DuplicateLocalServerError)
4. Eliminar servidor con operaciones activas → 409 (ServerInUseError)
"""
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.v1.servers.application.dtos.server_result import ServerResult
from app.v1.servers.application.exceptions import DuplicateLocalServerError, ServerInUseError
from app.v1.servers.infrastructure.presentation.deps import (
    get_current_user_id,
    get_current_user_role,
    get_delete_server,
    get_register_local_server,
    get_register_server,
)
from main import app, jwt_provider

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

_USER_ID = "user-server-flows"
_SERVER_ID = "srv-flow-001"
_NOW = datetime(2026, 4, 2, 12, 0, 0, tzinfo=timezone.utc)

_RESULT_REMOTE = ServerResult(
    server_id=_SERVER_ID,
    user_id=_USER_ID,
    name="web-01",
    server_type="remote",
    status="active",
    host="10.0.0.1",
    port=22,
    credential_id="cred-abc",
    description=None,
    os_id=None,
    os_version=None,
    os_name=None,
    created_at=_NOW,
    updated_at=_NOW,
)

_RESULT_LOCAL = ServerResult(
    server_id="srv-local-flow",
    user_id=_USER_ID,
    name="localhost",
    server_type="local",
    status="active",
    host=None,
    port=None,
    credential_id=None,
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


class FakeRegisterServerOk:
    """Fake que simula registro exitoso de servidor remoto."""

    async def execute(self, **kwargs) -> ServerResult:
        """Devuelve ServerResult remoto sin lanzar excepciones."""
        return _RESULT_REMOTE


class FakeRegisterLocalServerOk:
    """Fake que simula registro exitoso de servidor local."""

    async def execute(self, **kwargs) -> ServerResult:
        """Devuelve ServerResult local sin lanzar excepciones."""
        return _RESULT_LOCAL


class FakeRegisterLocalServerDuplicate:
    """Fake que lanza DuplicateLocalServerError al registrar un segundo servidor local."""

    async def execute(self, **kwargs) -> ServerResult:
        """Lanza DuplicateLocalServerError simulando que ya existe un servidor local."""
        raise DuplicateLocalServerError(
            "Ya existe un servidor local para este usuario.")


class FakeDeleteServerInUse:
    """Fake que lanza ServerInUseError al intentar eliminar un servidor con operaciones activas."""

    async def execute(self, **kwargs) -> None:
        """Lanza ServerInUseError simulando que el servidor tiene operaciones activas."""
        raise ServerInUseError("El servidor tiene operaciones activas.")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _auth_headers(role: str = "user") -> dict:
    """Genera cabeceras de autenticación JWT con el rol indicado."""
    token = jwt_provider.create_access_token(
        user_id=_USER_ID,
        additional_claims={"role": role},
    ).token
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def client_remote_ok():
    """Cliente con use cases que simulan registro exitoso de servidor remoto."""
    app.dependency_overrides[get_register_server] = lambda: FakeRegisterServerOk(
    )
    app.dependency_overrides[get_register_local_server] = lambda: FakeRegisterLocalServerOk(
    )
    app.dependency_overrides[get_current_user_id] = lambda: _USER_ID
    app.dependency_overrides[get_current_user_role] = lambda: "user"
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def client_local_ok():
    """Cliente con use cases que simulan registro exitoso de servidor local (rol admin)."""
    app.dependency_overrides[get_register_server] = lambda: FakeRegisterServerOk(
    )
    app.dependency_overrides[get_register_local_server] = lambda: FakeRegisterLocalServerOk(
    )
    app.dependency_overrides[get_current_user_id] = lambda: _USER_ID
    app.dependency_overrides[get_current_user_role] = lambda: "admin"
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def client_local_duplicate():
    """Cliente con use case que lanza DuplicateLocalServerError al registrar un segundo local."""
    app.dependency_overrides[get_register_server] = lambda: FakeRegisterServerOk(
    )
    app.dependency_overrides[get_register_local_server] = lambda: FakeRegisterLocalServerDuplicate(
    )
    app.dependency_overrides[get_current_user_id] = lambda: _USER_ID
    app.dependency_overrides[get_current_user_role] = lambda: "admin"
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def client_delete_in_use():
    """Cliente con use case que lanza ServerInUseError al eliminar un servidor en uso."""
    app.dependency_overrides[get_delete_server] = lambda: FakeDeleteServerInUse(
    )
    app.dependency_overrides[get_current_user_id] = lambda: _USER_ID
    yield TestClient(app)
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_register_remote_server_returns_201(client_remote_ok: TestClient) -> None:
    """POST /servers con tipo remote devuelve 201."""
    resp = client_remote_ok.post(
        "/api/v1/servers",
        json={
            "type": "remote",
            "name": "web-01",
            "host": "10.0.0.1",
            "port": 22,
            "credential_id": "cred-abc",
        },
        headers=_auth_headers("user"),
    )
    assert resp.status_code == 201
    assert resp.json()["server_type"] == "remote"


def test_register_local_server_returns_201(client_local_ok: TestClient) -> None:
    """POST /servers con tipo local devuelve 201 (requiere rol admin)."""
    resp = client_local_ok.post(
        "/api/v1/servers",
        json={"type": "local", "name": "localhost"},
        headers=_auth_headers("admin"),
    )
    assert resp.status_code == 201
    assert resp.json()["server_type"] == "local"


def test_register_second_local_server_returns_409(client_local_duplicate: TestClient) -> None:
    """POST /servers local cuando ya existe uno devuelve 409."""
    resp = client_local_duplicate.post(
        "/api/v1/servers",
        json={"type": "local", "name": "localhost"},
        headers=_auth_headers("admin"),
    )
    assert resp.status_code == 409
    assert "detail" in resp.json()


def test_delete_server_with_active_operations_returns_409(client_delete_in_use: TestClient) -> None:
    """DELETE /servers/{id} con operaciones activas devuelve 409."""
    resp = client_delete_in_use.delete(
        f"/api/v1/servers/{_SERVER_ID}",
        headers=_auth_headers(),
    )
    assert resp.status_code == 409
    assert "detail" in resp.json()
