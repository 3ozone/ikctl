"""Tests para el Value Object OperationStatus — T-01."""
import pytest

from app.v1.operations.domain.exceptions.operation import InvalidOperationStatusError
from app.v1.operations.domain.value_objects.operation_status import OperationStatus


class TestOperationStatusValidValues:
    """Los 6 valores válidos se construyen sin error."""

    def test_pending_is_valid(self):
        assert OperationStatus("pending").value == "pending"

    def test_in_progress_is_valid(self):
        assert OperationStatus("in_progress").value == "in_progress"

    def test_completed_is_valid(self):
        assert OperationStatus("completed").value == "completed"

    def test_failed_is_valid(self):
        assert OperationStatus("failed").value == "failed"

    def test_cancelled_is_valid(self):
        assert OperationStatus("cancelled").value == "cancelled"

    def test_cancelled_unsafe_is_valid(self):
        assert OperationStatus("cancelled_unsafe").value == "cancelled_unsafe"


class TestOperationStatusInvalidValue:
    """Valores fuera del enum lanzan error."""

    def test_invalid_value_raises_error(self):
        with pytest.raises(InvalidOperationStatusError):
            OperationStatus("running")


class TestOperationStatusTerminalStates:
    """terminal_states() devuelve exactamente los 4 estados terminales."""

    def test_terminal_states_contains_completed(self):
        assert "completed" in OperationStatus.terminal_states()

    def test_terminal_states_contains_failed(self):
        assert "failed" in OperationStatus.terminal_states()

    def test_terminal_states_contains_cancelled(self):
        assert "cancelled" in OperationStatus.terminal_states()

    def test_terminal_states_contains_cancelled_unsafe(self):
        assert "cancelled_unsafe" in OperationStatus.terminal_states()

    def test_terminal_states_does_not_contain_pending(self):
        assert "pending" not in OperationStatus.terminal_states()

    def test_terminal_states_does_not_contain_in_progress(self):
        assert "in_progress" not in OperationStatus.terminal_states()


class TestOperationStatusIsTerminal:
    """is_terminal() es True solo para los 4 estados terminales."""

    def test_completed_is_terminal(self):
        assert OperationStatus("completed").is_terminal() is True

    def test_failed_is_terminal(self):
        assert OperationStatus("failed").is_terminal() is True

    def test_cancelled_is_terminal(self):
        assert OperationStatus("cancelled").is_terminal() is True

    def test_cancelled_unsafe_is_terminal(self):
        assert OperationStatus("cancelled_unsafe").is_terminal() is True

    def test_pending_is_not_terminal(self):
        assert OperationStatus("pending").is_terminal() is False

    def test_in_progress_is_not_terminal(self):
        assert OperationStatus("in_progress").is_terminal() is False


class TestOperationStatusIsRetriable:
    """is_retriable() es True solo para failed y cancelled_unsafe."""

    def test_failed_is_retriable(self):
        assert OperationStatus("failed").is_retriable() is True

    def test_cancelled_unsafe_is_retriable(self):
        assert OperationStatus("cancelled_unsafe").is_retriable() is True

    def test_completed_is_not_retriable(self):
        assert OperationStatus("completed").is_retriable() is False

    def test_cancelled_is_not_retriable(self):
        assert OperationStatus("cancelled").is_retriable() is False

    def test_pending_is_not_retriable(self):
        assert OperationStatus("pending").is_retriable() is False

    def test_in_progress_is_not_retriable(self):
        assert OperationStatus("in_progress").is_retriable() is False


class TestOperationStatusEquality:
    """Igualdad por valor (frozen dataclass)."""

    def test_same_value_are_equal(self):
        assert OperationStatus("pending") == OperationStatus("pending")

    def test_different_values_are_not_equal(self):
        assert OperationStatus("pending") != OperationStatus("completed")
