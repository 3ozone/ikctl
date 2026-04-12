"""Tests de presentación — PUT /api/v1/credentials/{id} (T-48).

Verifica que el endpoint de actualización de credenciales:
1. Devuelve 200 con CredentialResponse actualizada cuando la credencial existe
2. Devuelve 404 cuando la credencial no existe o no pertenece al usuario
3. Devuelve 403 cuando el usuario no tiene permiso para actualizar la credencial
"""
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.v1.servers.infrastructure.presentation.schemas import UpdateCredentialRequest
from app.v1.servers.application.dtos.credential_result import CredentialResult
from app.v1.servers.domain.exceptions.credential import CredentialNotFoundError
from app.v1.servers.application.exceptions import UnauthorizedOperationError
from app.v1.servers.infrastructure.presentation.deps import (
    get_current_user_id,
    get_update_credential,
)
from main import app, jwt_provider

# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------

_USER_ID = "user-update-cred"
_CRED_ID = "cred-upd-123"
_NOW = datetime.now(timezone.utc)


class FakeUpdateCredentialOk:
    """Fake que simula actualización exitosa."""

    async def execute(self, **kwargs) -> CredentialResult:
        """Devuelve un CredentialResult con los datos actualizados."""
        return CredentialResult(
            credential_id=kwargs["credential_id"],
            user_id=kwargs["user_id"],
            name=kwargs["name"],
            credential_type="ssh",
            username=kwargs.get("username"),
            has_private_key=kwargs.get("private_key") is not None,
            created_at=_NOW,
            updated_at=_NOW,
        )


class FakeUpdateCredentialNotFound:
    """Fake que lanza CredentialNotFoundError."""

    async def execute(self, **kwargs) -> CredentialResult:
        """Lanza CredentialNotFoundError simulando que no existe."""
        raise CredentialNotFoundError("Credencial no encontrada.")


class FakeUpdateCredentialUnauthorized:
    """Fake que lanza UnauthorizedOperationError."""

    async def execute(self, **kwargs) -> CredentialResult:
        """Lanza UnauthorizedOperationError simulando acceso denegado."""
        raise UnauthorizedOperationError(
            "No tienes permiso para actualizar esta credencial.")


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
    app.dependency_overrides[get_update_credential] = lambda: FakeUpdateCredentialOk(
    )
    app.dependency_overrides[get_current_user_id] = lambda: _USER_ID
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def client_not_found():
    """Client con use case que lanza CredentialNotFoundError."""
    app.dependency_overrides[get_update_credential] = lambda: FakeUpdateCredentialNotFound(
    )
    app.dependency_overrides[get_current_user_id] = lambda: _USER_ID
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def client_unauthorized():
    """Client con use case que lanza UnauthorizedOperationError."""
    app.dependency_overrides[get_update_credential] = lambda: FakeUpdateCredentialUnauthorized(
    )
    app.dependency_overrides[get_current_user_id] = lambda: _USER_ID
    yield TestClient(app)
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_update_credential_returns_200(client_ok: TestClient) -> None:
    """PUT /credentials/{id} devuelve 200 con CredentialResponse actualizada."""
    payload = {"name": "updated-key", "username": "admin"}
    resp = client_ok.put(
        f"/api/v1/credentials/{_CRED_ID}", json=payload, headers=_auth_headers())
    assert resp.status_code == 200
    data = resp.json()
    assert data["credential_id"] == _CRED_ID
    assert data["name"] == "updated-key"
    assert "password" not in data
    assert "private_key" not in data


def test_update_credential_not_found_returns_404(client_not_found: TestClient) -> None:
    """PUT /credentials/{id} devuelve 404 cuando la credencial no existe."""
    payload = {"name": "updated-key"}
    resp = client_not_found.put(
        f"/api/v1/credentials/{_CRED_ID}", json=payload, headers=_auth_headers())
    assert resp.status_code == 404
    assert "detail" in resp.json()


def test_update_credential_unauthorized_returns_403(client_unauthorized: TestClient) -> None:
    """PUT /credentials/{id} devuelve 403 cuando el usuario no tiene permiso."""
    payload = {"name": "updated-key"}
    resp = client_unauthorized.put(
        f"/api/v1/credentials/{_CRED_ID}", json=payload, headers=_auth_headers())
    assert resp.status_code == 403
    assert "detail" in resp.json()


def test_update_credential_request_normalizes_empty_private_key_to_none() -> None:
    """UpdateCredentialRequest transforma private_key='' en None para borrar la clave (T-48)."""
    req = UpdateCredentialRequest(name="test-cred", private_key="")
    assert req.private_key is None
