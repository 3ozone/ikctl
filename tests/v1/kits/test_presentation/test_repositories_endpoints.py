"""Tests de presentación — endpoints /api/v1/repositories (T-37).

Verifica:
1.  POST   /api/v1/repositories          → 201 al registrar OK
2.  POST   /api/v1/repositories          → 422 credencial no git_https/git_ssh
3.  GET    /api/v1/repositories          → 200 lista paginada
4.  GET    /api/v1/repositories/{id}     → 200 repositorio existente
5.  GET    /api/v1/repositories/{id}     → 404 repositorio no encontrado
6.  PUT    /api/v1/repositories/{id}     → 200 actualización OK
7.  DELETE /api/v1/repositories/{id}     → 204 borrado OK
8.  DELETE /api/v1/repositories/{id}     → 409 repo en uso
9.  POST   /api/v1/repositories/{id}/sync → 200 sync exitoso
10. POST   /api/v1/repositories/{id}/sync → 200 con sync_error (sin ikctl.yaml)
"""
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.v1.kits.application.dtos.repository_list_result import RepositoryListResult
from app.v1.kits.application.dtos.repository_result import RepositoryResult
from app.v1.kits.application.dtos.repository_sync_result import RepositorySyncResult
from app.v1.kits.application.exceptions import (
    InvalidGitCredentialTypeError,
    RepositoryInUseError,
    RepositoryNotFoundError,
)
from app.v1.kits.infrastructure.presentation.deps import (
    get_current_user_id,
    get_delete_repository_uc,
    get_get_repository_uc,
    get_list_repositories_uc,
    get_register_repository_uc,
    get_sync_repository_uc,
    get_update_repository_uc,
)
from main import app, jwt_provider

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

_USER_ID = "user-repos-endpoints"
_REPO_ID = "repo-001"
_NOW = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

_REGISTER_BODY = {"url": "https://github.com/org/kits-repo", "ref": "main"}
_UPDATE_BODY = {"url": "https://github.com/org/kits-repo", "ref": "v2"}

_REPOSITORY_RESULT = RepositoryResult(
    repository_id=_REPO_ID,
    user_id=_USER_ID,
    url="https://github.com/org/kits-repo",
    ref="main",
    credential_id=None,
    sync_status="never_synced",
    last_synced_at=None,
    last_commit_sha=None,
    sync_error_message=None,
    created_at=_NOW,
    updated_at=_NOW,
)

_REPOSITORY_RESULT_UPDATED = RepositoryResult(
    repository_id=_REPO_ID,
    user_id=_USER_ID,
    url="https://github.com/org/kits-repo",
    ref="v2",
    credential_id=None,
    sync_status="never_synced",
    last_synced_at=None,
    last_commit_sha=None,
    sync_error_message=None,
    created_at=_NOW,
    updated_at=_NOW,
)

_SYNC_RESULT_OK = RepositorySyncResult(
    repository_id=_REPO_ID,
    sync_status="synced",
    last_commit_sha="abc123",
    sync_error_message=None,
    kits_created=2,
    kits_updated=0,
    kits_deleted=0,
)

_SYNC_RESULT_ERROR = RepositorySyncResult(
    repository_id=_REPO_ID,
    sync_status="sync_error",
    last_commit_sha=None,
    sync_error_message="No se encontró ikctl.yaml en la raíz",
    kits_created=0,
    kits_updated=0,
    kits_deleted=0,
)


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


class FakeRegisterRepositoryOk:
    async def execute(self, **kwargs) -> RepositoryResult:
        return _REPOSITORY_RESULT


class FakeRegisterRepositoryInvalidCredential:
    async def execute(self, **kwargs) -> RepositoryResult:
        raise InvalidGitCredentialTypeError("La credencial debe ser de tipo git_https o git_ssh.")


class FakeListRepositoriesOk:
    async def execute(self, **kwargs) -> RepositoryListResult:
        return RepositoryListResult(items=[_REPOSITORY_RESULT], total=1, page=1, per_page=50)


class FakeGetRepositoryOk:
    async def execute(self, **kwargs) -> RepositoryResult:
        return _REPOSITORY_RESULT


