"""Tests para el Value Object PipelineStatus — T-03."""
import pytest

from app.v1.pipelines.domain.value_objects.pipeline_status import PipelineStatus
from app.v1.pipelines.domain.exceptions.pipeline_status import InvalidPipelineStatusError


class TestPipelineStatusValidValues:
    """PipelineStatus acepta los 5 valores válidos."""

    def test_pending(self):
        assert PipelineStatus("pending").value == "pending"

    def test_in_progress(self):
        assert PipelineStatus("in_progress").value == "in_progress"

    def test_completed(self):
        assert PipelineStatus("completed").value == "completed"

    def test_failed(self):
        assert PipelineStatus("failed").value == "failed"

    def test_partial(self):
        assert PipelineStatus("partial").value == "partial"


class TestPipelineStatusIsTerminal:
    """is_terminal() devuelve True solo para estados terminales."""

    def test_pending_is_not_terminal(self):
        assert PipelineStatus("pending").is_terminal() is False

    def test_in_progress_is_not_terminal(self):
        assert PipelineStatus("in_progress").is_terminal() is False

    def test_completed_is_terminal(self):
        assert PipelineStatus("completed").is_terminal() is True

    def test_failed_is_terminal(self):
        assert PipelineStatus("failed").is_terminal() is True

    def test_partial_is_terminal(self):
        assert PipelineStatus("partial").is_terminal() is True


class TestPipelineStatusImmutability:
    """PipelineStatus es inmutable (frozen dataclass)."""

    def test_frozen(self):
        status = PipelineStatus("pending")
        with pytest.raises(AttributeError):
            status.value = "completed"

    def test_equality_by_value(self):
        assert PipelineStatus("pending") == PipelineStatus("pending")

    def test_inequality(self):
        assert PipelineStatus("pending") != PipelineStatus("completed")

    def test_hash_consistent(self):
        assert hash(PipelineStatus("pending")) == hash(PipelineStatus("pending"))


class TestPipelineStatusInvalidValue:
    """PipelineStatus rechaza valores inválidos."""

    def test_invalid_status_raises_error(self):
        with pytest.raises(InvalidPipelineStatusError):
            PipelineStatus("running")

    def test_empty_status_raises_error(self):
        with pytest.raises(InvalidPipelineStatusError):
            PipelineStatus("")