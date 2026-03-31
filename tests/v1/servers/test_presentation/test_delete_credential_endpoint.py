"""Tests de presentación — DELETE /api/v1/credentials/{id} (T-49).

Verifica que el endpoint de eliminación de credenciales:
1. Devuelve 204 sin body cuando la credencial se elimina correctamente
2. Devuelve 404 cuando la credencial no existe o no pertenece al usuario
3. Devuelve 403 cuando el usuario no tiene permiso
4. Devuelve 409 cuando la credencial está en uso por algún servidor
"""
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.v1.servers.domain.exceptions.credential import (
    CredentialInUseError,
    CredentialNotFoundError,
)
from app.v1.servers.application.exceptions import UnauthorizedOperationError
from app.v1.servers.infrastructure.presentation.deps import (
    get_current_user_id,
    get_delete_credential,
)
from main import app, jwt_provider

# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------

_USER_ID = "user-del-cred"
_CRED_ID = "cred-del-123"


class FakeDeleteCredentialOk:
    """Fake que simula eliminación exitosa."""

    async def execute(self, **kwargs) -> None:
        """No lanza ninguna excepción — eliminación exitosa."""


class FakeDeleteCredentialNotFound:
    """Fake que lanza CredentialNotFoundError."""

    async def execute(self, **kwargs) -> None:
        """Lanza CredentialNotFoundError simulando que no existe."""
        raise CredentialNotFoundError("Credencial no encontrada.")


class FakeDeleteCredentialUnauthorized:
    """Fake que lanza UnauthorizedOperationError."""

    async def execute(self, **kwargs) -> None:
        """Lanza UnauthorizedOperationError simulando acceso denegado."""
        raise UnauthorizedOperationError("No tienes permiso para eliminar esta credencial.")


class FakeDeleteCredentialInUse:
    """Fake que lanza CredentialInUseError."""

    async def execute(self, **kwargs) -> None:
        """Lanza CredentialInUseError simulando que está en uso."""
        raise CredentialInUseError("La credencial está en uso por uno o más servidores.")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _auth_headers() -> dict:
    """Genera headers con Bearer token real para pasar el AuthenticationMiddleware."""
    token = jwt_provider.create_access_token(user_id=_USER_ID).token
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def client_ok():
    """Client con use case que devuelve éxito."""
    app.dependency_overrides[get_delete_credential] = lambda: FakeDeleteCredentialOk()
    app.dependency_overrides[get_current_user_id] = lambda: _USER_ID
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def client_not_found():
    """Client con use case que lanza CredentialNotFoundError."""
    app.dependency_overrides[get_delete_credential] = lambda: FakeDeleteCredentialNotFound()
    app.dependency_overrides[get_current_user_id] = lambda: _USER_ID
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def client_unauthorized():
    """Client con use case que lanza UnauthorizedOperationError."""
    app.dependency_overrides[get_delete_credential] = lambda: FakeDeleteCredentialUnauthorized()
    app.dependency_overrides[get_current_user_id] = lambda: _USER_ID
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def client_in_use():
    """Client con use case que lanza CredentialInUseError."""
    app.dependency_overrides[get_delete_credential] = lambda: FakeDeleteCredentialInUse()
    app.dependency_overrides[get_current_user_id] = lambda: _USER_ID
    yield TestClient(app)
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_delete_credential_returns_204(client_ok: TestClient) -> None:
    """DELETE /credentials/{id} devuelve 204 sin body al eliminar correctamente."""
    resp = client_ok.delete(f"/api/v1/credentials/{_CRED_ID}", headers=_auth_headers())
    assert resp.status_code == 204
    assert resp.content == b""


def test_delete_credential_not_found_returns_404(client_not_found: TestClient) -> None:
    """DELETE /credentials/{id} devuelve 404 cuando la credencial no existe."""
    resp = client_not_found.delete(f"/api/v1/credentials/{_CRED_ID}", headers=_auth_headers())
    assert resp.status_code == 404
    assert "detail" in resp.json()


def test_delete_credential_unauthorized_returns_403(client_unauthorized: TestClient) -> None:
    """DELETE /credentials/{id} devuelve 403 cuando el usuario no tiene permiso."""
    resp = client_unauthorized.delete(f"/api/v1/credentials/{_CRED_ID}", headers=_auth_headers())
    assert resp.status_code == 403
    assert "detail" in resp.json()


def test_delete_credential_in_use_returns_409(client_in_use: TestClient) -> None:
    """DELETE /credentials/{id} devuelve 409 cuando la credencial está en uso."""
    resp = client_in_use.delete(f"/api/v1/credentials/{_CRED_ID}", headers=_auth_headers())
    assert resp.status_code == 409
    assert "detail" in resp.json()
