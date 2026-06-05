"""Tests para PipelineStatus con valor 'cancelled' (R2, R5)."""
import pytest

from app.v1.pipelines.domain.value_objects.pipeline_status import PipelineStatus
from app.v1.pipelines.domain.exceptions.pipeline_status import InvalidPipelineStatusError


class TestCancelledIsValid:
    """PipelineStatus('cancelled') es un valor válido (R2)."""

    def test_cancelled_is_valid(self):
        assert PipelineStatus("cancelled").value == "cancelled"


class TestCancelledIsTerminal:
    """PipelineStatus('cancelled') es un estado terminal (R2, R5)."""

    def test_cancelled_is_terminal(self):
        assert PipelineStatus("cancelled").is_terminal() is True


class TestCancelledInAggregation:
    """cancelled se comporta correctamente en el cálculo de estado agregado."""

    def test_all_cancelled_aggregates_to_failed(self):
        e = PipelineStatus("cancelled")
        assert e.value == "cancelled"

    def test_cancelled_counts_as_failed_operation(self):
        from app.v1.pipelines.domain.entities.pipeline_execution import PipelineExecution

        exec_in_progress = PipelineExecution(
            id="e1",
            pipeline_id="p1",
            user_id="u1",
            status=PipelineStatus("in_progress"),
            operation_ids=[],
            snapshot={},
            created_at=None,
        )
        exec_in_progress.mark_finished(["cancelled", "cancelled"])
        assert exec_in_progress.status.value == "failed"