"""Dependencias FastAPI para los endpoints del módulo servers.

Separa las funciones Depends() del Composition Root (main.py) para evitar
imports circulares.

Patrón:
- Singletons (event_bus) → leídos de request.app.state
- Repositorios (scoped) → construidos a partir de la AsyncSession del request
- Use cases → construidos a partir de repositorios scoped
"""
from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.v1.servers.application.commands.create_credential import CreateCredential
from app.v1.servers.application.commands.update_credential import UpdateCredential
from app.v1.servers.application.commands.delete_credential import DeleteCredential
from app.v1.servers.application.commands.register_server import RegisterServer
from app.v1.servers.application.commands.register_local_server import RegisterLocalServer
from app.v1.servers.application.commands.update_server import UpdateServer
from app.v1.servers.application.commands.delete_server import DeleteServer
from app.v1.servers.application.commands.toggle_server_status import ToggleServerStatus
from app.v1.servers.application.commands.create_group import CreateGroup
from app.v1.servers.application.commands.update_group import UpdateGroup
from app.v1.servers.application.commands.delete_group import DeleteGroup
from app.v1.servers.application.queries.get_credential import GetCredential
from app.v1.servers.application.queries.list_credentials import ListCredentials
from app.v1.servers.application.queries.get_server import GetServer
from app.v1.servers.application.queries.list_servers import ListServers
from app.v1.servers.application.queries.check_server_health import CheckServerHealth
from app.v1.servers.application.queries.execute_ad_hoc_command import ExecuteAdHocCommand
from app.v1.servers.application.queries.get_group import GetGroup
from app.v1.servers.application.queries.list_groups import ListGroups
from app.v1.servers.infrastructure.adapters.connection_factory import (
    ConnectionFactory as ConnectionFactoryAdapter,
)
from app.v1.servers.infrastructure.repositories.credential_repository import (
    SQLAlchemyCredentialRepository,
)
from app.v1.servers.infrastructure.repositories.group_repository import (
    SQLAlchemyGroupRepository,
)
from app.v1.servers.infrastructure.repositories.server_repository import (
    SQLAlchemyServerRepository,
)
from app.v1.shared.infrastructure.database import get_db_session as _get_db_session


# ---------------------------------------------------------------------------
# Singletons — leídos de app.state (depositados por main.py en lifespan)
# ---------------------------------------------------------------------------


def get_event_bus(request: Request):
    """Retorna el EventBus singleton depositado en app.state por main.py."""
    return request.app.state.event_bus


def get_encryption_key(request: Request) -> str:
    """Retorna la ENCRYPTION_KEY desde app.state."""
    return request.app.state.encryption_key


def get_current_user_id(request: Request) -> str:
    """Retorna el user_id inyectado por AuthenticationMiddleware en request.state."""
    return request.state.user_id


def get_current_user_role(request: Request) -> str:
    """Retorna el role del JWT inyectado por AuthenticationMiddleware en request.state.token_payload."""
    payload = getattr(request.state, "token_payload", {}) or {}
    return payload.get("role", "user")


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


