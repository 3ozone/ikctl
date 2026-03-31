"""Tests de presentación — GET /api/v1/credentials/{id} (T-47).

Verifica que el endpoint de obtener credencial:
1. Devuelve 200 con CredentialResponse cuando la credencial existe
2. Devuelve 404 cuando la credencial no existe o no pertenece al usuario
"""
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.v1.servers.application.dtos.credential_result import CredentialResult
from app.v1.servers.domain.exceptions.credential import CredentialNotFoundError
from app.v1.servers.infrastructure.presentation.deps import (
    get_current_user_id,
    get_get_credential,
)
from main import app, jwt_provider

# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------

_USER_ID = "user-get-cred"
_CRED_ID = "cred-abc-123"
_NOW = datetime.now(timezone.utc)


class FakeGetCredentialOk:
    """Fake que devuelve una credencial existente."""

    async def execute(self, user_id: str, credential_id: str) -> CredentialResult:
        """Devuelve un CredentialResult con los IDs recibidos."""
        return CredentialResult(
            credential_id=credential_id,
            user_id=user_id,
            name="my-key",
            credential_type="ssh",
            username="deploy",
            created_at=_NOW,
            updated_at=_NOW,
        )


class FakeGetCredentialNotFound:
    """Fake que lanza CredentialNotFoundError."""

    async def execute(self, user_id: str, credential_id: str) -> CredentialResult:
        """Lanza CredentialNotFoundError simulando que no existe."""
        raise CredentialNotFoundError("Credencial no encontrada.")


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
    """Client con use case que devuelve la credencial."""
    app.dependency_overrides[get_get_credential] = lambda: FakeGetCredentialOk()
    app.dependency_overrides[get_current_user_id] = lambda: _USER_ID
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def client_not_found():
    """Client con use case que lanza CredentialNotFoundError."""
    app.dependency_overrides[get_get_credential] = lambda: FakeGetCredentialNotFound()
    app.dependency_overrides[get_current_user_id] = lambda: _USER_ID
    yield TestClient(app)
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_get_credential_returns_200(client_ok: TestClient) -> None:
    """GET /credentials/{id} devuelve 200 con CredentialResponse."""
    resp = client_ok.get(f"/api/v1/credentials/{_CRED_ID}", headers=_auth_headers())
    assert resp.status_code == 200
    data = resp.json()
    assert data["credential_id"] == _CRED_ID
    assert data["user_id"] == _USER_ID
    assert data["credential_type"] == "ssh"
    assert "password" not in data
    assert "private_key" not in data


def test_get_credential_not_found_returns_404(client_not_found: TestClient) -> None:
    """GET /credentials/{id} devuelve 404 cuando la credencial no existe."""
    resp = client_not_found.get(f"/api/v1/credentials/{_CRED_ID}", headers=_auth_headers())
    assert resp.status_code == 404
    assert "detail" in resp.json()
