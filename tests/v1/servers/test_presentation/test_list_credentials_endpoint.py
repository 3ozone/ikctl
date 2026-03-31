"""Tests de presentación — GET /api/v1/credentials (T-46).

Verifica que el endpoint de listado de credenciales:
1. Devuelve 200 con CredentialListResponse cuando el usuario tiene credenciales
2. Devuelve 200 con lista vacía cuando el usuario no tiene credenciales
3. Acepta parámetros de paginación page y per_page
"""
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.v1.servers.application.dtos.credential_list_result import CredentialListResult
from app.v1.servers.application.dtos.credential_result import CredentialResult
from app.v1.servers.infrastructure.presentation.deps import (
    get_current_user_id,
    get_list_credentials,
)
from main import app, jwt_provider

# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------

_USER_ID = "user-list-creds"
_NOW = datetime.now(timezone.utc)


def _make_result(n: int) -> CredentialListResult:
    """Genera un CredentialListResult con n items."""
    items = [
        CredentialResult(
            credential_id=f"cred-{i}",
            user_id=_USER_ID,
            name=f"key-{i}",
            credential_type="ssh",
            username="root",
            created_at=_NOW,
            updated_at=_NOW,
        )
        for i in range(n)
    ]
    return CredentialListResult(items=items, total=n, page=1, per_page=20)


class FakeListCredentialsWithItems:
    """Fake que devuelve 2 credenciales."""

    async def execute(self, **kwargs) -> CredentialListResult:
        """Devuelve un listado con 2 credenciales."""
        return _make_result(2)


class FakeListCredentialsEmpty:
    """Fake que devuelve lista vacía."""

    async def execute(self, **kwargs) -> CredentialListResult:
        """Devuelve un listado vacío."""
        return CredentialListResult(
            items=[], total=0, page=kwargs.get("page", 1), per_page=kwargs.get("per_page", 20)
        )


class FakeListCredentialsPaginated:
    """Fake que retorna los parámetros de paginación recibidos."""

    async def execute(self, **kwargs) -> CredentialListResult:
        """Devuelve un listado respetando los parámetros page y per_page."""
        return CredentialListResult(
            items=[], total=0, page=kwargs["page"], per_page=kwargs["per_page"]
        )


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
def client_with_items():
    """Client con use case que devuelve 2 credenciales."""
    app.dependency_overrides[get_list_credentials] = lambda: FakeListCredentialsWithItems()
    app.dependency_overrides[get_current_user_id] = lambda: _USER_ID
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def client_empty():
    """Client con use case que devuelve lista vacía."""
    app.dependency_overrides[get_list_credentials] = lambda: FakeListCredentialsEmpty()
    app.dependency_overrides[get_current_user_id] = lambda: _USER_ID
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def client_paginated():
    """Client con use case que refleja los parámetros de paginación."""
    app.dependency_overrides[get_list_credentials] = lambda: FakeListCredentialsPaginated()
    app.dependency_overrides[get_current_user_id] = lambda: _USER_ID
    yield TestClient(app)
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_list_credentials_returns_200_with_items(client_with_items: TestClient) -> None:
    """GET /credentials devuelve 200 con lista de credenciales."""
    resp = client_with_items.get("/api/v1/credentials", headers=_auth_headers())
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2
    assert data["items"][0]["credential_id"] == "cred-0"


def test_list_credentials_returns_200_empty(client_empty: TestClient) -> None:
    """GET /credentials devuelve 200 con lista vacía cuando no hay credenciales."""
    resp = client_empty.get("/api/v1/credentials", headers=_auth_headers())
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["items"] == []


def test_list_credentials_accepts_pagination_params(client_paginated: TestClient) -> None:
    """GET /credentials acepta y reenvía los parámetros page y per_page."""
    resp = client_paginated.get(
        "/api/v1/credentials?page=2&per_page=5", headers=_auth_headers()
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["page"] == 2
    assert data["per_page"] == 5
