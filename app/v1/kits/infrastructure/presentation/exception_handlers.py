"""Exception handlers FastAPI — convierte excepciones del módulo kits a respuestas HTTP.

Jerarquía y códigos HTTP:
- RepositoryNotFoundError   → 404 Not Found
- KitNotFoundError          → 404 Not Found
- RepositoryInUseError      → 409 Conflict
- KitNotUsableError         → 422 Unprocessable
- InvalidGitCredentialTypeError → 422 Unprocessable
- MissingRootManifestError  → 422 Unprocessable
- UseCaseException (catch-all) → 422 Unprocessable
"""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.v1.kits.application.exceptions import (
    InvalidGitCredentialTypeError,
    KitNotFoundError,
    KitNotUsableError,
    MissingRootManifestError,
    RepositoryInUseError,
    RepositoryNotFoundError,
    UseCaseException,
)
from app.v1.shared.infrastructure.logger import get_logger

logger = get_logger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    """Registra todos los exception handlers del módulo kits en la aplicación FastAPI.

    Args:
        app: Instancia de FastAPI donde se registrarán los handlers.
    """

    # ── 404 Not Found ─────────────────────────────────────────────────────────

    @app.exception_handler(RepositoryNotFoundError)
    async def repository_not_found_handler(
        request: Request, exc: RepositoryNotFoundError
    ) -> JSONResponse:
        """Convierte RepositoryNotFoundError a HTTP 404."""
        logger.warning(
            "repository_not_found",
            path=request.url.path,
            error=str(exc),
        )
        return JSONResponse(
            status_code=404,
            content={"detail": str(exc) or "Repositorio no encontrado"},
        )

    @app.exception_handler(KitNotFoundError)
    async def kit_not_found_handler(
        request: Request, exc: KitNotFoundError
    ) -> JSONResponse:
        """Convierte KitNotFoundError a HTTP 404."""
        logger.warning(
            "kit_not_found",
            path=request.url.path,
            error=str(exc),
        )
        return JSONResponse(
            status_code=404,
            content={"detail": str(exc) or "Kit no encontrado"},
        )

    # ── 409 Conflict ──────────────────────────────────────────────────────────

    @app.exception_handler(RepositoryInUseError)
    async def repository_in_use_handler(
        request: Request, exc: RepositoryInUseError
    ) -> JSONResponse:
        """Convierte RepositoryInUseError a HTTP 409."""
        logger.warning(
            "repository_in_use",
            path=request.url.path,
            error=str(exc),
        )
        return JSONResponse(
            status_code=409,
            content={"detail": str(exc) or "El repositorio tiene kits referenciados y no puede eliminarse"},
        )

    # ── 422 Unprocessable ─────────────────────────────────────────────────────

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

    @app.exception_handler(InvalidGitCredentialTypeError)
    async def invalid_git_credential_type_handler(
        request: Request, exc: InvalidGitCredentialTypeError
    ) -> JSONResponse:
        """Convierte InvalidGitCredentialTypeError a HTTP 422."""
        logger.warning(
            "invalid_git_credential_type",
            path=request.url.path,
            error=str(exc),
        )
        return JSONResponse(
            status_code=422,
            content={"detail": str(exc) or "La credencial debe ser de tipo git_https o git_ssh"},
        )

    @app.exception_handler(MissingRootManifestError)
    async def missing_root_manifest_handler(
        request: Request, exc: MissingRootManifestError
    ) -> JSONResponse:
        """Convierte MissingRootManifestError a HTTP 422."""
        logger.warning(
            "missing_root_manifest",
            path=request.url.path,
            error=str(exc),
        )
        return JSONResponse(
            status_code=422,
            content={"detail": str(exc) or "No se encontró ikctl.yaml en la raíz del repositorio"},
        )

    # ── 422 Unprocessable (catch-all) ─────────────────────────────────────────

    @app.exception_handler(UseCaseException)
    async def use_case_exception_handler(
        request: Request, exc: UseCaseException
    ) -> JSONResponse:
        """Convierte UseCaseException genérica del módulo kits a HTTP 422."""
        logger.warning(
            "kits_use_case_exception",
            path=request.url.path,
            error=str(exc),
        )
        return JSONResponse(
            status_code=422,
            content={"detail": str(exc)},
        )
