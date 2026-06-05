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


class TestPipelineTargetKitIds:
    """PipelineTarget acepta kit_ids opcional y valida contenido."""

    def test_kit_ids_none_by_default(self):
        target = PipelineTarget(server_id="srv-1")
        assert target.kit_ids is None

    def test_kit_ids_empty_tuple(self):
        target = PipelineTarget(server_id="srv-1", kit_ids=())
        assert target.kit_ids == ()

    def test_kit_ids_with_values(self):
        target = PipelineTarget(server_id="srv-1", kit_ids=("kit-1", "kit-2"))
        assert target.kit_ids == ("kit-1", "kit-2")

    def test_kit_ids_inmutable(self):
        target = PipelineTarget(server_id="srv-1", kit_ids=("kit-1",))
        assert isinstance(target.kit_ids, tuple)

    def test_kit_ids_empty_string_raises(self):
        with pytest.raises(InvalidPipelineTargetError):
            PipelineTarget(server_id="srv-1", kit_ids=("",))

    def test_kit_ids_whitespace_string_raises(self):
        with pytest.raises(InvalidPipelineTargetError):
            PipelineTarget(server_id="srv-1", kit_ids=("   ",))


class TestPipelineTargetValues:
    """PipelineTarget acepta values opcional (dict)."""

    def test_values_empty_dict_by_default(self):
        target = PipelineTarget(server_id="srv-1")
        assert target.values == {}

    def test_values_with_data(self):
        target = PipelineTarget(server_id="srv-1", values={"env": "staging"})
        assert target.values == {"env": "staging"}

    def test_values_independent_instances(self):
        """Cada instancia tiene su propio dict (field(default_factory=dict))."""
        t1 = PipelineTarget(server_id="srv-1")
        t2 = PipelineTarget(server_id="srv-2", values={"env": "prod"})
        assert t1.values == {}
        assert t2.values == {"env": "prod"}


class TestPipelineTargetHashWithNewFields:
    """El hash incluye kit_ids y values."""

    def test_hash_equal_with_same_kit_ids_and_values(self):
        t1 = PipelineTarget(server_id="s1", kit_ids=("k1",), values={"a": 1})
        t2 = PipelineTarget(server_id="s1", kit_ids=("k1",), values={"a": 1})
        assert hash(t1) == hash(t2)
        assert t1 == t2

    def test_hash_different_with_different_kit_ids(self):
        t1 = PipelineTarget(server_id="s1", kit_ids=("k1",))
        t2 = PipelineTarget(server_id="s1", kit_ids=("k2",))
        assert hash(t1) != hash(t2)

    def test_hash_different_with_different_values(self):
        t1 = PipelineTarget(server_id="s1", values={"a": 1})
        t2 = PipelineTarget(server_id="s1", values={"a": 2})
        assert hash(t1) != hash(t2)