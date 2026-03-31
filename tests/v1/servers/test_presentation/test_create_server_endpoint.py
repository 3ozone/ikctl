"""Tests de presentación — POST /api/v1/servers (T-50).

Verifica que el endpoint de registro de servidores:
1. Devuelve 201 al registrar un servidor remoto con body válido
2. Devuelve 201 al registrar un servidor local con rol admin
3. Devuelve 404 cuando la credencial no existe (servidor remoto)
4. Devuelve 409 cuando ya existe un servidor local (DuplicateLocalServerError)
5. Devuelve 403 cuando un usuario no-admin intenta registrar servidor local
"""
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.v1.servers.application.dtos.server_result import ServerResult
from app.v1.servers.application.exceptions import DuplicateLocalServerError, UnauthorizedOperationError
from app.v1.servers.domain.exceptions.credential import CredentialNotFoundError
from app.v1.servers.infrastructure.presentation.deps import (
    get_current_user_id,
    get_current_user_role,
    get_register_local_server,
    get_register_server,
)
from main import app, jwt_provider

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

_USER_ID = "user-create-server"
_NOW = datetime(2026, 3, 31, 12, 0, 0, tzinfo=timezone.utc)

_REMOTE_BODY = {
    "type": "remote",
    "name": "web-01",
    "host": "192.168.1.10",
    "port": 22,
    "credential_id": "cred-abc",
    "description": "Servidor web principal",
}

_LOCAL_BODY = {
    "type": "local",
    "name": "localhost",
    "description": "Servidor local de control",
}

_SERVER_RESULT_REMOTE = ServerResult(
    server_id="srv-remote-1",
    user_id=_USER_ID,
    name="web-01",
    server_type="remote",
    status="active",
    host="192.168.1.10",
    port=22,
    credential_id="cred-abc",
    description="Servidor web principal",
    os_id=None,
    os_version=None,
    os_name=None,
    created_at=_NOW,
    updated_at=_NOW,
)

_SERVER_RESULT_LOCAL = ServerResult(
    server_id="srv-local-1",
    user_id=_USER_ID,
    name="localhost",
    server_type="local",
    status="active",
    host=None,
    port=None,
    credential_id=None,
    description="Servidor local de control",
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
        return _SERVER_RESULT_REMOTE


class FakeRegisterLocalServerOk:
    """Fake que simula registro exitoso de servidor local."""

    async def execute(self, **kwargs) -> ServerResult:
        return _SERVER_RESULT_LOCAL


class FakeRegisterServerCredentialNotFound:
    """Fake que lanza CredentialNotFoundError."""

    async def execute(self, **kwargs) -> ServerResult:
        """Simula error de credencial no encontrada al registrar servidor remoto."""
        raise CredentialNotFoundError("Credencial no encontrada.")


class FakeRegisterLocalServerDuplicate:
    """Fake que lanza DuplicateLocalServerError."""

    async def execute(self, **kwargs) -> ServerResult:
        """Simula error de servidor local duplicado al registrar servidor local."""
        raise DuplicateLocalServerError(
            "Ya existe un servidor local para este usuario.")


class FakeRegisterLocalServerUnauthorized:
    """Fake que lanza UnauthorizedOperationError."""

    async def execute(self, **kwargs) -> ServerResult:
        """Simula error de acceso denegado al registrar servidor local por usuario no-admin."""
        raise UnauthorizedOperationError(
            "Solo administradores pueden registrar servidores locales.")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _auth_headers(role: str = "user") -> dict:
    """Genera headers con Bearer token real. Incluye role en los claims."""
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
    """Client para registro exitoso de servidor remoto."""
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
    """Client para registro exitoso de servidor local."""
    app.dependency_overrides[get_register_server] = lambda: FakeRegisterServerOk(
    )
    app.dependency_overrides[get_register_local_server] = lambda: FakeRegisterLocalServerOk(
    )
    app.dependency_overrides[get_current_user_id] = lambda: _USER_ID
    app.dependency_overrides[get_current_user_role] = lambda: "admin"
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def client_credential_not_found():
    """Client donde la credencial no existe."""
    app.dependency_overrides[get_register_server] = lambda: FakeRegisterServerCredentialNotFound(
    )
    app.dependency_overrides[get_register_local_server] = lambda: FakeRegisterLocalServerOk(
    )
    app.dependency_overrides[get_current_user_id] = lambda: _USER_ID
    app.dependency_overrides[get_current_user_role] = lambda: "user"
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def client_local_duplicate():
    """Client donde ya existe un servidor local."""
    app.dependency_overrides[get_register_server] = lambda: FakeRegisterServerOk(
    )
    app.dependency_overrides[get_register_local_server] = lambda: FakeRegisterLocalServerDuplicate(
    )
    app.dependency_overrides[get_current_user_id] = lambda: _USER_ID
    app.dependency_overrides[get_current_user_role] = lambda: "admin"
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def client_local_unauthorized():
    """Client donde el usuario no tiene rol admin."""
    app.dependency_overrides[get_register_server] = lambda: FakeRegisterServerOk(
    )
    app.dependency_overrides[get_register_local_server] = lambda: FakeRegisterLocalServerUnauthorized(
    )
    app.dependency_overrides[get_current_user_id] = lambda: _USER_ID
    app.dependency_overrides[get_current_user_role] = lambda: "user"
    yield TestClient(app)
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_create_remote_server_returns_201(client_remote_ok: TestClient) -> None:
    """POST /servers con type=remote devuelve 201 con ServerResponse."""
    resp = client_remote_ok.post(
        "/api/v1/servers", json=_REMOTE_BODY, headers=_auth_headers())
    assert resp.status_code == 201
    data = resp.json()
    assert data["server_type"] == "remote"
    assert data["host"] == "192.168.1.10"
    assert data["credential_id"] == "cred-abc"


def test_create_local_server_returns_201(client_local_ok: TestClient) -> None:
    """POST /servers con type=local y rol admin devuelve 201 con ServerResponse."""
    resp = client_local_ok.post(
        "/api/v1/servers", json=_LOCAL_BODY, headers=_auth_headers(role="admin"))
    assert resp.status_code == 201
    data = resp.json()
    assert data["server_type"] == "local"
    assert data["host"] is None


def test_create_remote_server_credential_not_found_returns_404(
    client_credential_not_found: TestClient,
) -> None:
    """POST /servers devuelve 404 cuando la credencial no existe."""
    resp = client_credential_not_found.post(
        "/api/v1/servers", json=_REMOTE_BODY, headers=_auth_headers()
    )
    assert resp.status_code == 404
    assert "detail" in resp.json()


def test_create_local_server_duplicate_returns_409(client_local_duplicate: TestClient) -> None:
    """POST /servers devuelve 409 cuando ya existe un servidor local para el usuario."""
    resp = client_local_duplicate.post(
        "/api/v1/servers", json=_LOCAL_BODY, headers=_auth_headers(role="admin")
    )
    assert resp.status_code == 409
    assert "detail" in resp.json()


def test_create_local_server_unauthorized_returns_403(client_local_unauthorized: TestClient) -> None:
    """POST /servers devuelve 403 cuando un usuario no-admin intenta registrar servidor local."""
    resp = client_local_unauthorized.post(
        "/api/v1/servers", json=_LOCAL_BODY, headers=_auth_headers()
    )
    assert resp.status_code == 403
    assert "detail" in resp.json()
