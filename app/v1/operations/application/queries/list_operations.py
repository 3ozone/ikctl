"""Query ListOperations — T-15."""
from __future__ import annotations

from typing import Optional

from app.v1.operations.application.dtos.operation_dtos import OperationListResult, OperationResult
from app.v1.operations.application.interfaces.operation_repository import OperationRepository
from app.v1.operations.application.queries.get_operation import _filter_output


class ListOperations:
    """Lista las operaciones de un usuario con paginación y filtros opcionales."""

    def __init__(self, operation_repository: OperationRepository) -> None:
        self._operation_repo = operation_repository

    async def execute(
        self,
        user_id: str,
        page: int,
        per_page: int,
        server_id: Optional[str] = None,
        kit_id: Optional[str] = None,
        status: Optional[str] = None,
    ) -> OperationListResult:
        """Lista las operaciones del usuario.

        Args:
            user_id: ID del usuario propietario.
            page: Número de página (1-indexed).
            per_page: Resultados por página.
            server_id: Filtro opcional por servidor.
            kit_id: Filtro opcional por kit.
            status: Filtro opcional por estado.

        Returns:
            OperationListResult con items paginados y total.
        """
        operations, total = await self._operation_repo.find_all_by_user(
            user_id, page, per_page,
            server_id=server_id,
            kit_id=kit_id,
            status=status,
        )

        items = tuple(
            OperationResult(
                operation_id=op.id,
                user_id=op.user_id,
                server_id=op.server_id,
                kit_id=op.kit_id,
                values=op.values,
                sudo=op.sudo,
                status=op.status.value,
                debug_level=op.debug_level,
                output=_filter_output(op.output, op.debug_level),
                backup_files=op.backup_files,
                created_at=op.created_at,
                updated_at=op.updated_at,
                started_at=op.started_at,
                finished_at=op.finished_at,
            )
            for op in operations
        )

        return OperationListResult(
            items=items,
            total=total,
            page=page,
            per_page=per_page,
        )
