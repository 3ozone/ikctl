"""Tests de presentación — DELETE /api/v1/groups/{id} (T-62).

Verifica que el endpoint de eliminar grupo:
1. Devuelve 204 cuando el grupo se elimina correctamente
2. Devuelve 404 cuando el grupo no existe o no pertenece al usuario
3. Devuelve 409 cuando el grupo tiene pipelines activos
"""
import pytest
from fastapi.testclient import TestClient

from app.v1.servers.application.exceptions import GroupInUseError
from app.v1.servers.domain.exceptions.group import GroupNotFoundError
from app.v1.servers.infrastructure.presentation.deps import (
    get_current_user_id,
    get_delete_group,
)
from main import app, jwt_provider

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

_USER_ID = "user-group-delete"
_GROUP_ID = "grp-del-001"


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


class FakeDeleteGroupOk:
    """Fake que elimina el grupo correctamente."""

    async def execute(self, **kwargs) -> None:
        """No hace nada — elimina sin error."""
        return None


class FakeDeleteGroupNotFound:
    """Fake que lanza GroupNotFoundError."""

    async def execute(self, **kwargs) -> None:
        """Lanza GroupNotFoundError."""
        raise GroupNotFoundError("Grupo no encontrado.")


class FakeDeleteGroupInUse:
    """Fake que lanza GroupInUseError."""

    async def execute(self, **kwargs) -> None:
        """Lanza GroupInUseError."""
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
def client_ok():
    """Cliente con use case que elimina correctamente."""
    app.dependency_overrides[get_delete_group] = lambda: FakeDeleteGroupOk()
    app.dependency_overrides[get_current_user_id] = lambda: _USER_ID
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def client_not_found():
    """Cliente con use case que lanza GroupNotFoundError."""
    app.dependency_overrides[get_delete_group] = lambda: FakeDeleteGroupNotFound(
    )
    app.dependency_overrides[get_current_user_id] = lambda: _USER_ID
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def client_in_use():
    """Cliente con use case que lanza GroupInUseError."""
    app.dependency_overrides[get_delete_group] = lambda: FakeDeleteGroupInUse()
    app.dependency_overrides[get_current_user_id] = lambda: _USER_ID
    yield TestClient(app)
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_delete_group_returns_204(client_ok: TestClient) -> None:
    """DELETE /groups/{id} devuelve 204 sin body al eliminar correctamente."""
    resp = client_ok.delete(
        f"/api/v1/groups/{_GROUP_ID}",
        headers=_auth_headers(),
    )
    assert resp.status_code == 204
    assert resp.content == b""


def test_delete_group_not_found_returns_404(client_not_found: TestClient) -> None:
    """DELETE /groups/{id} devuelve 404 cuando el grupo no existe."""
    resp = client_not_found.delete(
        f"/api/v1/groups/{_GROUP_ID}",
        headers=_auth_headers(),
    )
    assert resp.status_code == 404
    assert "detail" in resp.json()


def test_delete_group_in_use_returns_409(client_in_use: TestClient) -> None:
    """DELETE /groups/{id} devuelve 409 cuando el grupo tiene pipelines activos."""
    resp = client_in_use.delete(
        f"/api/v1/groups/{_GROUP_ID}",
        headers=_auth_headers(),
    )
    assert resp.status_code == 409
    assert "detail" in resp.json()
