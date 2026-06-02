"""Tests para RestoreBackupTask — RF-18.

Verifica que la task de restauración:
1. Restaura los ficheros .bak.ikctl usando BackupRestorer
2. Actualiza el output de la operación con el resultado
3. Sale silenciosamente si la operación no existe
4. Sale silenciosamente si no hay backup_files
"""
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from app.v1.operations.application.tasks.restore_backup import RestoreBackupTask
from app.v1.operations.domain.entities.operation import Operation
from app.v1.operations.domain.value_objects.operation_status import OperationStatus

NOW = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


def make_operation(backup_files=("/etc/nginx/nginx.conf",)) -> Operation:
    return Operation(
        id="op-1",
        user_id="user-1",
        server_id="srv-1",
        kit_id="kit-1",
        values={},
        sudo=False,
        status=OperationStatus("failed"),
        debug_level="none",
        output="",
        backup_files=backup_files,
        created_at=NOW,
        updated_at=NOW,
        started_at=NOW,
        finished_at=NOW,
    )


class TestRestoreBackupTask:
    """Tests de la task de restauración de backup."""

    @pytest.mark.asyncio
    async def test_restore_calls_backup_restorer_with_server_id(self):
        op = make_operation()
        op_repo = AsyncMock()
        op_repo.find_by_id_no_ownership.return_value = op
        backup_restorer = AsyncMock()
        backup_restorer.restore.return_value = ("/etc/nginx/nginx.conf",)

        task = RestoreBackupTask(
            operation_repository=op_repo,
            backup_restorer=backup_restorer,
        )

        await task.execute("op-1")

        backup_restorer.restore.assert_awaited_once_with(
            server_id="srv-1",
            backup_files=("/etc/nginx/nginx.conf",),
        )

    @pytest.mark.asyncio
    async def test_restore_updates_output_with_result(self):
        op = make_operation()
        op_repo = AsyncMock()
        op_repo.find_by_id_no_ownership.return_value = op
        backup_restorer = AsyncMock()
        backup_restorer.restore.return_value = ("/etc/nginx/nginx.conf",)

        task = RestoreBackupTask(
            operation_repository=op_repo,
            backup_restorer=backup_restorer,
        )

        await task.execute("op-1")

        op_repo.update.assert_awaited_once()
        assert "1/1 ficheros restaurados" in op.output

    @pytest.mark.asyncio
    async def test_restore_exits_silently_on_missing_operation(self):
        op_repo = AsyncMock()
        op_repo.find_by_id_no_ownership.return_value = None
        backup_restorer = AsyncMock()

        task = RestoreBackupTask(
            operation_repository=op_repo,
            backup_restorer=backup_restorer,
        )

        await task.execute("op-x")

        backup_restorer.restore.assert_not_awaited()
        op_repo.update.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_restore_exits_silently_on_empty_backup_files(self):
        op = make_operation(backup_files=())
        op_repo = AsyncMock()
        op_repo.find_by_id_no_ownership.return_value = op
        backup_restorer = AsyncMock()

        task = RestoreBackupTask(
            operation_repository=op_repo,
            backup_restorer=backup_restorer,
        )

        await task.execute("op-1")

        backup_restorer.restore.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_restore_reports_partial_restore(self):
        op = make_operation(backup_files=("/etc/nginx/nginx.conf", "/etc/app/config.yml"))
        op_repo = AsyncMock()
        op_repo.find_by_id_no_ownership.return_value = op
        backup_restorer = AsyncMock()
        backup_restorer.restore.return_value = ("/etc/nginx/nginx.conf",)

        task = RestoreBackupTask(
            operation_repository=op_repo,
            backup_restorer=backup_restorer,
        )

        await task.execute("op-1")

        assert "1/2 ficheros restaurados" in op.output