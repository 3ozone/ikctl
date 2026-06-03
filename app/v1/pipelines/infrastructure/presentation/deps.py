"""Dependencias FastAPI para los endpoints del módulo pipelines.

Patrón:
- Singletons (event_bus, session_factory) → leídos de request.app.state
- Repositorios (scoped) → construidos a partir de la AsyncSession del request
- Use cases → construidos a partir de repositorios scoped + TaskQueue + Adapteres
- ExecutePipelineOperations → usa session_factory para crear sesión propia en background
"""
from collections.abc import AsyncGenerator
from typing import Annotated, Callable

from fastapi import BackgroundTasks, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.v1.kits.infrastructure.repositories.kit_repository import SQLAlchemyKitRepository
from app.v1.operations.infrastructure.adapters.kit_read_adapter import (
    KitReadAdapter as OperationsKitReadAdapter,
)
from app.v1.operations.infrastructure.adapters.fastapi_task_queue import FastAPITaskQueue
from app.v1.operations.application.commands.launch_operation import LaunchOperation
from app.v1.operations.infrastructure.repositories.operation_repository import (
    SQLAlchemyOperationRepository,
)
from app.v1.pipelines.application.commands.create_pipeline import CreatePipeline
from app.v1.pipelines.application.commands.delete_pipeline import DeletePipeline
from app.v1.pipelines.application.commands.launch_pipeline import LaunchPipeline
from app.v1.pipelines.application.commands.update_pipeline import UpdatePipeline
from app.v1.pipelines.application.queries.get_pipeline import GetPipeline
from app.v1.pipelines.application.queries.get_pipeline_execution_detail import (
    GetPipelineExecutionDetail,
)
from app.v1.pipelines.application.queries.get_pipeline_executions import GetPipelineExecutions
from app.v1.pipelines.application.queries.list_pipelines import ListPipelines
from app.v1.pipelines.infrastructure.adapters.kit_read_adapter import KitReadAdapter
from app.v1.pipelines.infrastructure.adapters.operation_launcher_adapter import (
    OperationLauncherAdapter,
)
from app.v1.pipelines.infrastructure.adapters.operation_read_adapter import OperationReadAdapter
from app.v1.pipelines.infrastructure.adapters.server_read_adapter import ServerReadAdapter
from app.v1.pipelines.infrastructure.repositories.pipeline_execution_repository import (
    SQLAlchemyPipelineExecutionRepository,
)
from app.v1.pipelines.infrastructure.repositories.pipeline_repository import (
    SQLAlchemyPipelineRepository,
)
from app.v1.servers.infrastructure.repositories.server_repository import (
    SQLAlchemyServerRepository,
)
from app.v1.shared.infrastructure.database import get_db_session as _get_db_session


# ---------------------------------------------------------------------------
# Singletons — leídos de app.state (depositados por main.py en lifespan)
# ---------------------------------------------------------------------------


def get_current_user_id(request: Request) -> str:
    """Retorna el user_id inyectado por AuthenticationMiddleware en request.state."""
    return request.state.user_id


def get_execute_pipeline_fn(request: Request) -> Callable:
    """Retorna la función real ExecutePipelineOperations.execute desde app.state."""
    return getattr(request.app.state, "execute_pipeline_fn", None)


def get_event_bus(request: Request):
    return request.app.state.event_bus


def get_execute_operation_fn(request: Request) -> Callable:
    return getattr(request.app.state, "execute_operation_fn", None)


# ---------------------------------------------------------------------------
# Session scoped
# ---------------------------------------------------------------------------


async def get_db_session(request: Request) -> AsyncGenerator[AsyncSession, None]:
    """Dependencia FastAPI — proporciona una AsyncSession scoped al request."""
    async for session in _get_db_session(request.app.state.session_factory):
        yield session


# ---------------------------------------------------------------------------
# Repositories scoped — pipelines
# ---------------------------------------------------------------------------


def get_pipeline_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> SQLAlchemyPipelineRepository:
    return SQLAlchemyPipelineRepository(session)


def get_pipeline_execution_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> SQLAlchemyPipelineExecutionRepository:
    return SQLAlchemyPipelineExecutionRepository(session)


# ---------------------------------------------------------------------------
# Cross-module read adapters
# ---------------------------------------------------------------------------


