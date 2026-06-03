"""Command CreatePipeline — T-10.

Crea un nuevo pipeline (definición reutilizable de kits × servidores).
Valida RN-17: ningún target puede ser un servidor de tipo local.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from app.v1.pipelines.application.dtos.pipeline_dtos import PipelineResult
from app.v1.pipelines.application.exceptions import LocalServerInPipelineError
from app.v1.pipelines.application.interfaces.pipeline_repository import PipelineRepository
from app.v1.pipelines.application.interfaces.server_repository import ServerRepository
from app.v1.pipelines.domain.entities.pipeline import Pipeline
from app.v1.pipelines.domain.value_objects.pipeline_kit_config import PipelineKitConfig
from app.v1.pipelines.domain.value_objects.pipeline_target import PipelineTarget


class CreatePipeline:
    """Crea un pipeline y lo persiste.

    Raises:
        LocalServerInPipelineError: si algún target apunta a un servidor local (RN-17).
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
        name: str,
        description: Optional[str],
        targets: list[PipelineTarget],
        kits: list[PipelineKitConfig],
        values: Optional[dict] = None,
        sudo: bool = False,
        debug_level: str = "none",
    ) -> PipelineResult:
        await self._validate_no_local_servers(targets)

        pipeline = Pipeline(
            id=str(uuid.uuid4()),
            user_id=user_id,
            name=name,
            description=description,
            targets=targets,
            kits=kits,
            values=values or {},
            sudo=sudo,
            debug_level=debug_level,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

        await self._pipeline_repo.save(pipeline)

        return self._to_result(pipeline)

    async def _validate_no_local_servers(self, targets: list[PipelineTarget]) -> None:
        """RN-17: ningún target puede apuntar a un servidor de tipo local."""
        for target in targets:
            server = await self._server_repo.find_server_by_id_internal(target.server_id)
            if server is not None and server.type.value == "local":
                raise LocalServerInPipelineError(
                    f"El servidor '{target.server_id}' es de tipo local y no puede "
                    "formar parte de un pipeline."
                )

    @staticmethod
    def _to_result(pipeline: Pipeline) -> PipelineResult:
        return PipelineResult(
            pipeline_id=pipeline.id,
            user_id=pipeline.user_id,
            name=pipeline.name,
            description=pipeline.description,
            targets=tuple({"server_id": t.server_id} for t in pipeline.targets),
            kits=tuple(
                {
                    "kit_id": k.kit_id,
                    "sudo": k.sudo,
                    "debug_level": k.debug_level,
                    "values": dict(k.values),
                }
                for k in pipeline.kits
            ),
            values=pipeline.values,
            sudo=pipeline.sudo,
            debug_level=pipeline.debug_level,
            created_at=pipeline.created_at,
            updated_at=pipeline.updated_at,
        )
