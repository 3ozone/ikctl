"""Tests para SSHKitExecutor — T-35 y T-36.

T-35: Flujo de ejecución completo con mocks de Connection, GitClient, FileCacheRepository.
T-36: Tests de caché SHA-256 — diferencial upload, auto-repair.
"""
from __future__ import annotations

import hashlib
import os
from datetime import datetime, timezone
from typing import Optional
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.v1.kits.domain.entities.kit import Kit
from app.v1.kits.domain.entities.repository import Repository
from app.v1.kits.domain.value_objects.sync_status import SyncStatus
from app.v1.operations.infrastructure.adapters.ssh_kit_executor import SSHKitExecutor
from app.v1.servers.domain.entities.credential import Credential
from app.v1.servers.domain.entities.server import Server
from app.v1.servers.domain.value_objects.credential_type import CredentialType
from app.v1.servers.domain.value_objects.server_status import ServerStatus
from app.v1.servers.domain.value_objects.server_type import ServerType

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Factories
# ---------------------------------------------------------------------------


def make_server() -> Server:
    return Server(
        id="srv-1",
        user_id="user-1",
        name="prod",
        description="",
        type=ServerType("remote"),
        status=ServerStatus("active"),
        host="10.0.0.1",
        port=22,
        credential_id="cred-1",
        os_id=None,
        os_version=None,
        os_name=None,
        created_at=NOW,
        updated_at=NOW,
    )


def make_kit(
    upload_files: tuple[str, ...] = ("nginx.conf.j2", "install.sh"),
    pipeline_files: tuple[str, ...] = ("install.sh",),
    backup_files: tuple[str, ...] = ("/etc/nginx/nginx.conf",),
) -> Kit:
    return Kit(
        id="kit-1",
        user_id="user-1",
        repository_id="repo-1",
        path_in_repo="nginx",
        name="Install NGINX",
        description="",
        version="1.0.0",
        tags=[],
        values={"port": 80},
        debug_level="none",
        upload_files=upload_files,
        pipeline_files=pipeline_files,
        backup_files=backup_files,
        sync_status=SyncStatus("synced"),
        last_synced_at=NOW,
        last_commit_sha="abc123",
        sync_error_message=None,
        is_deleted=False,
        created_at=NOW,
        updated_at=NOW,
    )


def make_ssh_credential() -> Credential:
    return Credential(
        id="cred-1",
        user_id="user-1",
        name="prod-key",
        type=CredentialType("ssh"),
        username="root",
        password=None,
        private_key="-----BEGIN RSA PRIVATE KEY-----\nfake\n-----END RSA PRIVATE KEY-----",
        created_at=NOW,
        updated_at=NOW,
    )


def make_repository() -> Repository:
    return Repository(
        id="repo-1",
        user_id="user-1",
        url="https://github.com/org/kits.git",
        ref="main",
        credential_id=None,
        sync_status=SyncStatus("synced"),
        last_synced_at=NOW,
        last_commit_sha="abc123",
        sync_error_message=None,
        is_deleted=False,
        created_at=NOW,
        updated_at=NOW,
    )


def _make_clone_side_effect(kit: Kit):
    """Crea un side_effect para clone_shallow que genera los archivos del kit en dest_path."""
    async def _clone(url, ref, dest_path, credential):
        kit_dir = os.path.join(dest_path, kit.path_in_repo)
        os.makedirs(kit_dir, exist_ok=True)
        for filename in kit.upload_files:
            filepath = os.path.join(kit_dir, filename)
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, "w") as f:
                if filename.endswith(".j2"):
                    f.write("listen {{ port }};")
                else:
                    f.write("#!/bin/bash\necho done")
        return "abc123sha"
    return _clone


