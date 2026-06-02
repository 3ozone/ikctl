"""Command UpdatePipeline — T-11.

Actualiza un pipeline existente del usuario.
Valida:
- RN-01: ownership — solo el propietario puede actualizar.
- RN-16: sin ejecuciones activas en curso.
- RN-17: ningún nuevo target puede ser un servidor local.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from app.v1.pipelines.application.commands.create_pipeline import CreatePipeline
from app.v1.pipelines.application.dtos.pipeline_dtos import PipelineResult
from app.v1.pipelines.application.exceptions import (
    LocalServerInPipelineError,
    PipelineInProgressError,
)
from app.v1.pipelines.application.interfaces.pipeline_repository import PipelineRepository
from app.v1.pipelines.application.interfaces.server_repository import ServerRepository
from app.v1.pipelines.domain.exceptions.pipeline import PipelineNotFoundError
from app.v1.pipelines.domain.value_objects.pipeline_kit_config import PipelineKitConfig
from app.v1.pipelines.domain.value_objects.pipeline_target import PipelineTarget


class UpdatePipeline:
    """Actualiza un pipeline existente y persiste los cambios.

    Raises:
        PipelineNotFoundError: si el pipeline no existe o no pertenece al usuario (RN-01).
        PipelineInProgressError: si hay ejecuciones activas (RN-16).
        LocalServerInPipelineError: si algún nuevo target apunta a un servidor local (RN-17).
    """

    def __init__(
        self,
        pipeline_repository: PipelineRepository,
        server_repository: ServerRepository,
    ) -> None:
        self._pipeline_repo = pipeline_repository
        self._server_repo = server_repository

    async def execute(
        self,
        user_id: str,
        pipeline_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        targets: Optional[list[PipelineTarget]] = None,
        kits: Optional[list[PipelineKitConfig]] = None,
        values: Optional[dict] = None,
        sudo: Optional[bool] = None,
        debug_level: Optional[str] = None,
    ) -> PipelineResult:
        # RN-01: ownership
        pipeline = await self._pipeline_repo.find_by_id(pipeline_id, user_id)
        if pipeline is None:
            raise PipelineNotFoundError(
                f"Pipeline '{pipeline_id}' no encontrado o no pertenece al usuario."
            )

        # RN-16: sin ejecuciones activas
        if await self._pipeline_repo.has_active_executions(pipeline_id):
            raise PipelineInProgressError(
                f"El pipeline '{pipeline_id}' tiene ejecuciones activas y no puede modificarse."
            )

        # RN-17: ningún nuevo target puede ser local
        if targets is not None:
            await self._validate_no_local_servers(targets)

        pipeline.update(
            name=name,
            description=description,
            targets=targets,
            kits=kits,
            values=values,
            sudo=sudo,
            debug_level=debug_level,
        )
        pipeline.updated_at = datetime.now(timezone.utc)

        await self._pipeline_repo.update(pipeline)

        return CreatePipeline._to_result(pipeline)

    async def _validate_no_local_servers(self, targets: list[PipelineTarget]) -> None:
        """RN-17: ningún target puede apuntar a un servidor de tipo local."""
        for target in targets:
            server = await self._server_repo.find_server_by_id_internal(target.server_id)
            if server is not None and server.type.value == "local":
                raise LocalServerInPipelineError(
                    f"El servidor '{target.server_id}' es de tipo local y no puede "
                    "formar parte de un pipeline."
                )
