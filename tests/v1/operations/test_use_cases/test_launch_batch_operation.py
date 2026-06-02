"""Tests para el command LaunchBatchOperation — T-10.3."""
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from app.v1.operations.application.commands.launch_batch_operation import (
    LaunchBatchOperation,
)
from app.v1.operations.application.dtos.operation_dtos import BatchOperationResult
from app.v1.operations.application.exceptions import (
    GroupNotFoundError,
    KitNotUsableError,
    ServerNotActiveError,
)
from app.v1.servers.domain.entities.group import Group
from app.v1.servers.domain.entities.server import Server
from app.v1.servers.domain.value_objects.server_status import ServerStatus
from app.v1.servers.domain.value_objects.server_type import ServerType
from app.v1.kits.domain.entities.kit import Kit
from app.v1.kits.domain.value_objects.sync_status import SyncStatus

NOW = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


def make_group(server_ids: list[str] | None = None) -> Group:
    return Group(
        id="grp-1",
        user_id="user-1",
        name="My Group",
        description=None,
        server_ids=server_ids if server_ids is not None else ["srv-1", "srv-2"],
        created_at=NOW,
        updated_at=NOW,
    )


def make_server(server_id: str = "srv-1", status: str = "active") -> Server:
    return Server(
        id=server_id,
        user_id="user-1",
        name=f"Server {server_id}",
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


def make_kit(synced: bool = True, deleted: bool = False) -> Kit:
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
        debug_level="none",
        upload_files=("nginx.conf.j2",),
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


def make_use_case(group: Group | None, servers: list[Server], kit: Kit | None):
    operation_repo = AsyncMock()
    server_repo = AsyncMock()
    kit_repo = AsyncMock()
    task_queue = AsyncMock()
    event_bus = AsyncMock()

    server_repo.find_group_by_id_internal.return_value = group
    server_repo.find_servers_by_ids.return_value = servers
    # LaunchOperation (sub-use-case) llama a find_by_id_internal por cada servidor
    server_map = {s.id: s for s in servers}
    server_repo.find_by_id_internal.side_effect = lambda sid: server_map.get(sid)
    kit_repo.find_by_id_internal.return_value = kit

    use_case = LaunchBatchOperation(
        operation_repository=operation_repo,
        server_repository=server_repo,
        kit_repository=kit_repo,
        task_queue=task_queue,
        event_bus=event_bus,
    )
    return use_case, operation_repo, server_repo, kit_repo, task_queue, event_bus


class TestLaunchBatchOperationSuccess:
    """Casos de éxito al lanzar una operación en batch sobre un grupo."""

    @pytest.mark.asyncio
    async def test_launch_creates_one_operation_per_server(self):
        group = make_group(server_ids=["srv-1", "srv-2"])
        servers = [make_server("srv-1"), make_server("srv-2")]
        kit = make_kit()
        uc, op_repo, *_ = make_use_case(group=group, servers=servers, kit=kit)

        result = await uc.execute(
            user_id="user-1",
            group_id="grp-1",
            kit_id="kit-1",
            debug_level=None,
        )

        assert op_repo.save.await_count == 2
        assert isinstance(result, BatchOperationResult)
        assert len(result.operations) == 2

    @pytest.mark.asyncio
    async def test_result_operations_have_correct_server_ids(self):
        group = make_group(server_ids=["srv-1", "srv-2"])
        servers = [make_server("srv-1"), make_server("srv-2")]
        kit = make_kit()
        uc, *_ = make_use_case(group=group, servers=servers, kit=kit)

        result = await uc.execute(
            user_id="user-1",
            group_id="grp-1",
            kit_id="kit-1",
            debug_level=None,
        )

        server_ids_in_result = {op.server_id for op in result.operations}
        assert server_ids_in_result == {"srv-1", "srv-2"}

    @pytest.mark.asyncio
    async def test_result_operations_are_pending(self):
        group = make_group(server_ids=["srv-1"])
        servers = [make_server("srv-1")]
        kit = make_kit()
        uc, *_ = make_use_case(group=group, servers=servers, kit=kit)

        result = await uc.execute(
            user_id="user-1",
            group_id="grp-1",
            kit_id="kit-1",
            debug_level=None,
        )

        assert all(op.status == "pending" for op in result.operations)

    @pytest.mark.asyncio
    async def test_enqueues_one_task_per_server(self):
        group = make_group(server_ids=["srv-1", "srv-2"])
        servers = [make_server("srv-1"), make_server("srv-2")]
        kit = make_kit()
        uc, _, _, _, task_queue, _ = make_use_case(group=group, servers=servers, kit=kit)

        await uc.execute(
            user_id="user-1",
            group_id="grp-1",
            kit_id="kit-1",
            debug_level=None,
        )

        assert task_queue.enqueue.await_count == 2

    @pytest.mark.asyncio
    async def test_publishes_one_event_per_server_after_saves(self):
        group = make_group(server_ids=["srv-1", "srv-2"])
        servers = [make_server("srv-1"), make_server("srv-2")]
        kit = make_kit()
        uc, op_repo, _, _, _, event_bus = make_use_case(group=group, servers=servers, kit=kit)

        call_order = []
        op_repo.save.side_effect = lambda *a, **kw: call_order.append("save")
        event_bus.publish.side_effect = lambda *a, **kw: call_order.append("publish")

        await uc.execute(
            user_id="user-1",
            group_id="grp-1",
            kit_id="kit-1",
            debug_level=None,
        )

        # save antes de publish para cada operación
        assert call_order == ["save", "publish", "save", "publish"]

    @pytest.mark.asyncio
    async def test_empty_group_returns_empty_batch(self):
        group = make_group(server_ids=[])
        kit = make_kit()
        uc, op_repo, *_ = make_use_case(group=group, servers=[], kit=kit)

        result = await uc.execute(
            user_id="user-1",
            group_id="grp-1",
            kit_id="kit-1",
            debug_level=None,
        )

        op_repo.save.assert_not_awaited()
        assert result.operations == []


class TestLaunchBatchOperationErrors:
    """Casos de error al lanzar operación batch."""

    @pytest.mark.asyncio
    async def test_group_not_found_raises_group_not_found_error(self):
        kit = make_kit()
        uc, *_ = make_use_case(group=None, servers=[], kit=kit)

        with pytest.raises(GroupNotFoundError):
            await uc.execute(
                user_id="user-1",
                group_id="grp-x",
                kit_id="kit-1",
                debug_level=None,
            )

    @pytest.mark.asyncio
    async def test_kit_not_found_raises_error(self):
        group = make_group(server_ids=["srv-1"])
        servers = [make_server("srv-1")]
        uc, *_ = make_use_case(group=group, servers=servers, kit=None)

        with pytest.raises(Exception):
            await uc.execute(
                user_id="user-1",
                group_id="grp-1",
                kit_id="kit-x",
                debug_level=None,
            )

    @pytest.mark.asyncio
    async def test_kit_not_usable_raises_kit_not_usable_error(self):
        group = make_group(server_ids=["srv-1"])
        servers = [make_server("srv-1")]
        kit = make_kit(synced=False)
        uc, *_ = make_use_case(group=group, servers=servers, kit=kit)

        with pytest.raises(KitNotUsableError):
            await uc.execute(
                user_id="user-1",
                group_id="grp-1",
                kit_id="kit-1",
                debug_level=None,
            )

    @pytest.mark.asyncio
    async def test_inactive_server_raises_server_not_active_error(self):
        group = make_group(server_ids=["srv-1"])
        servers = [make_server("srv-1", status="inactive")]
        kit = make_kit()
        uc, *_ = make_use_case(group=group, servers=servers, kit=kit)

        with pytest.raises(ServerNotActiveError):
            await uc.execute(
                user_id="user-1",
                group_id="grp-1",
                kit_id="kit-1",
                debug_level=None,
            )
