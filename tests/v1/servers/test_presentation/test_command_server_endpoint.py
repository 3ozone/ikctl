"""Tests de presentación — POST /api/v1/servers/{id}/command (T-57).

Verifica que el endpoint de comando ad-hoc:
1. Devuelve 200 con AdHocCommandResponse al ejecutar un comando exitoso
2. Devuelve 200 con AdHocCommandResponse cuando el comando falla (exit_code != 0)
3. Devuelve 404 cuando el servidor no existe o no pertenece al usuario
"""
import pytest
from fastapi.testclient import TestClient

from app.v1.servers.application.dtos.ad_hoc_command_result import AdHocCommandResult
from app.v1.servers.domain.exceptions.server import ServerNotFoundError
from app.v1.servers.infrastructure.presentation.deps import (
    get_current_user_id,
    get_execute_ad_hoc_command,
)
from main import app, jwt_provider

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

_USER_ID = "user-command-server"
_SERVER_ID = "srv-cmd-001"
_COMMAND = "df -h"


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


class FakeExecuteAdHocCommandSuccess:
    """Fake que devuelve ejecución exitosa."""

    async def execute(self, **kwargs) -> AdHocCommandResult:
        return AdHocCommandResult(
            server_id=_SERVER_ID,
            command=_COMMAND,
            stdout="Filesystem      Size  Used Avail Use% Mounted on\n/dev/sda1        50G   10G   40G  20% /",
            stderr="",
            exit_code=0,
        )


class FakeExecuteAdHocCommandFailed:
    """Fake que devuelve ejecución fallida (exit_code != 0)."""

    async def execute(self, **kwargs) -> AdHocCommandResult:
        return AdHocCommandResult(
            server_id=_SERVER_ID,
            command="invalid-cmd",
            stdout="",
            stderr="bash: invalid-cmd: command not found",
            exit_code=127,
        )


class FakeExecuteAdHocCommandNotFound:
    """Fake que lanza ServerNotFoundError."""

    async def execute(self, **kwargs) -> AdHocCommandResult:
        raise ServerNotFoundError("Servidor no encontrado.")


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
def client_success():
    app.dependency_overrides[get_execute_ad_hoc_command] = lambda: FakeExecuteAdHocCommandSuccess()
    app.dependency_overrides[get_current_user_id] = lambda: _USER_ID
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def client_failed():
    app.dependency_overrides[get_execute_ad_hoc_command] = lambda: FakeExecuteAdHocCommandFailed()
    app.dependency_overrides[get_current_user_id] = lambda: _USER_ID
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def client_not_found():
    app.dependency_overrides[get_execute_ad_hoc_command] = lambda: FakeExecuteAdHocCommandNotFound()
    app.dependency_overrides[get_current_user_id] = lambda: _USER_ID
    yield TestClient(app)
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_execute_command_success_returns_200(client_success: TestClient) -> None:
    """POST /servers/{id}/command con comando válido devuelve 200 con stdout y exit_code 0."""
    resp = client_success.post(
        f"/api/v1/servers/{_SERVER_ID}/command",
        json={"command": _COMMAND},
        headers=_auth_headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["server_id"] == _SERVER_ID
    assert data["command"] == _COMMAND
    assert data["exit_code"] == 0
    assert "Filesystem" in data["stdout"]
    assert data["stderr"] == ""


def test_execute_command_failed_returns_200(client_failed: TestClient) -> None:
    """POST /servers/{id}/command con comando fallido devuelve 200 con exit_code != 0."""
    resp = client_failed.post(
        f"/api/v1/servers/{_SERVER_ID}/command",
        json={"command": "invalid-cmd"},
        headers=_auth_headers(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["server_id"] == _SERVER_ID
    assert data["exit_code"] == 127
    assert "command not found" in data["stderr"]
    assert data["stdout"] == ""


def test_execute_command_not_found_returns_404(client_not_found: TestClient) -> None:
    """POST /servers/{id}/command devuelve 404 cuando el servidor no existe."""
    resp = client_not_found.post(
        f"/api/v1/servers/{_SERVER_ID}/command",
        json={"command": _COMMAND},
        headers=_auth_headers(),
    )
    assert resp.status_code == 404
    assert "detail" in resp.json()
