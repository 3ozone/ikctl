"""SSHKitExecutor — Implementación concreta de RemoteKitExecutor.

Ejecuta los 6 pasos de un kit sobre un servidor remoto vía SSH:
  1. Snapshot de ficheros de backup (copia en directorio temporal remoto)
  2. Git clone del repositorio del kit (shallow, depth=1)
  3. Render Jinja2 de los upload_files con los valores de la operación
  4. Transferencia SFTP diferencial con caché SHA-256 (solo archivos cambiados)
  5. Ejecución del pipeline (scripts en orden, con sudo)
  6. Limpieza del directorio temporal remoto (best-effort en finally)
"""
from __future__ import annotations

import hashlib
import os
import tempfile
from pathlib import Path
from typing import Callable, Optional
from uuid import uuid4

import jinja2

from app.v1.kits.application.interfaces.git_client import GitClient
from app.v1.kits.domain.entities.kit import Kit
from app.v1.operations.application.interfaces.credential_repository import (
    CredentialRepository,
)
from app.v1.operations.application.interfaces.file_cache_repository import (
    FileCacheRepository,
)
from app.v1.operations.application.interfaces.git_repository_port import GitRepositoryPort
from app.v1.operations.application.interfaces.remote_kit_executor import RemoteKitExecutor
from app.v1.operations.infrastructure.exceptions import SSHCommandError
from app.v1.servers.application.interfaces.connection import Connection
from app.v1.servers.domain.entities.credential import Credential
from app.v1.servers.domain.entities.server import Server
from app.v1.servers.infrastructure.adapters.ssh_connection import SSHConnectionAdapter


def _default_connection_factory(server: Server, credential: Credential) -> Connection:
    """Crea un SSHConnectionAdapter a partir del servidor y su credencial SSH."""
    return SSHConnectionAdapter(
        host=server.host or "",
        port=server.port or 22,
        username=credential.username or "root",
        private_key=credential.private_key,
        password=credential.password,
    )


