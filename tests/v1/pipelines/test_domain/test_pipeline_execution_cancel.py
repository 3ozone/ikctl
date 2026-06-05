"""Tests para cancel() y mark_timeout_failed() en PipelineExecution."""
from datetime import datetime, timezone

import pytest

from app.v1.pipelines.domain.entities.pipeline_execution import PipelineExecution
from app.v1.pipelines.domain.exceptions.pipeline_execution import (
    PipelineExecutionNotCancellableError,
)
from app.v1.pipelines.domain.exceptions.pipeline_status import InvalidPipelineStatusError
from app.v1.pipelines.domain.value_objects.pipeline_status import PipelineStatus

_NOW = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


def _make_execution(**overrides) -> PipelineExecution:
    defaults = dict(
        id="exec-001",
        pipeline_id="pipe-001",
        user_id="user-001",
        status=PipelineStatus("in_progress"),
        operation_ids=["op-1", "op-2"],
        snapshot={},
        created_at=_NOW,
        started_at=_NOW,
        finished_at=None,
    )
    defaults.update(overrides)
    return PipelineExecution(**defaults)


class TestCancelInProgress:
    """cancel() transiciona in_progress → cancelled y registra finished_at (R2)."""

    def test_cancel_in_progress_transitions_to_cancelled(self):
        e = _make_execution()
        e.cancel()
        assert e.status.value == "cancelled"

    def test_cancel_registers_finished_at(self):
        e = _make_execution()
        before = datetime.now(timezone.utc)
        e.cancel()
        assert e.finished_at is not None
        assert e.finished_at >= before


class TestCancelPendingRaises:
    """cancel() falla si la ejecución está en pending (R6)."""

    def test_cancel_pending_raises_error(self):
        e = _make_execution(status=PipelineStatus("pending"))
        with pytest.raises(PipelineExecutionNotCancellableError):
            e.cancel()


class TestCancelTerminalRaises:
    """cancel() falla si la ejecución está en estado terminal (R5)."""

    def test_cancel_completed_raises_error(self):
        e = _make_execution(status=PipelineStatus("completed"), finished_at=_NOW)
        with pytest.raises(PipelineExecutionNotCancellableError):
            e.cancel()

    def test_cancel_failed_raises_error(self):
        e = _make_execution(status=PipelineStatus("failed"), finished_at=_NOW)
        with pytest.raises(PipelineExecutionNotCancellableError):
            e.cancel()

    def test_cancel_partial_raises_error(self):
        e = _make_execution(status=PipelineStatus("partial"), finished_at=_NOW)
        with pytest.raises(PipelineExecutionNotCancellableError):
            e.cancel()


class TestMarkTimeoutFailed:
    """mark_timeout_failed() transiciona in_progress → failed y registra finished_at (R10)."""

    def test_mark_timeout_failed_in_progress_transitions_to_failed(self):
        e = _make_execution()
        e.mark_timeout_failed()
        assert e.status.value == "failed"

    def test_mark_timeout_failed_registers_finished_at(self):
        e = _make_execution()
        before = datetime.now(timezone.utc)
        e.mark_timeout_failed()
        assert e.finished_at is not None
        assert e.finished_at >= before

    def test_mark_timeout_failed_pending_raises_error(self):
        e = _make_execution(status=PipelineStatus("pending"), started_at=None)
        with pytest.raises(InvalidPipelineStatusError):
            e.mark_timeout_failed()