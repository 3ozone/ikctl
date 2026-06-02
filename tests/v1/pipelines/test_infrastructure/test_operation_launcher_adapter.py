"""Tests para OperationLauncherAdapter — T-21."""
from datetime import datetime, timezone

import pytest
from unittest.mock import AsyncMock

from app.v1.operations.application.dtos.operation_dtos import OperationResult
from app.v1.pipelines.infrastructure.adapters.operation_launcher_adapter import (
    OperationLauncherAdapter,
)


def _make_result(return_id: str = "op-returned-123") -> OperationResult:
    """Crea un OperationResult de prueba."""
    return OperationResult(
        operation_id=return_id,
        user_id="user-1",
        server_id="srv-1",
        kit_id="kit-1",
        values={},
        sudo=False,
        status="pending",
        debug_level="none",
        output="",
        backup_files=(),
        created_at=datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
        updated_at=datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
        started_at=None,
        finished_at=None,
    )


def _make_launch_operation_mock(return_id: str = "op-returned-123") -> AsyncMock:
    """Crea un mock de LaunchOperation donde execute devuelve un OperationResult."""
    launch_op = AsyncMock()
    launch_op.execute.return_value = _make_result(return_id)
    return launch_op


# ---------------------------------------------------------------------------
# Test 1: launch delega en LaunchOperation.execute y devuelve operation_id
# ---------------------------------------------------------------------------

async def test_launch_delegates_and_returns_operation_id():
    """launch delega en LaunchOperation.execute y devuelve el operation_id."""
    launch_op = _make_launch_operation_mock(return_id="op-42")
    adapter = OperationLauncherAdapter(launch_operation=launch_op)

    result = await adapter.launch(
        user_id="user-1",
        server_id="srv-1",
        kit_id="kit-1",
        values={"key": "val"},
        sudo=True,
        debug_level="full",
    )

    assert result == "op-42"
    launch_op.execute.assert_awaited_once_with(
        user_id="user-1",
        server_id="srv-1",
        kit_id="kit-1",
        values={"key": "val"},
        sudo=True,
        debug_level="full",
    )


# ---------------------------------------------------------------------------
# Test 2: launch con values=None pasa defaults al use case
# ---------------------------------------------------------------------------

async def test_launch_with_defaults():
    """launch con values=None y defaults los pasa tal cual al use case."""
    launch_op = _make_launch_operation_mock()
    adapter = OperationLauncherAdapter(launch_operation=launch_op)

    await adapter.launch(
        user_id="user-2",
        server_id="srv-2",
        kit_id="kit-2",
    )

    launch_op.execute.assert_awaited_once_with(
        user_id="user-2",
        server_id="srv-2",
        kit_id="kit-2",
        values=None,
        sudo=False,
        debug_level="none",
    )


# ---------------------------------------------------------------------------
# Test 3: launch propaga excepciones del use case
# ---------------------------------------------------------------------------

async def test_launch_propagates_exceptions():
    """launch propaga excepciones lanzadas por LaunchOperation.execute."""
    from app.v1.operations.application.exceptions import KitNotUsableError

    launch_op = AsyncMock()
    launch_op.execute.side_effect = KitNotUsableError("Kit no usable")
    adapter = OperationLauncherAdapter(launch_operation=launch_op)

    with pytest.raises(KitNotUsableError):
        await adapter.launch(
            user_id="user-1",
            server_id="srv-1",
            kit_id="kit-bad",
        )