class FakeGetRepositoryNotFound:
    async def execute(self, **kwargs) -> RepositoryResult:
        raise RepositoryNotFoundError("Repositorio no encontrado.")


class FakeUpdateRepositoryOk:
    async def execute(self, **kwargs) -> RepositoryResult:
        return _REPOSITORY_RESULT_UPDATED


class FakeDeleteRepositoryOk:
    async def execute(self, **kwargs) -> None:
        return None


class FakeDeleteRepositoryInUse:
    async def execute(self, **kwargs) -> None:
        raise RepositoryInUseError("El repositorio tiene kits referenciados.")


class FakeSyncRepositoryOk:
    async def execute(self, **kwargs) -> RepositorySyncResult:
        return _SYNC_RESULT_OK


class FakeSyncRepositoryError:
    async def execute(self, **kwargs) -> RepositorySyncResult:
        return _SYNC_RESULT_ERROR


# ---------------------------------------------------------------------------
# Helper auth
# ---------------------------------------------------------------------------


def _auth_headers() -> dict:
    token = jwt_provider.create_access_token(
        user_id=_USER_ID,
        additional_claims={"role": "user"},
    ).token
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def client_register_ok():
    app.dependency_overrides[get_register_repository_uc] = lambda: FakeRegisterRepositoryOk()
    app.dependency_overrides[get_current_user_id] = lambda: _USER_ID
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def client_register_invalid_credential():
    app.dependency_overrides[get_register_repository_uc] = (
        lambda: FakeRegisterRepositoryInvalidCredential()
    )
    app.dependency_overrides[get_current_user_id] = lambda: _USER_ID
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def client_list_ok():
    app.dependency_overrides[get_list_repositories_uc] = lambda: FakeListRepositoriesOk()
    app.dependency_overrides[get_current_user_id] = lambda: _USER_ID
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def client_get_ok():
    app.dependency_overrides[get_get_repository_uc] = lambda: FakeGetRepositoryOk()
    app.dependency_overrides[get_current_user_id] = lambda: _USER_ID
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def client_get_not_found():
    app.dependency_overrides[get_get_repository_uc] = lambda: FakeGetRepositoryNotFound()
    app.dependency_overrides[get_current_user_id] = lambda: _USER_ID
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def client_update_ok():
    app.dependency_overrides[get_update_repository_uc] = lambda: FakeUpdateRepositoryOk()
    app.dependency_overrides[get_current_user_id] = lambda: _USER_ID
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def client_delete_ok():
    app.dependency_overrides[get_delete_repository_uc] = lambda: FakeDeleteRepositoryOk()
    app.dependency_overrides[get_current_user_id] = lambda: _USER_ID
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def client_delete_in_use():
    app.dependency_overrides[get_delete_repository_uc] = lambda: FakeDeleteRepositoryInUse()
    app.dependency_overrides[get_current_user_id] = lambda: _USER_ID
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def client_sync_ok():
    app.dependency_overrides[get_sync_repository_uc] = lambda: FakeSyncRepositoryOk()
    app.dependency_overrides[get_current_user_id] = lambda: _USER_ID
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def client_sync_error():
    app.dependency_overrides[get_sync_repository_uc] = lambda: FakeSyncRepositoryError()
    app.dependency_overrides[get_current_user_id] = lambda: _USER_ID
    yield TestClient(app)
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Tests — T-29: POST /api/v1/repositories
# ---------------------------------------------------------------------------


def test_register_repository_returns_201(client_register_ok: TestClient) -> None:
    """POST /api/v1/repositories devuelve 201 con el repositorio creado."""
    resp = client_register_ok.post("/api/v1/repositories", json=_REGISTER_BODY, headers=_auth_headers())

    assert resp.status_code == 201
    data = resp.json()
    assert data["repository_id"] == _REPO_ID
    assert data["url"] == "https://github.com/org/kits-repo"
    assert data["sync_status"] == "never_synced"
    assert data["credential_id"] is None


