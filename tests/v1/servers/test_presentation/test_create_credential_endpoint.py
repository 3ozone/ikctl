"""Tests de presentación — POST /api/v1/credentials (T-45).

Verifica que el endpoint de creación de credenciales:
1. Devuelve 201 con CredentialResponse (sin password ni private_key) al crear una credencial válida
2. Devuelve 400 cuando el tipo de credencial no es válido
3. Devuelve 400 cuando la configuración es inválida según el tipo
"""
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.v1.servers.application.dtos.credential_result import CredentialResult
from app.v1.servers.domain.exceptions.credential import (
    InvalidCredentialTypeError,
    InvalidCredentialConfigurationError,
)
from app.v1.servers.infrastructure.presentation.deps import (
    get_create_credential,
    get_current_user_id,
)
from main import app, jwt_provider


def _auth_headers() -> dict:
    """Genera headers con Bearer token real para pasar el AuthenticationMiddleware."""
    token = jwt_provider.create_access_token(user_id=_USER_ID).token
    return {"Authorization": f"Bearer {token}"}

# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------

_USER_ID = "user-test-1"
_NOW = datetime.now(timezone.utc)



class FakeCreateCredentialOk:
    """Fake que simula creación exitosa."""

    async def execute(self, **kwargs) -> CredentialResult:
        """Simula creación exitosa devolviendo un CredentialResult con los datos de entrada."""
        return CredentialResult(
            credential_id="cred-123",
            user_id=_USER_ID,
            name=kwargs["name"],
            credential_type=kwargs["credential_type"],
            username=kwargs.get("username"),
            created_at=_NOW,
            updated_at=_NOW,
        )


class FakeCreateCredentialInvalidType:
    """Fake que lanza InvalidCredentialTypeError."""

    async def execute(self, **kwargs) -> CredentialResult:
        """Simula error por tipo inválido lanzando InvalidCredentialTypeError."""
        raise InvalidCredentialTypeError("Tipo de credencial inválido.")


class FakeCreateCredentialInvalidConfig:
    """Fake que lanza InvalidCredentialConfigurationError."""

    async def execute(self, **kwargs) -> CredentialResult:
        """Simula error por configuración inválida lanzando InvalidCredentialConfigurationError."""
        raise InvalidCredentialConfigurationError(
            "Configuración inválida para el tipo.")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def client_ok():
    """Client con use case que devuelve éxito."""
    app.dependency_overrides[get_create_credential] = lambda: FakeCreateCredentialOk(
    )
    app.dependency_overrides[get_current_user_id] = lambda: _USER_ID
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def client_invalid_type():
    """Client con use case que lanza InvalidCredentialTypeError."""
    app.dependency_overrides[get_create_credential] = lambda: FakeCreateCredentialInvalidType(
    )
    app.dependency_overrides[get_current_user_id] = lambda: _USER_ID
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def client_invalid_config():
    """Client con use case que lanza InvalidCredentialConfigurationError."""
    app.dependency_overrides[get_create_credential] = lambda: FakeCreateCredentialInvalidConfig(
    )
    app.dependency_overrides[get_current_user_id] = lambda: _USER_ID
    yield TestClient(app)
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_create_credential_returns_201(client_ok: TestClient) -> None:
    """POST /credentials con body válido devuelve 201 y CredentialResponse."""
    payload = {
        "name": "my-ssh-key",
        "type": "ssh",
        "username": "root",
        "password": "s3cr3t",
    }
    resp = client_ok.post("/api/v1/credentials", json=payload, headers=_auth_headers())
    assert resp.status_code == 201
    data = resp.json()
    assert data["credential_id"] == "cred-123"
    assert data["user_id"] == _USER_ID
    assert data["name"] == "my-ssh-key"
    assert data["credential_type"] == "ssh"
    assert "password" not in data
    assert "private_key" not in data


def test_create_credential_invalid_type_returns_400(client_invalid_type: TestClient) -> None:
    """POST /credentials con tipo inválido devuelve 400."""
    payload = {"name": "bad-cred", "type": "ftp"}
    resp = client_invalid_type.post("/api/v1/credentials", json=payload, headers=_auth_headers())
    assert resp.status_code == 400
    assert "detail" in resp.json()


def test_create_credential_invalid_config_returns_400(client_invalid_config: TestClient) -> None:
    """POST /credentials con configuración inválida devuelve 400."""
    payload = {"name": "git-ssh-key", "type": "git_ssh"}  # falta private_key
    resp = client_invalid_config.post("/api/v1/credentials", json=payload, headers=_auth_headers())
    assert resp.status_code == 400
    assert "detail" in resp.json()
