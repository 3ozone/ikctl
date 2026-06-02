"""Tests para la Entity Pipeline — T-04."""
from datetime import datetime, timezone

import pytest

from app.v1.pipelines.domain.entities.pipeline import Pipeline
from app.v1.pipelines.domain.value_objects.pipeline_kit_config import PipelineKitConfig
from app.v1.pipelines.domain.value_objects.pipeline_target import PipelineTarget


_NOW = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


def _make_pipeline(**overrides) -> Pipeline:
    defaults = dict(
        id="pipe-001",
        user_id="user-001",
        name="Deploy Kubernetes",
        description="Setup k8s cluster",
        targets=[
            PipelineTarget(server_id="srv-001"),
            PipelineTarget(server_id="srv-002"),
        ],
        kits=[
            PipelineKitConfig(kit_id="kit-001", sudo=True),
            PipelineKitConfig(kit_id="kit-002", debug_level="errors"),
        ],
        values={"kit-001": {"version": "1.29"}},
        sudo=False,
        debug_level="none",
        created_at=_NOW,
        updated_at=_NOW,
    )
    defaults.update(overrides)
    return Pipeline(**defaults)


class TestPipelineCreation:
    """Pipeline se crea correctamente con todos los campos."""

    def test_create_pipeline(self):
        p = _make_pipeline()
        assert p.id == "pipe-001"
        assert p.user_id == "user-001"
        assert p.name == "Deploy Kubernetes"
        assert p.description == "Setup k8s cluster"
        assert len(p.targets) == 2
        assert len(p.kits) == 2
        assert p.values == {"kit-001": {"version": "1.29"}}
        assert p.sudo is False
        assert p.debug_level == "none"

    def test_create_pipeline_without_description(self):
        p = _make_pipeline(description=None)
        assert p.description is None

    def test_create_pipeline_with_empty_targets_and_kits(self):
        p = _make_pipeline(targets=[], kits=[])
        assert p.targets == []
        assert p.kits == []


class TestPipelineEquality:
    """Pipeline compara por id, no por valor de campos."""

    def test_equal_by_id(self):
        p1 = _make_pipeline(id="pipe-001", name="A")
        p2 = _make_pipeline(id="pipe-001", name="B")
        assert p1 == p2

    def test_unequal_by_id(self):
        p1 = _make_pipeline(id="pipe-001")
        p2 = _make_pipeline(id="pipe-002")
        assert p1 != p2


class TestPipelineUpdate:
    """Pipeline.update() muta los campos editables."""

    def test_update_name_and_description(self):
        p = _make_pipeline()
        p.update(name="New Name", description="New Desc")
        assert p.name == "New Name"
        assert p.description == "New Desc"

    def test_update_targets_and_kits(self):
        p = _make_pipeline()
        new_targets = [PipelineTarget(server_id="srv-099")]
        new_kits = [PipelineKitConfig(kit_id="kit-099")]
        p.update(targets=new_targets, kits=new_kits)
        assert len(p.targets) == 1
        assert p.targets[0].server_id == "srv-099"
        assert len(p.kits) == 1
        assert p.kits[0].kit_id == "kit-099"

    def test_update_values_and_sudo_and_debug_level(self):
        p = _make_pipeline()
        p.update(values={"kit-003": {"port": 443}}, sudo=True, debug_level="full")
        assert p.values == {"kit-003": {"port": 443}}
        assert p.sudo is True
        assert p.debug_level == "full"


class TestPipelineResolvedSudo:
    """resolved_sudo_for(kit_id) — RN-14: kit config prioridad sobre global."""

    def test_kit_with_explicit_sudo_true(self):
        p = _make_pipeline(sudo=False, kits=[PipelineKitConfig(kit_id="k1", sudo=True)])
        assert p.resolved_sudo_for("k1") is True

    def test_kit_with_explicit_sudo_false(self):
        p = _make_pipeline(sudo=True, kits=[PipelineKitConfig(kit_id="k1", sudo=False)])
        assert p.resolved_sudo_for("k1") is False

    def test_kit_inherits_global_sudo(self):
        p = _make_pipeline(sudo=True, kits=[PipelineKitConfig(kit_id="k1", sudo=None)])
        assert p.resolved_sudo_for("k1") is True

    def test_kit_not_found_returns_global(self):
        p = _make_pipeline(sudo=False, kits=[PipelineKitConfig(kit_id="k1")])
        assert p.resolved_sudo_for("k2") is False


class TestPipelineResolvedDebugLevel:
    """resolved_debug_level_for(kit_id) — RN-15: kit > global > none."""

    def test_kit_with_explicit_debug_level(self):
        p = _make_pipeline(debug_level="none", kits=[PipelineKitConfig(kit_id="k1", debug_level="full")])
        assert p.resolved_debug_level_for("k1") == "full"

    def test_kit_inherits_global_debug_level(self):
        p = _make_pipeline(debug_level="errors", kits=[PipelineKitConfig(kit_id="k1", debug_level=None)])
        assert p.resolved_debug_level_for("k1") == "errors"

    def test_kit_not_found_returns_global(self):
        p = _make_pipeline(debug_level="full", kits=[PipelineKitConfig(kit_id="k1")])
        assert p.resolved_debug_level_for("k2") == "full"

    def test_global_is_none_returns_none(self):
        p = _make_pipeline(debug_level="none", kits=[PipelineKitConfig(kit_id="k1", debug_level=None)])
        assert p.resolved_debug_level_for("k1") == "none"


class TestPipelineHasLocalServer:
    """has_local_server() — RN-17: servidor local no permitido en pipeline."""

    def test_no_local_servers(self):
        p = _make_pipeline(targets=[
            PipelineTarget(server_id="srv-001"),
            PipelineTarget(server_id="srv-002"),
        ])
        assert p.has_local_server(["local"]) is False

    def test_has_local_server(self):
        p = _make_pipeline(targets=[
            PipelineTarget(server_id="srv-001"),
            PipelineTarget(server_id="local"),
        ])
        assert p.has_local_server(["srv-001", "local"]) is True

    def test_empty_targets(self):
        p = _make_pipeline(targets=[])
        assert p.has_local_server(["local"]) is False