"""Tests para la async task ExecuteOperation — T-16."""
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.v1.operations.application.tasks.execute_operation import ExecuteOperation
from app.v1.operations.domain.entities.operation import Operation
from app.v1.operations.domain.value_objects.operation_status import OperationStatus
from app.v1.servers.domain.entities.server import Server
from app.v1.servers.domain.value_objects.server_type import ServerType
from app.v1.servers.domain.value_objects.server_status import ServerStatus
from app.v1.kits.domain.entities.kit import Kit
from app.v1.kits.domain.value_objects.sync_status import SyncStatus
from app.v1.servers.domain.entities.credential import Credential
from app.v1.servers.domain.value_objects.credential_type import CredentialType

NOW = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


def make_operation(status="pending") -> Operation:
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
        backup_files=(),
        created_at=NOW,
        updated_at=NOW,
        started_at=None,
        finished_at=None,
    )


def make_server() -> Server:
    return Server(
        id="srv-1",
        user_id="user-1",
        name="My Server",
        type=ServerType("remote"),
        status=ServerStatus("active"),
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


def make_kit() -> Kit:
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
        upload_files=("nginx.conf.j2", "install.sh"),
        pipeline_files=("install.sh",),
        backup_files=("/etc/nginx/nginx.conf",),
        sync_status=SyncStatus("synced"),
        last_synced_at=NOW,
        last_commit_sha="abc123",
        sync_error_message=None,
        is_deleted=False,
        created_at=NOW,
        updated_at=NOW,
    )


def make_credential() -> Credential:
    return Credential(
        id="cred-1",
        user_id="user-1",
        name="My Key",
        type=CredentialType("ssh"),
        username="root",
        private_key="-----BEGIN...",
        password=None,
        created_at=NOW,
        updated_at=NOW,
    )


def make_use_case(
    operation=None,
    server=None,
    kit=None,
    credential=None,
    executor_result=("done\n", ("/etc/nginx.bak.ikctl",)),
    executor_raises=None,
):
    op_repo = AsyncMock()
    server_repo = AsyncMock()
    kit_repo = AsyncMock()
    credential_repo = AsyncMock()
    remote_executor = AsyncMock()
    event_bus = AsyncMock()

    op_repo.find_by_id_no_ownership.return_value = operation
    server_repo.find_by_id_internal.return_value = server
    kit_repo.find_by_id_internal.return_value = kit
    credential_repo.find_by_id_internal.return_value = credential

    if executor_raises:
        remote_executor.execute.side_effect = executor_raises
    else:
        remote_executor.execute.return_value = executor_result

    use_case = ExecuteOperation(
        operation_repository=op_repo,
        server_repository=server_repo,
        kit_repository=kit_repo,
        credential_repository=credential_repo,
        remote_kit_executor=remote_executor,
        event_bus=event_bus,
    )
    return use_case, op_repo, server_repo, kit_repo, credential_repo, remote_executor, event_bus


class TestExecuteOperationSuccess:
    """Casos de éxito en la ejecución completa de una operación."""

    @pytest.mark.asyncio
    async def test_execute_starts_operation(self):
        op = make_operation()
        uc, op_repo, *_ = make_use_case(
            operation=op, server=make_server(), kit=make_kit(), credential=make_credential()
        )

        statuses_at_update = []

        async def capture(operation):
            statuses_at_update.append(operation.status.value)

        op_repo.update.side_effect = capture

        await uc.execute("op-1")

        assert statuses_at_update[0] == "in_progress"

    @pytest.mark.asyncio
    async def test_execute_completes_operation_on_success(self):
        op = make_operation()
        uc, op_repo, *_ = make_use_case(
            operation=op, server=make_server(), kit=make_kit(), credential=make_credential()
        )

        statuses_at_update = []

        async def capture(operation):
            statuses_at_update.append(operation.status.value)

        op_repo.update.side_effect = capture

        await uc.execute("op-1")

        assert statuses_at_update[-1] == "completed"

    @pytest.mark.asyncio
    async def test_execute_sets_backup_files_on_success(self):
        op = make_operation()
        files = ("/etc/nginx.bak.ikctl",)
        uc, op_repo, *_ = make_use_case(
            operation=op, server=make_server(), kit=make_kit(), credential=make_credential(),
            executor_result=("done\n", files),
        )

        snapshots = []

        async def capture(operation):
            snapshots.append(operation.backup_files)

        op_repo.update.side_effect = capture

        await uc.execute("op-1")

        assert snapshots[-1] == files

    @pytest.mark.asyncio
    async def test_execute_appends_output_on_success(self):
        op = make_operation()
        uc, op_repo, *_ = make_use_case(
            operation=op, server=make_server(), kit=make_kit(), credential=make_credential(),
            executor_result=("hello output\n", ()),
        )

        outputs = []

        async def capture(operation):
            outputs.append(operation.output)

        op_repo.update.side_effect = capture

        await uc.execute("op-1")

        assert "hello output" in outputs[-1]

    @pytest.mark.asyncio
    async def test_execute_publishes_completed_event_after_update(self):
        op = make_operation()
        uc, op_repo, _, _, _, _, event_bus = make_use_case(
            operation=op, server=make_server(), kit=make_kit(), credential=make_credential()
        )

        call_order = []
        op_repo.update.side_effect = lambda *a, **kw: call_order.append("update")
        event_bus.publish.side_effect = lambda *a, **kw: call_order.append("publish")

        await uc.execute("op-1")

        assert call_order[-2:] == ["update", "publish"]


