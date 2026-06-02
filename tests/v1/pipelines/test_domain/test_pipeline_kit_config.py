"""Tests para el Value Object PipelineKitConfig — T-02."""
import pytest

from app.v1.pipelines.domain.value_objects.pipeline_kit_config import PipelineKitConfig
from app.v1.pipelines.domain.exceptions.pipeline_kit_config import InvalidPipelineKitConfigError


class TestPipelineKitConfigCreation:
    """PipelineKitConfig se crea correctamente con kit_id válido."""

    def test_minimal_config(self):
        config = PipelineKitConfig(kit_id="kit-001")
        assert config.kit_id == "kit-001"
        assert config.sudo is None
        assert config.debug_level is None

    def test_full_config(self):
        config = PipelineKitConfig(kit_id="kit-001", sudo=True, debug_level="errors")
        assert config.kit_id == "kit-001"
        assert config.sudo is True
        assert config.debug_level == "errors"

    def test_sudo_false(self):
        config = PipelineKitConfig(kit_id="kit-001", sudo=False)
        assert config.sudo is False

    def test_debug_level_none_means_inherit(self):
        config = PipelineKitConfig(kit_id="kit-001", debug_level=None)
        assert config.debug_level is None


class TestPipelineKitConfigEquality:
    """PipelineKitConfig compara por valor (frozen dataclass)."""

    def test_equal_configs(self):
        assert PipelineKitConfig(kit_id="k1", sudo=True, debug_level="full") == PipelineKitConfig(kit_id="k1", sudo=True, debug_level="full")

    def test_unequal_kit_id(self):
        assert PipelineKitConfig(kit_id="k1") != PipelineKitConfig(kit_id="k2")

    def test_unequal_sudo(self):
        assert PipelineKitConfig(kit_id="k1", sudo=True) != PipelineKitConfig(kit_id="k1", sudo=False)

    def test_hash_equal(self):
        assert hash(PipelineKitConfig(kit_id="k1", sudo=False, debug_level="none")) == hash(PipelineKitConfig(kit_id="k1", sudo=False, debug_level="none"))


class TestPipelineKitConfigInvalidKitId:
    """PipelineKitConfig rechaza kit_id vacío."""

    def test_empty_kit_id_raises_error(self):
        with pytest.raises(InvalidPipelineKitConfigError):
            PipelineKitConfig(kit_id="")

    def test_whitespace_kit_id_raises_error(self):
        with pytest.raises(InvalidPipelineKitConfigError):
            PipelineKitConfig(kit_id="   ")


class TestPipelineKitConfigInvalidDebugLevel:
    """PipelineKitConfig rechaza debug_level inválido."""

    def test_invalid_debug_level_raises_error(self):
        with pytest.raises(InvalidPipelineKitConfigError):
            PipelineKitConfig(kit_id="kit-001", debug_level="invalid")

    def test_valid_debug_levels(self):
        for level in ("none", "errors", "full"):
            config = PipelineKitConfig(kit_id="kit-001", debug_level=level)
            assert config.debug_level == level