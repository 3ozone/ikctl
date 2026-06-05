"""Exception handlers FastAPI — convierte excepciones del módulo pipelines a respuestas HTTP.

Jerarquía y códigos HTTP:
- PipelineNotFoundError            → 404 Not Found
- PipelineExecutionNotFoundError   → 404 Not Found
- PipelineExecutionNotCancellableError → 422 Unprocessable
- PipelineInProgressError          → 409 Conflict
- LocalServerInPipelineError       → 422 Unprocessable
- PipelineNotLaunchableError       → 422 Unprocessable
- UseCaseException (catch-all)     → 422 Unprocessable
"""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.v1.pipelines.application.exceptions import (
    LocalServerInPipelineError,
    PipelineInProgressError,
    PipelineNotLaunchableError,
    UseCaseException,
)
from app.v1.pipelines.domain.exceptions.pipeline import PipelineNotFoundError
from app.v1.pipelines.domain.exceptions.pipeline_execution import (
    PipelineExecutionNotFoundError,
    PipelineExecutionNotCancellableError,
)
from app.v1.shared.infrastructure.logger import get_logger

logger = get_logger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    """Registra todos los exception handlers del módulo pipelines en la aplicación FastAPI."""

    # ── 404 Not Found ─────────────────────────────────────────────────────────

    @app.exception_handler(PipelineNotFoundError)
    async def pipeline_not_found_handler(
        request: Request, exc: PipelineNotFoundError
    ) -> JSONResponse:
        logger.warning(
            "pipeline_not_found",
            path=request.url.path,
            error=str(exc),
        )
        return JSONResponse(
            status_code=404,
            content={"detail": str(exc) or "Pipeline no encontrado"},
        )

    @app.exception_handler(PipelineExecutionNotFoundError)
    async def pipeline_execution_not_found_handler(
        request: Request, exc: PipelineExecutionNotFoundError
    ) -> JSONResponse:
        logger.warning(
            "pipeline_execution_not_found",
            path=request.url.path,
            error=str(exc),
        )
        return JSONResponse(
            status_code=404,
            content={"detail": str(exc) or "Ejecución de pipeline no encontrada"},
        )

    # ── 409 Conflict ──────────────────────────────────────────────────────────

    @app.exception_handler(PipelineInProgressError)
    async def pipeline_in_progress_handler(
        request: Request, exc: PipelineInProgressError
    ) -> JSONResponse:
        logger.warning(
            "pipeline_in_progress",
            path=request.url.path,
            error=str(exc),
        )
        return JSONResponse(
            status_code=409,
            content={"detail": str(exc) or "El pipeline tiene ejecuciones activas"},
        )

    # ── 422 Unprocessable ─────────────────────────────────────────────────────

    @app.exception_handler(LocalServerInPipelineError)
    async def local_server_in_pipeline_handler(
        request: Request, exc: LocalServerInPipelineError
    ) -> JSONResponse:
        logger.warning(
            "local_server_in_pipeline",
            path=request.url.path,
            error=str(exc),
        )
        return JSONResponse(
            status_code=422,
            content={"detail": str(exc) or "Un servidor local no puede formar parte de un pipeline"},
        )

    @app.exception_handler(PipelineNotLaunchableError)
    async def pipeline_not_launchable_handler(
        request: Request, exc: PipelineNotLaunchableError
    ) -> JSONResponse:
        logger.warning(
            "pipeline_not_launchable",
            path=request.url.path,
            error=str(exc),
        )
        return JSONResponse(
            status_code=422,
            content={"detail": str(exc) or "El pipeline no puede lanzarse"},
        )

    @app.exception_handler(PipelineExecutionNotCancellableError)
    async def pipeline_execution_not_cancellable_handler(
        request: Request, exc: PipelineExecutionNotCancellableError
    ) -> JSONResponse:
        logger.warning(
            "pipeline_execution_not_cancellable",
            path=request.url.path,
            error=str(exc),
        )
        return JSONResponse(
            status_code=422,
            content={"detail": str(exc) or "La ejecución no puede cancelarse"},
        )

    # ── 422 Unprocessable (catch-all) ─────────────────────────────────────────

    @app.exception_handler(UseCaseException)
    async def use_case_exception_handler(
        request: Request, exc: UseCaseException
    ) -> JSONResponse:
        logger.warning(
            "pipelines_use_case_exception",
            path=request.url.path,
            error=str(exc),
        )
        return JSONResponse(
            status_code=422,
            content={"detail": str(exc)},
        )