class SSHKitExecutor(RemoteKitExecutor):
    """Ejecuta un kit en un servidor remoto siguiendo los 6 pasos SSH.

    Attrs:
        git_client: GitClient para clonar el repositorio del kit.
        file_cache: FileCacheRepository para la caché SHA-256 diferencial.
        git_repository_port: Puerto para obtener la URL y credencial del repo.
        credential_repository: Puerto para obtener la credencial git del repo.
        connection_factory: Callable que construye la Connection SSH. Si es None,
            usa _default_connection_factory (SSHConnectionAdapter con asyncssh).
            Se puede inyectar en tests para pasar una Connection mock.
    """

    def __init__(
        self,
        git_client: GitClient,
        file_cache: FileCacheRepository,
        git_repository_port: GitRepositoryPort,
        credential_repository: CredentialRepository,
        connection_factory: Optional[Callable[[Server, Credential], Connection]] = None,
    ) -> None:
        self._git_client = git_client
        self._file_cache = file_cache
        self._git_repo_port = git_repository_port
        self._credential_repo = credential_repository
        self._connection_factory = connection_factory or _default_connection_factory

    # ------------------------------------------------------------------
    # RemoteKitExecutor port
    # ------------------------------------------------------------------

    async def execute(
        self,
        server: Server,
        kit: Kit,
        credential: Credential,
        debug_level: str,
        values: dict,
    ) -> tuple[str, tuple[str, ...]]:
        """Ejecuta el kit en el servidor remoto.

        Args:
            server: Servidor destino.
            kit: Kit a ejecutar (contiene upload_files, pipeline_files, backup_files).
            credential: Credencial SSH del servidor destino.
            debug_level: Nivel de debug de la operación.
            values: Valores para el render Jinja2.

        Returns:
            Tupla (output acumulado, backup_files declarados en el kit).

        Raises:
            SSHCommandError: Si algún pipeline script falla (exit code != 0).
            Exception: Cualquier error de conexión, clone, render o SFTP.
        """
        conn = self._connection_factory(server, credential)
        tmp_id = str(uuid4())
        remote_tmp_dir = f"/tmp/ikctl_{tmp_id}"
        output_parts: list[str] = []

        try:
            # ── Paso 1: Snapshot backup (in-place .bak.ikctl) ────────────────
            if kit.backup_files:
                for path in kit.backup_files:
                    await conn.execute(
                        f"cp {path} {path}.bak.ikctl 2>/dev/null || true",
                        timeout=30,
                    )
                output_parts.append(f"[snapshot] backup in-place creado para {len(kit.backup_files)} ficheros")

            # ── Paso 2: Git clone ────────────────────────────────────────
            repo = await self._git_repo_port.find_by_id_internal(kit.repository_id)
            git_credential = None
            if repo and repo.credential_id:
                git_credential = await self._credential_repo.find_by_id_internal(
                    repo.credential_id
                )

            with tempfile.TemporaryDirectory() as local_tmp:
                if repo:
                    await self._git_client.clone_shallow(
                        repo.url, repo.ref, local_tmp, git_credential
                    )

                kit_local_path = Path(local_tmp) / kit.path_in_repo

                # ── Paso 3: Render Jinja2 ────────────────────────────────
                rendered_files: dict[str, bytes] = {}
                jinja_env = jinja2.Environment(
                    loader=jinja2.BaseLoader(), undefined=jinja2.Undefined
                )
                for filename in kit.upload_files:
                    file_path = kit_local_path / filename
                    template_content = file_path.read_text(encoding="utf-8")
                    template = jinja_env.from_string(template_content)
                    rendered = template.render(**values)
                    rendered_files[filename] = rendered.encode("utf-8")

                # ── Paso 4: SHA-256 diferencial + SFTP ──────────────────
                # Auto-repair: si el directorio remoto no existe, invalidar caché
                dir_exists = await conn.file_exists(remote_tmp_dir)
                if not dir_exists:
                    await self._file_cache.invalidate_server_kit(server.id, kit.id)

                await conn.execute(f"mkdir -p {remote_tmp_dir}", timeout=10)

                for filename, content in rendered_files.items():
                    content_hash = hashlib.sha256(content).hexdigest()
                    cached_hash = await self._file_cache.find_hash(
                        server.id, kit.id, filename
                    )

                    if cached_hash == content_hash:
                        continue  # archivo sin cambios — skip

                    # Subir archivo via SFTP
                    remote_filename = Path(filename).name
                    remote_path = f"{remote_tmp_dir}/{remote_filename}"

                    fd, tmp_local = tempfile.mkstemp(suffix=".tmp")
                    try:
                        os.write(fd, content)
                    finally:
                        os.close(fd)
                    try:
                        await conn.upload_file(tmp_local, remote_path)
                    finally:
                        try:
                            os.unlink(tmp_local)
                        except OSError:
                            pass

                    await self._file_cache.upsert(server.id, kit.id, filename, content_hash)
                    output_parts.append(f"[upload] {filename}")

                # ── Paso 5: Ejecución pipeline ───────────────────────────
                script_timeout = 600  # 10 minutos por script
                for filename in kit.pipeline_files:
                    remote_script = f"{remote_tmp_dir}/{Path(filename).name}"
                    await conn.execute(f"chmod +x {remote_script}", timeout=10)

                    rc, stdout, stderr = await conn.execute(
                        remote_script, sudo=True, timeout=script_timeout
                    )
                    if stdout:
                        output_parts.append(stdout)
                    if stderr:
                        output_parts.append(f"[stderr] {stderr}")

                    if rc != 0:
                        raise SSHCommandError(
                            f"Script '{filename}' falló con código {rc}: {stderr[:300]}"
                        )

        finally:
            # ── Paso 6: Limpieza (best-effort) ───────────────────────────
            try:
                await conn.execute(f"rm -rf {remote_tmp_dir}", timeout=30)
            except Exception:
                pass
            await conn.close()

        return "\n".join(filter(None, output_parts)), kit.backup_files
