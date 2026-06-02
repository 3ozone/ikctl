"""Routers FastAPI para el módulo kits — repositorios y kits.

Endpoints:
  Repositories:
    POST   /api/v1/repositories          — T-29: registrar repositorio
    GET    /api/v1/repositories          — T-30: listar repositorios paginados
    GET    /api/v1/repositories/{id}     — T-31: obtener repositorio
    PUT    /api/v1/repositories/{id}     — T-32: actualizar repositorio
    DELETE /api/v1/repositories/{id}     — T-33: eliminar repositorio
    POST   /api/v1/repositories/{id}/sync — T-34: sincronizar repositorio

  Kits (solo lectura):
    GET    /api/v1/kits                  — T-35: listar kits paginados
    GET    /api/v1/kits/{id}             — T-36: obtener kit
"""
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, Query, Response, status

from app.v1.kits.application.commands.delete_repository import DeleteRepository
from app.v1.kits.application.commands.register_repository import RegisterRepository
from app.v1.kits.application.commands.sync_repository import SyncRepository
from app.v1.kits.application.commands.update_repository import UpdateRepository
from app.v1.kits.application.dtos.kit_result import KitResult
from app.v1.kits.application.dtos.repository_result import RepositoryResult
from app.v1.kits.application.dtos.repository_sync_result import RepositorySyncResult
from app.v1.kits.application.queries.get_kit import GetKit
from app.v1.kits.application.queries.get_repository import GetRepository
from app.v1.kits.application.queries.list_kits import ListKits
from app.v1.kits.application.queries.list_repositories import ListRepositories
from app.v1.kits.infrastructure.presentation.deps import (
    get_current_user_id,
    get_delete_repository_uc,
    get_get_kit_uc,
    get_get_repository_uc,
    get_list_kits_uc,
    get_list_repositories_uc,
    get_register_repository_uc,
    get_sync_repository_uc,
    get_update_repository_uc,
)
from app.v1.kits.infrastructure.presentation.schemas import (
    KitListResponse,
    KitResponse,
    RegisterRepositoryRequest,
    RepositoryListResponse,
    RepositoryResponse,
    RepositorySyncResponse,
    UpdateRepositoryRequest,
)
from app.v1.shared.infrastructure.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["kits"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _to_repository_response(result: RepositoryResult) -> RepositoryResponse:
    """Convierte RepositoryResult DTO a RepositoryResponse Pydantic."""
    return RepositoryResponse(
        repository_id=result.repository_id,
        user_id=result.user_id,
        url=result.url,
        ref=result.ref,
        credential_id=result.credential_id,
        sync_status=result.sync_status,
        last_synced_at=result.last_synced_at,
        last_commit_sha=result.last_commit_sha,
        sync_error_message=result.sync_error_message,
        created_at=result.created_at,
        updated_at=result.updated_at,
    )


def _to_sync_response(result: RepositorySyncResult) -> RepositorySyncResponse:
    """Convierte RepositorySyncResult DTO a RepositorySyncResponse Pydantic."""
    return RepositorySyncResponse(
        repository_id=result.repository_id,
        sync_status=result.sync_status,
        last_commit_sha=result.last_commit_sha,
        sync_error_message=result.sync_error_message,
        kits_created=result.kits_created,
        kits_updated=result.kits_updated,
        kits_deleted=result.kits_deleted,
    )


def _to_kit_response(result: KitResult) -> KitResponse:
    """Convierte KitResult DTO a KitResponse Pydantic."""
    return KitResponse(
        kit_id=result.kit_id,
        user_id=result.user_id,
        repository_id=result.repository_id,
        path_in_repo=result.path_in_repo,
        name=result.name,
        description=result.description,
        version=result.version,
        tags=result.tags,
        values=result.values,
        debug_level=result.debug_level,
        sync_status=result.sync_status,
        last_synced_at=result.last_synced_at,
        last_commit_sha=result.last_commit_sha,
        sync_error_message=result.sync_error_message,
        created_at=result.created_at,
        updated_at=result.updated_at,
    )


# ---------------------------------------------------------------------------
# T-29: POST /api/v1/repositories — registrar repositorio
# ---------------------------------------------------------------------------


@router.post(
    "/api/v1/repositories",
    response_model=RepositoryResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register_repository(
    body: RegisterRepositoryRequest,
    user_id: Annotated[str, Depends(get_current_user_id)],
    use_case: Annotated[RegisterRepository, Depends(get_register_repository_uc)],
) -> RepositoryResponse:
    """Registra un nuevo repositorio Git como fuente de kits.

    Returns:
        201 RepositoryResponse con sync_status 'never_synced'.

    Raises:
        422: Si la credencial no es de tipo git_https o git_ssh.
    """
    correlation_id = str(uuid4())
    result = await use_case.execute(
        user_id=user_id,
        url=body.url,
        ref=body.ref,
        credential_id=body.credential_id,
        correlation_id=correlation_id,
    )
    logger.info(
        "repository_registered",
        user_id=user_id,
        repository_id=result.repository_id,
        correlation_id=correlation_id,
    )
    return _to_repository_response(result)


# ---------------------------------------------------------------------------
# T-30: GET /api/v1/repositories — listar repositorios paginados
# ---------------------------------------------------------------------------


@router.get(
    "/api/v1/repositories",
    response_model=RepositoryListResponse,
    status_code=status.HTTP_200_OK,
)
async def list_repositories(
    user_id: Annotated[str, Depends(get_current_user_id)],
    use_case: Annotated[ListRepositories, Depends(get_list_repositories_uc)],
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=50),
) -> RepositoryListResponse:
    """Lista los repositorios del usuario con paginación.

    Returns:
        200 RepositoryListResponse paginada (solo no eliminados).
    """
    result = await use_case.execute(user_id=user_id, page=page, per_page=per_page)
    return RepositoryListResponse(
        items=[_to_repository_response(r) for r in result.items],
        total=result.total,
        page=result.page,
        per_page=result.per_page,
    )


# ---------------------------------------------------------------------------
# T-31: GET /api/v1/repositories/{id} — obtener repositorio
# ---------------------------------------------------------------------------


@router.get(
    "/api/v1/repositories/{repository_id}",
    response_model=RepositoryResponse,
    status_code=status.HTTP_200_OK,
)
async def get_repository(
    repository_id: str,
    user_id: Annotated[str, Depends(get_current_user_id)],
    use_case: Annotated[GetRepository, Depends(get_get_repository_uc)],
) -> RepositoryResponse:
    """Obtiene un repositorio por ID.

    Returns:
        200 RepositoryResponse.

    Raises:
        404: Si el repositorio no existe o no pertenece al usuario.
    """
    result = await use_case.execute(user_id=user_id, repository_id=repository_id)
    return _to_repository_response(result)


# ---------------------------------------------------------------------------
# T-32: PUT /api/v1/repositories/{id} — actualizar repositorio
# ---------------------------------------------------------------------------


@router.put(
    "/api/v1/repositories/{repository_id}",
    response_model=RepositoryResponse,
    status_code=status.HTTP_200_OK,
)
async def update_repository(
    repository_id: str,
    body: UpdateRepositoryRequest,
    user_id: Annotated[str, Depends(get_current_user_id)],
    use_case: Annotated[UpdateRepository, Depends(get_update_repository_uc)],
) -> RepositoryResponse:
    """Actualiza URL, ref y credencial de un repositorio.

    Returns:
        200 RepositoryResponse actualizado.

    Raises:
        404: Si el repositorio no existe o no pertenece al usuario.
        422: Si la credencial no es de tipo git_https o git_ssh.
    """
    correlation_id = str(uuid4())
    result = await use_case.execute(
        user_id=user_id,
        repository_id=repository_id,
        url=body.url,
        ref=body.ref,
        credential_id=body.credential_id,
        correlation_id=correlation_id,
    )
    logger.info(
        "repository_updated",
        user_id=user_id,
        repository_id=repository_id,
        correlation_id=correlation_id,
    )
    return _to_repository_response(result)


# ---------------------------------------------------------------------------
# T-33: DELETE /api/v1/repositories/{id} — eliminar repositorio
# ---------------------------------------------------------------------------


@router.delete(
    "/api/v1/repositories/{repository_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_repository(
    repository_id: str,
    user_id: Annotated[str, Depends(get_current_user_id)],
    use_case: Annotated[DeleteRepository, Depends(get_delete_repository_uc)],
) -> Response:
    """Elimina físicamente un repositorio y todos sus kits.

    Returns:
        204 No Content.

    Raises:
        404: Si el repositorio no existe o no pertenece al usuario.
        409: Si el repositorio tiene kits referenciados en pipelines u operaciones.
    """
    correlation_id = str(uuid4())
    await use_case.execute(
        user_id=user_id,
        repository_id=repository_id,
        correlation_id=correlation_id,
    )
    logger.info(
        "repository_deleted",
        user_id=user_id,
        repository_id=repository_id,
        correlation_id=correlation_id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# T-34: POST /api/v1/repositories/{id}/sync — sincronizar repositorio
# ---------------------------------------------------------------------------


@router.post(
    "/api/v1/repositories/{repository_id}/sync",
    response_model=RepositorySyncResponse,
    status_code=status.HTTP_200_OK,
)
async def sync_repository(
    repository_id: str,
    user_id: Annotated[str, Depends(get_current_user_id)],
    use_case: Annotated[SyncRepository, Depends(get_sync_repository_uc)],
) -> RepositorySyncResponse:
    """Sincroniza un repositorio desde Git y reconcilia sus kits.

    Siempre devuelve 200. Si el sync falla, sync_status es 'sync_error'
    con el mensaje de error — nunca 500.

    Returns:
        200 RepositorySyncResponse con contadores kits_created/updated/deleted.

    Raises:
        404: Si el repositorio no existe o no pertenece al usuario.
    """
    correlation_id = str(uuid4())
    result = await use_case.execute(
        user_id=user_id,
        repository_id=repository_id,
        correlation_id=correlation_id,
    )
    logger.info(
        "repository_synced",
        user_id=user_id,
        repository_id=repository_id,
        sync_status=result.sync_status,
        kits_created=result.kits_created,
        kits_updated=result.kits_updated,
        kits_deleted=result.kits_deleted,
        correlation_id=correlation_id,
    )
    return _to_sync_response(result)


# ---------------------------------------------------------------------------
# T-35: GET /api/v1/kits — listar kits paginados
# ---------------------------------------------------------------------------


@router.get(
    "/api/v1/kits",
    response_model=KitListResponse,
    status_code=status.HTTP_200_OK,
)
async def list_kits(
    user_id: Annotated[str, Depends(get_current_user_id)],
    use_case: Annotated[ListKits, Depends(get_list_kits_uc)],
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=50),
    tags: list[str] = Query(default=[]),
    repository_id: str | None = Query(default=None),
) -> KitListResponse:
    """Lista los kits del usuario con paginación y filtros opcionales.

    Query params:
        tags: filtro AND por tags (multi-valor)
        repository_id: filtro por repositorio

    Returns:
        200 KitListResponse paginada (solo kits no eliminados).
    """
    result = await use_case.execute(
        user_id=user_id,
        page=page,
        per_page=per_page,
        tags_filter=tags if tags else None,
        repository_id_filter=repository_id,
    )
    return KitListResponse(
        items=[_to_kit_response(k) for k in result.items],
        total=result.total,
        page=result.page,
        per_page=result.per_page,
    )


# ---------------------------------------------------------------------------
# T-36: GET /api/v1/kits/{id} — obtener kit
# ---------------------------------------------------------------------------


@router.get(
    "/api/v1/kits/{kit_id}",
    response_model=KitResponse,
    status_code=status.HTTP_200_OK,
)
async def get_kit(
    kit_id: str,
    user_id: Annotated[str, Depends(get_current_user_id)],
    use_case: Annotated[GetKit, Depends(get_get_kit_uc)],
) -> KitResponse:
    """Obtiene un kit por ID.

    Returns:
        200 KitResponse.

    Raises:
        404: Si el kit no existe o no pertenece al usuario.
    """
    result = await use_case.execute(user_id=user_id, kit_id=kit_id)
    return _to_kit_response(result)
