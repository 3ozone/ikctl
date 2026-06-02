"""SSHBackupRestorer — implementa BackupRestorer via SSH.

Para cada path en backup_files, ejecuta:
    cp {path}.bak.ikctl {path}
en el servidor remoto usando la Connection del módulo servers.
"""
from __future__ import annotations

from typing import Callable, Optional

from app.v1.operations.application.interfaces.backup_restorer import BackupRestorer
from app.v1.operations.application.interfaces.credential_repository import CredentialRepository
from app.v1.operations.application.interfaces.server_repository import ServerRepository
from app.v1.servers.application.interfaces.connection import Connection
from app.v1.servers.domain.entities.credential import Credential
from app.v1.servers.domain.entities.server import Server
from app.v1.servers.infrastructure.adapters.ssh_connection import SSHConnectionAdapter


def _default_connection_factory(server: Server, credential: Credential) -> Connection:
    """Crea un SSHConnectionAdapter a partir del servidor y su credencial SSH."""
    return SSHConnectionAdapter(
        host=server.host or "",
        port=server.port or 22,
        username=credential.username or "root" if credential else "root",
        private_key=credential.private_key if credential else None,
        password=credential.password if credential else None,
    )


class SSHBackupRestorer(BackupRestorer):
    """Restaura ficheros .bak.ikctl en un servidor remoto via SSH."""

    def __init__(
        self,
        server_repo: ServerRepository,
        credential_repo: CredentialRepository,
        connection_factory: Optional[Callable[[Server, Credential], Connection]] = None,
    ) -> None:
        self._server_repo = server_repo
        self._credential_repo = credential_repo
        self._connection_factory = connection_factory or _default_connection_factory

    async def restore(
        self,
        server_id: str,
        backup_files: tuple[str, ...],
    ) -> tuple[str, ...]:
        server = await self._server_repo.find_by_id_internal(server_id)
        if server is None:
            return ()

        credential = None
        if server.credential_id:
            credential = await self._credential_repo.find_by_id_internal(server.credential_id)

        conn = self._connection_factory(server, credential)
        try:
            restored: list[str] = []
            for path in backup_files:
                rc, _, _ = await conn.execute(
                    f"cp {path}.bak.ikctl {path}",
                    sudo=True,
                    timeout=30,
                )
                if rc == 0:
                    restored.append(path)
            return tuple(restored)
        finally:
            await conn.close()