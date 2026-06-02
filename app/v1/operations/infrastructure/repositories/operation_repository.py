"""SQLAlchemyOperationRepository — Implementación SQLAlchemy del repositorio de operaciones."""
import json
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.v1.operations.application.interfaces.operation_repository import OperationRepository
from app.v1.operations.domain.entities.operation import Operation
from app.v1.operations.domain.value_objects.operation_status import OperationStatus
from app.v1.operations.infrastructure.exceptions import DatabaseQueryError
from app.v1.operations.infrastructure.persistence.models import OperationModel


class SQLAlchemyOperationRepository(OperationRepository):
    """Implementación SQLAlchemy del repositorio de operaciones."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ------------------------------------------------------------------
    # Conversión entidad ↔ modelo
    # ------------------------------------------------------------------

    def _entity_to_model(self, op: Operation) -> OperationModel:
        return OperationModel(
            id=op.id,
            user_id=op.user_id,
            server_id=op.server_id,
            kit_id=op.kit_id,
            values=op.values,
            sudo=op.sudo,
            status=op.status.value,
            debug_level=op.debug_level,
            output=op.output,
            backup_files=list(op.backup_files),  # tuple → list para JSON
            started_at=op.started_at,
            finished_at=op.finished_at,
            created_at=op.created_at,
            updated_at=op.updated_at,
        )

    def _model_to_entity(self, model: OperationModel) -> Operation:
        raw = model.backup_files
        if isinstance(raw, str):
            raw = json.loads(raw)
        raw_values = model.values
        if isinstance(raw_values, str):
            raw_values = json.loads(raw_values)
        return Operation(
            id=model.id,
            user_id=model.user_id,
            server_id=model.server_id,
            kit_id=model.kit_id,
            values=raw_values if raw_values else {},
            sudo=model.sudo,
            status=OperationStatus(model.status),
            debug_level=model.debug_level,
            output=model.output or "",
            backup_files=tuple(raw) if raw else (),
            created_at=model.created_at,
            updated_at=model.updated_at,
            started_at=model.started_at,
            finished_at=model.finished_at,
        )

    # ------------------------------------------------------------------
    # Puerto — operaciones de escritura
    # ------------------------------------------------------------------

    async def save(self, operation: Operation) -> None:
        """Persiste una nueva operación.

        El commit/rollback se gestiona en el scoped session (UoW).
        """
        model = self._entity_to_model(operation)
        self._session.add(model)

    async def update(self, operation: Operation) -> None:
        """Actualiza los campos mutables de una operación existente.

        El commit/rollback se gestiona en el scoped session (UoW).
        """
        result = await self._session.execute(
            select(OperationModel).where(OperationModel.id == operation.id)
        )
        model = result.scalar_one_or_none()
        if model is None:
            return
        model.status = operation.status.value
        model.debug_level = operation.debug_level
        model.output = operation.output
        model.backup_files = list(operation.backup_files)
        model.started_at = operation.started_at
        model.finished_at = operation.finished_at
        model.updated_at = operation.updated_at

    # ------------------------------------------------------------------
    # Puerto — operaciones de lectura
    # ------------------------------------------------------------------

    async def find_by_id(self, operation_id: str, user_id: str) -> Optional[Operation]:
        """Busca una operación por id y user_id (ownership).

        Raises:
            DatabaseQueryError: Si ocurre un error de consulta.
        """
        try:
            result = await self._session.execute(
                select(OperationModel).where(
                    OperationModel.id == operation_id,
                    OperationModel.user_id == user_id,
                )
            )
            model = result.scalar_one_or_none()
            return self._model_to_entity(model) if model else None
        except Exception as exc:
            raise DatabaseQueryError(f"Error buscando operación: {exc}") from exc

    async def find_by_id_no_ownership(self, operation_id: str) -> Optional[Operation]:
        """Busca una operación por id sin validar ownership (uso interno de tasks).

        Raises:
            DatabaseQueryError: Si ocurre un error de consulta.
        """
        try:
            result = await self._session.execute(
                select(OperationModel).where(OperationModel.id == operation_id)
            )
            model = result.scalar_one_or_none()
            return self._model_to_entity(model) if model else None
        except Exception as exc:
            raise DatabaseQueryError(f"Error buscando operación interna: {exc}") from exc

    async def find_all_by_user(
        self,
        user_id: str,
        page: int,
        per_page: int,
        server_id: Optional[str] = None,
        kit_id: Optional[str] = None,
        status: Optional[str] = None,
    ) -> tuple[list[Operation], int]:
        """Lista las operaciones del usuario con paginación y filtros opcionales.

        Returns:
            Tupla (lista de operaciones, total de resultados).

        Raises:
            DatabaseQueryError: Si ocurre un error de consulta.
        """
        try:
            base_query = select(OperationModel).where(
                OperationModel.user_id == user_id,
            )
            if server_id:
                base_query = base_query.where(OperationModel.server_id == server_id)
            if kit_id:
                base_query = base_query.where(OperationModel.kit_id == kit_id)
            if status:
                base_query = base_query.where(OperationModel.status == status)

            # Total
            count_query = select(func.count()).select_from(base_query.subquery())
            total_result = await self._session.execute(count_query)
            total = total_result.scalar_one()

            # Paginación
            offset = (page - 1) * per_page
            paged_query = (
                base_query.order_by(OperationModel.created_at.desc())
                .offset(offset)
                .limit(per_page)
            )
            result = await self._session.execute(paged_query)
            ops = [self._model_to_entity(m) for m in result.scalars().all()]
            return ops, total

        except Exception as exc:
            raise DatabaseQueryError(f"Error listando operaciones: {exc}") from exc