class TestExecuteOperationFailure:
    """Casos de fallo en la ejecución de una operación."""

    @pytest.mark.asyncio
    async def test_execute_fails_operation_on_executor_error(self):
        op = make_operation()
        uc, op_repo, *_ = make_use_case(
            operation=op, server=make_server(), kit=make_kit(), credential=make_credential(),
            executor_raises=RuntimeError("SSH timeout"),
        )

        statuses_at_update = []

        async def capture(operation):
            statuses_at_update.append(operation.status.value)

        op_repo.update.side_effect = capture

        await uc.execute("op-1")

        assert statuses_at_update[-1] == "failed"

    @pytest.mark.asyncio
    async def test_execute_appends_error_message_on_failure(self):
        op = make_operation()
        uc, op_repo, *_ = make_use_case(
            operation=op, server=make_server(), kit=make_kit(), credential=make_credential(),
            executor_raises=RuntimeError("SSH timeout"),
        )

        outputs_at_update = []

        async def capture(operation):
            outputs_at_update.append(operation.output)

        op_repo.update.side_effect = capture

        await uc.execute("op-1")

        assert "SSH timeout" in outputs_at_update[-1]

    @pytest.mark.asyncio
    async def test_execute_publishes_failed_event_on_error(self):
        op = make_operation()
        uc, _, _, _, _, _, event_bus = make_use_case(
            operation=op, server=make_server(), kit=make_kit(), credential=make_credential(),
            executor_raises=RuntimeError("SSH timeout"),
        )

        await uc.execute("op-1")

        event_bus.publish.assert_awaited_once()
        published = event_bus.publish.call_args[0][0]
        assert published.__class__.__name__ == "OperationFailed"


class TestExecuteOperationSudo:
    """Verifica que el flag sudo de la operación se propaga al executor."""

    @pytest.mark.asyncio
    async def test_execute_passes_sudo_true_to_executor(self):
        op = Operation(
            id="op-1",
            user_id="user-1",
            server_id="srv-1",
            kit_id="kit-1",
            values={},
            sudo=True,
            status=OperationStatus("pending"),
            debug_level="none",
            output="",
            backup_files=(),
            created_at=NOW,
            updated_at=NOW,
            started_at=None,
            finished_at=None,
        )
        uc, _, _, _, _, remote_executor, _ = make_use_case(
            operation=op, server=make_server(), kit=make_kit(), credential=make_credential()
        )

        await uc.execute("op-1")

        _, kwargs = remote_executor.execute.call_args
        assert kwargs["sudo"] is True

    @pytest.mark.asyncio
    async def test_execute_passes_sudo_false_to_executor(self):
        op = Operation(
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
        uc, _, _, _, _, remote_executor, _ = make_use_case(
            operation=op, server=make_server(), kit=make_kit(), credential=make_credential()
        )

        await uc.execute("op-1")

        _, kwargs = remote_executor.execute.call_args
        assert kwargs["sudo"] is False


class TestExecuteOperationValues:
    """Verifica que el executor recibe operation.values, no kit.values."""

    @pytest.mark.asyncio
    async def test_execute_passes_operation_values_to_executor(self):
        """Los valores del usuario (operation.values) deben llegar al executor,
        no los defaults del kit (kit.values)."""
        op = Operation(
            id="op-1",
            user_id="user-1",
            server_id="srv-1",
            kit_id="kit-1",
            values={"port": "9090"},   # usuario sobreescribe el default 80
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
        uc, _, _, _, _, remote_executor, _ = make_use_case(
            operation=op,
            server=make_server(),
            kit=make_kit(),          # kit.values = {"port": 80}
            credential=make_credential(),
        )

        await uc.execute("op-1")

        _, kwargs = remote_executor.execute.call_args
        assert kwargs["values"] == {"port": "9090"}

    @pytest.mark.asyncio
    async def test_execute_passes_empty_operation_values_to_executor(self):
        """Si operation.values está vacío se pasa vacío, sin caer al default del kit."""
        op = make_operation()  # values={}
        uc, _, _, _, _, remote_executor, _ = make_use_case(
            operation=op,
            server=make_server(),
            kit=make_kit(),          # kit.values = {"port": 80}
            credential=make_credential(),
        )

        await uc.execute("op-1")

        _, kwargs = remote_executor.execute.call_args
        assert kwargs["values"] == {}


class TestExecuteOperationEdgeCases:
    """Casos borde de la tarea de ejecución."""

    @pytest.mark.asyncio
    async def test_execute_no_op_if_operation_not_found(self):
        uc, op_repo, *_ = make_use_case(operation=None)

        await uc.execute("op-x")  # no debe lanzar excepción

        op_repo.update.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_execute_fails_if_server_not_found(self):
        op = make_operation()
        uc, op_repo, *_ = make_use_case(operation=op, server=None, kit=make_kit(), credential=make_credential())

        statuses_at_update = []

        async def capture(operation):
            statuses_at_update.append(operation.status.value)

        op_repo.update.side_effect = capture

        await uc.execute("op-1")

        assert statuses_at_update[-1] == "failed"

    @pytest.mark.asyncio
    async def test_execute_fails_if_kit_not_found(self):
        op = make_operation()
        uc, op_repo, *_ = make_use_case(operation=op, server=make_server(), kit=None, credential=make_credential())

        statuses_at_update = []

        async def capture(operation):
            statuses_at_update.append(operation.status.value)

        op_repo.update.side_effect = capture

        await uc.execute("op-1")

        assert statuses_at_update[-1] == "failed"

    @pytest.mark.asyncio
    async def test_execute_fails_if_credential_not_found(self):
        op = make_operation()
        uc, op_repo, *_ = make_use_case(operation=op, server=make_server(), kit=make_kit(), credential=None)

        statuses_at_update = []

        async def capture(operation):
            statuses_at_update.append(operation.status.value)

        op_repo.update.side_effect = capture

        await uc.execute("op-1")

        assert statuses_at_update[-1] == "failed"
