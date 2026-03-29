"""LocalConnectionAdapter — Implementación local del port Connection.

Ejecuta comandos en la máquina local usando asyncio.create_subprocess_shell.
Usado exclusivamente para el servidor `local` (el propio host donde corre ikctl).

El flag `sudo` se ignora con un warning — el proceso local ya corre con los
permisos del usuario que levantó ikctl (RNF-16).
La transferencia de archivos se resuelve con shutil.copy2 (copia local a local).
"""
import asyncio
import logging
import os
import shutil

from app.v1.servers.application.interfaces.connection import Connection
from app.v1.servers.infrastructure.exceptions import SSHConnectionError

logger = logging.getLogger(__name__)


class LocalConnectionAdapter(Connection):
    """Adaptador de conexión local — ejecuta comandos en el host donde corre ikctl."""

    async def execute(
        self, command: str, sudo: bool = False, timeout: int = 30
    ) -> tuple[int, str, str]:
        """Ejecuta un comando en el host local.

        Args:
            command: Comando a ejecutar.
            sudo: Ignorado — se emite un WARNING. El proceso ya tiene los permisos
                  del usuario que levantó ikctl (RNF-16).
            timeout: Timeout de ejecución en segundos (default 30).

        Returns:
            Tupla (return_code, stdout, stderr).

        Raises:
            SSHConnectionError: Si el subprocess falla al iniciarse.
        """
        if sudo:
            logger.warning(
                "sudo=True ignorado en LocalConnectionAdapter — "
                "el proceso local ya corre con los permisos de ikctl (RNF-16)"
            )

        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(), timeout=timeout
            )
            rc = proc.returncode if proc.returncode is not None else -1
            return rc, stdout_bytes.decode(), stderr_bytes.decode()
        except Exception as exc:
            raise SSHConnectionError(
                f"Error ejecutando comando local: {exc}"
            ) from exc

    async def upload_file(self, local_path: str, remote_path: str) -> None:
        """Copia un archivo de local_path a remote_path en el sistema de archivos local.

        Args:
            local_path: Ruta origen del archivo.
            remote_path: Ruta destino del archivo.

        Raises:
            SSHConnectionError: Si la copia falla.
        """
        try:
            shutil.copy2(local_path, remote_path)
        except Exception as exc:
            raise SSHConnectionError(
                f"Error copiando archivo local {local_path} → {remote_path}: {exc}"
            ) from exc

    async def file_exists(self, remote_path: str) -> bool:
        """Comprueba si un path existe en el sistema de archivos local.

        Args:
            remote_path: Ruta a comprobar.

        Returns:
            True si existe, False si no.
        """
        return os.path.exists(remote_path)

    async def close(self) -> None:
        """No-op — no hay conexión que cerrar en el adaptador local."""
