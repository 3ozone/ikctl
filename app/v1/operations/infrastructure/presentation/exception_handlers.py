"""Exception handlers FastAPI — convierte excepciones del módulo operations a respuestas HTTP.

Jerarquía y códigos HTTP:
- OperationNotFoundError          → 404 Not Found
- GroupNotFoundError              → 404 Not Found
- InvalidOperationTransitionError → 409 Conflict  (dominio y aplicación)
- OperationNotRestorableError     → 422 Unprocessable
- OperationNotRetriableError      → 422 Unprocessable
- ServerNotActiveError            → 422 Unprocessable
- KitNotUsableError               → 422 Unprocessable
- UseCaseException (catch-all)    → 422 Unprocessable
"""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.v1.operations.application.exceptions import (
    GroupNotFoundError,
    KitNotUsableError,
    OperationNotRestorableError,
    OperationNotRetriableError,
    ServerNotActiveError,
    UseCaseException,
)
from app.v1.operations.domain.exceptions.operation import (
    InvalidOperationTransitionError,
    OperationNotFoundError,
)
from app.v1.shared.infrastructure.logger import get_logger

logger = get_logger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    """Registra todos los exception handlers del módulo operations en la aplicación FastAPI.

    Args:
        app: Instancia de FastAPI donde se registrarán los handlers.
    """

    # ── 404 Not Found ─────────────────────────────────────────────────────────

    @app.exception_handler(OperationNotFoundError)
    async def operation_not_found_handler(
        request: Request, exc: OperationNotFoundError
    ) -> JSONResponse:
        """Convierte OperationNotFoundError a HTTP 404."""
        logger.warning(
            "operation_not_found",
            path=request.url.path,
            error=str(exc),
        )
        return JSONResponse(
            status_code=404,
            content={"detail": str(exc) or "Operación no encontrada"},
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
            content={"detail": str(exc) or "Grupo no encontrado"},
        )

    # ── 409 Conflict ──────────────────────────────────────────────────────────

    @app.exception_handler(InvalidOperationTransitionError)
    async def invalid_transition_handler(
        request: Request, exc: InvalidOperationTransitionError
    ) -> JSONResponse:
        """Convierte InvalidOperationTransitionError a HTTP 409."""
        logger.warning(
            "invalid_operation_transition",
            path=request.url.path,
            error=str(exc),
        )
        return JSONResponse(
            status_code=409,
            content={"detail": str(exc) or "Transición de estado no válida para la operación"},
        )

    # ── 422 Unprocessable ─────────────────────────────────────────────────────

    @app.exception_handler(OperationNotRestorableError)
    async def operation_not_restorable_handler(
        request: Request, exc: OperationNotRestorableError
    ) -> JSONResponse:
        """Convierte OperationNotRestorableError a HTTP 422."""
        logger.warning(
            "operation_not_restorable",
            path=request.url.path,
            error=str(exc),
        )
        return JSONResponse(
            status_code=422,
            content={"detail": str(exc) or "La operación no puede restaurarse"},
        )

    @app.exception_handler(OperationNotRetriableError)
    async def operation_not_retriable_handler(
        request: Request, exc: OperationNotRetriableError
    ) -> JSONResponse:
        """Convierte OperationNotRetriableError a HTTP 422."""
        logger.warning(
            "operation_not_retriable",
            path=request.url.path,
            error=str(exc),
        )
        return JSONResponse(
            status_code=422,
            content={"detail": str(exc) or "La operación no puede reintentarse"},
        )

    @app.exception_handler(ServerNotActiveError)
    async def server_not_active_handler(
        request: Request, exc: ServerNotActiveError
    ) -> JSONResponse:
        """Convierte ServerNotActiveError a HTTP 422."""
        logger.warning(
            "server_not_active",
            path=request.url.path,
            error=str(exc),
        )
        return JSONResponse(
            status_code=422,
            content={"detail": str(exc) or "El servidor está inactivo"},
        )

    @app.exception_handler(KitNotUsableError)
    async def kit_not_usable_handler(
        request: Request, exc: KitNotUsableError
    ) -> JSONResponse:
        """Convierte KitNotUsableError a HTTP 422."""
        logger.warning(
            "kit_not_usable",
            path=request.url.path,
            error=str(exc),
        )
        return JSONResponse(
            status_code=422,
            content={"detail": str(exc) or "El kit no es usable: está eliminado o en error de sync"},
        )

    # ── 422 Unprocessable (catch-all) ─────────────────────────────────────────

    @app.exception_handler(UseCaseException)
    async def use_case_exception_handler(
        request: Request, exc: UseCaseException
    ) -> JSONResponse:
        """Convierte UseCaseException genérica del módulo operations a HTTP 422."""
        logger.warning(
            "operations_use_case_exception",
            path=request.url.path,
            error=str(exc),
        )
        return JSONResponse(
            status_code=422,
            content={"detail": str(exc)},
        )
