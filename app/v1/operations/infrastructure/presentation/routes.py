"""Routers FastAPI para el módulo operations.

Endpoints:
  POST   /api/v1/operations              — T-28: lanzar operación
  GET    /api/v1/operations              — T-29: listar operaciones paginadas
  GET    /api/v1/operations/{id}         — T-30: consultar estado
  POST   /api/v1/operations/{id}/cancel  — T-31: cancelar operación
  POST   /api/v1/operations/{id}/restore — T-32: restaurar backup
  POST   /api/v1/operations/{id}/retry   — T-33: reintentar operación
"""
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, Query, Response, status

from app.v1.operations.application.commands.cancel_operation import CancelOperation
from app.v1.operations.application.commands.launch_operation import LaunchOperation
from app.v1.operations.application.commands.restore_operation_backup import (
    RestoreOperationBackup,
)
from app.v1.operations.application.commands.retry_operation import RetryOperation
from app.v1.operations.application.dtos.operation_dtos import (
    OperationListResult,
    OperationResult,
    RestoreResult,
)
from app.v1.operations.application.queries.get_operation import GetOperation
from app.v1.operations.application.queries.list_operations import ListOperations
from app.v1.operations.infrastructure.presentation.deps import (
    get_cancel_operation_uc,
    get_current_user_id,
    get_get_operation_uc,
    get_launch_operation_uc,
    get_list_operations_uc,
    get_restore_operation_backup_uc,
    get_retry_operation_uc,
)
from app.v1.operations.infrastructure.presentation.schemas import (
    LaunchOperationRequest,
    OperationListResponse,
    OperationResponse,
    RestoreResponse,
)
from app.v1.shared.infrastructure.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["operations"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _to_operation_response(result: OperationResult) -> OperationResponse:
    """Convierte OperationResult DTO a OperationResponse Pydantic."""
    return OperationResponse(
        operation_id=result.operation_id,
        user_id=result.user_id,
        server_id=result.server_id,
        kit_id=result.kit_id,
        values=result.values,
        sudo=result.sudo,
        status=result.status,
        debug_level=result.debug_level,
        output=result.output,
        backup_files=list(result.backup_files),
        created_at=result.created_at,
        updated_at=result.updated_at,
        started_at=result.started_at,
        finished_at=result.finished_at,
    )


def _to_restore_response(result: RestoreResult) -> RestoreResponse:
    """Convierte RestoreResult DTO a RestoreResponse Pydantic."""
    return RestoreResponse(
        operation_id=result.operation_id,
        restored_files=list(result.restored_files),
    )


# ---------------------------------------------------------------------------
# T-28: POST /api/v1/operations — lanzar operación
# ---------------------------------------------------------------------------


@router.post(
    "/api/v1/operations",
    response_model=OperationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def launch_operation(
    body: LaunchOperationRequest,
    user_id: Annotated[str, Depends(get_current_user_id)],
    use_case: Annotated[LaunchOperation, Depends(get_launch_operation_uc)],
) -> OperationResponse:
    """Lanza una operación asíncrona ejecutando un kit en un servidor.

    Returns:
        201 OperationResponse con estado pending.

    Raises:
        422: Si el servidor está inactivo o el kit no está sincronizado.
    """
    correlation_id = str(uuid4())
    result = await use_case.execute(
        user_id=user_id,
        server_id=body.server_id,
        kit_id=body.kit_id,
        debug_level=body.debug_level,
        values=body.values,
        sudo=body.sudo,
        correlation_id=correlation_id,
    )
    logger.info(
        "operation_launched",
        user_id=user_id,
        operation_id=result.operation_id,
        server_id=body.server_id,
        kit_id=body.kit_id,
        correlation_id=correlation_id,
    )
    return _to_operation_response(result)


# ---------------------------------------------------------------------------
# T-29: GET /api/v1/operations — listar operaciones paginadas
# ---------------------------------------------------------------------------


@router.get(
    "/api/v1/operations",
    response_model=OperationListResponse,
    status_code=status.HTTP_200_OK,
)
async def list_operations(
    user_id: Annotated[str, Depends(get_current_user_id)],
    use_case: Annotated[ListOperations, Depends(get_list_operations_uc)],
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=50),
    server_id: str | None = Query(default=None),
    kit_id: str | None = Query(default=None),
    operation_status: str | None = Query(default=None, alias="status"),
) -> OperationListResponse:
    """Lista las operaciones del usuario con paginación y filtros opcionales.

    Query params:
        server_id: filtro por servidor
        kit_id: filtro por kit
        status: filtro por estado

    Returns:
        200 OperationListResponse paginada.
    """
    result: OperationListResult = await use_case.execute(
        user_id=user_id,
        page=page,
        per_page=per_page,
        server_id=server_id,
        kit_id=kit_id,
        status=operation_status,
    )
    return OperationListResponse(
        items=[_to_operation_response(op) for op in result.items],
        total=result.total,
        page=result.page,
        per_page=result.per_page,
    )


# ---------------------------------------------------------------------------
# T-30: GET /api/v1/operations/{id} — consultar estado
# ---------------------------------------------------------------------------


@router.get(
    "/api/v1/operations/{operation_id}",
    response_model=OperationResponse,
    status_code=status.HTTP_200_OK,
)
async def get_operation(
    operation_id: str,
    user_id: Annotated[str, Depends(get_current_user_id)],
    use_case: Annotated[GetOperation, Depends(get_get_operation_uc)],
) -> OperationResponse:
    """Consulta el estado de una operación.

    Returns:
        200 OperationResponse.

    Raises:
        404: Si la operación no existe o no pertenece al usuario.
    """
    result = await use_case.execute(user_id=user_id, operation_id=operation_id)
    return _to_operation_response(result)


# ---------------------------------------------------------------------------
# T-31: POST /api/v1/operations/{id}/cancel — cancelar operación
# ---------------------------------------------------------------------------


@router.post(
    "/api/v1/operations/{operation_id}/cancel",
    response_model=OperationResponse,
    status_code=status.HTTP_200_OK,
)
async def cancel_operation(
    operation_id: str,
    user_id: Annotated[str, Depends(get_current_user_id)],
    use_case: Annotated[CancelOperation, Depends(get_cancel_operation_uc)],
) -> OperationResponse:
    """Cancela una operación en estado pending o running.

    Returns:
        200 OperationResponse con nuevo estado (cancelled o cancelled_unsafe).

    Raises:
        404: Si la operación no existe o no pertenece al usuario.
        409: Si la operación está en un estado terminal y no puede cancelarse.
    """
    correlation_id = str(uuid4())
    result = await use_case.execute(
        user_id=user_id,
        operation_id=operation_id,
    )
    logger.info(
        "operation_cancelled",
        user_id=user_id,
        operation_id=operation_id,
        status=result.status,
        correlation_id=correlation_id,
    )
    return _to_operation_response(result)


# ---------------------------------------------------------------------------
# T-32: POST /api/v1/operations/{id}/restore — restaurar backup
# ---------------------------------------------------------------------------


@router.post(
    "/api/v1/operations/{operation_id}/restore",
    response_model=RestoreResponse,
    status_code=status.HTTP_200_OK,
)
async def restore_operation_backup(
    operation_id: str,
    user_id: Annotated[str, Depends(get_current_user_id)],
    use_case: Annotated[RestoreOperationBackup, Depends(get_restore_operation_backup_uc)],
) -> RestoreResponse:
    """Restaura los ficheros de backup de una operación fallida o cancelada.

    Returns:
        200 RestoreResponse con los ficheros restaurados.

    Raises:
        404: Si la operación no existe o no pertenece al usuario.
        422: Si la operación no tiene backup o no está en estado restorable.
    """
    correlation_id = str(uuid4())
    result = await use_case.execute(
        user_id=user_id,
        operation_id=operation_id,
    )
    logger.info(
        "operation_backup_restored",
        user_id=user_id,
        operation_id=operation_id,
        restored_count=len(result.restored_files),
        correlation_id=correlation_id,
    )
    return _to_restore_response(result)


# ---------------------------------------------------------------------------
# T-33: POST /api/v1/operations/{id}/retry — reintentar operación
# ---------------------------------------------------------------------------


@router.post(
    "/api/v1/operations/{operation_id}/retry",
    response_model=OperationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def retry_operation(
    operation_id: str,
    user_id: Annotated[str, Depends(get_current_user_id)],
    use_case: Annotated[RetryOperation, Depends(get_retry_operation_uc)],
) -> OperationResponse:
    """Reintenta una operación fallida o cancelada creando una nueva operación.

    La operación original permanece intacta. Se crea una nueva con estado pending.

    Returns:
        201 OperationResponse de la nueva operación con estado pending.

    Raises:
        404: Si la operación no existe o no pertenece al usuario.
        422: Si la operación no puede reintentarse (no está en failed/cancelled_unsafe).
    """
    correlation_id = str(uuid4())
    result = await use_case.execute(
        user_id=user_id,
        operation_id=operation_id,
    )
    logger.info(
        "operation_retried",
        user_id=user_id,
        original_operation_id=operation_id,
        new_operation_id=result.operation_id,
        correlation_id=correlation_id,
    )
    return _to_operation_response(result)
