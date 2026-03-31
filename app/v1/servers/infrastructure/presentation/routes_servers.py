"""Router FastAPI para el módulo servers — Servers.

Endpoints:
    POST   /api/v1/servers           — registrar servidor remoto o local (T-50)
    GET    /api/v1/servers           — listar servidores paginados (T-51)
    GET    /api/v1/servers/{id}      — obtener servidor (T-52)
    PUT    /api/v1/servers/{id}      — actualizar servidor (T-53)
    DELETE /api/v1/servers/{id}      — eliminar servidor (T-54)
    POST   /api/v1/servers/{id}/toggle   — habilitar/deshabilitar (T-55)
    GET    /api/v1/servers/{id}/health   — health check SSH (T-56)
    POST   /api/v1/servers/{id}/command  — ejecutar comando ad-hoc (T-57)
"""
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, Query, status

from app.v1.servers.application.commands.register_local_server import RegisterLocalServer
from app.v1.servers.application.commands.register_server import RegisterServer
from app.v1.servers.application.queries.get_server import GetServer
from app.v1.servers.application.queries.list_servers import ListServers
from app.v1.servers.infrastructure.presentation.deps import (
    get_current_user_id,
    get_current_user_role,
    get_get_server,
    get_list_servers,
    get_register_local_server,
    get_register_server,
)
from app.v1.servers.infrastructure.presentation.schemas import (
    RegisterLocalServerRequest,
    RegisterServerRequest,
    ServerListResponse,
    ServerResponse,
)
from app.v1.shared.infrastructure.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/servers", tags=["servers"])


# ---------------------------------------------------------------------------
# Schemas internos para el discriminador
# ---------------------------------------------------------------------------


class _CreateServerBody(RegisterServerRequest):
    """Extiende RegisterServerRequest añadiendo el campo discriminador `type`."""

    type: str = "remote"


class _CreateLocalServerBody(RegisterLocalServerRequest):
    """Extiende RegisterLocalServerRequest añadiendo el campo discriminador `type`."""

    type: str = "local"


# ---------------------------------------------------------------------------
# Helper para construir ServerResponse desde ServerResult
# ---------------------------------------------------------------------------


def _to_server_response(result) -> ServerResponse:
    return ServerResponse(
        server_id=result.server_id,
        user_id=result.user_id,
        name=result.name,
        server_type=result.server_type,
        status=result.status,
        host=result.host,
        port=result.port,
        credential_id=result.credential_id,
        description=result.description,
        os_id=result.os_id,
        os_version=result.os_version,
        os_name=result.os_name,
        created_at=result.created_at,
        updated_at=result.updated_at,
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_server(
    body: dict,
    user_id: Annotated[str, Depends(get_current_user_id)],
    user_role: Annotated[str, Depends(get_current_user_role)],
    register_server: Annotated[RegisterServer, Depends(get_register_server)],
    register_local_server: Annotated[RegisterLocalServer, Depends(get_register_local_server)],
) -> ServerResponse:
    """Registra un nuevo servidor remoto o local según el campo `type`.

    - `type=remote` (por defecto): requiere `host`, `port` y `credential_id`.
    - `type=local`: solo requiere `name`. Solo usuarios con rol `admin` pueden crearlo.

    Returns:
        201 ServerResponse con los datos del servidor creado.

    Raises:
        400 si la configuración es inválida.
        403 si un usuario no-admin intenta crear un servidor local.
        404 si la credencial no existe.
        409 si ya existe un servidor local para el usuario.
    """
    correlation_id = str(uuid4())
    server_type = body.get("type", "remote")

    if server_type == "local":
        req = RegisterLocalServerRequest.model_validate(body)
        result = await register_local_server.execute(
            user_id=user_id,
            user_role=user_role,
            name=req.name,
            description=req.description,
            correlation_id=correlation_id,
        )
    else:
        req = RegisterServerRequest.model_validate(body)
        result = await register_server.execute(
            user_id=user_id,
            name=req.name,
            host=req.host,
            port=req.port,
            credential_id=req.credential_id,
            description=req.description,
            correlation_id=correlation_id,
        )

    logger.info(
        "server_registered",
        user_id=user_id,
        server_id=result.server_id,
        server_type=result.server_type,
    )
    return _to_server_response(result)


@router.get("", status_code=status.HTTP_200_OK)
async def list_servers(
    user_id: Annotated[str, Depends(get_current_user_id)],
    use_case: Annotated[ListServers, Depends(get_list_servers)],
    page: Annotated[int, Query(ge=1, description="Número de página (1-based)")] = 1,
    per_page: Annotated[int, Query(ge=1, le=100, description="Elementos por página")] = 20,
) -> ServerListResponse:
    """Lista los servidores del usuario autenticado con paginación.

    Returns:
        200 ServerListResponse — lista paginada de servidores.
    """
    result = await use_case.execute(user_id=user_id, page=page, per_page=per_page)
    return ServerListResponse(
        items=[_to_server_response(item) for item in result.items],
        total=result.total,
        page=result.page,
        per_page=result.per_page,
    )


@router.get("/{server_id}", status_code=status.HTTP_200_OK)
async def get_server(
    server_id: str,
    user_id: Annotated[str, Depends(get_current_user_id)],
    use_case: Annotated[GetServer, Depends(get_get_server)],
) -> ServerResponse:
    """Obtiene un servidor por su ID.

    Returns:
        200 ServerResponse.

    Raises:
        404 si el servidor no existe o no pertenece al usuario.
    """
    result = await use_case.execute(user_id=user_id, server_id=server_id)
    return _to_server_response(result)
