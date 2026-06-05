"""SQLAlchemyPipelineRepository — Implementación SQLAlchemy del repositorio de pipelines."""
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.v1.pipelines.application.interfaces.pipeline_repository import PipelineRepository
from app.v1.pipelines.domain.entities.pipeline import Pipeline
from app.v1.pipelines.domain.value_objects.pipeline_kit_config import PipelineKitConfig
from app.v1.pipelines.domain.value_objects.pipeline_target import PipelineTarget
from app.v1.pipelines.infrastructure.exceptions import DatabaseQueryError
from app.v1.pipelines.infrastructure.persistence.models import (
    PipelineExecutionModel,
    PipelineModel,
)

_ACTIVE_STATUSES = ("pending", "in_progress")


class SQLAlchemyPipelineRepository(PipelineRepository):
    """Implementación SQLAlchemy del repositorio de pipelines."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ------------------------------------------------------------------
    # Conversión entidad ↔ modelo
    # ------------------------------------------------------------------

    def _entity_to_model(self, pipeline: Pipeline) -> PipelineModel:
        return PipelineModel(
            id=pipeline.id,
            user_id=pipeline.user_id,
            name=pipeline.name,
            description=pipeline.description,
            targets=[
                {
                    "server_id": t.server_id,
                    "kit_ids": list(t.kit_ids) if t.kit_ids is not None else None,
                    "values": dict(t.values),
                }
                for t in pipeline.targets
            ],
            kits=[
                {
                    "kit_id": k.kit_id,
                    "sudo": k.sudo,
                    "debug_level": k.debug_level,
                    "values": dict(k.values),
                }
                for k in pipeline.kits
            ],
            values=dict(pipeline.values),
            sudo=pipeline.sudo,
            debug_level=pipeline.debug_level,
            created_at=pipeline.created_at,
            updated_at=pipeline.updated_at,
        )

    def _model_to_entity(self, model: PipelineModel) -> Pipeline:
        targets_raw = model.targets or []
        if isinstance(targets_raw, str):
            import json
            targets_raw = json.loads(targets_raw)

        kits_raw = model.kits or []
        if isinstance(kits_raw, str):
            import json
            kits_raw = json.loads(kits_raw)

        values_raw = model.values or {}
        if isinstance(values_raw, str):
            import json
            values_raw = json.loads(values_raw)

        return Pipeline(
            id=model.id,
            user_id=model.user_id,
            name=model.name,
            description=model.description,
            targets=[
                PipelineTarget(
                    server_id=t["server_id"],
                    kit_ids=tuple(t["kit_ids"]) if t.get("kit_ids") is not None else None,
                    values=t.get("values", {}),
                )
                for t in targets_raw
            ],
            kits=[
                PipelineKitConfig(
                    kit_id=k["kit_id"],
                    sudo=k.get("sudo"),
                    debug_level=k.get("debug_level"),
                    values=k.get("values", {}),
                )
                for k in kits_raw
            ],
            values=values_raw,
            sudo=bool(model.sudo),
            debug_level=model.debug_level,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    # ------------------------------------------------------------------
    # Puerto — escritura
    # ------------------------------------------------------------------

    async def save(self, pipeline: Pipeline) -> None:
        """Persiste un nuevo pipeline."""
        try:
            model = self._entity_to_model(pipeline)
            self._session.add(model)
        except Exception as exc:
            raise DatabaseQueryError(f"Error guardando pipeline: {exc}") from exc

    async def update(self, pipeline: Pipeline) -> None:
        """Actualiza los campos mutables de un pipeline existente."""
        try:
            result = await self._session.execute(
                select(PipelineModel).where(PipelineModel.id == pipeline.id)
            )
            model = result.scalar_one_or_none()
            if model is None:
                return
            model.name = pipeline.name
            model.description = pipeline.description
            model.targets = [
                {
                    "server_id": t.server_id,
                    "kit_ids": list(t.kit_ids) if t.kit_ids is not None else None,
                    "values": dict(t.values),
                }
                for t in pipeline.targets
            ]
            model.kits = [
                {
                    "kit_id": k.kit_id,
                    "sudo": k.sudo,
                    "debug_level": k.debug_level,
                    "values": dict(k.values),
                }
                for k in pipeline.kits
            ]
            model.values = dict(pipeline.values)
            model.sudo = pipeline.sudo
            model.debug_level = pipeline.debug_level
            model.updated_at = pipeline.updated_at
        except Exception as exc:
            raise DatabaseQueryError(f"Error actualizando pipeline: {exc}") from exc

    async def delete(self, pipeline_id: str) -> None:
        """Elimina un pipeline por ID."""
        try:
            result = await self._session.execute(
                select(PipelineModel).where(PipelineModel.id == pipeline_id)
            )
            model = result.scalar_one_or_none()
            if model is not None:
                await self._session.delete(model)
        except Exception as exc:
            raise DatabaseQueryError(f"Error eliminando pipeline: {exc}") from exc

    # ------------------------------------------------------------------
    # Puerto — lectura
    # ------------------------------------------------------------------

    async def find_by_id(self, pipeline_id: str, user_id: str) -> Optional[Pipeline]:
        """Busca un pipeline por ID scoped al usuario propietario."""
        try:
            result = await self._session.execute(
                select(PipelineModel).where(
                    PipelineModel.id == pipeline_id,
                    PipelineModel.user_id == user_id,
                )
            )
            model = result.scalar_one_or_none()
            return self._model_to_entity(model) if model else None
        except Exception as exc:
            raise DatabaseQueryError(f"Error buscando pipeline: {exc}") from exc

    async def find_by_id_no_ownership(self, pipeline_id: str) -> Optional[Pipeline]:
        """Busca un pipeline por ID sin validar ownership (uso interno de tasks)."""
        try:
            result = await self._session.execute(
                select(PipelineModel).where(PipelineModel.id == pipeline_id)
            )
            model = result.scalar_one_or_none()
            return self._model_to_entity(model) if model else None
        except Exception as exc:
            raise DatabaseQueryError(f"Error buscando pipeline interno: {exc}") from exc

    async def find_all_by_user(
        self, user_id: str, page: int, per_page: int
    ) -> tuple[list[Pipeline], int]:
        """Lista pipelines del usuario con paginación (1-based).

        Returns:
            Tupla (lista de pipelines, total de resultados).
        """
        try:
            base_query = select(PipelineModel).where(
                PipelineModel.user_id == user_id
            )

            # Total
            count_query = select(func.count()).select_from(base_query.subquery())
            total_result = await self._session.execute(count_query)
            total = total_result.scalar_one()

            # Paginación
            offset = (page - 1) * per_page
            result = await self._session.execute(
                base_query.order_by(PipelineModel.created_at.desc())
                .offset(offset)
                .limit(per_page)
            )
            pipelines = [self._model_to_entity(m) for m in result.scalars().all()]
            return pipelines, total
        except Exception as exc:
            raise DatabaseQueryError(f"Error listando pipelines: {exc}") from exc

    async def has_active_executions(self, pipeline_id: str) -> bool:
        """Comprueba si el pipeline tiene ejecuciones activas (pending o in_progress)."""
        try:
            result = await self._session.execute(
                select(PipelineExecutionModel.id).where(
                    PipelineExecutionModel.pipeline_id == pipeline_id,
                    PipelineExecutionModel.status.in_(_ACTIVE_STATUSES),
                )
            )
            return result.first() is not None
        except Exception as exc:
            raise DatabaseQueryError(f"Error comprobando ejecuciones activas: {exc}") from exc
