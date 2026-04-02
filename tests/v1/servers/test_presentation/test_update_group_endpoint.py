"""Tests de presentación — PUT /api/v1/groups/{id} (T-61).

Verifica que el endpoint de actualizar grupo:
1. Devuelve 200 con GroupResponse al actualizar correctamente
2. Devuelve 404 cuando el grupo no existe o no pertenece al usuario
"""
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.v1.servers.application.dtos.group_result import GroupResult
from app.v1.servers.domain.exceptions.group import GroupNotFoundError
from app.v1.servers.infrastructure.presentation.deps import (
    get_current_user_id,
    get_update_group,
)
from main import app, jwt_provider

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

_USER_ID = "user-group-update"
_GROUP_ID = "grp-upd-001"
_NOW = datetime(2026, 4, 2, 12, 0, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


class FakeUpdateGroupOk:
    """Fake que devuelve grupo actualizado."""

    async def execute(self, **kwargs) -> GroupResult:
        """Devuelve grupo con los datos actualizados."""
        return GroupResult(
            group_id=_GROUP_ID,
            user_id=_USER_ID,
            name="k8s-nodes-updated",
            description="Descripción actualizada",
            server_ids=["srv-001", "srv-002", "srv-003"],
            created_at=_NOW,
            updated_at=_NOW,
        )


class FakeUpdateGroupNotFound:
    """Fake que lanza GroupNotFoundError."""

    async def execute(self, **kwargs) -> GroupResult:
        """Lanza GroupNotFoundError."""
        raise GroupNotFoundError("Grupo no encontrado.")


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
    """Cliente con use case que devuelve grupo actualizado."""
    app.dependency_overrides[get_update_group] = lambda: FakeUpdateGroupOk()
    app.dependency_overrides[get_current_user_id] = lambda: _USER_ID
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def client_not_found():
    """Cliente con use case que lanza GroupNotFoundError."""
    app.dependency_overrides[get_update_group] = lambda: FakeUpdateGroupNotFound(
    )
    app.dependency_overrides[get_current_user_id] = lambda: _USER_ID
    yield TestClient(app)
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_update_group_returns_200(client_ok: TestClient) -> None:
    """PUT /groups/{id} devuelve 200 con GroupResponse actualizado."""
    resp = client_ok.put(
        f"/api/v1/groups/{_GROUP_ID}",
        json={
            "name": "k8s-nodes-updated",
            "description": "Descripción actualizada",
            "server_ids": ["srv-001", "srv-002", "srv-003"],
        },
        headers=_auth_headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["group_id"] == _GROUP_ID
    assert data["name"] == "k8s-nodes-updated"
    assert len(data["server_ids"]) == 3


def test_update_group_not_found_returns_404(client_not_found: TestClient) -> None:
    """PUT /groups/{id} devuelve 404 cuando el grupo no existe."""
    resp = client_not_found.put(
        f"/api/v1/groups/{_GROUP_ID}",
        json={"name": "nuevo-nombre", "server_ids": []},
        headers=_auth_headers(),
    )
    assert resp.status_code == 404
    assert "detail" in resp.json()
