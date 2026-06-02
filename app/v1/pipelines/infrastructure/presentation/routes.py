"""Routers FastAPI para el módulo pipelines.

Endpoints:
  POST   /api/v1/pipelines                            — T-29: crear pipeline
  GET    /api/v1/pipelines                            — T-30: listar pipelines paginados
  GET    /api/v1/pipelines/{id}                       — T-31: obtener pipeline
  PUT    /api/v1/pipelines/{id}                       — T-32: actualizar pipeline
  DELETE /api/v1/pipelines/{id}                       — T-33: eliminar pipeline
  POST   /api/v1/pipelines/{id}/executions            — T-34: lanzar pipeline
  GET    /api/v1/pipelines/{id}/executions            — T-35: historial de ejecuciones
  GET    /api/v1/pipelines/{id}/executions/{exec_id}  — T-35.1: detalle de ejecución
"""
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status

from app.v1.pipelines.application.commands.create_pipeline import CreatePipeline
from app.v1.pipelines.application.commands.delete_pipeline import DeletePipeline
from app.v1.pipelines.application.commands.launch_pipeline import LaunchPipeline
from app.v1.pipelines.application.commands.update_pipeline import UpdatePipeline
from app.v1.pipelines.application.dtos.pipeline_dtos import PipelineExecutionDetailResult
from app.v1.pipelines.application.dtos.pipeline_dtos import PipelineExecutionResult as ExecutionResultDTO
from app.v1.pipelines.application.dtos.pipeline_dtos import PipelineExecutionSummary, PipelineListResult, PipelineResult
from app.v1.pipelines.application.queries.get_pipeline import GetPipeline
from app.v1.pipelines.application.queries.get_pipeline_execution_detail import GetPipelineExecutionDetail
from app.v1.pipelines.application.queries.get_pipeline_executions import GetPipelineExecutions
from app.v1.pipelines.application.queries.list_pipelines import ListPipelines
from app.v1.pipelines.domain.value_objects.pipeline_kit_config import PipelineKitConfig
from app.v1.pipelines.domain.value_objects.pipeline_target import PipelineTarget
from app.v1.pipelines.infrastructure.presentation.deps import (
    get_create_pipeline_uc,
    get_current_user_id,
    get_delete_pipeline_uc,
    get_get_pipeline_execution_detail_uc,
    get_get_pipeline_executions_uc,
    get_get_pipeline_uc,
    get_launch_pipeline_uc,
    get_list_pipelines_uc,
    get_update_pipeline_uc,
)
from app.v1.pipelines.infrastructure.presentation.schemas import (
    CreatePipelineRequest,
    LaunchPipelineRequest,
    PipelineExecutionDetailResponse,
    PipelineExecutionListResponse,
    PipelineExecutionResponse,
    PipelineExecutionSummaryResponse,
    PipelineKitConfigResponse,
    PipelineListResponse,
    PipelineOperationItemResponse,
    PipelineResponse,
    PipelineTargetResponse,
    UpdatePipelineRequest,
)
from app.v1.shared.infrastructure.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["pipelines"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _to_pipeline_response(result: PipelineResult) -> PipelineResponse:
    """Convierte PipelineResult DTO a PipelineResponse Pydantic."""
    return PipelineResponse(
        pipeline_id=result.pipeline_id,
        user_id=result.user_id,
        name=result.name,
        description=result.description,
        targets=[PipelineTargetResponse(server_id=t["server_id"]) for t in result.targets],
        kits=[
            PipelineKitConfigResponse(kit_id=k["kit_id"], sudo=k.get("sudo"), debug_level=k.get("debug_level"))
            for k in result.kits
        ],
        values=result.values,
        sudo=result.sudo,
        debug_level=result.debug_level,
        created_at=result.created_at or datetime.now(timezone.utc),
        updated_at=result.updated_at or datetime.now(timezone.utc),
    )


# ---------------------------------------------------------------------------
# T-29: POST /api/v1/pipelines — crear pipeline
# ---------------------------------------------------------------------------


@router.post(
    "/api/v1/pipelines",
    response_model=PipelineResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_pipeline(
    body: CreatePipelineRequest,
    user_id: Annotated[str, Depends(get_current_user_id)],
    use_case: Annotated[CreatePipeline, Depends(get_create_pipeline_uc)],
) -> PipelineResponse:
    """Crea un nuevo pipeline.

    Returns:
        201 PipelineResponse.

    Raises:
        422: Si algún target es un servidor local (LocalServerInPipelineError).
    """
    targets = [PipelineTarget(server_id=t.server_id) for t in body.targets]
    kits = [
        PipelineKitConfig(kit_id=k.kit_id, sudo=k.sudo, debug_level=k.debug_level)
        for k in body.kits
    ]
    result = await use_case.execute(
        user_id=user_id,
        name=body.name,
        description=body.description,
        targets=targets,
        kits=kits,
        values=body.values or {},
        sudo=body.sudo,
        debug_level=body.debug_level,
    )
    logger.info("pipeline_created", user_id=user_id, pipeline_id=result.pipeline_id)
    return _to_pipeline_response(result)


# ---------------------------------------------------------------------------
# T-30: GET /api/v1/pipelines — listar pipelines paginados
# ---------------------------------------------------------------------------


@router.get(
    "/api/v1/pipelines",
    response_model=PipelineListResponse,
    status_code=status.HTTP_200_OK,
)
async def list_pipelines(
    user_id: Annotated[str, Depends(get_current_user_id)],
    use_case: Annotated[ListPipelines, Depends(get_list_pipelines_uc)],
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=50),
) -> PipelineListResponse:
    """Lista los pipelines del usuario con paginación.

    Returns:
        200 PipelineListResponse paginada.
    """
    result: PipelineListResult = await use_case.execute(
        user_id=user_id,
        page=page,
        per_page=per_page,
    )
    return PipelineListResponse(
        items=[_to_pipeline_response(p) for p in result.items],
        total=result.total,
        page=result.page,
        per_page=result.per_page,
    )


# ---------------------------------------------------------------------------
# T-31: GET /api/v1/pipelines/{id} — obtener pipeline
# ---------------------------------------------------------------------------


@router.get(
    "/api/v1/pipelines/{pipeline_id}",
    response_model=PipelineResponse,
    status_code=status.HTTP_200_OK,
)
async def get_pipeline(
    pipeline_id: str,
    user_id: Annotated[str, Depends(get_current_user_id)],
    use_case: Annotated[GetPipeline, Depends(get_get_pipeline_uc)],
) -> PipelineResponse:
    """Obtiene el detalle de un pipeline.

    Returns:
        200 PipelineResponse.

    Raises:
        404: Si el pipeline no existe o no pertenece al usuario.
    """
    result = await use_case.execute(user_id=user_id, pipeline_id=pipeline_id)
    return _to_pipeline_response(result)


# ---------------------------------------------------------------------------
# T-32: PUT /api/v1/pipelines/{id} — actualizar pipeline
# ---------------------------------------------------------------------------


@router.put(
    "/api/v1/pipelines/{pipeline_id}",
    response_model=PipelineResponse,
    status_code=status.HTTP_200_OK,
)
async def update_pipeline(
    pipeline_id: str,
    body: UpdatePipelineRequest,
    user_id: Annotated[str, Depends(get_current_user_id)],
    use_case: Annotated[UpdatePipeline, Depends(get_update_pipeline_uc)],
) -> PipelineResponse:
    """Actualiza un pipeline existente.

    Returns:
        200 PipelineResponse.

    Raises:
        404: Si el pipeline no existe o no pertenece al usuario.
        409: Si el pipeline tiene ejecuciones activas.
        422: Si algún target es un servidor local.
    """
    targets = [PipelineTarget(server_id=t.server_id) for t in body.targets] if body.targets else None
    kits = (
        [PipelineKitConfig(kit_id=k.kit_id, sudo=k.sudo, debug_level=k.debug_level) for k in body.kits]
        if body.kits
        else None
    )
    result = await use_case.execute(
        user_id=user_id,
        pipeline_id=pipeline_id,
        name=body.name,
        description=body.description,
        targets=targets,
        kits=kits,
        values=body.values,
        sudo=body.sudo,
        debug_level=body.debug_level,
    )
    logger.info("pipeline_updated", user_id=user_id, pipeline_id=pipeline_id)
    return _to_pipeline_response(result)


# ---------------------------------------------------------------------------
# T-33: DELETE /api/v1/pipelines/{id} — eliminar pipeline
# ---------------------------------------------------------------------------


@router.delete(
    "/api/v1/pipelines/{pipeline_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_pipeline(
    pipeline_id: str,
    user_id: Annotated[str, Depends(get_current_user_id)],
    use_case: Annotated[DeletePipeline, Depends(get_delete_pipeline_uc)],
) -> Response:
    """Elimina un pipeline.

    Returns:
        204 No Content.

    Raises:
        404: Si el pipeline no existe o no pertenece al usuario.
        409: Si el pipeline tiene ejecuciones activas.
    """
    await use_case.execute(user_id=user_id, pipeline_id=pipeline_id)
    logger.info("pipeline_deleted", user_id=user_id, pipeline_id=pipeline_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# T-34: POST /api/v1/pipelines/{id}/executions — lanzar pipeline
# ---------------------------------------------------------------------------


@router.post(
    "/api/v1/pipelines/{pipeline_id}/executions",
    response_model=PipelineExecutionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def launch_pipeline(
    pipeline_id: str,
    user_id: Annotated[str, Depends(get_current_user_id)],
    use_case: Annotated[LaunchPipeline, Depends(get_launch_pipeline_uc)],
    _body: LaunchPipelineRequest = None,
) -> PipelineExecutionResponse:
    """Lanza una ejecución de un pipeline.

    Crea una PipelineExecution en estado pending, captura snapshot y encola
    la tarea async para procesar las operaciones.

    Returns:
        201 PipelineExecutionResponse con status pending y snapshot.

    Raises:
        404: Si el pipeline no existe o no pertenece al usuario.
        422: Si algún kit del pipeline no es usable (PipelineNotLaunchableError).
    """
    result = await use_case.execute(user_id=user_id, pipeline_id=pipeline_id)
    logger.info(
        "pipeline_launched",
        user_id=user_id,
        pipeline_id=pipeline_id,
        execution_id=result.execution_id,
    )
    return PipelineExecutionResponse(
        execution_id=result.execution_id,
        pipeline_id=result.pipeline_id,
        user_id=result.user_id,
        status=result.status,
        snapshot=result.snapshot,
        created_at=result.created_at or datetime.now(timezone.utc),
    )


# ---------------------------------------------------------------------------
# T-35: GET /api/v1/pipelines/{id}/executions — historial de ejecuciones
# ---------------------------------------------------------------------------


@router.get(
    "/api/v1/pipelines/{pipeline_id}/executions",
    response_model=PipelineExecutionListResponse,
    status_code=status.HTTP_200_OK,
)
async def get_pipeline_executions(
    pipeline_id: str,
    user_id: Annotated[str, Depends(get_current_user_id)],
    use_case: Annotated[GetPipelineExecutions, Depends(get_get_pipeline_executions_uc)],
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=50),
) -> PipelineExecutionListResponse:
    """Lista las ejecuciones de un pipeline con paginación.

    Returns:
        200 PipelineExecutionListResponse paginada.

    Raises:
        404: Si el pipeline no existe o no pertenece al usuario.
    """
    result = await use_case.execute(
        user_id=user_id,
        pipeline_id=pipeline_id,
        page=page,
        per_page=per_page,
    )
    return PipelineExecutionListResponse(
        items=[
            PipelineExecutionSummaryResponse(
                execution_id=item.execution_id,
                pipeline_id=item.pipeline_id,
                status=item.status,
                total_operations=item.total_operations,
                completed_operations=item.completed_operations,
                failed_operations=item.failed_operations,
                created_at=item.created_at,
                started_at=item.started_at,
                finished_at=item.finished_at,
            )
            for item in result.items
        ],
        total=result.total,
        page=result.page,
        per_page=result.per_page,
    )


# ---------------------------------------------------------------------------
# T-35.1: GET /api/v1/pipelines/{id}/executions/{exec_id} — detalle ejecución
# ---------------------------------------------------------------------------


@router.get(
    "/api/v1/pipelines/{pipeline_id}/executions/{execution_id}",
    response_model=PipelineExecutionDetailResponse,
    status_code=status.HTTP_200_OK,
)
async def get_pipeline_execution_detail(
    pipeline_id: str,
    execution_id: str,
    user_id: Annotated[str, Depends(get_current_user_id)],
    use_case: Annotated[GetPipelineExecutionDetail, Depends(get_get_pipeline_execution_detail_uc)],
) -> PipelineExecutionDetailResponse:
    """Obtiene el detalle completo de una ejecución de pipeline.

    Incluye snapshot inmutable y lista de operaciones individuales.

    Returns:
        200 PipelineExecutionDetailResponse.

    Raises:
        404: Si el pipeline o la ejecución no existen, o no pertenecen al usuario.
    """
    result = await use_case.execute(
        user_id=user_id,
        pipeline_id=pipeline_id,
        execution_id=execution_id,
    )
    return PipelineExecutionDetailResponse(
        execution_id=result.execution_id,
        pipeline_id=result.pipeline_id,
        user_id=result.user_id,
        status=result.status,
        snapshot=result.snapshot,
        operations=[
            PipelineOperationItemResponse(
                operation_id=op.operation_id,
                server_id=op.server_id,
                kit_id=op.kit_id,
                status=op.status,
                output=op.output,
                error=op.error,
            )
            for op in result.operations
        ],
        created_at=result.created_at,
        started_at=result.started_at,
        finished_at=result.finished_at,
    )