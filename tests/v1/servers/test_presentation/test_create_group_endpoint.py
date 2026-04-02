"""Tests de presentación — POST /api/v1/groups (T-58).

Verifica que el endpoint de crear grupo:
1. Devuelve 201 con GroupResponse al crear un grupo con servidores
2. Devuelve 201 con GroupResponse al crear un grupo vacío (sin server_ids)
3. Devuelve 404 cuando algún server_id no existe o no pertenece al usuario
4. Devuelve 422 cuando algún server_id es de tipo local (RNF-16)
"""
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.v1.servers.application.dtos.group_result import GroupResult
from app.v1.servers.application.exceptions import LocalServerNotAllowedInGroupError
from app.v1.servers.domain.exceptions.server import ServerNotFoundError
from app.v1.servers.infrastructure.presentation.deps import (
    get_create_group,
    get_current_user_id,
)
from main import app, jwt_provider

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

_USER_ID = "user-group-create"
_GROUP_ID = "grp-001"
_NOW = datetime(2026, 4, 2, 12, 0, 0, tzinfo=timezone.utc)


def _make_result(server_ids: list[str] | None = None) -> GroupResult:
    """Construye un GroupResult de prueba con los server_ids indicados."""
    return GroupResult(
        group_id=_GROUP_ID,
        user_id=_USER_ID,
        name="k8s-nodes",
        description="Nodos de Kubernetes",
        server_ids=server_ids or [],
        created_at=_NOW,
        updated_at=_NOW,
    )


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


class FakeCreateGroupOk:
    """Fake que devuelve grupo creado con servidores."""

    async def execute(self, **kwargs) -> GroupResult:
        return _make_result(server_ids=["srv-001", "srv-002"])


class FakeCreateGroupEmpty:
    """Fake que devuelve grupo creado sin servidores."""

    async def execute(self, **kwargs) -> GroupResult:
        return _make_result(server_ids=[])


class FakeCreateGroupServerNotFound:
    """Fake que lanza ServerNotFoundError."""

    async def execute(self, **kwargs) -> GroupResult:
        raise ServerNotFoundError("Servidor no encontrado.")


class FakeCreateGroupLocalNotAllowed:
    """Fake que lanza LocalServerNotAllowedInGroupError."""

    async def execute(self, **kwargs) -> GroupResult:
        raise LocalServerNotAllowedInGroupError(
            "No se puede añadir un servidor local a un grupo.")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _auth_headers() -> dict:
    """Genera cabeceras de autenticación JWT para _USER_ID."""
    token = jwt_provider.create_access_token(user_id=_USER_ID).token
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def client_ok():
    """Cliente con use case que devuelve grupo creado con 2 servidores."""
    app.dependency_overrides[get_create_group] = lambda: FakeCreateGroupOk()
    app.dependency_overrides[get_current_user_id] = lambda: _USER_ID
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def client_empty():
    """Cliente con use case que devuelve grupo creado sin servidores."""
    app.dependency_overrides[get_create_group] = lambda: FakeCreateGroupEmpty()
    app.dependency_overrides[get_current_user_id] = lambda: _USER_ID
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def client_server_not_found():
    """Cliente con use case que lanza ServerNotFoundError."""
    app.dependency_overrides[get_create_group] = lambda: FakeCreateGroupServerNotFound(
    )
    app.dependency_overrides[get_current_user_id] = lambda: _USER_ID
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def client_local_not_allowed():
    """Cliente con use case que lanza LocalServerNotAllowedInGroupError."""
    app.dependency_overrides[get_create_group] = lambda: FakeCreateGroupLocalNotAllowed(
    )
    app.dependency_overrides[get_current_user_id] = lambda: _USER_ID
    yield TestClient(app)
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_create_group_returns_201(client_ok: TestClient) -> None:
    """POST /groups con server_ids válidos devuelve 201 con GroupResponse."""
    resp = client_ok.post(
        "/api/v1/groups",
        json={"name": "k8s-nodes", "description": "Nodos de Kubernetes",
              "server_ids": ["srv-001", "srv-002"]},
        headers=_auth_headers(),
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["group_id"] == _GROUP_ID
    assert data["user_id"] == _USER_ID
    assert data["name"] == "k8s-nodes"
    assert len(data["server_ids"]) == 2


def test_create_group_empty_server_ids_returns_201(client_empty: TestClient) -> None:
    """POST /groups sin server_ids devuelve 201 con grupo vacío."""
    resp = client_empty.post(
        "/api/v1/groups",
        json={"name": "k8s-nodes"},
        headers=_auth_headers(),
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["group_id"] == _GROUP_ID
    assert data["server_ids"] == []


def test_create_group_server_not_found_returns_404(client_server_not_found: TestClient) -> None:
    """POST /groups devuelve 404 cuando algún server_id no existe."""
    resp = client_server_not_found.post(
        "/api/v1/groups",
        json={"name": "k8s-nodes", "server_ids": ["srv-inexistente"]},
        headers=_auth_headers(),
    )
    assert resp.status_code == 404
    assert "detail" in resp.json()


def test_create_group_local_server_returns_422(client_local_not_allowed: TestClient) -> None:
    """POST /groups devuelve 422 cuando algún server_id es de tipo local (RNF-16)."""
    resp = client_local_not_allowed.post(
        "/api/v1/groups",
        json={"name": "k8s-nodes", "server_ids": ["srv-local-001"]},
        headers=_auth_headers(),
    )
    assert resp.status_code == 422
    assert "detail" in resp.json()
