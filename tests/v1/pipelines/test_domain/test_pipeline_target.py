"""Tests para el Value Object PipelineTarget — T-01."""
import pytest

from app.v1.pipelines.domain.value_objects.pipeline_target import PipelineTarget
from app.v1.pipelines.domain.exceptions.pipeline_target import InvalidPipelineTargetError


class TestPipelineTargetCreation:
    """PipelineTarget se crea correctamente con server_id válido."""

    def test_valid_server_id(self):
        target = PipelineTarget(server_id="server-001")
        assert target.server_id == "server-001"

    def test_uuid_server_id(self):
        target = PipelineTarget(server_id="550e8400-e29b-41d4-a716-446655440000")
        assert target.server_id == "550e8400-e29b-41d4-a716-446655440000"


class TestPipelineTargetEquality:
    """PipelineTarget compara por valor (frozen dataclass)."""

    def test_equal_targets(self):
        assert PipelineTarget(server_id="s1") == PipelineTarget(server_id="s1")

    def test_unequal_targets(self):
        assert PipelineTarget(server_id="s1") != PipelineTarget(server_id="s2")

    def test_hash_equal(self):
        assert hash(PipelineTarget(server_id="s1")) == hash(PipelineTarget(server_id="s1"))


class TestPipelineTargetInvalidServerId:
    """PipelineTarget rechaza server_id vacío o None."""

    def test_empty_server_id_raises_error(self):
        with pytest.raises(InvalidPipelineTargetError):
            PipelineTarget(server_id="")

    def test_whitespace_server_id_raises_error(self):
        with pytest.raises(InvalidPipelineTargetError):
            PipelineTarget(server_id="   ")