"""Port BackupRestorer — restaura ficheros .bak.ikctl en el servidor remoto."""
from __future__ import annotations

from abc import ABC, abstractmethod


class BackupRestorer(ABC):
    """Restaura los ficheros de backup de una operación fallida.

    Para cada path en backup_files, ejecuta:
        cp {path}.bak.ikctl {path}

    Los ficheros .bak.ikctl fueron creados por SSHKitExecutor en el paso 1
    (snapshot in-place) y se conservan en el servidor tras la ejecución.
    """

    @abstractmethod
    async def restore(
        self,
        server_id: str,
        backup_files: tuple[str, ...],
    ) -> tuple[str, ...]:
        """Restaura los ficheros de backup en el servidor remoto.

        Args:
            server_id: ID del servidor donde restaurar.
            backup_files: Rutas originales de los ficheros a restaurar.

        Returns:
            Tupla de rutas restauradas correctamente.
        """