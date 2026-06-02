"""Dependencias FastAPI para los endpoints del módulo operations.

Patrón:
- Singletons (event_bus, encryption_key, session_factory) → leídos de request.app.state
- Repositorios (scoped) → construidos a partir de la AsyncSession del request
- Use cases → construidos a partir de repositorios scoped + TaskQueue
- ExecuteOperation task → usa session_factory para crear sesión propia en background
"""
from collections.abc import AsyncGenerator
from typing import Annotated, Any, Callable

from fastapi import BackgroundTasks, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.v1.operations.application.commands.cancel_operation import CancelOperation
from app.v1.operations.application.commands.launch_batch_operation import (
    LaunchBatchOperation,
)
from app.v1.operations.application.commands.launch_operation import LaunchOperation
from app.v1.operations.application.commands.restore_operation_backup import (
    RestoreOperationBackup,
)
from app.v1.operations.application.commands.retry_operation import RetryOperation
from app.v1.operations.application.queries.get_operation import GetOperation
from app.v1.operations.application.queries.list_operations import ListOperations
from app.v1.operations.infrastructure.adapters.credential_read_adapter import (
    CredentialReadAdapter,
)
from app.v1.operations.infrastructure.adapters.fastapi_task_queue import (
    FastAPITaskQueue,
)
from app.v1.operations.infrastructure.adapters.kit_read_adapter import KitReadAdapter
from app.v1.operations.infrastructure.adapters.server_read_adapter import (
    ServerReadAdapter,
)
from app.v1.operations.infrastructure.repositories.file_cache_repository import (
    SQLAlchemyFileCacheRepository,
)
from app.v1.operations.infrastructure.repositories.operation_repository import (
    SQLAlchemyOperationRepository,
)
from app.v1.shared.infrastructure.database import get_db_session as _get_db_session


# ---------------------------------------------------------------------------
# Singletons — leídos de app.state (depositados por main.py en lifespan)
# ---------------------------------------------------------------------------


def get_event_bus(request: Request):
    """Retorna el EventBus singleton depositado en app.state por main.py."""
    return request.app.state.event_bus


def get_current_user_id(request: Request) -> str:
    """Retorna el user_id inyectado por AuthenticationMiddleware en request.state."""
    return request.state.user_id


def get_encryption_key(request: Request) -> str:
    """Retorna la clave de cifrado AES-256 desde app.state."""
    return request.app.state.encryption_key


def get_execute_operation_fn(request: Request) -> Callable:
    """Retorna la función real ExecuteOperation.execute desde app.state.

    Depositada en lifespan por main.py. Si no está disponible, usa el placeholder.
    """
    return getattr(request.app.state, "execute_operation_fn", None)


def get_restore_operation_fn(request: Request) -> Callable:
    """Retorna la función real RestoreBackupTask.execute desde app.state.

    Depositada en lifespan por main.py. Si no está disponible, usa el placeholder.
    """
    return getattr(request.app.state, "restore_operation_fn", None)


# ---------------------------------------------------------------------------
# Session scoped
# ---------------------------------------------------------------------------


async def get_db_session(request: Request) -> AsyncGenerator[AsyncSession, None]:
    """Dependencia FastAPI — proporciona una AsyncSession scoped al request."""
    async for session in _get_db_session(request.app.state.session_factory):
        yield session


# ---------------------------------------------------------------------------
# Repositories scoped
# ---------------------------------------------------------------------------


def get_operation_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> SQLAlchemyOperationRepository:
    """Construye SQLAlchemyOperationRepository con la sesión scoped al request."""
    return SQLAlchemyOperationRepository(session)


def get_file_cache_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> SQLAlchemyFileCacheRepository:
    """Construye SQLAlchemyFileCacheRepository con la sesión scoped al request."""
    return SQLAlchemyFileCacheRepository(session)


