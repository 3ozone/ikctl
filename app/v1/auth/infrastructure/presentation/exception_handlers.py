"""Exception handlers FastAPI — convierte excepciones a respuestas HTTP estandarizadas.

Jerarquía y códigos HTTP según ADR-006:
- DomainException        → 400 Bad Request   (reglas de negocio, validaciones)
- UseCaseException       → 422 Unprocessable  (orquestación, operaciones no válidas)
  - UnauthorizedOperationError → 403 Forbidden
  - ResourceNotFoundError      → 404 Not Found
  - TwoFactorRequiredError     → 403 Forbidden
  - UserBlockedError           → 429 Too Many Requests
- InfrastructureException → 500 Internal Server Error

Todos los handlers loggean con contexto estructurado (sin exponer internals al cliente).
"""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.v1.auth.application.exceptions import (
    EmailAlreadyExistsError,
    UnauthorizedOperationError,
    ResourceNotFoundError,
    TwoFactorRequiredError,
    UserBlockedError,
    UseCaseException,
)
from app.v1.shared.domain.exceptions import DomainException
from app.v1.shared.infrastructure.exceptions import InfrastructureException
from app.v1.shared.infrastructure.logger import get_logger

logger = get_logger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    """Registra todos los exception handlers en la aplicación FastAPI.

    Args:
        app: Instancia de FastAPI donde se registrarán los handlers.
    """

    @app.exception_handler(EmailAlreadyExistsError)
    async def email_already_exists_handler(
        request: Request, exc: EmailAlreadyExistsError
    ) -> JSONResponse:
        """Convierte EmailAlreadyExistsError a HTTP 409 Conflict."""
        logger.warning(
            "email_already_exists",
            path=request.url.path,
            error=str(exc),
        )
        return JSONResponse(
            status_code=409,
            content={"detail": str(exc)},
        )

    @app.exception_handler(UnauthorizedOperationError)
    async def unauthorized_handler(
        request: Request, exc: UnauthorizedOperationError
    ) -> JSONResponse:
        """Convierte UnauthorizedOperationError y TwoFactorRequiredError a HTTP 403."""
        logger.warning(
            "unauthorized_operation",
            path=request.url.path,
            error=str(exc),
        )
        return JSONResponse(
            status_code=403,
            content={"detail": str(exc)},
        )

    @app.exception_handler(TwoFactorRequiredError)
    async def two_factor_required_handler(
        request: Request, exc: TwoFactorRequiredError
    ) -> JSONResponse:
        """Convierte TwoFactorRequiredError a HTTP 403."""
        logger.warning(
            "two_factor_required",
            path=request.url.path,
            error=str(exc),
        )
        return JSONResponse(
            status_code=403,
            content={"detail": str(exc)},
        )

    @app.exception_handler(ResourceNotFoundError)
    async def not_found_handler(
        request: Request, exc: ResourceNotFoundError
    ) -> JSONResponse:
        """Convierte ResourceNotFoundError a HTTP 404."""
        logger.info(
            "resource_not_found",
            path=request.url.path,
            error=str(exc),
        )
        return JSONResponse(
            status_code=404,
            content={"detail": str(exc)},
        )

    @app.exception_handler(UserBlockedError)
    async def user_blocked_handler(
        request: Request, exc: UserBlockedError
    ) -> JSONResponse:
        """Convierte UserBlockedError a HTTP 429."""
        logger.warning(
            "user_blocked",
            path=request.url.path,
            error=str(exc),
        )
        return JSONResponse(
            status_code=429,
            content={"detail": str(exc)},
        )

    @app.exception_handler(UseCaseException)
    async def use_case_handler(
        request: Request, exc: UseCaseException
    ) -> JSONResponse:
        """Convierte UseCaseException genérica a HTTP 422."""
        logger.warning(
            "use_case_error",
            path=request.url.path,
            error_type=type(exc).__name__,
            error=str(exc),
        )
        return JSONResponse(
            status_code=422,
            content={"detail": str(exc)},
        )

    @app.exception_handler(DomainException)
    async def domain_handler(
        request: Request, exc: DomainException
    ) -> JSONResponse:
        """Convierte DomainException a HTTP 400."""
        logger.warning(
            "domain_error",
            path=request.url.path,
            error_type=type(exc).__name__,
            error=str(exc),
        )
        return JSONResponse(
            status_code=400,
            content={"detail": str(exc)},
        )

    @app.exception_handler(InfrastructureException)
    async def infrastructure_handler(
        request: Request, exc: InfrastructureException
    ) -> JSONResponse:
        """Convierte InfrastructureException a HTTP 500 sin exponer internals."""
        logger.error(
            "infrastructure_error",
            path=request.url.path,
            error_type=type(exc).__name__,
            error=str(exc),
            exc_info=True,
        )
        return JSONResponse(
            status_code=500,
            content={
                "detail": "Error interno del servidor. Por favor, inténtalo más tarde."},
        )
