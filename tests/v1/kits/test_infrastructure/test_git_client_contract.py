"""Contract Tests — GitClient port (T-40).

Verifica que GitPythonClient implementa el contrato definido por el port GitClient:

1. GitPythonClient es instancia de GitClient (satisface el contrato de tipo)
2. clone_shallow siempre retorna un str con formato SHA hexadecimal
3. Los archivos temporales se eliminan incluso cuando el clone falla
4. Las credenciales nunca se persisten en disco después de la operación
"""
import os
import re
import tempfile
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.v1.kits.application.interfaces.git_client import GitClient
from app.v1.kits.infrastructure.adapters.git_python_client import GitPythonClient
from app.v1.kits.infrastructure.exceptions import GitClientError
from app.v1.servers.domain.entities.credential import Credential
from app.v1.servers.domain.value_objects.credential_type import CredentialType

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_NOW = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
_HEX_SHA_RE = re.compile(r"^[0-9a-f]{7,40}$")


def _make_process(returncode: int, stdout: bytes = b"", stderr: bytes = b"") -> MagicMock:
    process = MagicMock()
    process.returncode = returncode
    process.communicate = AsyncMock(return_value=(stdout, stderr))
    return process


def _ssh_credential() -> Credential:
    return Credential(
        id="cred-contract-ssh",
        user_id="user-contract",
        name="Contract SSH Key",
        type=CredentialType("git_ssh"),
        username=None,
        password=None,
        private_key="-----BEGIN OPENSSH PRIVATE KEY-----\ncontractkey\n-----END OPENSSH PRIVATE KEY-----",
        created_at=_NOW,
        updated_at=_NOW,
    )


# ---------------------------------------------------------------------------
# T-40-1: GitPythonClient satisface el contrato de tipo GitClient
# ---------------------------------------------------------------------------


def test_git_python_client_is_instance_of_git_client() -> None:
    """GitPythonClient es una instancia de GitClient (contrato de tipo satisfecho)."""
    client = GitPythonClient()
    assert isinstance(client, GitClient)


# ---------------------------------------------------------------------------
# T-40-2: clone_shallow retorna str con formato SHA hexadecimal
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_clone_shallow_returns_hexadecimal_sha_string() -> None:
    """clone_shallow devuelve un str con formato de SHA hexadecimal."""
    client = GitPythonClient()

    clone_process = _make_process(returncode=0)
    sha_process = _make_process(returncode=0, stdout=b"a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2\n")

    with patch(
        "asyncio.create_subprocess_exec",
        new=AsyncMock(side_effect=[clone_process, sha_process]),
    ):
        with tempfile.TemporaryDirectory() as tmp:
            result = await client.clone_shallow(
                url="https://github.com/org/repo",
                ref="main",
                dest_path=tmp,
            )

    # El contrato exige que retorne un str (commit_sha)
    assert isinstance(result, str)
    assert len(result) > 0
    assert _HEX_SHA_RE.match(result), f"SHA no tiene formato hexadecimal: {result!r}"


# ---------------------------------------------------------------------------
# T-40-3: Los archivos temporales se eliminan incluso cuando el clone falla
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_temp_files_cleaned_up_even_when_clone_fails() -> None:
    """Los archivos temporales se eliminan aunque el clone falle (RNF-15)."""
    client = GitPythonClient()
    cred = _ssh_credential()

    # El clone falla con código de salida != 0
    failing_process = _make_process(returncode=1, stderr=b"Connection refused")

    captured_key_paths: list[str] = []
    original_write_ssh = client._write_ssh_key

    def spy_write_ssh_key(private_key: str) -> str:
        path = original_write_ssh(private_key)
        captured_key_paths.append(path)
        return path

    with patch.object(client, "_write_ssh_key", side_effect=spy_write_ssh_key):
        with patch(
            "asyncio.create_subprocess_exec",
            new=AsyncMock(return_value=failing_process),
        ):
            with tempfile.TemporaryDirectory() as tmp:
                with pytest.raises(GitClientError):
                    await client.clone_shallow(
                        url="git@github.com:org/repo.git",
                        ref="main",
                        dest_path=tmp,
                        credential=cred,
                    )

    assert len(captured_key_paths) == 1
    # El archivo temporal debe haberse limpiado aunque el clone haya fallado
    assert not os.path.exists(captured_key_paths[0]), (
        "La clave SSH temporal no fue eliminada tras un clone fallido (RNF-15)"
    )


# ---------------------------------------------------------------------------
# T-40-4: Las credenciales no se persisten en disco después de la operación
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_credentials_not_persisted_on_disk_after_operation() -> None:
    """Las credenciales SSH no se persisten en disco permanentemente (RNF-09, RNF-15).

    Verifica que ningún archivo con la clave privada permanece en el
    sistema de archivos tras una operación exitosa o fallida.
    """
    client = GitPythonClient()
    cred = _ssh_credential()

    clone_process = _make_process(returncode=0)
    sha_process = _make_process(returncode=0, stdout=b"cafebabe\n")

    # Capturamos todos los archivos temporales creados durante la operación
    temp_files_created: list[str] = []
    original_mkstemp = tempfile.mkstemp

    def spy_mkstemp(*args, **kwargs):
        fd, path = original_mkstemp(*args, **kwargs)
        temp_files_created.append(path)
        return fd, path

    with patch("tempfile.mkstemp", side_effect=spy_mkstemp):
        with patch(
            "asyncio.create_subprocess_exec",
            new=AsyncMock(side_effect=[clone_process, sha_process]),
        ):
            with tempfile.TemporaryDirectory() as tmp:
                await client.clone_shallow(
                    url="git@github.com:org/repo.git",
                    ref="main",
                    dest_path=tmp,
                    credential=cred,
                )

    # Ningún archivo temporal creado durante la operación debe permanecer en disco
    assert len(temp_files_created) == 1, "Se esperaba exactamente 1 archivo temporal para la clave SSH"
    for path in temp_files_created:
        assert not os.path.exists(path), (
            f"La credencial fue persistida permanentemente en: {path} (viola RNF-09, RNF-15)"
        )
