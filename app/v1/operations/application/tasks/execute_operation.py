"""Async task ExecuteOperation — T-16.

Orquesta los 6 pasos de ejecución de un kit sobre un servidor:
  1. Snapshot de ficheros de backup
  2. Git clone del kit
  3. Render Jinja2
  4. Transferencia SFTP con caché SHA-256
  5. Ejecución del pipeline
  6. Limpieza del servidor

Estos 6 pasos están abstraídos detrás del port RemoteKitExecutor.
"""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from app.v1.operations.application.interfaces.credential_repository import CredentialRepository
from app.v1.operations.application.interfaces.kit_repository import KitRepository
from app.v1.operations.application.interfaces.operation_repository import OperationRepository
from app.v1.operations.application.interfaces.remote_kit_executor import RemoteKitExecutor
from app.v1.operations.application.interfaces.server_repository import ServerRepository
from app.v1.operations.domain.events.operation_completed import OperationCompleted
from app.v1.operations.domain.events.operation_failed import OperationFailed
from app.v1.shared.application.interfaces.event_bus import EventBus


class ExecuteOperation:
    """Tarea asíncrona que ejecuta un kit en un servidor.

    Se inyecta en composition root como reemplazo del placeholder en LaunchOperation
    y RetryOperation.
    """

    def __init__(
        self,
        operation_repository: OperationRepository,
        server_repository: ServerRepository,
        kit_repository: KitRepository,
        credential_repository: CredentialRepository,
        remote_kit_executor: RemoteKitExecutor,
        event_bus: EventBus,
    ) -> None:
        self._operation_repo = operation_repository
        self._server_repo = server_repository
        self._kit_repo = kit_repository
        self._credential_repo = credential_repository
        self._remote_executor = remote_kit_executor
        self._event_bus = event_bus

    async def execute(self, operation_id: str) -> None:
        """Ejecuta la operación indicada.

        Si la operación no existe, sale silenciosamente.
        Si falla en cualquier paso, marca la operación como failed y publica el evento.

        Args:
            operation_id: ID de la operación a ejecutar.
        """
        operation = await self._operation_repo.find_by_id_no_ownership(operation_id)
        if operation is None:
            return

        started_at = datetime.now(timezone.utc)
        operation.start(started_at)
        await self._operation_repo.update(operation)

        correlation_id = str(uuid4())

        # Resolver dependencias externas
        server = await self._server_repo.find_by_id_internal(operation.server_id)
        if server is None:
            await self._fail(operation, f"Servidor '{operation.server_id}' no encontrado.", correlation_id)
            return

        kit = await self._kit_repo.find_by_id_internal(operation.kit_id)
        if kit is None:
            await self._fail(operation, f"Kit '{operation.kit_id}' no encontrado.", correlation_id)
            return

        credential = await self._credential_repo.find_by_id_internal(server.credential_id)
        if credential is None:
            await self._fail(operation, f"Credencial '{server.credential_id}' no encontrada.", correlation_id)
            return

        # Ejecutar los 6 pasos via RemoteKitExecutor
        try:
            output, backup_files = await self._remote_executor.execute(
                server=server,
                kit=kit,
                credential=credential,
                debug_level=operation.debug_level,
                values=operation.values,
                sudo=operation.sudo,
            )
            operation.append_output(output)
            operation.set_backup_files(backup_files)

            finished_at = datetime.now(timezone.utc)
            operation.complete(finished_at)
            await self._operation_repo.update(operation)

            duration_ms = int((finished_at - started_at).total_seconds() * 1000)
            await self._event_bus.publish(
                OperationCompleted(
                    operation_id=operation.id,
                    user_id=operation.user_id,
                    duration_ms=duration_ms,
                    correlation_id=correlation_id,
                )
            )

        except Exception as exc:
            await self._fail(operation, str(exc), correlation_id, started_at=started_at)

    async def _fail(
        self,
        operation,
        error_message: str,
        correlation_id: str,
        started_at: datetime | None = None,
    ) -> None:
        """Marca la operación como fallida, persiste y publica el evento."""
        operation.append_output(error_message)

        finished_at = datetime.now(timezone.utc)
        operation.fail(finished_at)
        await self._operation_repo.update(operation)

        duration_ms = 0
        if started_at is not None:
            duration_ms = int((finished_at - started_at).total_seconds() * 1000)

        await self._event_bus.publish(
            OperationFailed(
                operation_id=operation.id,
                user_id=operation.user_id,
                error=error_message,
                duration_ms=duration_ms,
                correlation_id=correlation_id,
            )
        )
