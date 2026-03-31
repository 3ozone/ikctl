"""Router FastAPI para el módulo servers — Credentials.

Endpoints:
    POST   /api/v1/credentials       — crear credencial (T-45)
    GET    /api/v1/credentials       — listar credenciales paginadas (T-46)
    GET    /api/v1/credentials/{id}  — obtener credencial (T-47)
    PUT    /api/v1/credentials/{id}  — actualizar credencial (T-48)
    DELETE /api/v1/credentials/{id}  — eliminar credencial (T-49)
"""
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, Query, Response, status

from app.v1.servers.application.commands.create_credential import CreateCredential
from app.v1.servers.application.commands.delete_credential import DeleteCredential
from app.v1.servers.application.commands.update_credential import UpdateCredential
from app.v1.servers.application.queries.get_credential import GetCredential
from app.v1.servers.application.queries.list_credentials import ListCredentials
from app.v1.servers.infrastructure.presentation.deps import (
    get_create_credential,
    get_current_user_id,
    get_delete_credential,
    get_get_credential,
    get_list_credentials,
    get_update_credential,
)
from app.v1.servers.infrastructure.presentation.schemas import (
    CreateCredentialRequest,
    CredentialListResponse,
    CredentialResponse,
    UpdateCredentialRequest,
)
from app.v1.shared.infrastructure.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/credentials", tags=["credentials"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_credential(
    body: CreateCredentialRequest,
    user_id: Annotated[str, Depends(get_current_user_id)],
    use_case: Annotated[CreateCredential, Depends(get_create_credential)],
) -> CredentialResponse:
    """Crea una nueva credencial de acceso para el usuario autenticado.

    Returns:
        201 CredentialResponse — sin password ni private_key.

    Raises:
        400 si el tipo o la configuración son inválidos.
    """
    correlation_id = str(uuid4())
    result = await use_case.execute(
        user_id=user_id,
        name=body.name,
        credential_type=body.type,
        username=body.username,
        password=body.password,
        private_key=body.private_key,
        correlation_id=correlation_id,
    )
    logger.info(
        "credential_created",
        user_id=user_id,
        credential_id=result.credential_id,
        credential_type=result.credential_type,
    )
    return CredentialResponse(
        credential_id=result.credential_id,
        user_id=result.user_id,
        name=result.name,
        credential_type=result.credential_type,
        username=result.username,
        created_at=result.created_at,
        updated_at=result.updated_at,
    )


@router.get("", status_code=status.HTTP_200_OK)
async def list_credentials(
    user_id: Annotated[str, Depends(get_current_user_id)],
    use_case: Annotated[ListCredentials, Depends(get_list_credentials)],
    page: Annotated[int, Query(
        ge=1, description="Número de página (1-based)")] = 1,
    per_page: Annotated[int, Query(
        ge=1, le=100, description="Elementos por página")] = 20,
) -> CredentialListResponse:
    """Lista las credenciales del usuario autenticado con paginación.

    Returns:
        200 CredentialListResponse — lista paginada sin password ni private_key.
    """
    result = await use_case.execute(user_id=user_id, page=page, per_page=per_page)
    return CredentialListResponse(
        items=[
            CredentialResponse(
                credential_id=item.credential_id,
                user_id=item.user_id,
                name=item.name,
                credential_type=item.credential_type,
                username=item.username,
                created_at=item.created_at,
                updated_at=item.updated_at,
            )
            for item in result.items
        ],
        total=result.total,
        page=result.page,
        per_page=result.per_page,
    )


@router.get("/{credential_id}", status_code=status.HTTP_200_OK)
async def get_credential(
    credential_id: str,
    user_id: Annotated[str, Depends(get_current_user_id)],
    use_case: Annotated[GetCredential, Depends(get_get_credential)],
) -> CredentialResponse:
    """Obtiene una credencial por su ID.

    Returns:
        200 CredentialResponse — sin password ni private_key.

    Raises:
        404 si la credencial no existe o no pertenece al usuario.
    """
    result = await use_case.execute(user_id=user_id, credential_id=credential_id)
    return CredentialResponse(
        credential_id=result.credential_id,
        user_id=result.user_id,
        name=result.name,
        credential_type=result.credential_type,
        username=result.username,
        created_at=result.created_at,
        updated_at=result.updated_at,
    )


@router.put("/{credential_id}", status_code=status.HTTP_200_OK)
async def update_credential(
    credential_id: str,
    body: UpdateCredentialRequest,
    user_id: Annotated[str, Depends(get_current_user_id)],
    use_case: Annotated[UpdateCredential, Depends(get_update_credential)],
) -> CredentialResponse:
    """Actualiza una credencial existente del usuario autenticado.

    Returns:
        200 CredentialResponse — sin password ni private_key.

    Raises:
        404 si la credencial no existe o no pertenece al usuario.
        403 si el usuario no tiene permiso para actualizar la credencial.
    """
    correlation_id = str(uuid4())
    result = await use_case.execute(
        user_id=user_id,
        credential_id=credential_id,
        name=body.name,
        username=body.username,
        password=body.password,
        private_key=body.private_key,
        correlation_id=correlation_id,
    )
    logger.info(
        "credential_updated",
        user_id=user_id,
        credential_id=result.credential_id,
    )
    return CredentialResponse(
        credential_id=result.credential_id,
        user_id=result.user_id,
        name=result.name,
        credential_type=result.credential_type,
        username=result.username,
        created_at=result.created_at,
        updated_at=result.updated_at,
    )


@router.delete("/{credential_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_credential(
    credential_id: str,
    user_id: Annotated[str, Depends(get_current_user_id)],
    use_case: Annotated[DeleteCredential, Depends(get_delete_credential)],
) -> Response:
    """Elimina una credencial del usuario autenticado.

    Returns:
        204 sin body.

    Raises:
        404 si la credencial no existe o no pertenece al usuario.
        409 si la credencial está en uso por algún servidor.
    """
    correlation_id = str(uuid4())
    await use_case.execute(
        user_id=user_id,
        credential_id=credential_id,
        correlation_id=correlation_id,
    )
    logger.info(
        "credential_deleted",
        user_id=user_id,
        credential_id=credential_id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
