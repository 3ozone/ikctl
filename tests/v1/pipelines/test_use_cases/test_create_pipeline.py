"""Tests para el command CreatePipeline — T-10."""
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from app.v1.pipelines.application.exceptions import LocalServerInPipelineError
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


def make_use_case(server_lookup: dict | None = None):
    """Construye el use case con mocks.

    server_lookup: dict {server_id: Server | None} para simular find_server_by_id_internal.
    """
    from app.v1.pipelines.application.commands.create_pipeline import CreatePipeline

    pipeline_repo = AsyncMock()
    server_repo = AsyncMock()

    lookup = server_lookup or {}

    async def _find_server(server_id: str):
        return lookup.get(server_id)

    server_repo.find_server_by_id_internal.side_effect = _find_server

    use_case = CreatePipeline(
        pipeline_repository=pipeline_repo,
        server_repository=server_repo,
    )
    return use_case, pipeline_repo, server_repo


DEFAULT_TARGETS = [PipelineTarget(server_id="srv-1")]
DEFAULT_KITS = [PipelineKitConfig(kit_id="kit-1")]


class TestCreatePipelineSuccess:
    """Casos de éxito al crear un pipeline."""

    @pytest.mark.asyncio
    async def test_create_returns_pipeline_result_with_correct_data(self):
        server = make_server("remote", "srv-1")
        uc, _, _ = make_use_case(server_lookup={"srv-1": server})

        result = await uc.execute(
            user_id="user-1",
            name="Mi Pipeline",
            description="Descripción",
            targets=DEFAULT_TARGETS,
            kits=DEFAULT_KITS,
        )

        assert result.user_id == "user-1"
        assert result.name == "Mi Pipeline"
        assert result.description == "Descripción"
        assert len(result.targets) == 1
        assert result.targets[0]["server_id"] == "srv-1"
        assert len(result.kits) == 1
        assert result.kits[0]["kit_id"] == "kit-1"

    @pytest.mark.asyncio
    async def test_create_generates_non_empty_pipeline_id(self):
        server = make_server("remote", "srv-1")
        uc, _, _ = make_use_case(server_lookup={"srv-1": server})

        result = await uc.execute(
            user_id="user-1",
            name="Mi Pipeline",
            description=None,
            targets=DEFAULT_TARGETS,
            kits=DEFAULT_KITS,
        )

        assert isinstance(result.pipeline_id, str)
        assert len(result.pipeline_id) > 0

    @pytest.mark.asyncio
    async def test_create_calls_repository_save_once(self):
        server = make_server("remote", "srv-1")
        uc, pipeline_repo, _ = make_use_case(server_lookup={"srv-1": server})

        await uc.execute(
            user_id="user-1",
            name="Mi Pipeline",
            description=None,
            targets=DEFAULT_TARGETS,
            kits=DEFAULT_KITS,
        )

        pipeline_repo.save.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_create_server_not_found_does_not_raise(self):
        """Si un server_id no existe aún en la BD, la creación del pipeline no falla.

        La validación de existencia real se hace en LaunchPipeline (T-13).
        """
        uc, _, _ = make_use_case(server_lookup={})  # server_id no encontrado → None

        result = await uc.execute(
            user_id="user-1",
            name="Mi Pipeline",
            description=None,
            targets=DEFAULT_TARGETS,
            kits=DEFAULT_KITS,
        )

        assert result.name == "Mi Pipeline"


class TestCreatePipelineErrors:
    """Casos de error al crear un pipeline."""

    @pytest.mark.asyncio
    async def test_create_raises_when_target_is_local_server(self):
        """RN-17: un servidor local no puede formar parte de un pipeline."""
        local_server = make_server("local", "srv-local")
        uc, _, _ = make_use_case(server_lookup={"srv-local": local_server})

        targets_with_local = [PipelineTarget(server_id="srv-local")]

        with pytest.raises(LocalServerInPipelineError):
            await uc.execute(
                user_id="user-1",
                name="Mi Pipeline",
                description=None,
                targets=targets_with_local,
                kits=DEFAULT_KITS,
            )