def get_server_read_adapter(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ServerReadAdapter:
    return ServerReadAdapter(session)


def get_kit_read_adapter(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> KitReadAdapter:
    return KitReadAdapter(session)


def get_operation_read_adapter(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> OperationReadAdapter:
    return OperationReadAdapter(session)


def get_operation_repository_scoped(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> SQLAlchemyOperationRepository:
    return SQLAlchemyOperationRepository(session)


def get_kit_read_adapter_operations(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> OperationsKitReadAdapter:
    return OperationsKitReadAdapter(session)


# ---------------------------------------------------------------------------
# TaskQueue — FastAPI BackgroundTasks (v1)
# ---------------------------------------------------------------------------


def get_task_queue(background_tasks: BackgroundTasks) -> FastAPITaskQueue:
    """Construye FastAPITaskQueue con el BackgroundTasks del request."""
    return FastAPITaskQueue(background_tasks)


# ---------------------------------------------------------------------------
# OperationLauncher adapter — envuelve LaunchOperation
# ---------------------------------------------------------------------------


def get_operation_launcher(
    request: Request,
    task_queue=Depends(get_task_queue),
    operation_repo: Annotated[
        SQLAlchemyOperationRepository, Depends(get_operation_repository_scoped)
    ] = None,
    server_repo: Annotated[ServerReadAdapter, Depends(get_server_read_adapter)] = None,
    kit_repo: Annotated[OperationsKitReadAdapter, Depends(get_kit_read_adapter_operations)] = None,
    event_bus=Depends(get_event_bus),
    execute_fn=Depends(get_execute_operation_fn),
) -> OperationLauncherAdapter:
    """Construye OperationLauncherAdapter envolviendo LaunchOperation."""
    launch_op = LaunchOperation(
        operation_repository=operation_repo,
        server_repository=server_repo,
        kit_repository=kit_repo,
        task_queue=task_queue,
        event_bus=event_bus,
        execute_fn=execute_fn,
    )
    return OperationLauncherAdapter(launch_operation=launch_op)


# ---------------------------------------------------------------------------
# Use Cases — Commands
# ---------------------------------------------------------------------------


def get_create_pipeline_uc(
    pipeline_repo: Annotated[SQLAlchemyPipelineRepository, Depends(get_pipeline_repository)],
    server_repo: Annotated[ServerReadAdapter, Depends(get_server_read_adapter)],
) -> CreatePipeline:
    return CreatePipeline(
        pipeline_repository=pipeline_repo,
        server_repository=server_repo,
    )


def get_update_pipeline_uc(
    pipeline_repo: Annotated[SQLAlchemyPipelineRepository, Depends(get_pipeline_repository)],
    execution_repo: Annotated[
        SQLAlchemyPipelineExecutionRepository,
        Depends(get_pipeline_execution_repository),
    ],
    server_repo: Annotated[ServerReadAdapter, Depends(get_server_read_adapter)],
) -> UpdatePipeline:
    return UpdatePipeline(
        pipeline_repository=pipeline_repo,
        execution_repository=execution_repo,
        server_repository=server_repo,
    )


def get_delete_pipeline_uc(
    pipeline_repo: Annotated[SQLAlchemyPipelineRepository, Depends(get_pipeline_repository)],
) -> DeletePipeline:
    return DeletePipeline(
        pipeline_repository=pipeline_repo,
    )


def get_launch_pipeline_uc(
    pipeline_repo: Annotated[SQLAlchemyPipelineRepository, Depends(get_pipeline_repository)],
    execution_repo: Annotated[
        SQLAlchemyPipelineExecutionRepository,
        Depends(get_pipeline_execution_repository),
    ],
    kit_repo: Annotated[KitReadAdapter, Depends(get_kit_read_adapter)],
    task_queue=Depends(get_task_queue),
    execute_fn=Depends(get_execute_pipeline_fn),
) -> LaunchPipeline:
    return LaunchPipeline(
        pipeline_repository=pipeline_repo,
        execution_repository=execution_repo,
        kit_repository=kit_repo,
        task_queue=task_queue,
        execute_fn=execute_fn,
    )


# ---------------------------------------------------------------------------
# Use Cases — Queries
# ---------------------------------------------------------------------------


def get_get_pipeline_uc(
    pipeline_repo: Annotated[SQLAlchemyPipelineRepository, Depends(get_pipeline_repository)],
) -> GetPipeline:
    return GetPipeline(pipeline_repository=pipeline_repo)


def get_list_pipelines_uc(
    pipeline_repo: Annotated[SQLAlchemyPipelineRepository, Depends(get_pipeline_repository)],
) -> ListPipelines:
    return ListPipelines(pipeline_repository=pipeline_repo)


def get_get_pipeline_executions_uc(
    pipeline_repo: Annotated[SQLAlchemyPipelineRepository, Depends(get_pipeline_repository)],
    execution_repo: Annotated[
        SQLAlchemyPipelineExecutionRepository,
        Depends(get_pipeline_execution_repository),
    ],
) -> GetPipelineExecutions:
    return GetPipelineExecutions(
        pipeline_repository=pipeline_repo,
        execution_repository=execution_repo,
    )


def get_get_pipeline_execution_detail_uc(
    execution_repo: Annotated[
        SQLAlchemyPipelineExecutionRepository,
        Depends(get_pipeline_execution_repository),
    ],
    operation_read_adapter: Annotated[OperationReadAdapter, Depends(get_operation_read_adapter)],
) -> GetPipelineExecutionDetail:
    return GetPipelineExecutionDetail(
        execution_repository=execution_repo,
        operation_repository=operation_read_adapter,
    )