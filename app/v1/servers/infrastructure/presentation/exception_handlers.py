"""Exception handlers FastAPI — convierte excepciones a respuestas HTTP estandarizadas.

Jerarquía y códigos HTTP:
- DomainException (invalid type/config) → 400 Bad Request
  - CredentialNotFoundError             → 404 Not Found
  - ServerNotFoundError                 → 404 Not Found
  - GroupNotFoundError                  → 404 Not Found
  - CredentialInUseError                → 409 Conflict
- UseCaseException (catch-all)          → 422 Unprocessable
  - UnauthorizedOperationError          → 403 Forbidden
  - DuplicateLocalServerError           → 409 Conflict
  - ServerInUseError                    → 409 Conflict
  - GroupInUseError                     → 409 Conflict
- InfrastructureException               → 500 Internal Server Error
"""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.v1.servers.application.exceptions import (
    DuplicateLocalServerError,
    GroupInUseError,
    LocalServerNotAllowedInGroupError,
    ServerInUseError,
    UnauthorizedOperationError,
    UseCaseException,
)
from app.v1.servers.domain.exceptions.credential import (
    CredentialInUseError,
    CredentialNotFoundError,
)
from app.v1.servers.domain.exceptions.group import GroupNotFoundError
from app.v1.servers.domain.exceptions.server import ServerNotFoundError
from app.v1.shared.domain.exceptions import DomainException
from app.v1.shared.infrastructure.exceptions import InfrastructureException
from app.v1.shared.infrastructure.logger import get_logger

logger = get_logger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    """Registra todos los exception handlers del módulo servers en la aplicación FastAPI.

    Args:
        app: Instancia de FastAPI donde se registrarán los handlers.
    """

    # ── 404 Not Found ────────────────────────────────────────────────────────

    @app.exception_handler(CredentialNotFoundError)
    async def credential_not_found_handler(
        request: Request, exc: CredentialNotFoundError
    ) -> JSONResponse:
        """Convierte CredentialNotFoundError a HTTP 404."""
        logger.warning(
            "credential_not_found",
            path=request.url.path,
            error=str(exc),
        )
        return JSONResponse(
            status_code=404,
            content={"detail": str(exc)},
        )

    @app.exception_handler(ServerNotFoundError)
    async def server_not_found_handler(
        request: Request, exc: ServerNotFoundError
    ) -> JSONResponse:
        """Convierte ServerNotFoundError a HTTP 404."""
        logger.warning(
            "server_not_found",
            path=request.url.path,
            error=str(exc),
        )
        return JSONResponse(
            status_code=404,
            content={"detail": str(exc)},
        )

    @app.exception_handler(GroupNotFoundError)
    async def group_not_found_handler(
        request: Request, exc: GroupNotFoundError
    ) -> JSONResponse:
        """Convierte GroupNotFoundError a HTTP 404."""
        logger.warning(
            "group_not_found",
            path=request.url.path,
            error=str(exc),
        )
        return JSONResponse(
            status_code=404,
            content={"detail": str(exc)},
        )

    # ── 409 Conflict ─────────────────────────────────────────────────────────

    @app.exception_handler(CredentialInUseError)
    async def credential_in_use_handler(
        request: Request, exc: CredentialInUseError
    ) -> JSONResponse:
        """Convierte CredentialInUseError a HTTP 409."""
        logger.warning(
            "credential_in_use",
            path=request.url.path,
            error=str(exc),
        )
        return JSONResponse(
            status_code=409,
            content={"detail": str(exc)},
        )

    @app.exception_handler(DuplicateLocalServerError)
    async def duplicate_local_server_handler(
        request: Request, exc: DuplicateLocalServerError
    ) -> JSONResponse:
        """Convierte DuplicateLocalServerError a HTTP 409."""
        logger.warning(
            "duplicate_local_server",
            path=request.url.path,
            error=str(exc),
        )
        return JSONResponse(
            status_code=409,
            content={"detail": str(exc)},
        )

    @app.exception_handler(ServerInUseError)
    async def server_in_use_handler(
        request: Request, exc: ServerInUseError
    ) -> JSONResponse:
        """Convierte ServerInUseError a HTTP 409."""
        logger.warning(
            "server_in_use",
            path=request.url.path,
            error=str(exc),
        )
        return JSONResponse(
            status_code=409,
            content={"detail": str(exc)},
        )

    @app.exception_handler(GroupInUseError)
    async def group_in_use_handler(
        request: Request, exc: GroupInUseError
    ) -> JSONResponse:
        """Convierte GroupInUseError a HTTP 409."""
        logger.warning(
            "group_in_use",
            path=request.url.path,
            error=str(exc),
        )
        return JSONResponse(
            status_code=409,
            content={"detail": str(exc)},
        )

    # ── 403 Forbidden ────────────────────────────────────────────────────────

    @app.exception_handler(UnauthorizedOperationError)
    async def unauthorized_handler(
        request: Request, exc: UnauthorizedOperationError
    ) -> JSONResponse:
        """Convierte UnauthorizedOperationError a HTTP 403."""
        logger.warning(
            "unauthorized_operation",
            path=request.url.path,
            error=str(exc),
        )
        return JSONResponse(
            status_code=403,
            content={"detail": str(exc)},
        )

    @app.exception_handler(LocalServerNotAllowedInGroupError)
    async def local_server_not_allowed_handler(
        request: Request, exc: LocalServerNotAllowedInGroupError
    ) -> JSONResponse:
        """Convierte LocalServerNotAllowedInGroupError a HTTP 422."""
        logger.warning(
            "local_server_not_allowed_in_group",
            path=request.url.path,
            error=str(exc),
        )
        return JSONResponse(
            status_code=422,
            content={"detail": str(exc)},
        )

    # ── 400 Bad Request ───────────────────────────────────────────────────────

    @app.exception_handler(DomainException)
    async def domain_exception_handler(
        request: Request, exc: DomainException
    ) -> JSONResponse:
        """Convierte DomainException genérica (invalid type/config) a HTTP 400."""
        logger.warning(
            "domain_exception",
            path=request.url.path,
            error=str(exc),
        )
        return JSONResponse(
            status_code=400,
            content={"detail": str(exc)},
        )

    # ── 422 Unprocessable ─────────────────────────────────────────────────────

    @app.exception_handler(UseCaseException)
    async def use_case_exception_handler(
        request: Request, exc: UseCaseException
    ) -> JSONResponse:
        """Convierte UseCaseException genérica a HTTP 422."""
        logger.warning(
            "use_case_exception",
            path=request.url.path,
            error=str(exc),
        )
        return JSONResponse(
            status_code=422,
            content={"detail": str(exc)},
        )

    # ── 500 Internal Server Error ─────────────────────────────────────────────

    @app.exception_handler(InfrastructureException)
    async def infrastructure_exception_handler(
        request: Request, exc: InfrastructureException
    ) -> JSONResponse:
        """Convierte InfrastructureException a HTTP 500."""
        logger.error(
            "infrastructure_exception",
            path=request.url.path,
            error=str(exc),
        )
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
        )
