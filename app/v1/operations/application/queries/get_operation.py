"""Query GetOperation — T-14."""
from __future__ import annotations

from app.v1.operations.application.dtos.operation_dtos import OperationResult
from app.v1.operations.application.interfaces.operation_repository import OperationRepository
from app.v1.operations.domain.exceptions.operation import OperationNotFoundError


def _filter_output(output: str, debug_level: str) -> str:
    """Filtra el output de una operación según su debug_level (RF-15).

    - "none": no se devuelve ningún output.
    - "errors": solo líneas que empiezan con [stderr].
    - "full": se devuelve todo el output (stdout + stderr).
    """
    if not output:
        return ""
    if debug_level == "none":
        return ""
    if debug_level == "errors":
        lines = output.split("\n")
        stderr_lines = [line for line in lines if line.startswith("[stderr]")]
        return "\n".join(stderr_lines)
    return output


class GetOperation:
    """Devuelve los detalles de una operación por ID con validación de ownership.

    Filtra el output según debug_level (RF-15):
    - "none": output vacío.
    - "errors": solo líneas [stderr].
    - "full": output completo.

    Raises:
        OperationNotFoundError: Si la operación no existe o no pertenece al usuario.
    """

    def __init__(self, operation_repository: OperationRepository) -> None:
        self._operation_repo = operation_repository

    async def execute(self, operation_id: str, user_id: str) -> OperationResult:
        """Obtiene la operación indicada.

        Args:
            operation_id: ID de la operación a consultar.
            user_id: ID del usuario propietario.

        Returns:
            OperationResult con los datos de la operación (output filtrado).

        Raises:
            OperationNotFoundError: Si la operación no existe o no pertenece al usuario.
        """
        operation = await self._operation_repo.find_by_id(operation_id, user_id)
        if operation is None:
            raise OperationNotFoundError(
                f"Operación '{operation_id}' no encontrada."
            )

        filtered_output = _filter_output(operation.output, operation.debug_level)

        return OperationResult(
            operation_id=operation.id,
            user_id=operation.user_id,
            server_id=operation.server_id,
            kit_id=operation.kit_id,
            values=operation.values,
            sudo=operation.sudo,
            status=operation.status.value,
            debug_level=operation.debug_level,
            output=filtered_output,
            backup_files=operation.backup_files,
            created_at=operation.created_at,
            updated_at=operation.updated_at,
            started_at=operation.started_at,
            finished_at=operation.finished_at,
        )