def make_executor(kit: Kit | None = None, mock_conn: AsyncMock | None = None):
    """Factory del executor con todos los mocks configurados."""
    _kit = kit or make_kit()
    _conn = mock_conn or AsyncMock()
    # Default connection responses
    _conn.execute = AsyncMock(return_value=(0, "ok", ""))
    _conn.file_exists = AsyncMock(return_value=True)
    _conn.upload_file = AsyncMock()
    _conn.close = AsyncMock()

    git_client = AsyncMock()
    git_client.clone_shallow = AsyncMock(side_effect=_make_clone_side_effect(_kit))

    file_cache = AsyncMock()
    file_cache.find_hash = AsyncMock(return_value=None)
    file_cache.upsert = AsyncMock()
    file_cache.invalidate_server_kit = AsyncMock()

    git_repo_port = AsyncMock()
    git_repo_port.find_by_id_internal = AsyncMock(return_value=make_repository())

    credential_repo = AsyncMock()
    credential_repo.find_by_id_internal = AsyncMock(return_value=None)

    executor = SSHKitExecutor(
        git_client=git_client,
        file_cache=file_cache,
        git_repository_port=git_repo_port,
        credential_repository=credential_repo,
        connection_factory=lambda s, c: _conn,
    )
    return executor, git_client, file_cache, git_repo_port, credential_repo, _conn


# ---------------------------------------------------------------------------
# T-35: Flujo de ejecución completo
# ---------------------------------------------------------------------------


class TestSSHKitExecutorExecution:
    """T-35: Tests del flujo de ejecución con mocks."""

    @pytest.mark.asyncio
    async def test_snapshot_creates_backup_of_backup_files(self):
        """Paso 1: se ejecuta cp {path} {path}.bak.ikctl para cada archivo de backup."""
        kit = make_kit(backup_files=("/etc/nginx/nginx.conf",))
        executor, _, _, _, _, conn = make_executor(kit=kit)
        conn.execute = AsyncMock(return_value=(0, "content", ""))
        conn.file_exists = AsyncMock(return_value=True)

        await executor.execute(make_server(), kit, make_ssh_credential(), "none", {"port": 80}, sudo=True)

        # Se debe haber ejecutado cp con sufijo .bak.ikctl para cada backup_file
        calls = [str(call) for call in conn.execute.call_args_list]
        bak_calls = [c for c in calls if ".bak.ikctl" in c]
        assert len(bak_calls) >= 1, "Ningún comando de backup .bak.ikctl encontrado"

    @pytest.mark.asyncio
    async def test_pipeline_executed_with_sudo(self):
        """Paso 5: con sudo=True cada pipeline_file se ejecuta con sudo=True."""
        kit = make_kit(pipeline_files=("install.sh",))
        executor, _, _, _, _, conn = make_executor(kit=kit)

        await executor.execute(make_server(), kit, make_ssh_credential(), "none", {"port": 80}, sudo=True)

        sudo_calls = [
            call for call in conn.execute.call_args_list
            if call.kwargs.get("sudo") is True or (len(call.args) > 1 and call.args[1] is True)
        ]
        assert len(sudo_calls) > 0, "Ningún comando ejecutado con sudo=True"

    @pytest.mark.asyncio
    async def test_pipeline_executed_without_sudo(self):
        """Paso 5: con sudo=False cada pipeline_file se ejecuta con sudo=False."""
        kit = make_kit(pipeline_files=("install.sh",))
        executor, _, _, _, _, conn = make_executor(kit=kit)

        await executor.execute(make_server(), kit, make_ssh_credential(), "none", {"port": 80}, sudo=False)

        sudo_calls = [
            call for call in conn.execute.call_args_list
            if call.kwargs.get("sudo") is True
        ]
        assert len(sudo_calls) == 0, "Algún comando se ejecutó con sudo=True cuando debería ser False"

    @pytest.mark.asyncio
    async def test_output_accumulated_from_pipeline(self):
        """La salida del pipeline se incluye en el output retornado."""
        kit = make_kit(pipeline_files=("install.sh",))
        executor, _, _, _, _, conn = make_executor(kit=kit)
        conn.execute = AsyncMock(return_value=(0, "NGINX installed successfully", ""))

        output, _ = await executor.execute(make_server(), kit, make_ssh_credential(), "none", {"port": 80}, sudo=True)

        assert "NGINX installed successfully" in output

    @pytest.mark.asyncio
    async def test_cleanup_removes_remote_temp_dir(self):
        """Paso 6: se ejecuta rm -rf del directorio temporal remoto."""
        kit = make_kit()
        executor, _, _, _, _, conn = make_executor(kit=kit)

        await executor.execute(make_server(), kit, make_ssh_credential(), "none", {"port": 80}, sudo=True)

        cleanup_calls = [
            call for call in conn.execute.call_args_list
            if "rm -rf" in str(call)
        ]
        assert len(cleanup_calls) > 0, "No se ejecutó ningún rm -rf de limpieza"

    @pytest.mark.asyncio
    async def test_backup_files_returned_match_kit_backup_files(self):
        """Los backup_files retornados son los declarados en el kit."""
        expected = ("/etc/nginx/nginx.conf", "/etc/nginx/conf.d/default.conf")
        kit = make_kit(backup_files=expected)
        executor, _, _, _, _, _ = make_executor(kit=kit)

        _, backup_files = await executor.execute(
            make_server(), kit, make_ssh_credential(), "none", {"port": 80}
        )

        assert backup_files == expected


