"""Tests para el command RestoreOperationBackup — T-12."""
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from app.v1.operations.application.commands.restore_operation_backup import RestoreOperationBackup
from app.v1.operations.application.exceptions import OperationNotRestorableError
from app.v1.operations.domain.entities.operation import Operation
from app.v1.operations.domain.exceptions.operation import OperationNotFoundError
from app.v1.operations.domain.value_objects.operation_status import OperationStatus

NOW = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


def make_operation(status="failed", backup_files=("/etc/nginx/nginx.conf.bak.ikctl",)) -> Operation:
    return Operation(
        id="op-1",
        user_id="user-1",
        server_id="srv-1",
        kit_id="kit-1",
        values={},
        sudo=False,
        status=OperationStatus(status),
        debug_level="none",
        output="",
        backup_files=backup_files,
        created_at=NOW,
        updated_at=NOW,
        started_at=NOW,
        finished_at=NOW,
    )


def make_use_case(operation=None):
    operation_repo = AsyncMock()
    task_queue = AsyncMock()

    operation_repo.find_by_id.return_value = operation

    use_case = RestoreOperationBackup(
        operation_repository=operation_repo,
        task_queue=task_queue,
    )
    return use_case, operation_repo, task_queue


class TestRestoreOperationBackupSuccess:
    """Casos de éxito al restaurar el backup de una operación."""

    @pytest.mark.asyncio
    async def test_restore_enqueues_task(self):
        op = make_operation(status="failed")
        uc, _, task_queue = make_use_case(operation=op)

        await uc.execute(operation_id="op-1", user_id="user-1")

        task_queue.enqueue.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_restore_returns_backup_files_in_result(self):
        files = ("/etc/nginx/nginx.conf.bak.ikctl", "/etc/nginx/sites.conf.bak.ikctl")
        op = make_operation(status="cancelled_unsafe", backup_files=files)
        uc, *_ = make_use_case(operation=op)

        result = await uc.execute(operation_id="op-1", user_id="user-1")

        assert result.operation_id == "op-1"
        assert result.restored_files == files


class TestRestoreOperationBackupErrors:
    """Casos de error al restaurar el backup de una operación."""

    @pytest.mark.asyncio
    async def test_restore_not_found_raises_error(self):
        uc, *_ = make_use_case(operation=None)

        with pytest.raises(OperationNotFoundError):
            await uc.execute(operation_id="op-x", user_id="user-1")

    @pytest.mark.asyncio
    async def test_restore_not_restorable_wrong_status_raises_error(self):
        op = make_operation(status="completed", backup_files=("/etc/nginx.bak.ikctl",))
        uc, *_ = make_use_case(operation=op)

        with pytest.raises(OperationNotRestorableError):
            await uc.execute(operation_id="op-1", user_id="user-1")

    @pytest.mark.asyncio
    async def test_restore_not_restorable_no_backup_files_raises_error(self):
        op = make_operation(status="failed", backup_files=())
        uc, *_ = make_use_case(operation=op)

        with pytest.raises(OperationNotRestorableError):
            await uc.execute(operation_id="op-1", user_id="user-1")
