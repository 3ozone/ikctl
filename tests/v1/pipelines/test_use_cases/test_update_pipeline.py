"""Tests para el command UpdatePipeline — T-11."""
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from app.v1.pipelines.application.exceptions import (
    LocalServerInPipelineError,
    PipelineInProgressError,
)
from app.v1.pipelines.domain.entities.pipeline import Pipeline
from app.v1.pipelines.domain.exceptions.pipeline import PipelineNotFoundError
from app.v1.pipelines.domain.value_objects.pipeline_kit_config import PipelineKitConfig
from app.v1.pipelines.domain.value_objects.pipeline_target import PipelineTarget
from app.v1.servers.domain.entities.server import Server
from app.v1.servers.domain.value_objects.server_status import ServerStatus
from app.v1.servers.domain.value_objects.server_type import ServerType

NOW = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


def make_server(server_type: str = "remote", server_id: str = "srv-1") -> Server:
    is_local = server_type == "local"
    return Server(
        id=server_id,
        user_id="user-1",
        name="My Server",
        type=ServerType(server_type),
        status=ServerStatus("active"),
        host=None if is_local else "192.168.1.1",
        port=None if is_local else 22,
        credential_id=None if is_local else "cred-1",
        description=None,
        os_id=None,
        os_version=None,
        os_name=None,
        created_at=NOW,
        updated_at=NOW,
    )


def make_pipeline(pipeline_id: str = "pipe-1", user_id: str = "user-1") -> Pipeline:
    return Pipeline(
        id=pipeline_id,
        user_id=user_id,
        name="Pipeline Original",
        description="Descripción original",
        targets=[PipelineTarget(server_id="srv-1")],
        kits=[PipelineKitConfig(kit_id="kit-1")],
        sudo=False,
        debug_level="none",
        values={},
        created_at=NOW,
        updated_at=NOW,
    )


def make_use_case(
    existing_pipeline: Pipeline | None = None,
    has_active_executions: bool = False,
    server_lookup: dict | None = None,
):
    from app.v1.pipelines.application.commands.update_pipeline import UpdatePipeline

    pipeline_repo = AsyncMock()
    server_repo = AsyncMock()

    pipeline_repo.find_by_id.return_value = existing_pipeline
    pipeline_repo.has_active_executions.return_value = has_active_executions

    lookup = server_lookup or {}

    async def _find_server(server_id: str):
        return lookup.get(server_id)

    server_repo.find_server_by_id_internal.side_effect = _find_server

    use_case = UpdatePipeline(
        pipeline_repository=pipeline_repo,
        server_repository=server_repo,
    )
    return use_case, pipeline_repo, server_repo


NEW_TARGETS = [PipelineTarget(server_id="srv-2")]
NEW_KITS = [PipelineKitConfig(kit_id="kit-2")]


class TestUpdatePipelineSuccess:
    """Casos de éxito al actualizar un pipeline."""

    @pytest.mark.asyncio
    async def test_update_returns_pipeline_result_with_updated_data(self):
        pipeline = make_pipeline()
        remote_server = make_server("remote", "srv-2")
        uc, _, _ = make_use_case(
            existing_pipeline=pipeline,
            server_lookup={"srv-2": remote_server},
        )

        result = await uc.execute(
            user_id="user-1",
            pipeline_id="pipe-1",
            name="Nuevo Nombre",
            description="Nueva descripción",
            targets=NEW_TARGETS,
            kits=NEW_KITS,
        )

        assert result.name == "Nuevo Nombre"
        assert result.description == "Nueva descripción"
        assert result.targets[0]["server_id"] == "srv-2"
        assert result.kits[0]["kit_id"] == "kit-2"

    @pytest.mark.asyncio
    async def test_update_calls_repository_update_once(self):
        pipeline = make_pipeline()
        uc, pipeline_repo, _ = make_use_case(existing_pipeline=pipeline)

        await uc.execute(
            user_id="user-1",
            pipeline_id="pipe-1",
            name="Nuevo Nombre",
        )

        pipeline_repo.update.assert_awaited_once()


class TestUpdatePipelineErrors:
    """Casos de error al actualizar un pipeline."""

    @pytest.mark.asyncio
    async def test_update_raises_when_pipeline_not_found(self):
        """RN-01: solo se puede actualizar el propio pipeline."""
        uc, _, _ = make_use_case(existing_pipeline=None)

        with pytest.raises(PipelineNotFoundError):
            await uc.execute(
                user_id="user-1",
                pipeline_id="pipe-x",
                name="Nombre",
            )

    @pytest.mark.asyncio
    async def test_update_raises_when_pipeline_has_active_executions(self):
        """RN-16: no se puede actualizar si hay ejecuciones activas."""
        pipeline = make_pipeline()
        uc, _, _ = make_use_case(
            existing_pipeline=pipeline,
            has_active_executions=True,
        )

        with pytest.raises(PipelineInProgressError):
            await uc.execute(
                user_id="user-1",
                pipeline_id="pipe-1",
                name="Nuevo Nombre",
            )

    @pytest.mark.asyncio
    async def test_update_raises_when_new_target_is_local_server(self):
        """RN-17: un servidor local no puede formar parte de un pipeline."""
        pipeline = make_pipeline()
        local_server = make_server("local", "srv-local")
        uc, _, _ = make_use_case(
            existing_pipeline=pipeline,
            server_lookup={"srv-local": local_server},
        )

        with pytest.raises(LocalServerInPipelineError):
            await uc.execute(
                user_id="user-1",
                pipeline_id="pipe-1",
                targets=[PipelineTarget(server_id="srv-local")],
            )
