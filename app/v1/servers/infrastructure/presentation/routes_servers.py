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
from typing import Annotated, Literal, Union
from uuid import uuid4

from fastapi import APIRouter, Depends, Query, Response, status

from pydantic import Field

from app.v1.servers.application.commands.delete_server import DeleteServer
from app.v1.servers.application.commands.register_local_server import RegisterLocalServer
from app.v1.servers.application.commands.register_server import RegisterServer
from app.v1.servers.application.commands.toggle_server_status import ToggleServerStatus
from app.v1.servers.application.commands.update_server import UpdateServer
from app.v1.servers.application.queries.check_server_health import CheckServerHealth
from app.v1.servers.application.queries.execute_ad_hoc_command import ExecuteAdHocCommand
from app.v1.servers.application.queries.get_server import GetServer
from app.v1.servers.application.queries.list_servers import ListServers
from app.v1.servers.infrastructure.presentation.deps import (
    get_check_server_health,
    get_current_user_id,
    get_current_user_role,
    get_delete_server,
    get_execute_ad_hoc_command,
    get_get_server,
    get_list_servers,
    get_register_local_server,
    get_register_server,
    get_toggle_server_status,
    get_update_server,
)
from app.v1.servers.infrastructure.presentation.schemas import (
    AdHocCommandRequest,
    AdHocCommandResponse,
    HealthCheckResponse,
    RegisterLocalServerRequest,
    RegisterServerRequest,
    ServerListResponse,
    ServerResponse,
    ToggleServerStatusRequest,
    UpdateServerRequest,
)
from app.v1.shared.infrastructure.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/servers", tags=["servers"])


# ---------------------------------------------------------------------------
# Schemas internos para el discriminador
# ---------------------------------------------------------------------------


class _CreateServerBody(RegisterServerRequest):
    """Extiende RegisterServerRequest añadiendo el campo discriminador `type`."""

    type: Literal["remote"] = "remote"


class _CreateLocalServerBody(RegisterLocalServerRequest):
    """Extiende RegisterLocalServerRequest añadiendo el campo discriminador `type`."""

    type: Literal["local"] = "local"


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
    body: Annotated[Union[_CreateServerBody, _CreateLocalServerBody], Field(discriminator="type")],
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

    if isinstance(body, _CreateLocalServerBody):
        result = await register_local_server.execute(
            user_id=user_id,
            user_role=user_role,
            name=body.name,
            description=body.description,
            correlation_id=correlation_id,
        )
    else:
        result = await register_server.execute(
            user_id=user_id,
            name=body.name,
            host=body.host,
            port=body.port,
            credential_id=body.credential_id,
            description=body.description,
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


@router.put("/{server_id}", status_code=status.HTTP_200_OK)
async def update_server(
    server_id: str,
    body: UpdateServerRequest,
    user_id: Annotated[str, Depends(get_current_user_id)],
    use_case: Annotated[UpdateServer, Depends(get_update_server)],
) -> ServerResponse:
    """Actualiza un servidor existente del usuario autenticado.

    Returns:
        200 ServerResponse con los datos actualizados.

    Raises:
        404 si el servidor no existe o no pertenece al usuario.
    """
    correlation_id = str(uuid4())
    result = await use_case.execute(
        user_id=user_id,
        server_id=server_id,
        name=body.name,
        host=body.host,
        port=body.port,
        credential_id=body.credential_id,
        description=body.description,
        correlation_id=correlation_id,
    )
    logger.info(
        "server_updated",
        user_id=user_id,
        server_id=result.server_id,
    )
    return _to_server_response(result)


@router.delete("/{server_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_server(
    server_id: str,
    user_id: Annotated[str, Depends(get_current_user_id)],
    use_case: Annotated[DeleteServer, Depends(get_delete_server)],
) -> Response:
    """Elimina un servidor del usuario autenticado.

    Returns:
        204 sin body.

    Raises:
        404 si el servidor no existe o no pertenece al usuario.
        409 si el servidor tiene operaciones activas.
    """
    correlation_id = str(uuid4())
    await use_case.execute(
        user_id=user_id,
        server_id=server_id,
        correlation_id=correlation_id,
    )
    logger.info(
        "server_deleted",
        user_id=user_id,
        server_id=server_id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{server_id}/toggle", status_code=status.HTTP_200_OK)
async def toggle_server_status(
    server_id: str,
    body: ToggleServerStatusRequest,
    user_id: Annotated[str, Depends(get_current_user_id)],
    use_case: Annotated[ToggleServerStatus, Depends(get_toggle_server_status)],
) -> ServerResponse:
    """Activa o desactiva un servidor del usuario autenticado.

    Returns:
        200 ServerResponse con el estado actualizado.

    Raises:
        404 si el servidor no existe o no pertenece al usuario.
    """
    correlation_id = str(uuid4())
    result = await use_case.execute(
        user_id=user_id,
        server_id=server_id,
        active=body.active,
        correlation_id=correlation_id,
    )
    logger.info(
        "server_toggled",
        user_id=user_id,
        server_id=result.server_id,
        active=body.active,
    )
    return _to_server_response(result)


@router.get("/{server_id}/health", status_code=status.HTTP_200_OK)
async def check_server_health(
    server_id: str,
    user_id: Annotated[str, Depends(get_current_user_id)],
    use_case: Annotated[CheckServerHealth, Depends(get_check_server_health)],
) -> HealthCheckResponse:
    """Verifica la conectividad SSH y detecta el SO del servidor.

    Returns:
        200 HealthCheckResponse con status online/offline, latency_ms y OS info.

    Raises:
        404 si el servidor no existe o no pertenece al usuario.
    """
    result = await use_case.execute(user_id=user_id, server_id=server_id)
    logger.info(
        "server_health_checked",
        user_id=user_id,
        server_id=server_id,
        status=result.status,
    )
    return HealthCheckResponse(
        server_id=result.server_id,
        status=result.status,
        latency_ms=result.latency_ms,
        os_id=result.os_id,
        os_version=result.os_version,
        os_name=result.os_name,
    )


@router.post("/{server_id}/command", status_code=status.HTTP_200_OK)
async def execute_command(
    server_id: str,
    body: AdHocCommandRequest,
    user_id: Annotated[str, Depends(get_current_user_id)],
    use_case: Annotated[ExecuteAdHocCommand, Depends(get_execute_ad_hoc_command)],
) -> AdHocCommandResponse:
    """Ejecuta un comando ad-hoc en el servidor indicado.

    Returns:
        200 AdHocCommandResponse con stdout, stderr y exit_code.

    Raises:
        404 si el servidor no existe o no pertenece al usuario.
    """
    result = await use_case.execute(
        user_id=user_id,
        server_id=server_id,
        command=body.command,
    )
    logger.info(
        "server_command_executed",
        user_id=user_id,
        server_id=server_id,
        exit_code=result.exit_code,
    )
    return AdHocCommandResponse(
        server_id=result.server_id,
        command=result.command,
        stdout=result.stdout,
        stderr=result.stderr,
        exit_code=result.exit_code,
    )
