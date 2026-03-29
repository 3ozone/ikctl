"""Tests para LocalConnectionAdapter (T-35).

Estrategia: mock de asyncio.create_subprocess_shell — sin ejecutar
procesos reales. Valida el comportamiento del adaptador local:
timeout, sudo ignorado con warning, shutil.copy2, os.path.exists.
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.v1.servers.infrastructure.adapters.local_connection import LocalConnectionAdapter
from app.v1.servers.infrastructure.exceptions import SSHConnectionError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_process(returncode: int = 0, stdout: bytes = b"", stderr: bytes = b"") -> MagicMock:
    proc = MagicMock()
    proc.returncode = returncode
    proc.communicate = AsyncMock(return_value=(stdout, stderr))
    return proc


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_execute_returns_stdout_stderr_returncode():
    """Test 1: execute retorna (returncode, stdout, stderr) de un proceso local."""
    adapter = LocalConnectionAdapter()
    proc = _make_process(returncode=0, stdout=b"hello\n", stderr=b"")

    with patch(
        "app.v1.servers.infrastructure.adapters.local_connection.asyncio.create_subprocess_shell",
        new=AsyncMock(return_value=proc),
    ):
        rc, stdout, stderr = await adapter.execute("echo hello")

    assert rc == 0
    assert stdout == "hello\n"
    assert stderr == ""


@pytest.mark.asyncio
async def test_execute_with_sudo_is_ignored_and_logs_warning(caplog):
    """Test 2: execute con sudo=True NO antepone sudo — lo ignora y emite warning."""
    import logging

    adapter = LocalConnectionAdapter()
    proc = _make_process(returncode=0, stdout=b"root\n", stderr=b"")

    with patch(
        "app.v1.servers.infrastructure.adapters.local_connection.asyncio.create_subprocess_shell",
        new=AsyncMock(return_value=proc),
    ) as mock_shell:
        with caplog.at_level(logging.WARNING):
            await adapter.execute("whoami", sudo=True)

    # El comando NO contiene "sudo"
    called_cmd = mock_shell.call_args[0][0]
    assert "sudo" not in called_cmd
    # Se emite un warning
    assert any("sudo" in record.message.lower() for record in caplog.records)


@pytest.mark.asyncio
async def test_execute_raises_ssh_connection_error_on_failure():
    """Test 3: execute envuelve excepciones en SSHConnectionError."""
    adapter = LocalConnectionAdapter()

    with patch(
        "app.v1.servers.infrastructure.adapters.local_connection.asyncio.create_subprocess_shell",
        side_effect=OSError("subprocess failed"),
    ):
        with pytest.raises(SSHConnectionError, match="subprocess failed"):
            await adapter.execute("bad-command")


@pytest.mark.asyncio
async def test_file_exists_returns_true_when_path_exists():
    """Test 4: file_exists devuelve True si el path existe localmente."""
    adapter = LocalConnectionAdapter()

    with patch(
        "app.v1.servers.infrastructure.adapters.local_connection.os.path.exists",
        return_value=True,
    ):
        result = await adapter.file_exists("/etc/hosts")

    assert result is True


@pytest.mark.asyncio
async def test_file_exists_returns_false_when_path_absent():
    """Test 5: file_exists devuelve False si el path no existe."""
    adapter = LocalConnectionAdapter()

    with patch(
        "app.v1.servers.infrastructure.adapters.local_connection.os.path.exists",
        return_value=False,
    ):
        result = await adapter.file_exists("/nonexistent/path")

    assert result is False


@pytest.mark.asyncio
async def test_upload_file_copies_file_locally():
    """Test 6: upload_file usa shutil.copy2 para copiar el archivo localmente."""
    adapter = LocalConnectionAdapter()

    with patch(
        "app.v1.servers.infrastructure.adapters.local_connection.shutil.copy2"
    ) as mock_copy:
        await adapter.upload_file("/local/source.sh", "/remote/dest.sh")

    mock_copy.assert_called_once_with("/local/source.sh", "/remote/dest.sh")
