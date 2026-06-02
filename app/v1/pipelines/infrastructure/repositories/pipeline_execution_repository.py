"""SQLAlchemyPipelineExecutionRepository — Implementación SQLAlchemy del repositorio de ejecuciones."""
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.v1.pipelines.application.interfaces.pipeline_execution_repository import (
    PipelineExecutionRepository,
)
from app.v1.pipelines.domain.entities.pipeline_execution import PipelineExecution
from app.v1.pipelines.domain.value_objects.pipeline_status import PipelineStatus
from app.v1.pipelines.infrastructure.exceptions import DatabaseQueryError
from app.v1.pipelines.infrastructure.persistence.models import PipelineExecutionModel


class SQLAlchemyPipelineExecutionRepository(PipelineExecutionRepository):
    """Implementación SQLAlchemy del repositorio de ejecuciones de pipeline."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ------------------------------------------------------------------
    # Conversión entidad ↔ modelo
    # ------------------------------------------------------------------

    def _entity_to_model(self, execution: PipelineExecution) -> PipelineExecutionModel:
        return PipelineExecutionModel(
            id=execution.id,
            pipeline_id=execution.pipeline_id,
            user_id=execution.user_id,
            status=execution.status.value,
            operation_ids=list(execution.operation_ids),
            snapshot=dict(execution.snapshot),
            started_at=execution.started_at,
            finished_at=execution.finished_at,
            created_at=execution.created_at,
        )

    def _model_to_entity(self, model: PipelineExecutionModel) -> PipelineExecution:
        operation_ids_raw = model.operation_ids or []
        if isinstance(operation_ids_raw, str):
            import json
            operation_ids_raw = json.loads(operation_ids_raw)

        snapshot_raw = model.snapshot or {}
        if isinstance(snapshot_raw, str):
            import json
            snapshot_raw = json.loads(snapshot_raw)

        return PipelineExecution(
            id=model.id,
            pipeline_id=model.pipeline_id,
            user_id=model.user_id,
            status=PipelineStatus(model.status),
            operation_ids=list(operation_ids_raw),
            snapshot=snapshot_raw,
            started_at=model.started_at,
            finished_at=model.finished_at,
            created_at=model.created_at,
        )

    # ------------------------------------------------------------------
    # Puerto — escritura
    # ------------------------------------------------------------------

    async def save(self, execution: PipelineExecution) -> None:
        """Persiste una nueva ejecución de pipeline."""
        try:
            model = self._entity_to_model(execution)
            self._session.add(model)
        except Exception as exc:
            raise DatabaseQueryError(f"Error guardando ejecución: {exc}") from exc

    async def update(self, execution: PipelineExecution) -> None:
        """Actualiza los campos mutables de una ejecución existente."""
        try:
            result = await self._session.execute(
                select(PipelineExecutionModel).where(
                    PipelineExecutionModel.id == execution.id
                )
            )
            model = result.scalar_one_or_none()
            if model is None:
                return
            model.status = execution.status.value
            model.operation_ids = list(execution.operation_ids)
            model.started_at = execution.started_at
            model.finished_at = execution.finished_at
        except Exception as exc:
            raise DatabaseQueryError(f"Error actualizando ejecución: {exc}") from exc

    # ------------------------------------------------------------------
    # Puerto — lectura
    # ------------------------------------------------------------------

    async def find_by_id(self, execution_id: str) -> Optional[PipelineExecution]:
        """Busca una ejecución por ID."""
        try:
            result = await self._session.execute(
                select(PipelineExecutionModel).where(
                    PipelineExecutionModel.id == execution_id
                )
            )
            model = result.scalar_one_or_none()
            return self._model_to_entity(model) if model else None
        except Exception as exc:
            raise DatabaseQueryError(f"Error buscando ejecución: {exc}") from exc

    async def find_by_pipeline_id(
        self, pipeline_id: str, page: int, per_page: int
    ) -> tuple[list[PipelineExecution], int]:
        """Lista ejecuciones de un pipeline con paginación (1-based).

        Returns:
            Tupla (lista de ejecuciones, total de resultados).
        """
        try:
            base_query = select(PipelineExecutionModel).where(
                PipelineExecutionModel.pipeline_id == pipeline_id
            )

            # Total
            count_query = select(func.count()).select_from(base_query.subquery())
            total_result = await self._session.execute(count_query)
            total = total_result.scalar_one()

            # Paginación
            offset = (page - 1) * per_page
            result = await self._session.execute(
                base_query.order_by(PipelineExecutionModel.created_at.desc())
                .offset(offset)
                .limit(per_page)
            )
            executions = [self._model_to_entity(m) for m in result.scalars().all()]
            return executions, total
        except Exception as exc:
            raise DatabaseQueryError(f"Error listando ejecuciones: {exc}") from exc

    async def find_latest_by_pipeline(
        self, pipeline_id: str
    ) -> Optional[PipelineExecution]:
        """Devuelve la ejecución más reciente de un pipeline."""
        try:
            result = await self._session.execute(
                select(PipelineExecutionModel)
                .where(PipelineExecutionModel.pipeline_id == pipeline_id)
                .order_by(PipelineExecutionModel.created_at.desc())
                .limit(1)
            )
            model = result.scalar_one_or_none()
            return self._model_to_entity(model) if model else None
        except Exception as exc:
            raise DatabaseQueryError(f"Error buscando última ejecución: {exc}") from exc
