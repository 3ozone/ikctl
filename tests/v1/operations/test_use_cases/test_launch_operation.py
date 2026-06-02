"""Tests para el command LaunchOperation — T-10."""
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.v1.operations.application.commands.launch_operation import LaunchOperation
from app.v1.operations.application.exceptions import (
    ServerNotActiveError,
    KitNotUsableError,
)
from app.v1.operations.domain.exceptions.operation import OperationNotFoundError
from app.v1.servers.domain.entities.server import Server
from app.v1.servers.domain.value_objects.server_type import ServerType
from app.v1.servers.domain.value_objects.server_status import ServerStatus
from app.v1.kits.domain.entities.kit import Kit
from app.v1.kits.domain.value_objects.sync_status import SyncStatus

NOW = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


def make_server(status="active") -> Server:
    return Server(
        id="srv-1",
        user_id="user-1",
        name="My Server",
        type=ServerType("remote"),
        status=ServerStatus(status),
        host="192.168.1.1",
        port=22,
        credential_id="cred-1",
        description=None,
        os_id=None,
        os_version=None,
        os_name=None,
        created_at=NOW,
        updated_at=NOW,
    )


def make_kit(synced=True, deleted=False, debug_level="none") -> Kit:
    return Kit(
        id="kit-1",
        user_id="user-1",
        repository_id="repo-1",
        path_in_repo="nginx",
        name="Install NGINX",
        description="",
        version="1.0.0",
        tags=[],
        values={"port": 80},
        debug_level=debug_level,
        upload_files=("nginx.conf.j2", "install.sh"),
        pipeline_files=("install.sh",),
        backup_files=("/etc/nginx/nginx.conf",),
        sync_status=SyncStatus("synced" if synced else "sync_error"),
        last_synced_at=NOW if synced else None,
        last_commit_sha="abc123" if synced else None,
        sync_error_message=None,
        is_deleted=deleted,
        created_at=NOW,
        updated_at=NOW,
    )


def make_use_case(server=None, kit=None):
    operation_repo = AsyncMock()
    server_repo = AsyncMock()
    kit_repo = AsyncMock()
    task_queue = AsyncMock()
    event_bus = AsyncMock()

    server_repo.find_by_id_internal.return_value = server
    kit_repo.find_by_id_internal.return_value = kit

    use_case = LaunchOperation(
        operation_repository=operation_repo,
        server_repository=server_repo,
        kit_repository=kit_repo,
        task_queue=task_queue,
        event_bus=event_bus,
    )
    return use_case, operation_repo, server_repo, kit_repo, task_queue, event_bus


class TestLaunchOperationSuccess:
    """Casos de éxito al lanzar una operación."""

    @pytest.mark.asyncio
    async def test_launch_creates_operation_in_pending_status(self):
        server = make_server(status="active")
        kit = make_kit(synced=True)
        uc, op_repo, *_ = make_use_case(server=server, kit=kit)

        await uc.execute(user_id="user-1", server_id="srv-1", kit_id="kit-1", debug_level=None)

        op_repo.save.assert_awaited_once()
        saved_op = op_repo.save.call_args[0][0]
        assert saved_op.status.value == "pending"
        assert saved_op.server_id == "srv-1"
        assert saved_op.kit_id == "kit-1"
        assert saved_op.user_id == "user-1"

    @pytest.mark.asyncio
    async def test_launch_enqueues_execute_task(self):
        server = make_server(status="active")
        kit = make_kit(synced=True)
        uc, _, _, _, task_queue, _ = make_use_case(server=server, kit=kit)

        await uc.execute(user_id="user-1", server_id="srv-1", kit_id="kit-1", debug_level=None)

        task_queue.enqueue.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_launch_publishes_operation_launched_event_after_save(self):
        server = make_server(status="active")
        kit = make_kit(synced=True)
        uc, op_repo, _, _, _, event_bus = make_use_case(server=server, kit=kit)

        call_order = []
        op_repo.save.side_effect = lambda *a, **kw: call_order.append("save")
        event_bus.publish.side_effect = lambda *a, **kw: call_order.append("publish")

        await uc.execute(user_id="user-1", server_id="srv-1", kit_id="kit-1", debug_level=None)

        assert call_order == ["save", "publish"]

    @pytest.mark.asyncio
    async def test_launch_inherits_debug_level_from_kit_when_not_provided(self):
        server = make_server(status="active")
        kit = make_kit(synced=True, debug_level="verbose")
        uc, op_repo, *_ = make_use_case(server=server, kit=kit)

        await uc.execute(user_id="user-1", server_id="srv-1", kit_id="kit-1", debug_level=None)

        saved_op = op_repo.save.call_args[0][0]
        assert saved_op.debug_level == "verbose"

    @pytest.mark.asyncio
    async def test_launch_explicit_debug_level_overrides_kit_default(self):
        server = make_server(status="active")
        kit = make_kit(synced=True, debug_level="none")
        uc, op_repo, *_ = make_use_case(server=server, kit=kit)

        await uc.execute(user_id="user-1", server_id="srv-1", kit_id="kit-1", debug_level="verbose")

        saved_op = op_repo.save.call_args[0][0]
        assert saved_op.debug_level == "verbose"


class TestLaunchOperationErrors:
    """Casos de error al lanzar una operación."""

    @pytest.mark.asyncio
    async def test_server_not_found_raises_error(self):
        uc, *_ = make_use_case(server=None, kit=make_kit())
        with pytest.raises(OperationNotFoundError):
            await uc.execute(user_id="user-1", server_id="srv-x", kit_id="kit-1", debug_level=None)

    @pytest.mark.asyncio
    async def test_server_inactive_raises_error(self):
        server = make_server(status="inactive")
        kit = make_kit(synced=True)
        uc, *_ = make_use_case(server=server, kit=kit)
        with pytest.raises(ServerNotActiveError):
            await uc.execute(user_id="user-1", server_id="srv-1", kit_id="kit-1", debug_level=None)

    @pytest.mark.asyncio
    async def test_kit_not_found_raises_error(self):
        server = make_server(status="active")
        uc, *_ = make_use_case(server=server, kit=None)
        with pytest.raises(OperationNotFoundError):
            await uc.execute(user_id="user-1", server_id="srv-1", kit_id="kit-x", debug_level=None)

    @pytest.mark.asyncio
    async def test_kit_not_usable_raises_error(self):
        server = make_server(status="active")
        kit = make_kit(synced=False)
        uc, *_ = make_use_case(server=server, kit=kit)
        with pytest.raises(KitNotUsableError):
            await uc.execute(user_id="user-1", server_id="srv-1", kit_id="kit-1", debug_level=None)

    @pytest.mark.asyncio
    async def test_kit_deleted_raises_error(self):
        server = make_server(status="active")
        kit = make_kit(synced=True, deleted=True)
        uc, *_ = make_use_case(server=server, kit=kit)
        with pytest.raises(KitNotUsableError):
            await uc.execute(user_id="user-1", server_id="srv-1", kit_id="kit-1", debug_level=None)
