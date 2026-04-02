"""Tests de integración presentación — flujos credentials (T-63).

Escenarios:
1. Crear credencial OK → 201
2. Body sin campo requerido `type` → 422 (validación Pydantic, antes del use case)
3. Usuario no propietario intenta eliminar → 403
4. Credencial en uso no se puede eliminar → 409
"""
from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient

from app.v1.servers.application.dtos.credential_result import CredentialResult
from app.v1.servers.application.exceptions import UnauthorizedOperationError
from app.v1.servers.domain.exceptions.credential import (
    CredentialInUseError,
)
from app.v1.servers.infrastructure.presentation.deps import (
    get_create_credential,
    get_current_user_id,
    get_delete_credential,
)
from main import app, jwt_provider

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

_USER_ID = "user-cred-flows"
_CRED_ID = "cred-flow-001"
_NOW = datetime(2026, 4, 2, 12, 0, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


class FakeCreateCredentialOk:
    async def execute(self, **kwargs) -> CredentialResult:
        return CredentialResult(
            credential_id=_CRED_ID,
            user_id=_USER_ID,
            name=kwargs["name"],
            credential_type=kwargs["credential_type"],
            username=kwargs.get("username"),
            created_at=_NOW,
            updated_at=_NOW,
        )


class FakeDeleteCredentialUnauthorized:
    async def execute(self, **kwargs) -> None:
        raise UnauthorizedOperationError(
            "No eres propietario de esta credencial.")


class FakeDeleteCredentialInUse:
    async def execute(self, **kwargs) -> None:
        raise CredentialInUseError(
            "La credencial está en uso por uno o más servidores.")


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
def client_create_ok():
    app.dependency_overrides[get_create_credential] = lambda: FakeCreateCredentialOk(
    )
    app.dependency_overrides[get_current_user_id] = lambda: _USER_ID
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def client_create_any():
    """Cliente con auth válida para testear validación Pydantic (422)."""
    app.dependency_overrides[get_create_credential] = lambda: FakeCreateCredentialOk(
    )
    app.dependency_overrides[get_current_user_id] = lambda: _USER_ID
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def client_delete_unauthorized():
    app.dependency_overrides[get_delete_credential] = lambda: FakeDeleteCredentialUnauthorized(
    )
    app.dependency_overrides[get_current_user_id] = lambda: _USER_ID
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def client_delete_in_use():
    app.dependency_overrides[get_delete_credential] = lambda: FakeDeleteCredentialInUse(
    )
    app.dependency_overrides[get_current_user_id] = lambda: _USER_ID
    yield TestClient(app)
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_create_credential_returns_201(client_create_ok: TestClient) -> None:
    """POST /credentials con body válido devuelve 201."""
    resp = client_create_ok.post(
        "/api/v1/credentials",
        json={"name": "deploy-key", "type": "ssh", "username": "deploy"},
        headers=_auth_headers(),
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["credential_id"] == _CRED_ID
    assert data["credential_type"] == "ssh"


def test_create_credential_missing_type_returns_422(client_create_any: TestClient) -> None:
    """POST /credentials sin campo requerido `type` devuelve 422 (validación Pydantic)."""
    resp = client_create_any.post(
        "/api/v1/credentials",
        json={"name": "deploy-key"},  # `type` ausente → Pydantic lo rechaza
        headers=_auth_headers(),
    )
    assert resp.status_code == 422
    body = resp.json()
    assert "detail" in body


def test_delete_credential_not_owner_returns_403(client_delete_unauthorized: TestClient) -> None:
    """DELETE /credentials/{id} devuelve 403 cuando el usuario no es propietario."""
    resp = client_delete_unauthorized.delete(
        f"/api/v1/credentials/{_CRED_ID}",
        headers=_auth_headers(),
    )
    assert resp.status_code == 403
    assert "detail" in resp.json()


def test_delete_credential_in_use_returns_409(client_delete_in_use: TestClient) -> None:
    """DELETE /credentials/{id} devuelve 409 cuando la credencial está en uso."""
    resp = client_delete_in_use.delete(
        f"/api/v1/credentials/{_CRED_ID}",
        headers=_auth_headers(),
    )
    assert resp.status_code == 409
    assert "detail" in resp.json()
