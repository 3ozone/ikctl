"""Tests para la Entity PipelineExecution — T-05."""
from datetime import datetime, timezone

import pytest

from app.v1.pipelines.domain.entities.pipeline_execution import PipelineExecution
from app.v1.pipelines.domain.exceptions.pipeline_status import InvalidPipelineStatusError
from app.v1.pipelines.domain.value_objects.pipeline_status import PipelineStatus


_NOW = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


def _make_execution(**overrides) -> PipelineExecution:
    defaults = dict(
        id="exec-001",
        pipeline_id="pipe-001",
        user_id="user-001",
        status=PipelineStatus("pending"),
        operation_ids=[],
        snapshot={"targets": [{"server_id": "srv-001"}], "kits": [{"kit_id": "kit-001"}]},
        created_at=_NOW,
        started_at=None,
        finished_at=None,
    )
    defaults.update(overrides)
    return PipelineExecution(**defaults)


class TestPipelineExecutionCreation:
    """PipelineExecution se crea correctamente con todos los campos."""

    def test_create_pending_execution(self):
        e = _make_execution()
        assert e.id == "exec-001"
        assert e.pipeline_id == "pipe-001"
        assert e.user_id == "user-001"
        assert e.status.value == "pending"
        assert e.operation_ids == []
        assert e.snapshot is not None
        assert e.started_at is None
        assert e.finished_at is None

    def test_create_with_operation_ids(self):
        e = _make_execution(operation_ids=["op-001", "op-002"])
        assert len(e.operation_ids) == 2


class TestPipelineExecutionEquality:
    """PipelineExecution compara por id."""

    def test_equal_by_id(self):
        e1 = _make_execution(id="exec-001", status=PipelineStatus("pending"))
        e2 = _make_execution(id="exec-001", status=PipelineStatus("completed"))
        assert e1 == e2

    def test_unequal_by_id(self):
        e1 = _make_execution(id="exec-001")
        e2 = _make_execution(id="exec-002")
        assert e1 != e2


class TestPipelineExecutionStart:
    """start() cambia status de pending a in_progress y registra started_at."""

    def test_start_from_pending(self):
        e = _make_execution()
        e.start()
        assert e.status.value == "in_progress"
        assert e.started_at is not None

    def test_start_sets_started_at(self):
        e = _make_execution()
        before = datetime.now(timezone.utc)
        e.start()
        assert e.started_at is not None
        assert e.started_at >= before


class TestPipelineExecutionStartInvalid:
    """start() falla si no está en pending."""

    def test_start_from_in_progress_raises(self):
        e = _make_execution(status=PipelineStatus("in_progress"))
        with pytest.raises(InvalidPipelineStatusError):
            e.start()

    def test_start_from_completed_raises(self):
        e = _make_execution(status=PipelineStatus("completed"))
        with pytest.raises(InvalidPipelineStatusError):
            e.start()


class TestPipelineExecutionMarkFinished:
    """mark_finished() calcula RN-20: estado agregado basado en operation statuses."""

    def test_all_completed(self):
        e = _make_execution(status=PipelineStatus("in_progress"))
        e.mark_finished(["completed", "completed", "completed"])
        assert e.status.value == "completed"
        assert e.finished_at is not None

    def test_all_failed(self):
        e = _make_execution(status=PipelineStatus("in_progress"))
        e.mark_finished(["failed", "failed"])
        assert e.status.value == "failed"
        assert e.finished_at is not None

    def test_partial_some_completed_some_failed(self):
        e = _make_execution(status=PipelineStatus("in_progress"))
        e.mark_finished(["completed", "failed", "completed"])
        assert e.status.value == "partial"
        assert e.finished_at is not None

    def test_partial_with_cancelled_unsafe(self):
        e = _make_execution(status=PipelineStatus("in_progress"))
        e.mark_finished(["completed", "cancelled_unsafe"])
        assert e.status.value == "partial"

    def test_all_terminal_no_completed(self):
        e = _make_execution(status=PipelineStatus("in_progress"))
        e.mark_finished(["failed", "cancelled_unsafe"])
        assert e.status.value == "failed"

    def test_cancelled_counts_as_failed_for_aggregation(self):
        e = _make_execution(status=PipelineStatus("in_progress"))
        e.mark_finished(["cancelled", "cancelled"])
        assert e.status.value == "failed"

    def test_mark_finished_from_pending_raises(self):
        e = _make_execution(status=PipelineStatus("pending"))
        with pytest.raises(InvalidPipelineStatusError):
            e.mark_finished(["completed"])