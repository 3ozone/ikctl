"""Tests para la entity Operation — T-02."""
from datetime import datetime, timezone

import pytest

from app.v1.operations.domain.entities.operation import Operation
from app.v1.operations.domain.value_objects.operation_status import OperationStatus
from app.v1.operations.domain.exceptions.operation import (
    InvalidOperationTransitionError,
    OperationNotFoundError,
)

NOW = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


def make_operation(**overrides) -> Operation:
    defaults = dict(
        id="op-1",
        user_id="user-1",
        server_id="srv-1",
        kit_id="kit-1",
        values={},
        sudo=False,
        status=OperationStatus("pending"),
        debug_level="none",
        output="",
        backup_files=(),
        created_at=NOW,
        updated_at=NOW,
        started_at=None,
        finished_at=None,
    )
    defaults.update(overrides)
    return Operation(**defaults)


class TestOperationCreation:
    """La entity se construye correctamente con campos válidos."""

    def test_operation_creates_with_valid_fields(self):
        op = make_operation()
        assert op.id == "op-1"
        assert op.user_id == "user-1"
        assert op.server_id == "srv-1"
        assert op.kit_id == "kit-1"
        assert op.status == OperationStatus("pending")
        assert op.debug_level == "none"
        assert op.output == ""

    def test_operation_equality_by_id(self):
        op_a = make_operation(id="op-1", user_id="user-1")
        op_b = make_operation(id="op-1", user_id="user-2")
        assert op_a == op_b

    def test_operation_inequality_different_ids(self):
        op_a = make_operation(id="op-1")
        op_b = make_operation(id="op-2")
        assert op_a != op_b


class TestOperationTransitions:
    """State machine — transiciones válidas."""

    def test_start_transitions_pending_to_in_progress(self):
        op = make_operation()
        op.start(started_at=NOW)
        assert op.status == OperationStatus("in_progress")
        assert op.started_at == NOW

    def test_complete_transitions_in_progress_to_completed(self):
        op = make_operation(status=OperationStatus("in_progress"), started_at=NOW)
        op.complete(finished_at=NOW)
        assert op.status == OperationStatus("completed")
        assert op.finished_at == NOW

    def test_fail_transitions_in_progress_to_failed(self):
        op = make_operation(status=OperationStatus("in_progress"), started_at=NOW)
        op.fail(finished_at=NOW)
        assert op.status == OperationStatus("failed")
        assert op.finished_at == NOW

    def test_cancel_transitions_pending_to_cancelled(self):
        op = make_operation()
        op.cancel(finished_at=NOW)
        assert op.status == OperationStatus("cancelled")
        assert op.finished_at == NOW

    def test_cancel_unsafe_transitions_in_progress_to_cancelled_unsafe(self):
        op = make_operation(status=OperationStatus("in_progress"), started_at=NOW)
        op.cancel_unsafe(finished_at=NOW)
        assert op.status == OperationStatus("cancelled_unsafe")
        assert op.finished_at == NOW


class TestOperationInvalidTransitions:
    """Transiciones desde estados terminales lanzan InvalidOperationTransitionError."""

    def test_start_from_completed_raises_error(self):
        op = make_operation(status=OperationStatus("completed"))
        with pytest.raises(InvalidOperationTransitionError):
            op.start(started_at=NOW)

    def test_complete_from_pending_raises_error(self):
        op = make_operation(status=OperationStatus("pending"))
        with pytest.raises(InvalidOperationTransitionError):
            op.complete(finished_at=NOW)

    def test_fail_from_pending_raises_error(self):
        op = make_operation(status=OperationStatus("pending"))
        with pytest.raises(InvalidOperationTransitionError):
            op.fail(finished_at=NOW)

    def test_cancel_from_in_progress_raises_error(self):
        op = make_operation(status=OperationStatus("in_progress"), started_at=NOW)
        with pytest.raises(InvalidOperationTransitionError):
            op.cancel(finished_at=NOW)

    def test_cancel_unsafe_from_pending_raises_error(self):
        op = make_operation(status=OperationStatus("pending"))
        with pytest.raises(InvalidOperationTransitionError):
            op.cancel_unsafe(finished_at=NOW)

    def test_start_from_terminal_raises_error(self):
        for terminal in ("completed", "failed", "cancelled", "cancelled_unsafe"):
            op = make_operation(status=OperationStatus(terminal))
            with pytest.raises(InvalidOperationTransitionError):
                op.start(started_at=NOW)


class TestOperationAppendOutput:
    """append_output acumula texto de salida."""

    def test_append_output_adds_text(self):
        op = make_operation(output="")
        op.append_output("línea 1\n")
        assert op.output == "línea 1\n"

    def test_append_output_accumulates(self):
        op = make_operation(output="línea 1\n")
        op.append_output("línea 2\n")
        assert op.output == "línea 1\nlínea 2\n"


class TestOperationQueries:
    """Queries de estado — sin mutación."""

    def test_is_terminal_true_for_completed(self):
        op = make_operation(status=OperationStatus("completed"))
        assert op.is_terminal() is True

    def test_is_terminal_false_for_pending(self):
        op = make_operation(status=OperationStatus("pending"))
        assert op.is_terminal() is False

    def test_is_retriable_true_for_failed(self):
        op = make_operation(status=OperationStatus("failed"))
        assert op.is_retriable() is True

    def test_is_retriable_false_for_completed(self):
        op = make_operation(status=OperationStatus("completed"))
        assert op.is_retriable() is False

    def test_is_restorable_true_when_failed_with_backup_files(self):
        op = make_operation(
            status=OperationStatus("failed"),
            backup_files=("/etc/nginx/nginx.conf",),
        )
        assert op.is_restorable() is True

    def test_is_restorable_false_when_failed_without_backup_files(self):
        op = make_operation(
            status=OperationStatus("failed"),
            backup_files=(),
        )
        assert op.is_restorable() is False

    def test_is_restorable_false_when_completed_with_backup_files(self):
        op = make_operation(
            status=OperationStatus("completed"),
            backup_files=("/etc/nginx/nginx.conf",),
        )
        assert op.is_restorable() is False