def get_server_read_adapter(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ServerReadAdapter:
    """Construye ServerReadAdapter (cross-módulo, sin ownership) con la sesión scoped."""
    return ServerReadAdapter(session)


def get_kit_read_adapter(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> KitReadAdapter:
    """Construye KitReadAdapter (cross-módulo, sin ownership) con la sesión scoped."""
    return KitReadAdapter(session)


# ---------------------------------------------------------------------------
# TaskQueue — FastAPI BackgroundTasks (v1)
# ---------------------------------------------------------------------------


def get_task_queue(background_tasks: BackgroundTasks) -> FastAPITaskQueue:
    """Construye FastAPITaskQueue con el BackgroundTasks del request."""
    return FastAPITaskQueue(background_tasks)


# ---------------------------------------------------------------------------
# Use Cases — Commands
# ---------------------------------------------------------------------------


def get_launch_operation_uc(
    request: Request,
    operation_repo: Annotated[
        SQLAlchemyOperationRepository, Depends(get_operation_repository)
    ],
    server_repo: Annotated[ServerReadAdapter, Depends(get_server_read_adapter)],
    kit_repo: Annotated[KitReadAdapter, Depends(get_kit_read_adapter)],
    task_queue: Annotated[FastAPITaskQueue, Depends(get_task_queue)],
    event_bus=Depends(get_event_bus),
    execute_fn: Annotated[Callable, Depends(get_execute_operation_fn)] = None,
) -> LaunchOperation:
    """Construye el use case LaunchOperation con sus dependencias."""
    return LaunchOperation(
        operation_repository=operation_repo,
        server_repository=server_repo,
        kit_repository=kit_repo,
        task_queue=task_queue,
        event_bus=event_bus,
        execute_fn=execute_fn,
    )


def get_launch_batch_operation_uc(
    request: Request,
    operation_repo: Annotated[
        SQLAlchemyOperationRepository, Depends(get_operation_repository)
    ],
    server_repo: Annotated[ServerReadAdapter, Depends(get_server_read_adapter)],
    kit_repo: Annotated[KitReadAdapter, Depends(get_kit_read_adapter)],
    task_queue: Annotated[FastAPITaskQueue, Depends(get_task_queue)],
    event_bus=Depends(get_event_bus),
    execute_fn: Annotated[Callable, Depends(get_execute_operation_fn)] = None,
) -> LaunchBatchOperation:
    """Construye el use case LaunchBatchOperation con sus dependencias."""
    return LaunchBatchOperation(
        operation_repository=operation_repo,
        server_repository=server_repo,
        kit_repository=kit_repo,
        task_queue=task_queue,
        event_bus=event_bus,
        execute_fn=execute_fn,
    )


def get_cancel_operation_uc(
    operation_repo: Annotated[
        SQLAlchemyOperationRepository, Depends(get_operation_repository)
    ],
    event_bus=Depends(get_event_bus),
) -> CancelOperation:
    """Construye el use case CancelOperation con sus dependencias."""
    return CancelOperation(
        operation_repository=operation_repo,
        event_bus=event_bus,
    )


def get_restore_operation_backup_uc(
    operation_repo: Annotated[
        SQLAlchemyOperationRepository, Depends(get_operation_repository)
    ],
    task_queue: Annotated[FastAPITaskQueue, Depends(get_task_queue)],
    restore_fn: Annotated[Callable, Depends(get_restore_operation_fn)] = None,
) -> RestoreOperationBackup:
    """Construye el use case RestoreOperationBackup con sus dependencias."""
    return RestoreOperationBackup(
        operation_repository=operation_repo,
        task_queue=task_queue,
        restore_fn=restore_fn,
    )


def get_retry_operation_uc(
    request: Request,
    operation_repo: Annotated[
        SQLAlchemyOperationRepository, Depends(get_operation_repository)
    ],
    task_queue: Annotated[FastAPITaskQueue, Depends(get_task_queue)],
    event_bus=Depends(get_event_bus),
    execute_fn: Annotated[Callable, Depends(get_execute_operation_fn)] = None,
) -> RetryOperation:
    """Construye el use case RetryOperation con sus dependencias."""
    return RetryOperation(
        operation_repository=operation_repo,
        task_queue=task_queue,
        event_bus=event_bus,
        execute_fn=execute_fn,
    )


# ---------------------------------------------------------------------------
# Use Cases — Queries
# ---------------------------------------------------------------------------


def get_get_operation_uc(
    operation_repo: Annotated[
        SQLAlchemyOperationRepository, Depends(get_operation_repository)
    ],
) -> GetOperation:
    """Construye el use case GetOperation con sus dependencias."""
    return GetOperation(operation_repository=operation_repo)


def get_list_operations_uc(
    operation_repo: Annotated[
        SQLAlchemyOperationRepository, Depends(get_operation_repository)
    ],
) -> ListOperations:
    """Construye el use case ListOperations con sus dependencias."""
    return ListOperations(operation_repository=operation_repo)
