"""Command LaunchBatchOperation — T-10.3.

Lanza una operación sobre cada servidor de un grupo, creando una operación
individual por servidor y encolando su ejecución.
"""
from __future__ import annotations

from typing import Optional

from app.v1.operations.application.commands.launch_operation import LaunchOperation
from app.v1.operations.application.dtos.operation_dtos import (
    BatchOperationResult,
    OperationResult,
)
from app.v1.operations.application.exceptions import GroupNotFoundError
from app.v1.operations.application.interfaces.kit_repository import KitRepository
from app.v1.operations.application.interfaces.operation_repository import (
    OperationRepository,
)
from app.v1.operations.application.interfaces.server_repository import ServerRepository
from app.v1.operations.application.interfaces.task_queue import TaskQueue
from app.v1.shared.application.interfaces.event_bus import EventBus


class LaunchBatchOperation:
    """Lanza una operación sobre todos los servidores de un grupo.

    Para cada servidor del grupo invoca la lógica de LaunchOperation
    (validación de servidor activo, kit usable, creación de entidad,
    persistencia, evento y encolado). Devuelve el conjunto de operaciones
    creadas como BatchOperationResult.

    Raises:
        GroupNotFoundError: Si el grupo no existe.
        KitNotUsableError: Si el kit no está sincronizado o fue eliminado.
        ServerNotActiveError: Si algún servidor del grupo está inactivo.
    """

    def __init__(
        self,
        operation_repository: OperationRepository,
        server_repository: ServerRepository,
        kit_repository: KitRepository,
        task_queue: TaskQueue,
        event_bus: EventBus,
        execute_fn=None,
    ) -> None:
        self._launch_operation = LaunchOperation(
            operation_repository=operation_repository,
            server_repository=server_repository,
            kit_repository=kit_repository,
            task_queue=task_queue,
            event_bus=event_bus,
            execute_fn=execute_fn,
        )
        self._server_repo = server_repository

    async def execute(
        self,
        user_id: str,
        group_id: str,
        kit_id: str,
        debug_level: Optional[str],
        values: Optional[dict] = None,
        sudo: bool = False,
    ) -> BatchOperationResult:
        """Lanza una operación por cada servidor del grupo.

        Args:
            user_id: ID del usuario que lanza las operaciones.
            group_id: ID del grupo de servidores destino.
            kit_id: ID del kit a ejecutar en cada servidor.
            debug_level: Nivel de debug explícito. Si None hereda del kit.
            values: Valores de configuración (sobreescriben defaults del kit).
            sudo: Si True, ejecuta los scripts del pipeline con sudo.

        Returns:
            BatchOperationResult con la lista de OperationResult creados.

        Raises:
            GroupNotFoundError: Si el grupo no existe.
            KitNotUsableError: Si el kit no está sincronizado o fue eliminado.
            ServerNotActiveError: Si algún servidor del grupo está inactivo.
        """
        group = await self._server_repo.find_group_by_id_internal(group_id)
        if group is None:
            raise GroupNotFoundError(f"Grupo '{group_id}' no encontrado.")

        if not group.server_ids:
            return BatchOperationResult(operations=[])

        servers = await self._server_repo.find_servers_by_ids(group.server_ids)

        results: list[OperationResult] = []
        for server in servers:
            result = await self._launch_operation.execute(
                user_id=user_id,
                server_id=server.id,
                kit_id=kit_id,
                debug_level=debug_level,
                values=values,
                sudo=sudo,
            )
            results.append(result)

        return BatchOperationResult(operations=results)
