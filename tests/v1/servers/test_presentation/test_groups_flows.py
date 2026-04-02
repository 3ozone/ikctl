"""Tests de integración presentación — flujos groups (T-65).

Escenarios:
1. Crear grupo con servidores OK → 201
2. Crear grupo vacío OK → 201
3. Eliminar grupo con pipeline activo → 409 (GroupInUseError)
"""
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.v1.servers.application.dtos.group_result import GroupResult
from app.v1.servers.application.exceptions import GroupInUseError
from app.v1.servers.infrastructure.presentation.deps import (
    get_create_group,
    get_current_user_id,
    get_delete_group,
)
from main import app, jwt_provider

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

_USER_ID = "user-group-flows"
_GROUP_ID = "grp-flow-001"
_NOW = datetime(2026, 4, 2, 12, 0, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


class FakeCreateGroupWithServers:
    """Fake que devuelve grupo creado con dos servidores."""

    async def execute(self, **kwargs) -> GroupResult:
        """Devuelve GroupResult con server_ids proporcionados."""
        return GroupResult(
            group_id=_GROUP_ID,
            user_id=_USER_ID,
            name="k8s-nodes",
            description=None,
            server_ids=kwargs.get("server_ids", []),
            created_at=_NOW,
            updated_at=_NOW,
        )


class FakeCreateGroupEmpty:
    """Fake que devuelve grupo creado sin servidores."""

    async def execute(self, **kwargs) -> GroupResult:
        """Devuelve GroupResult con lista de servidores vacía."""
        return GroupResult(
            group_id=_GROUP_ID,
            user_id=_USER_ID,
            name="grupo-vacio",
            description=None,
            server_ids=[],
            created_at=_NOW,
            updated_at=_NOW,
        )


class FakeDeleteGroupInUse:
    """Fake que lanza GroupInUseError al eliminar un grupo con pipelines activos."""

    async def execute(self, **kwargs) -> None:
        """Lanza GroupInUseError simulando que el grupo tiene pipelines activos."""
        raise GroupInUseError("El grupo tiene pipelines activos.")


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
def client_create_with_servers():
    """Cliente con use case que devuelve grupo creado con servidores."""
    app.dependency_overrides[get_create_group] = lambda: FakeCreateGroupWithServers()
    app.dependency_overrides[get_current_user_id] = lambda: _USER_ID
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def client_create_empty():
    """Cliente con use case que devuelve grupo creado sin servidores."""
    app.dependency_overrides[get_create_group] = lambda: FakeCreateGroupEmpty()
    app.dependency_overrides[get_current_user_id] = lambda: _USER_ID
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def client_delete_in_use():
    """Cliente con use case que lanza GroupInUseError al eliminar."""
    app.dependency_overrides[get_delete_group] = lambda: FakeDeleteGroupInUse()
    app.dependency_overrides[get_current_user_id] = lambda: _USER_ID
    yield TestClient(app)
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_create_group_with_servers_returns_201(client_create_with_servers: TestClient) -> None:
    """POST /groups con server_ids devuelve 201 con los servidores asignados."""
    resp = client_create_with_servers.post(
        "/api/v1/groups",
        json={"name": "k8s-nodes", "server_ids": ["srv-001", "srv-002"]},
        headers=_auth_headers(),
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["group_id"] == _GROUP_ID
    assert len(data["server_ids"]) == 2


def test_create_group_empty_returns_201(client_create_empty: TestClient) -> None:
    """POST /groups sin server_ids devuelve 201 con lista vacía."""
    resp = client_create_empty.post(
        "/api/v1/groups",
        json={"name": "grupo-vacio", "server_ids": []},
        headers=_auth_headers(),
    )
    assert resp.status_code == 201
    assert resp.json()["server_ids"] == []


def test_delete_group_with_active_pipeline_returns_409(client_delete_in_use: TestClient) -> None:
    """DELETE /groups/{id} con pipelines activos devuelve 409."""
    resp = client_delete_in_use.delete(
        f"/api/v1/groups/{_GROUP_ID}",
        headers=_auth_headers(),
    )
    assert resp.status_code == 409
    assert "detail" in resp.json()