def test_register_repository_invalid_credential_type_returns_422(
    client_register_invalid_credential: TestClient,
) -> None:
    """POST /api/v1/repositories devuelve 422 cuando la credencial no es git_https/git_ssh."""
    resp = client_register_invalid_credential.post(
        "/api/v1/repositories", json=_REGISTER_BODY, headers=_auth_headers()
    )

    assert resp.status_code == 422
    assert "detail" in resp.json()


# ---------------------------------------------------------------------------
# Tests — T-30: GET /api/v1/repositories
# ---------------------------------------------------------------------------


def test_list_repositories_returns_200(client_list_ok: TestClient) -> None:
    """GET /api/v1/repositories devuelve 200 con lista paginada."""
    resp = client_list_ok.get("/api/v1/repositories", headers=_auth_headers())

    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["page"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["repository_id"] == _REPO_ID


# ---------------------------------------------------------------------------
# Tests — T-31: GET /api/v1/repositories/{id}
# ---------------------------------------------------------------------------


def test_get_repository_returns_200(client_get_ok: TestClient) -> None:
    """GET /api/v1/repositories/{id} devuelve 200 con el repositorio."""
    resp = client_get_ok.get(f"/api/v1/repositories/{_REPO_ID}", headers=_auth_headers())

    assert resp.status_code == 200
    assert resp.json()["repository_id"] == _REPO_ID


def test_get_repository_not_found_returns_404(client_get_not_found: TestClient) -> None:
    """GET /api/v1/repositories/{id} devuelve 404 si el repositorio no existe."""
    resp = client_get_not_found.get(f"/api/v1/repositories/{_REPO_ID}", headers=_auth_headers())

    assert resp.status_code == 404
    assert "detail" in resp.json()


# ---------------------------------------------------------------------------
# Tests — T-32: PUT /api/v1/repositories/{id}
# ---------------------------------------------------------------------------


def test_update_repository_returns_200(client_update_ok: TestClient) -> None:
    """PUT /api/v1/repositories/{id} devuelve 200 con el repositorio actualizado."""
    resp = client_update_ok.put(
        f"/api/v1/repositories/{_REPO_ID}", json=_UPDATE_BODY, headers=_auth_headers()
    )

    assert resp.status_code == 200
    assert resp.json()["ref"] == "v2"


# ---------------------------------------------------------------------------
# Tests — T-33: DELETE /api/v1/repositories/{id}
# ---------------------------------------------------------------------------


def test_delete_repository_returns_204(client_delete_ok: TestClient) -> None:
    """DELETE /api/v1/repositories/{id} devuelve 204 al borrar correctamente."""
    resp = client_delete_ok.delete(f"/api/v1/repositories/{_REPO_ID}", headers=_auth_headers())

    assert resp.status_code == 204


def test_delete_repository_in_use_returns_409(client_delete_in_use: TestClient) -> None:
    """DELETE /api/v1/repositories/{id} devuelve 409 cuando el repo tiene kits referenciados."""
    resp = client_delete_in_use.delete(f"/api/v1/repositories/{_REPO_ID}", headers=_auth_headers())

    assert resp.status_code == 409
    assert "detail" in resp.json()


# ---------------------------------------------------------------------------
# Tests — T-34: POST /api/v1/repositories/{id}/sync
# ---------------------------------------------------------------------------


def test_sync_repository_returns_200_ok(client_sync_ok: TestClient) -> None:
    """POST /api/v1/repositories/{id}/sync devuelve 200 con sync exitoso."""
    resp = client_sync_ok.post(f"/api/v1/repositories/{_REPO_ID}/sync", headers=_auth_headers())

    assert resp.status_code == 200
    data = resp.json()
    assert data["sync_status"] == "synced"
    assert data["last_commit_sha"] == "abc123"
    assert data["kits_created"] == 2


def test_sync_repository_returns_200_on_sync_error(client_sync_error: TestClient) -> None:
    """POST /api/v1/repositories/{id}/sync devuelve 200 incluso con sync_error (no 500)."""
    resp = client_sync_error.post(f"/api/v1/repositories/{_REPO_ID}/sync", headers=_auth_headers())

    assert resp.status_code == 200
    data = resp.json()
    assert data["sync_status"] == "sync_error"
    assert data["sync_error_message"] is not None
    assert data["kits_created"] == 0
