"""Tests de integración — GitPythonClient (T-39).

Verifica:
1. clone_shallow público OK — retorna commit SHA
2. clone_shallow privado git_https OK — embede credentials en URL
3. clone_shallow privado git_ssh OK — crea y borra clave temporal del disco
4. clone_shallow timeout — lanza GitClientError
5. read_yaml_file YAML inválido — lanza GitClientError
"""
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.v1.kits.infrastructure.adapters.git_python_client import GitPythonClient
from app.v1.kits.infrastructure.exceptions import GitClientError
from app.v1.servers.domain.entities.credential import Credential
from app.v1.servers.domain.value_objects.credential_type import CredentialType

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_NOW = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


def _make_process(returncode: int, stdout: bytes = b"", stderr: bytes = b"") -> MagicMock:
    """Crea un mock de proceso subprocess async."""
    process = MagicMock()
    process.returncode = returncode
    process.communicate = AsyncMock(return_value=(stdout, stderr))
    return process


def _https_credential() -> Credential:
    return Credential(
        id="cred-https-001",
        user_id="user-001",
        name="My PAT",
        type=CredentialType("git_https"),
        username="myuser",
        password="mytoken",
        private_key=None,
        created_at=_NOW,
        updated_at=_NOW,
    )


def _ssh_credential() -> Credential:
    return Credential(
        id="cred-ssh-002",
        user_id="user-001",
        name="My SSH Key",
        type=CredentialType("git_ssh"),
        username=None,
        password=None,
        private_key="-----BEGIN OPENSSH PRIVATE KEY-----\nfakekey\n-----END OPENSSH PRIVATE KEY-----",
        created_at=_NOW,
        updated_at=_NOW,
    )


# ---------------------------------------------------------------------------
# T-39-1: clone público OK
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_clone_shallow_public_ok_returns_sha() -> None:
    """clone_shallow sin credencial retorna el SHA del commit HEAD."""
    client = GitPythonClient()
    _SHA = b"deadbeefcafebabe\n"

    clone_process = _make_process(returncode=0)
    sha_process = _make_process(returncode=0, stdout=_SHA)

    with patch(
        "asyncio.create_subprocess_exec",
        new=AsyncMock(side_effect=[clone_process, sha_process]),
    ) as mock_exec:
        with tempfile.TemporaryDirectory() as tmp:
            result = await client.clone_shallow(
                url="https://github.com/org/public-repo",
                ref="main",
                dest_path=tmp,
            )

    assert result == "deadbeefcafebabe"

    # Verificar args del primer call (git clone)
    first_args = mock_exec.call_args_list[0].args
    assert first_args[0] == "git"
    assert "clone" in first_args
    assert "--depth" in first_args
    assert "1" in first_args
    assert "--branch" in first_args
    assert "main" in first_args


# ---------------------------------------------------------------------------
# T-39-2: clone privado git_https embede credentials en URL
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_clone_shallow_git_https_embeds_credentials_in_url() -> None:
    """clone_shallow git_https embede user:token en la URL de clone."""
    client = GitPythonClient()
    cred = _https_credential()

    clone_process = _make_process(returncode=0)
    sha_process = _make_process(returncode=0, stdout=b"abc123\n")

    with patch(
        "asyncio.create_subprocess_exec",
        new=AsyncMock(side_effect=[clone_process, sha_process]),
    ) as mock_exec:
        with tempfile.TemporaryDirectory() as tmp:
            result = await client.clone_shallow(
                url="https://github.com/org/private-repo",
                ref="main",
                dest_path=tmp,
                credential=cred,
            )

    assert result == "abc123"

    # La URL pasada al clone debe contener las credenciales embebidas
    first_args = mock_exec.call_args_list[0].args
    # La URL es el penúltimo argumento (antes de dest_path)
    clone_url = first_args[-2]
    assert "myuser:mytoken@" in clone_url
    assert clone_url.startswith("https://")


# ---------------------------------------------------------------------------
# T-39-3: clone privado git_ssh no deja la clave en disco
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_clone_shallow_git_ssh_key_deleted_after_call() -> None:
    """clone_shallow git_ssh: la clave privada temporal se elimina del disco."""
    client = GitPythonClient()
    cred = _ssh_credential()

    clone_process = _make_process(returncode=0)
    sha_process = _make_process(returncode=0, stdout=b"sha456\n")

    captured_key_paths: list[str] = []
    original_write_ssh = client._write_ssh_key

    def spy_write_ssh_key(private_key: str) -> str:
        path = original_write_ssh(private_key)
        captured_key_paths.append(path)
        return path

    with patch.object(client, "_write_ssh_key", side_effect=spy_write_ssh_key):
        with patch(
            "asyncio.create_subprocess_exec",
            new=AsyncMock(side_effect=[clone_process, sha_process]),
        ):
            with tempfile.TemporaryDirectory() as tmp:
                result = await client.clone_shallow(
                    url="git@github.com:org/private-repo.git",
                    ref="main",
                    dest_path=tmp,
                    credential=cred,
                )

    assert result == "sha456"
    assert len(captured_key_paths) == 1
    # RNF-15: la clave temporal debe haberse borrado del disco
    assert not os.path.exists(captured_key_paths[0])


# ---------------------------------------------------------------------------
# T-39-4: clone timeout — lanza GitClientError
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_clone_shallow_timeout_raises_git_client_error() -> None:
    """clone_shallow con timeout lanza GitClientError con mensaje descriptivo."""
    client = GitPythonClient()

    with patch(
        "asyncio.create_subprocess_exec",
        new=AsyncMock(side_effect=TimeoutError("simulated timeout")),
    ):
        with tempfile.TemporaryDirectory() as tmp:
            with pytest.raises(GitClientError, match="timed out"):
                await client.clone_shallow(
                    url="https://github.com/org/slow-repo",
                    ref="main",
                    dest_path=tmp,
                )


# ---------------------------------------------------------------------------
# T-39-5: read_yaml_file con YAML inválido — lanza GitClientError
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_read_yaml_file_invalid_yaml_raises_git_client_error() -> None:
    """read_yaml_file con YAML sintácticamente inválido lanza GitClientError."""
    client = GitPythonClient()

    with tempfile.TemporaryDirectory() as tmp:
        yaml_path = Path(tmp) / "ikctl.yaml"
        yaml_path.write_text(
            "key: [\ninvalid yaml content: {{{{",
            encoding="utf-8",
        )

        with pytest.raises(GitClientError, match="Invalid YAML"):
            await client.read_yaml_file(dest_path=tmp, relative_path="ikctl.yaml")
