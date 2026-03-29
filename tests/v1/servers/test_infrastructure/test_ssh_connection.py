"""Tests para SSHConnectionAdapter (T-34).

Estrategia: mock de asyncssh — los tests validan el comportamiento del adaptador
(mapeo de resultados, manejo de sudo, propagación de errores, timeout) sin
necesitar un servidor SSH real.
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.v1.servers.infrastructure.adapters.ssh_connection import SSHConnectionAdapter
from app.v1.servers.infrastructure.exceptions import SSHConnectionError


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_adapter(
    host: str = "192.168.1.10",
    port: int = 22,
    username: str = "root",
    private_key: str = "-----BEGIN RSA PRIVATE KEY-----\nMIIE...",
    password: str | None = None,
    connect_timeout: int = 30,
) -> SSHConnectionAdapter:
    return SSHConnectionAdapter(
        host=host,
        port=port,
        username=username,
        private_key=private_key,
        password=password,
        connect_timeout=connect_timeout,
    )


def _make_process_result(returncode: int = 0, stdout: str = "", stderr: str = "") -> MagicMock:
    result = MagicMock()
    result.returncode = returncode
    result.stdout = stdout
    result.stderr = stderr
    return result


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_execute_returns_stdout_stderr_returncode():
    """Test 1: execute retorna (returncode, stdout, stderr) del proceso remoto."""
    adapter = _make_adapter()
    process_result = _make_process_result(returncode=0, stdout="hello\n", stderr="")

    mock_conn = AsyncMock()
    mock_conn.run = AsyncMock(return_value=process_result)

    with patch(
        "app.v1.servers.infrastructure.adapters.ssh_connection.asyncssh.connect",
        new=AsyncMock(return_value=mock_conn),
    ):
        rc, stdout, stderr = await adapter.execute("echo hello")

    assert rc == 0
    assert stdout == "hello\n"
    assert stderr == ""
    mock_conn.run.assert_awaited_once_with("echo hello", timeout=30)


@pytest.mark.asyncio
async def test_execute_with_sudo_prefixes_command():
    """Test 2: execute con sudo=True antepone 'sudo' al comando."""
    adapter = _make_adapter()
    process_result = _make_process_result(returncode=0, stdout="root\n", stderr="")

    mock_conn = AsyncMock()
    mock_conn.run = AsyncMock(return_value=process_result)

    with patch(
        "app.v1.servers.infrastructure.adapters.ssh_connection.asyncssh.connect",
        new=AsyncMock(return_value=mock_conn),
    ):
        await adapter.execute("whoami", sudo=True)

    mock_conn.run.assert_awaited_once_with("sudo whoami", timeout=30)


@pytest.mark.asyncio
async def test_execute_raises_ssh_connection_error_on_failure():
    """Test 3: execute lanza SSHConnectionError cuando asyncssh falla."""
    adapter = _make_adapter()

    with patch(
        "app.v1.servers.infrastructure.adapters.ssh_connection.asyncssh.connect",
        new=AsyncMock(side_effect=Exception("Connection refused")),
    ):
        with pytest.raises(SSHConnectionError):
            await adapter.execute("ls")


@pytest.mark.asyncio
async def test_file_exists_returns_true_when_file_present():
    """Test 4: file_exists retorna True cuando el archivo existe en el servidor."""
    adapter = _make_adapter()
    # exit_code 0 → archivo existe
    process_result = _make_process_result(returncode=0, stdout="", stderr="")

    mock_conn = AsyncMock()
    mock_conn.run = AsyncMock(return_value=process_result)

    with patch(
        "app.v1.servers.infrastructure.adapters.ssh_connection.asyncssh.connect",
        new=AsyncMock(return_value=mock_conn),
    ):
        exists = await adapter.file_exists("/etc/os-release")

    assert exists is True


@pytest.mark.asyncio
async def test_file_exists_returns_false_when_file_absent():
    """Test 5: file_exists retorna False cuando el archivo no existe (exit_code != 0)."""
    adapter = _make_adapter()
    # exit_code 1 → archivo no existe
    process_result = _make_process_result(returncode=1, stdout="", stderr="")

    mock_conn = AsyncMock()
    mock_conn.run = AsyncMock(return_value=process_result)

    with patch(
        "app.v1.servers.infrastructure.adapters.ssh_connection.asyncssh.connect",
        new=AsyncMock(return_value=mock_conn),
    ):
        exists = await adapter.file_exists("/tmp/nonexistent")

    assert exists is False


@pytest.mark.asyncio
async def test_upload_file_calls_sftp_put():
    """Test 6: upload_file usa SFTP para transferir el archivo al servidor remoto."""
    adapter = _make_adapter()

    mock_sftp = AsyncMock()
    mock_sftp.put = AsyncMock()

    mock_conn = AsyncMock()
    mock_conn.start_sftp_client = AsyncMock(return_value=mock_sftp)
    mock_sftp.__aenter__ = AsyncMock(return_value=mock_sftp)
    mock_sftp.__aexit__ = AsyncMock(return_value=None)

    with patch(
        "app.v1.servers.infrastructure.adapters.ssh_connection.asyncssh.connect",
        new=AsyncMock(return_value=mock_conn),
    ):
        await adapter.upload_file("/local/path/file.sh", "/remote/path/file.sh")

    mock_sftp.put.assert_awaited_once_with("/local/path/file.sh", "/remote/path/file.sh")


@pytest.mark.asyncio
async def test_close_disconnects_connection():
    """Test 7: close cierra la conexión SSH subyacente."""
    adapter = _make_adapter()

    mock_conn = AsyncMock()
    mock_conn.run = AsyncMock(return_value=_make_process_result())
    mock_conn.close = MagicMock()
    mock_conn.wait_closed = AsyncMock()

    with patch(
        "app.v1.servers.infrastructure.adapters.ssh_connection.asyncssh.connect",
        new=AsyncMock(return_value=mock_conn),
    ):
        # Forzar apertura de conexión
        await adapter.execute("echo test")
        await adapter.close()

    mock_conn.close.assert_called_once()


@pytest.mark.asyncio
async def test_execute_reuses_existing_connection():
    """Test 8: execute reutiliza la conexión abierta en lugar de crear una nueva."""
    adapter = _make_adapter()
    process_result = _make_process_result(returncode=0, stdout="ok", stderr="")

    mock_conn = AsyncMock()
    mock_conn.run = AsyncMock(return_value=process_result)

    with patch(
        "app.v1.servers.infrastructure.adapters.ssh_connection.asyncssh.connect",
        new=AsyncMock(return_value=mock_conn),
    ) as mock_connect:
        await adapter.execute("cmd1")
        await adapter.execute("cmd2")

    # connect solo debe llamarse una vez pese a dos execute
    mock_connect.assert_awaited_once()
