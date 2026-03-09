"""Dependencias FastAPI para los endpoints auth.

Separa las funciones Depends() del Composition Root (main.py) para evitar
imports circulares: router no puede importar de main.py.

Patrón:
- Singletons (event_bus, jwt_provider, …) → se leen de request.app.state,
  donde main.py los deposita durante el lifespan.
- Repositorios (scoped) → se construyen a partir de la AsyncSession del request.
"""
from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.v1.auth.application.exceptions import ResourceNotFoundError, UnauthorizedOperationError

from app.v1.auth.infrastructure.repositories.password_history_repository import (
    SQLAlchemyPasswordHistoryRepository,
)
from app.v1.auth.infrastructure.repositories.refresh_token_repository import (
    SQLAlchemyRefreshTokenRepository,
)
from app.v1.auth.infrastructure.repositories.user_repository import SQLAlchemyUserRepository
from app.v1.auth.infrastructure.repositories.verification_token_repository import (
    SQLAlchemyVerificationTokenRepository,
)
from app.v1.shared.infrastructure.database import get_db_session as _get_db_session


# ---------------------------------------------------------------------------
# Singletons — leídos de app.state (depositados por main.py en lifespan)
# ---------------------------------------------------------------------------


def get_event_bus(request: Request):
    """Retorna el EventBus singleton depositado en app.state por main.py."""
    return request.app.state.event_bus


def get_jwt_provider(request: Request):
    """Retorna el JWTProvider singleton depositado en app.state por main.py."""
    return request.app.state.jwt_provider


def get_email_service(request: Request):
    """Retorna el EmailService singleton depositado en app.state por main.py."""
    return request.app.state.email_service


def get_totp_provider(request: Request):
    """Retorna el TOTPProvider singleton depositado en app.state por main.py."""
    return request.app.state.totp_provider


def get_github_oauth(request: Request):
    """Retorna el GitHubOAuth singleton depositado en app.state por main.py."""
    return request.app.state.github_oauth


def get_rate_limiter(request: Request):
    """Retorna el RateLimiter singleton depositado en app.state por main.py."""
    return request.app.state.rate_limiter


def get_login_attempt_tracker(request: Request):
    """Retorna el LoginAttemptTracker singleton depositado en app.state por main.py."""
    return request.app.state.login_attempt_tracker


def get_current_user_id(request: Request) -> str:
    """Retorna el user_id inyectado por AuthenticationMiddleware en request.state."""
    return request.state.user_id


# ---------------------------------------------------------------------------
# Session scoped — provista por la session_factory de app.state
# ---------------------------------------------------------------------------


async def get_db_session(request: Request) -> AsyncGenerator[AsyncSession, None]:
    """Provee una AsyncSession scoped al request, usando la factory de app.state."""
    session_factory = request.app.state.session_factory
    async for session in _get_db_session(session_factory):
        yield session


# ---------------------------------------------------------------------------
# Repositorios scoped al request
# ---------------------------------------------------------------------------


def get_user_repository(
    session: AsyncSession = Depends(get_db_session),
) -> SQLAlchemyUserRepository:
    """Dependencia FastAPI — UserRepository scoped al request."""
    return SQLAlchemyUserRepository(session)


def get_refresh_token_repository(
    session: AsyncSession = Depends(get_db_session),
) -> SQLAlchemyRefreshTokenRepository:
    """Dependencia FastAPI — RefreshTokenRepository scoped al request."""
    return SQLAlchemyRefreshTokenRepository(session)


def get_verification_token_repository(
    session: AsyncSession = Depends(get_db_session),
) -> SQLAlchemyVerificationTokenRepository:
    """Dependencia FastAPI — VerificationTokenRepository scoped al request."""
    return SQLAlchemyVerificationTokenRepository(session)


def get_password_history_repository(
    session: AsyncSession = Depends(get_db_session),
) -> SQLAlchemyPasswordHistoryRepository:
    """Dependencia FastAPI — PasswordHistoryRepository scoped al request."""
    return SQLAlchemyPasswordHistoryRepository(session)


# ---------------------------------------------------------------------------
# Dependencias de seguridad
# ---------------------------------------------------------------------------


async def require_verified_email(
    user_id: Annotated[str, Depends(get_current_user_id)],
    user_repository: Annotated[SQLAlchemyUserRepository, Depends(get_user_repository)],
) -> str:
    """Verifica que el usuario autenticado tiene el email confirmado (RN-02).

    Args:
        user_id: ID del usuario autenticado, inyectado por el middleware.
        user_repository: Repositorio de usuarios (scoped al request).

    Returns:
        user_id si el email está verificado.

    Raises:
        UnauthorizedOperationError: 403 si el email no está verificado o el usuario no existe.
    """
    user = await user_repository.find_by_id(user_id)
    if user is None:
        raise ResourceNotFoundError(f"Usuario con ID {user_id} no encontrado")
    if not user.is_email_verified:
        raise UnauthorizedOperationError(
            "Debes verificar tu email antes de acceder a esta función"
        )
    return user_id
