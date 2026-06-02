"""Dependencias FastAPI para los endpoints del módulo kits.

Separa las funciones Depends() del Composition Root (main.py) para evitar
imports circulares.

Patrón:
- Singletons (event_bus, git_python_client) → leídos de request.app.state
- Repositorios (scoped) → construidos a partir de la AsyncSession del request
- Use cases → construidos a partir de repositorios scoped
"""
from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.v1.kits.application.commands.delete_repository import DeleteRepository
from app.v1.kits.application.commands.register_repository import RegisterRepository
from app.v1.kits.application.commands.sync_repository import SyncRepository
from app.v1.kits.application.commands.update_repository import UpdateRepository
from app.v1.kits.application.queries.get_kit import GetKit
from app.v1.kits.application.queries.get_repository import GetRepository
from app.v1.kits.application.queries.list_kits import ListKits
from app.v1.kits.application.queries.list_repositories import ListRepositories
from app.v1.kits.infrastructure.adapters.git_python_client import GitPythonClient
from app.v1.kits.infrastructure.repositories.kit_repository import SQLAlchemyKitRepository
from app.v1.kits.infrastructure.repositories.repository_repository import (
    SQLAlchemyRepositoryRepository as SQLAlchemyKitsRepositoryRepository,
)
from app.v1.servers.infrastructure.repositories.credential_repository import (
    SQLAlchemyCredentialRepository,
)
from app.v1.shared.infrastructure.database import get_db_session as _get_db_session


# ---------------------------------------------------------------------------
# Singletons — leídos de app.state (depositados por main.py en lifespan)
# ---------------------------------------------------------------------------


def get_event_bus(request: Request):
    """Retorna el EventBus singleton depositado en app.state por main.py."""
    return request.app.state.event_bus


def get_git_python_client(request: Request) -> GitPythonClient:
    """Retorna el GitPythonClient singleton depositado en app.state por main.py."""
    return request.app.state.git_python_client


def get_current_user_id(request: Request) -> str:
    """Retorna el user_id inyectado por AuthenticationMiddleware en request.state."""
    return request.state.user_id


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


def get_kits_repository_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> SQLAlchemyKitsRepositoryRepository:
    """Construye SQLAlchemyKitsRepositoryRepository con la sesión scoped al request."""
    return SQLAlchemyKitsRepositoryRepository(session)


def get_kit_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> SQLAlchemyKitRepository:
    """Construye SQLAlchemyKitRepository con la sesión scoped al request."""
    return SQLAlchemyKitRepository(session)


def get_credential_repository(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> SQLAlchemyCredentialRepository:
    """Construye SQLAlchemyCredentialRepository con la sesión y clave de cifrado del request."""
    return SQLAlchemyCredentialRepository(
        session, encryption_key=request.app.state.encryption_key
    )


# ---------------------------------------------------------------------------
# Use Cases — Commands
# ---------------------------------------------------------------------------


def get_register_repository_uc(
    repo_repo: Annotated[
        SQLAlchemyKitsRepositoryRepository, Depends(get_kits_repository_repository)
    ],
    credential_repo: Annotated[
        SQLAlchemyCredentialRepository, Depends(get_credential_repository)
    ],
    event_bus=Depends(get_event_bus),
) -> RegisterRepository:
    """Construye el use case RegisterRepository con sus dependencias."""
    return RegisterRepository(
        repository_repository=repo_repo,
        credential_repository=credential_repo,
        event_bus=event_bus,
    )


def get_update_repository_uc(
    repo_repo: Annotated[
        SQLAlchemyKitsRepositoryRepository, Depends(get_kits_repository_repository)
    ],
    credential_repo: Annotated[
        SQLAlchemyCredentialRepository, Depends(get_credential_repository)
    ],
) -> UpdateRepository:
    """Construye el use case UpdateRepository con sus dependencias."""
    return UpdateRepository(
        repository_repository=repo_repo,
        credential_repository=credential_repo,
    )


def get_delete_repository_uc(
    repo_repo: Annotated[
        SQLAlchemyKitsRepositoryRepository, Depends(get_kits_repository_repository)
    ],
    event_bus=Depends(get_event_bus),
) -> DeleteRepository:
    """Construye el use case DeleteRepository con sus dependencias."""
    return DeleteRepository(
        repository_repository=repo_repo,
        event_bus=event_bus,
    )


def get_sync_repository_uc(
    repo_repo: Annotated[
        SQLAlchemyKitsRepositoryRepository, Depends(get_kits_repository_repository)
    ],
    kit_repo: Annotated[SQLAlchemyKitRepository, Depends(get_kit_repository)],
    git_client: Annotated[GitPythonClient, Depends(get_git_python_client)],
    event_bus=Depends(get_event_bus),
) -> SyncRepository:
    """Construye el use case SyncRepository con sus dependencias."""
    return SyncRepository(
        repository_repository=repo_repo,
        kit_repository=kit_repo,
        git_client=git_client,
        event_bus=event_bus,
    )


# ---------------------------------------------------------------------------
# Use Cases — Queries
# ---------------------------------------------------------------------------


def get_get_repository_uc(
    repo_repo: Annotated[
        SQLAlchemyKitsRepositoryRepository, Depends(get_kits_repository_repository)
    ],
) -> GetRepository:
    """Construye el use case GetRepository con sus dependencias."""
    return GetRepository(repository_repository=repo_repo)


def get_list_repositories_uc(
    repo_repo: Annotated[
        SQLAlchemyKitsRepositoryRepository, Depends(get_kits_repository_repository)
    ],
) -> ListRepositories:
    """Construye el use case ListRepositories con sus dependencias."""
    return ListRepositories(repository_repository=repo_repo)


def get_get_kit_uc(
    kit_repo: Annotated[SQLAlchemyKitRepository, Depends(get_kit_repository)],
) -> GetKit:
    """Construye el use case GetKit con sus dependencias."""
    return GetKit(kit_repository=kit_repo)


def get_list_kits_uc(
    kit_repo: Annotated[SQLAlchemyKitRepository, Depends(get_kit_repository)],
) -> ListKits:
    """Construye el use case ListKits con sus dependencias."""
    return ListKits(kit_repository=kit_repo)