def get_credential_repository(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> SQLAlchemyCredentialRepository:
    """Construye SQLAlchemyCredentialRepository con la sesión y clave de cifrado del request."""
    return SQLAlchemyCredentialRepository(
        session, encryption_key=request.app.state.encryption_key
    )


def get_server_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> SQLAlchemyServerRepository:
    """Construye SQLAlchemyServerRepository con la sesión scoped al request."""
    return SQLAlchemyServerRepository(session)


def get_group_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> SQLAlchemyGroupRepository:
    """Construye SQLAlchemyGroupRepository con la sesión scoped al request."""
    return SQLAlchemyGroupRepository(session)


def get_connection_factory(
    credential_repo: Annotated[SQLAlchemyCredentialRepository, Depends(get_credential_repository)],
) -> ConnectionFactoryAdapter:
    """Construye ConnectionFactory con el repositorio de credenciales scoped al request."""
    return ConnectionFactoryAdapter(credential_repository=credential_repo)


# ---------------------------------------------------------------------------
# Use Cases — Commands
# ---------------------------------------------------------------------------


def get_create_credential(
    credential_repo: Annotated[SQLAlchemyCredentialRepository, Depends(get_credential_repository)],
    event_bus=Depends(get_event_bus),
) -> CreateCredential:
    """Construye el use case CreateCredential con sus dependencias."""
    return CreateCredential(credential_repository=credential_repo, event_bus=event_bus)


def get_update_credential(
    credential_repo: Annotated[SQLAlchemyCredentialRepository, Depends(get_credential_repository)],
    event_bus=Depends(get_event_bus),
) -> UpdateCredential:
    """Construye el use case UpdateCredential con sus dependencias."""
    return UpdateCredential(credential_repository=credential_repo, event_bus=event_bus)


def get_delete_credential(
    credential_repo: Annotated[SQLAlchemyCredentialRepository, Depends(get_credential_repository)],
    event_bus=Depends(get_event_bus),
) -> DeleteCredential:
    """Construye el use case DeleteCredential con sus dependencias."""
    return DeleteCredential(credential_repository=credential_repo, event_bus=event_bus)


def get_register_server(
    server_repo: Annotated[SQLAlchemyServerRepository, Depends(get_server_repository)],
    credential_repo: Annotated[SQLAlchemyCredentialRepository, Depends(get_credential_repository)],
    event_bus=Depends(get_event_bus),
) -> RegisterServer:
    """Construye el use case RegisterServer con sus dependencias."""
    return RegisterServer(
        server_repository=server_repo,
        credential_repository=credential_repo,
        event_bus=event_bus,
    )


def get_register_local_server(
    server_repo: Annotated[SQLAlchemyServerRepository, Depends(get_server_repository)],
    event_bus=Depends(get_event_bus),
) -> RegisterLocalServer:
    """Construye el use case RegisterLocalServer con sus dependencias."""
    return RegisterLocalServer(server_repository=server_repo, event_bus=event_bus)


def get_update_server(
    server_repo: Annotated[SQLAlchemyServerRepository, Depends(get_server_repository)],
    event_bus=Depends(get_event_bus),
) -> UpdateServer:
    """Construye el use case UpdateServer con sus dependencias."""
    return UpdateServer(server_repository=server_repo, event_bus=event_bus)


def get_delete_server(
    server_repo: Annotated[SQLAlchemyServerRepository, Depends(get_server_repository)],
    event_bus=Depends(get_event_bus),
) -> DeleteServer:
    """Construye el use case DeleteServer con sus dependencias."""
    return DeleteServer(server_repository=server_repo, event_bus=event_bus)


def get_toggle_server_status(
    server_repo: Annotated[SQLAlchemyServerRepository, Depends(get_server_repository)],
    event_bus=Depends(get_event_bus),
) -> ToggleServerStatus:
    """Construye el use case ToggleServerStatus con sus dependencias."""
    return ToggleServerStatus(server_repository=server_repo, event_bus=event_bus)


def get_create_group(
    group_repo: Annotated[SQLAlchemyGroupRepository, Depends(get_group_repository)],
    server_repo: Annotated[SQLAlchemyServerRepository, Depends(get_server_repository)],
    event_bus=Depends(get_event_bus),
) -> CreateGroup:
    """Construye el use case CreateGroup con sus dependencias."""
    return CreateGroup(
        group_repository=group_repo,
        server_repository=server_repo,
        event_bus=event_bus,
    )


def get_update_group(
    group_repo: Annotated[SQLAlchemyGroupRepository, Depends(get_group_repository)],
    event_bus=Depends(get_event_bus),
) -> UpdateGroup:
    """Construye el use case UpdateGroup con sus dependencias."""
    return UpdateGroup(group_repository=group_repo, event_bus=event_bus)


def get_delete_group(
    group_repo: Annotated[SQLAlchemyGroupRepository, Depends(get_group_repository)],
    event_bus=Depends(get_event_bus),
) -> DeleteGroup:
    """Construye el use case DeleteGroup con sus dependencias."""
    return DeleteGroup(group_repository=group_repo, event_bus=event_bus)


# ---------------------------------------------------------------------------
# Use Cases — Queries
# ---------------------------------------------------------------------------


def get_get_credential(
    credential_repo: Annotated[SQLAlchemyCredentialRepository, Depends(get_credential_repository)],
) -> GetCredential:
    """Construye el use case GetCredential con sus dependencias."""
    return GetCredential(credential_repository=credential_repo)


def get_list_credentials(
    credential_repo: Annotated[SQLAlchemyCredentialRepository, Depends(get_credential_repository)],
) -> ListCredentials:
    """Construye el use case ListCredentials con sus dependencias."""
    return ListCredentials(credential_repository=credential_repo)


def get_get_server(
    server_repo: Annotated[SQLAlchemyServerRepository, Depends(get_server_repository)],
) -> GetServer:
    """Construye el use case GetServer con sus dependencias."""
    return GetServer(server_repository=server_repo)


def get_list_servers(
    server_repo: Annotated[SQLAlchemyServerRepository, Depends(get_server_repository)],
) -> ListServers:
    """Construye el use case ListServers con sus dependencias."""
    return ListServers(server_repository=server_repo)


def get_check_server_health(
    server_repo: Annotated[SQLAlchemyServerRepository, Depends(get_server_repository)],
    connection_factory: Annotated[ConnectionFactoryAdapter, Depends(get_connection_factory)],
) -> CheckServerHealth:
    """Construye el use case CheckServerHealth con sus dependencias."""
    return CheckServerHealth(
        server_repository=server_repo,
        connection_factory=connection_factory,
    )


def get_execute_ad_hoc_command(
    server_repo: Annotated[SQLAlchemyServerRepository, Depends(get_server_repository)],
    connection_factory: Annotated[ConnectionFactoryAdapter, Depends(get_connection_factory)],
) -> ExecuteAdHocCommand:
    """Construye el use case ExecuteAdHocCommand con sus dependencias."""
    return ExecuteAdHocCommand(
        server_repository=server_repo,
        connection_factory=connection_factory,
    )


def get_get_group(
    group_repo: Annotated[SQLAlchemyGroupRepository, Depends(get_group_repository)],
) -> GetGroup:
    """Construye el use case GetGroup con sus dependencias."""
    return GetGroup(group_repository=group_repo)


def get_list_groups(
    group_repo: Annotated[SQLAlchemyGroupRepository, Depends(get_group_repository)],
) -> ListGroups:
    """Construye el use case ListGroups con sus dependencias."""
    return ListGroups(group_repository=group_repo)
