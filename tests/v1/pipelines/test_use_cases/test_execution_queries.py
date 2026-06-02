"""Tests para las queries GetPipelineExecutions (T-16) y GetPipelineExecutionDetail (T-17)."""
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from app.v1.pipelines.domain.entities.pipeline import Pipeline
from app.v1.pipelines.domain.entities.pipeline_execution import PipelineExecution
from app.v1.pipelines.domain.exceptions.pipeline import PipelineNotFoundError
from app.v1.pipelines.domain.exceptions.pipeline_execution import PipelineExecutionNotFoundError
from app.v1.pipelines.domain.value_objects.pipeline_kit_config import PipelineKitConfig
from app.v1.pipelines.domain.value_objects.pipeline_status import PipelineStatus
from app.v1.pipelines.domain.value_objects.pipeline_target import PipelineTarget

NOW = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


def make_pipeline(pipeline_id: str = "pipe-1") -> Pipeline:
    return Pipeline(
        id=pipeline_id,
        user_id="user-1",
        name="Mi Pipeline",
        description=None,
        targets=[PipelineTarget(server_id="srv-1")],
        kits=[PipelineKitConfig(kit_id="kit-1")],
        created_at=NOW,
        updated_at=NOW,
    )


def make_execution(
    execution_id: str = "exec-1",
    status: str = "completed",
    operation_ids: list[str] | None = None,
) -> PipelineExecution:
    return PipelineExecution(
        id=execution_id,
        pipeline_id="pipe-1",
        user_id="user-1",
        status=PipelineStatus(status),
        operation_ids=operation_ids or ["op-1", "op-2"],
        snapshot={
            "targets": [{"server_id": "srv-1"}],
            "kits": [{"kit_id": "kit-1", "sudo": None, "debug_level": None}],
            "values": {},
            "sudo": False,
            "debug_level": "none",
        },
        created_at=NOW,
        started_at=NOW,
        finished_at=NOW,
    )


# ---------------------------------------------------------------------------
# T-16: GetPipelineExecutions
# ---------------------------------------------------------------------------

class TestGetPipelineExecutions:
    def make_use_case(
        self,
        pipeline: Pipeline | None,
        executions: list[PipelineExecution],
        total: int,
    ):
        from app.v1.pipelines.application.queries.get_pipeline_executions import (
            GetPipelineExecutions,
        )

        pipeline_repo = AsyncMock()
        execution_repo = AsyncMock()
        pipeline_repo.find_by_id.return_value = pipeline
        execution_repo.find_by_pipeline_id.return_value = (executions, total)
        return GetPipelineExecutions(
            pipeline_repository=pipeline_repo,
            execution_repository=execution_repo,
        )

    @pytest.mark.asyncio
    async def test_list_executions_returns_paginated_result(self):
        pipeline = make_pipeline()
        executions = [make_execution("exec-1"), make_execution("exec-2")]
        uc = self.make_use_case(pipeline, executions, total=2)

        result = await uc.execute(user_id="user-1", pipeline_id="pipe-1", page=1, per_page=10)

        assert result.total == 2
        assert result.page == 1
        assert len(result.items) == 2
        assert result.items[0].execution_id == "exec-1"

    @pytest.mark.asyncio
    async def test_list_executions_raises_when_pipeline_not_found(self):
        uc = self.make_use_case(None, [], total=0)

        with pytest.raises(PipelineNotFoundError):
            await uc.execute(user_id="user-1", pipeline_id="pipe-x", page=1, per_page=10)


# ---------------------------------------------------------------------------
# T-17: GetPipelineExecutionDetail
# ---------------------------------------------------------------------------

class TestGetPipelineExecutionDetail:
    def make_use_case(
        self,
        pipeline: Pipeline | None,
        execution: PipelineExecution | None,
        operations: list,
    ):
        from app.v1.pipelines.application.queries.get_pipeline_execution_detail import (
            GetPipelineExecutionDetail,
        )
        from app.v1.operations.domain.entities.operation import Operation
        from app.v1.operations.domain.value_objects.operation_status import OperationStatus

        pipeline_repo = AsyncMock()
        execution_repo = AsyncMock()
        operation_repo = AsyncMock()

        pipeline_repo.find_by_id.return_value = pipeline
        execution_repo.find_by_id.return_value = execution
        operation_repo.find_by_id_internal.side_effect = (
            lambda op_id: next((o for o in operations if o.id == op_id), None)
        )

        return GetPipelineExecutionDetail(
            pipeline_repository=pipeline_repo,
            execution_repository=execution_repo,
            operation_repository=operation_repo,
        )

    def _make_operation(self, op_id: str, server_id: str = "srv-1", status: str = "completed"):
        from app.v1.operations.domain.entities.operation import Operation
        from app.v1.operations.domain.value_objects.operation_status import OperationStatus

        return Operation(
            id=op_id,
            user_id="user-1",
            server_id=server_id,
            kit_id="kit-1",
            values={},
            sudo=False,
            status=OperationStatus(status),
            debug_level="none",
            output="ok",
            backup_files=(),
            created_at=NOW,
            updated_at=NOW,
            started_at=NOW,
            finished_at=NOW,
        )

    @pytest.mark.asyncio
    async def test_detail_returns_execution_with_operations(self):
        pipeline = make_pipeline()
        execution = make_execution(operation_ids=["op-1", "op-2"])
        ops = [
            self._make_operation("op-1", "srv-1", "completed"),
            self._make_operation("op-2", "srv-2", "failed"),
        ]
        uc = self.make_use_case(pipeline, execution, ops)

        result = await uc.execute(
            user_id="user-1", pipeline_id="pipe-1", execution_id="exec-1"
        )

        assert result.execution_id == "exec-1"
        assert result.status == "completed"
        assert len(result.operations) == 2
        assert result.operations[0].operation_id == "op-1"
        assert result.operations[1].status == "failed"

    @pytest.mark.asyncio
    async def test_detail_raises_when_pipeline_not_found(self):
        uc = self.make_use_case(None, make_execution(), [])

        with pytest.raises(PipelineNotFoundError):
            await uc.execute(user_id="user-1", pipeline_id="pipe-x", execution_id="exec-1")

    @pytest.mark.asyncio
    async def test_detail_raises_when_execution_not_found(self):
        pipeline = make_pipeline()
        uc = self.make_use_case(pipeline, None, [])

        with pytest.raises(PipelineExecutionNotFoundError):
            await uc.execute(user_id="user-1", pipeline_id="pipe-1", execution_id="exec-x")
