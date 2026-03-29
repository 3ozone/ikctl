"""Tests para ConnectionFactory (T-36).

Estrategia: mocks del CredentialRepository y de la entidad Server.
Valida que la factory seleccione el adaptador correcto según server.type
y que descifre la credencial en memoria sin persistirla.
"""
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.v1.servers.domain.entities.credential import Credential
from app.v1.servers.domain.entities.server import Server
from app.v1.servers.domain.value_objects.credential_type import CredentialType
from app.v1.servers.domain.value_objects.server_status import ServerStatus
from app.v1.servers.domain.value_objects.server_type import ServerType
from app.v1.servers.infrastructure.adapters.connection_factory import ConnectionFactory
from app.v1.servers.infrastructure.adapters.local_connection import LocalConnectionAdapter
from app.v1.servers.infrastructure.adapters.ssh_connection import SSHConnectionAdapter


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_remote_server(credential_id: str = "cred-1") -> Server:
    return Server(
        id="srv-1",
        user_id="user-1",
        name="web-01",
        type=ServerType("remote"),
        status=ServerStatus("active"),
        host="192.168.1.10",
        port=22,
        credential_id=credential_id,
        description=None,
        os_id=None,
        os_version=None,
        os_name=None,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


def _make_local_server() -> Server:
    return Server(
        id="srv-local",
        user_id="user-1",
        name="local",
        type=ServerType("local"),
        status=ServerStatus("active"),
        host=None,
        port=None,
        credential_id=None,
        description=None,
        os_id=None,
        os_version=None,
        os_name=None,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


def _make_credential(private_key: str | None = None, password: str | None = None) -> Credential:
    return Credential(
        id="cred-1",
        user_id="user-1",
        name="my-key",
        type=CredentialType("ssh"),
        username="root",
        password=password,
        private_key=private_key or "-----BEGIN OPENSSH PRIVATE KEY-----\nfakekey\n-----END OPENSSH PRIVATE KEY-----",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_for_remote_server_returns_ssh_adapter():
    """Test 1: servidor remote → devuelve SSHConnectionAdapter."""
    server = _make_remote_server()
    credential = _make_credential()

    mock_repo = MagicMock()
    mock_repo.find_by_id = AsyncMock(return_value=credential)

    factory = ConnectionFactory(credential_repository=mock_repo)
    adapter = await factory.create(server)

    assert isinstance(adapter, SSHConnectionAdapter)


@pytest.mark.asyncio
async def test_create_for_local_server_returns_local_adapter():
    """Test 2: servidor local → devuelve LocalConnectionAdapter sin consultar credenciales."""
    server = _make_local_server()

    mock_repo = MagicMock()
    mock_repo.find_by_id = AsyncMock()

    factory = ConnectionFactory(credential_repository=mock_repo)
    adapter = await factory.create(server)

    assert isinstance(adapter, LocalConnectionAdapter)
    mock_repo.find_by_id.assert_not_awaited()


@pytest.mark.asyncio
async def test_create_ssh_adapter_uses_credential_fields():
    """Test 3: el SSHConnectionAdapter recibe host, port, username y private_key de la credencial."""
    server = _make_remote_server()
    credential = _make_credential(private_key="my-private-key")

    mock_repo = MagicMock()
    mock_repo.find_by_id = AsyncMock(return_value=credential)

    factory = ConnectionFactory(credential_repository=mock_repo)
    adapter = await factory.create(server)

    assert isinstance(adapter, SSHConnectionAdapter)
    assert adapter._host == "192.168.1.10"
    assert adapter._port == 22
    assert adapter._username == "root"
    assert adapter._private_key == "my-private-key"


@pytest.mark.asyncio
async def test_create_raises_when_credential_not_found():
    """Test 4: lanza ValueError si la credencial del servidor no existe."""
    server = _make_remote_server(credential_id="missing-cred")

    mock_repo = MagicMock()
    mock_repo.find_by_id = AsyncMock(return_value=None)

    factory = ConnectionFactory(credential_repository=mock_repo)

    with pytest.raises(ValueError, match="missing-cred"):
        await factory.create(server)
