"""Router FastAPI para el módulo servers — Groups.

Endpoints:
    POST   /api/v1/groups           — crear grupo (T-58)
    GET    /api/v1/groups           — listar grupos paginados (T-59)
    GET    /api/v1/groups/{id}      — obtener grupo (T-60)
    PUT    /api/v1/groups/{id}      — actualizar grupo (T-61)
    DELETE /api/v1/groups/{id}      — eliminar grupo (T-62)
"""
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, Query, status

from app.v1.servers.application.commands.create_group import CreateGroup
from app.v1.servers.application.commands.delete_group import DeleteGroup
from app.v1.servers.application.commands.update_group import UpdateGroup
from app.v1.servers.application.queries.get_group import GetGroup
from app.v1.servers.application.queries.list_groups import ListGroups
from app.v1.servers.infrastructure.presentation.deps import (
    get_create_group,
    get_current_user_id,
    get_delete_group,
    get_get_group,
    get_list_groups,
    get_update_group,
)
from app.v1.servers.infrastructure.presentation.schemas import (
    CreateGroupRequest,
    GroupListResponse,
    GroupResponse,
    UpdateGroupRequest,
)
from app.v1.shared.infrastructure.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/groups", tags=["groups"])


# ---------------------------------------------------------------------------
# Helper para construir GroupResponse desde GroupResult
# ---------------------------------------------------------------------------


def _to_group_response(result) -> GroupResponse:
    """Construye un GroupResponse a partir de un GroupResult."""
    return GroupResponse(
        group_id=result.group_id,
        user_id=result.user_id,
        name=result.name,
        description=result.description,
        server_ids=result.server_ids,
        created_at=result.created_at,
        updated_at=result.updated_at,
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_group(
    body: CreateGroupRequest,
    user_id: Annotated[str, Depends(get_current_user_id)],
    use_case: Annotated[CreateGroup, Depends(get_create_group)],
) -> GroupResponse:
    """Crea un nuevo grupo de servidores.

    Returns:
        201 GroupResponse con los datos del grupo creado.

    Raises:
        404 si algún server_id no existe o no pertenece al usuario.
        422 si algún server_id es de tipo local (RNF-16).
    """
    correlation_id = str(uuid4())
    result = await use_case.execute(
        user_id=user_id,
        name=body.name,
        description=body.description,
        server_ids=body.server_ids,
        correlation_id=correlation_id,
    )
    logger.info(
        "group_created",
        user_id=user_id,
        group_id=result.group_id,
        server_count=len(result.server_ids),
    )
    return _to_group_response(result)


@router.get("", status_code=status.HTTP_200_OK)
async def list_groups(
    user_id: Annotated[str, Depends(get_current_user_id)],
    use_case: Annotated[ListGroups, Depends(get_list_groups)],
    page: Annotated[int, Query(
        ge=1, description="Número de página (1-based)")] = 1,
    per_page: Annotated[int, Query(
        ge=1, le=100, description="Elementos por página")] = 20,
) -> GroupListResponse:
    """Lista los grupos del usuario autenticado con paginación.

    Returns:
        200 GroupListResponse — lista paginada de grupos.
    """
    result = await use_case.execute(user_id=user_id, page=page, per_page=per_page)
    return GroupListResponse(
        items=[_to_group_response(item) for item in result.items],
        total=result.total,
        page=result.page,
        per_page=result.per_page,
    )


@router.get("/{group_id}", status_code=status.HTTP_200_OK)
async def get_group(
    group_id: str,
    user_id: Annotated[str, Depends(get_current_user_id)],
    use_case: Annotated[GetGroup, Depends(get_get_group)],
) -> GroupResponse:
    """Obtiene un grupo por su ID.

    Returns:
        200 GroupResponse.

    Raises:
        404 si el grupo no existe o no pertenece al usuario.
    """
    result = await use_case.execute(user_id=user_id, group_id=group_id)
    return _to_group_response(result)


@router.put("/{group_id}", status_code=status.HTTP_200_OK)
async def update_group(
    group_id: str,
    body: UpdateGroupRequest,
    user_id: Annotated[str, Depends(get_current_user_id)],
    use_case: Annotated[UpdateGroup, Depends(get_update_group)],
) -> GroupResponse:
    """Actualiza un grupo de servidores.

    Returns:
        200 GroupResponse con los datos actualizados.

    Raises:
        404 si el grupo no existe o no pertenece al usuario.
    """
    correlation_id = str(uuid4())
    result = await use_case.execute(
        user_id=user_id,
        group_id=group_id,
        name=body.name,
        description=body.description,
        server_ids=body.server_ids or [],
        correlation_id=correlation_id,
    )
    logger.info(
        "group_updated",
        user_id=user_id,
        group_id=result.group_id,
    )
    return _to_group_response(result)


@router.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_group(
    group_id: str,
    user_id: Annotated[str, Depends(get_current_user_id)],
    use_case: Annotated[DeleteGroup, Depends(get_delete_group)],
) -> None:
    """Elimina un grupo de servidores.

    Returns:
        204 sin body al eliminar correctamente.

    Raises:
        404 si el grupo no existe o no pertenece al usuario.
        409 si el grupo tiene pipelines activos (RN-19).
    """
    correlation_id = str(uuid4())
    await use_case.execute(
        user_id=user_id,
        group_id=group_id,
        correlation_id=correlation_id,
    )
    logger.info(
        "group_deleted",
        user_id=user_id,
        group_id=group_id,
    )
