"""Async task RestoreBackupTask — restaura backup de una operación fallida.

Ejecuta `cp {path}.bak.ikctl {path}` para cada fichero en backup_files
usando BackupRestorer (SSHConnectionAdapter).
"""
from __future__ import annotations

from app.v1.operations.application.interfaces.backup_restorer import BackupRestorer
from app.v1.operations.application.interfaces.operation_repository import OperationRepository
from app.v1.operations.domain.exceptions.operation import OperationNotFoundError


class RestoreBackupTask:
    """Tarea asíncrona que restaura el backup de una operación fallida."""

    def __init__(
        self,
        operation_repository: OperationRepository,
        backup_restorer: BackupRestorer,
    ) -> None:
        self._operation_repo = operation_repository
        self._backup_restorer = backup_restorer

    async def execute(self, operation_id: str) -> None:
        """Restaura los ficheros de backup de la operación indicada.

        Args:
            operation_id: ID de la operación cuyo backup se restaurará.
        """
        operation = await self._operation_repo.find_by_id_no_ownership(operation_id)
        if operation is None:
            return

        if not operation.backup_files:
            return

        restored = await self._backup_restorer.restore(
            server_id=operation.server_id,
            backup_files=operation.backup_files,
        )

        operation.append_output(
            f"[restore] {len(restored)}/{len(operation.backup_files)} ficheros restaurados"
        )
        await self._operation_repo.update(operation)