# ---------------------------------------------------------------------------
# T-36: SHA-256 cache
# ---------------------------------------------------------------------------


class TestSSHKitExecutorCache:
    """T-36: Tests de la caché SHA-256 diferencial."""

    @pytest.mark.asyncio
    async def test_unchanged_file_not_uploaded(self):
        """Si el hash almacenado coincide con el contenido renderizado, no se sube el archivo."""
        kit = make_kit(upload_files=("nginx.conf.j2",), pipeline_files=())
        executor, git_client, file_cache, _, _, conn = make_executor(kit=kit)

        # Obtener el hash real del contenido que se renderizará
        rendered_content = "listen 80;".encode("utf-8")
        expected_hash = hashlib.sha256(rendered_content).hexdigest()

        # Configurar clone para que genere el template exacto que produce "listen 80;"
        async def clone_with_exact_template(url, ref, dest_path, credential):
            kit_dir = os.path.join(dest_path, kit.path_in_repo)
            os.makedirs(kit_dir, exist_ok=True)
            with open(os.path.join(kit_dir, "nginx.conf.j2"), "w") as f:
                f.write("listen {{ port }};")
            return "sha"

        git_client.clone_shallow = AsyncMock(side_effect=clone_with_exact_template)
        file_cache.find_hash = AsyncMock(return_value=expected_hash)

        await executor.execute(make_server(), kit, make_ssh_credential(), "none", {"port": 80}, sudo=True)

        conn.upload_file.assert_not_called()

    @pytest.mark.asyncio
    async def test_changed_file_is_uploaded_and_cache_updated(self):
        """Si el hash difiere del almacenado, se sube el archivo y se actualiza la caché."""
        kit = make_kit(upload_files=("nginx.conf.j2",), pipeline_files=())
        executor, git_client, file_cache, _, _, conn = make_executor(kit=kit)

        # Hash diferente → debe subir
        file_cache.find_hash = AsyncMock(return_value="old_hash_that_differs")

        async def clone_known(url, ref, dest_path, credential):
            kit_dir = os.path.join(dest_path, kit.path_in_repo)
            os.makedirs(kit_dir, exist_ok=True)
            with open(os.path.join(kit_dir, "nginx.conf.j2"), "w") as f:
                f.write("listen {{ port }};")
            return "sha"

        git_client.clone_shallow = AsyncMock(side_effect=clone_known)

        await executor.execute(make_server(), kit, make_ssh_credential(), "none", {"port": 80}, sudo=True)

        conn.upload_file.assert_called_once()
        file_cache.upsert.assert_called_once()

    @pytest.mark.asyncio
    async def test_autorepair_invalidates_cache_when_remote_dir_missing(self):
        """Si el directorio remoto no existe, se invalida la caché y se sube todo."""
        kit = make_kit(upload_files=("nginx.conf.j2",), pipeline_files=())
        executor, git_client, file_cache, _, _, conn = make_executor(kit=kit)

        # file_exists devuelve False → directorio no existe
        conn.file_exists = AsyncMock(return_value=False)
        # Hash "cacheado" que normalmente evitaría la subida
        file_cache.find_hash = AsyncMock(return_value="some_hash")

        async def clone_known(url, ref, dest_path, credential):
            kit_dir = os.path.join(dest_path, kit.path_in_repo)
            os.makedirs(kit_dir, exist_ok=True)
            with open(os.path.join(kit_dir, "nginx.conf.j2"), "w") as f:
                f.write("listen {{ port }};")
            return "sha"

        git_client.clone_shallow = AsyncMock(side_effect=clone_known)

        await executor.execute(make_server(), kit, make_ssh_credential(), "none", {"port": 80}, sudo=True)

        file_cache.invalidate_server_kit.assert_called_once_with("srv-1", "kit-1")
        conn.upload_file.assert_called_once()
