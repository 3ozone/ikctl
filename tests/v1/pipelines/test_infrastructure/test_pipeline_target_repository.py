"""Tests de serialización/deserialización de PipelineTarget con kit_ids y values."""
from datetime import datetime, timezone

import pytest

from app.v1.pipelines.domain.entities.pipeline import Pipeline
from app.v1.pipelines.domain.value_objects.pipeline_kit_config import PipelineKitConfig
from app.v1.pipelines.domain.value_objects.pipeline_target import PipelineTarget

NOW = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


def make_pipeline(
    pipeline_id: str = "pipe-1",
    targets: list[PipelineTarget] | None = None,
) -> Pipeline:
    return Pipeline(
        id=pipeline_id,
        user_id="user-1",
        name="Mi Pipeline",
        description=None,
        targets=targets or [PipelineTarget(server_id="srv-1")],
        kits=[PipelineKitConfig(kit_id="kit-1")],
        values={},
        sudo=False,
        debug_level="none",
        created_at=NOW,
        updated_at=NOW,
    )


class TestRepositoryTargetKitIdsAndValues:
    """R11: serialización/deserialización de kit_ids y values."""

    async def test_roundtrip_target_kit_ids_and_values(self, pipeline_repository):
        """save y find_by_id preservan kit_ids y values por target."""
        pipeline = make_pipeline(
            targets=[
                PipelineTarget(
                    server_id="srv-1",
                    kit_ids=("kit-1", "kit-2"),
                    values={"env": "staging"},
                ),
                PipelineTarget(
                    server_id="srv-2",
                    kit_ids=None,
                    values={"env": "prod"},
                ),
                PipelineTarget(
                    server_id="srv-3",
                    kit_ids=(),
                    values={},
                ),
            ],
        )
        await pipeline_repository.save(pipeline)

        found = await pipeline_repository.find_by_id("pipe-1", "user-1")

        assert found is not None
        assert len(found.targets) == 3
        # Target 1: kit_ids y values
        assert found.targets[0].server_id == "srv-1"
        assert found.targets[0].kit_ids == ("kit-1", "kit-2")
        assert found.targets[0].values == {"env": "staging"}
        # Target 2: kit_ids None
        assert found.targets[1].server_id == "srv-2"
        assert found.targets[1].kit_ids is None
        assert found.targets[1].values == {"env": "prod"}
        # Target 3: kit_ids vacío
        assert found.targets[2].server_id == "srv-3"
        assert found.targets[2].kit_ids == ()
        assert found.targets[2].values == {}

    async def test_update_preserves_target_kit_ids_and_values(self, pipeline_repository):
        """update serializa kit_ids y values correctamente."""
        pipeline = make_pipeline(
            targets=[PipelineTarget(server_id="srv-1", kit_ids=("kit-1",), values={"x": "y"})],
        )
        await pipeline_repository.save(pipeline)

        pipeline.update(
            targets=[PipelineTarget(server_id="srv-2", kit_ids=("kit-2",), values={"a": "b"})],
        )
        await pipeline_repository.update(pipeline)

        found = await pipeline_repository.find_by_id("pipe-1", "user-1")
        assert found is not None
        assert len(found.targets) == 1
        assert found.targets[0].server_id == "srv-2"
        assert found.targets[0].kit_ids == ("kit-2",)
        assert found.targets[0].values == {"a": "b"}

    async def test_backward_compatible_legacy_targets(self, pipeline_repository):
        """R10: targets sin kit_ids ni values se deserializan correctamente."""
        from app.v1.pipelines.infrastructure.persistence.models import PipelineModel

        # Insertar directamente un modelo con targets legacy (sin kit_ids ni values)
        model = PipelineModel(
            id="pipe-legacy",
            user_id="user-1",
            name="Legacy Pipeline",
            description=None,
            targets='[{"server_id": "srv-1"}, {"server_id": "srv-2"}]',
            kits='[{"kit_id": "kit-1"}]',
            values="{}",
            sudo=False,
            debug_level="none",
            created_at=NOW,
            updated_at=NOW,
        )
        pipeline_repository._session.add(model)
        await pipeline_repository._session.flush()

        found = await pipeline_repository.find_by_id("pipe-legacy", "user-1")

        assert found is not None
        assert len(found.targets) == 2
        assert found.targets[0].server_id == "srv-1"
        assert found.targets[0].kit_ids is None
        assert found.targets[0].values == {}
        assert found.targets[1].server_id == "srv-2"
        assert found.targets[1].kit_ids is None
        assert found.targets[1].values == {}
