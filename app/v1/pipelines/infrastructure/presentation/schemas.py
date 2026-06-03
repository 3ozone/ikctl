"""Schemas Pydantic para requests y responses del módulo pipelines.

Solo responsabilidad HTTP: validar entrada y serializar salida.
No contienen lógica de negocio — delegan a use cases.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# PIPELINE — Requests
# ---------------------------------------------------------------------------


class PipelineTargetRequest(BaseModel):
    """Target (servidor o grupo) dentro de un pipeline."""

    server_id: str = Field(
        ...,
        min_length=1,
        max_length=36,
        examples=["550e8400-e29b-41d4-a716-446655440000"],
        description="ID del servidor o grupo destino",
    )


class PipelineKitConfigRequest(BaseModel):
    """Configuración de un kit dentro de un pipeline."""

    kit_id: str = Field(
        ...,
        min_length=1,
        max_length=36,
        examples=["550e8400-e29b-41d4-a716-446655440001"],
        description="ID del kit a ejecutar",
    )
    sudo: Optional[bool] = Field(
        None,
        description="Si ejecutar con sudo. None = heredar del pipeline.",
    )
    debug_level: Optional[str] = Field(
        None,
        examples=["none", "errors", "full"],
        description="Nivel de debug. None = heredar del pipeline.",
    )
    values: dict = Field(
        default_factory=dict,
        examples=[{"command": "hostname"}],
        description="Variables de plantilla específicas de este kit.",
    )


class CreatePipelineRequest(BaseModel):
    """Body para POST /api/v1/pipelines."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        examples=["Deploy API to Production"],
    )
    description: Optional[str] = Field(
        None,
        max_length=2048,
        description="Descripción opcional del pipeline",
    )
    targets: list[PipelineTargetRequest] = Field(
        ...,
        min_length=1,
        description="Lista de servidores/grupos destino (mínimo 1)",
    )
    kits: list[PipelineKitConfigRequest] = Field(
        ...,
        min_length=1,
        description="Lista de kits a ejecutar (mínimo 1)",
    )
    values: Optional[dict] = Field(
        None,
        examples=[{"env": "production"}],
        description="Valores de configuración compartidos por todos los kits",
    )
    sudo: bool = Field(
        False,
        description="Ejecutar con sudo por defecto (los kits pueden sobreescribir)",
    )
    debug_level: str = Field(
        "none",
        examples=["none", "errors", "full"],
        description="Nivel de debug por defecto (los kits pueden sobreescribir)",
    )


class UpdatePipelineRequest(BaseModel):
    """Body para PUT /api/v1/pipelines/{id}."""

    name: Optional[str] = Field(
        None,
        min_length=1,
        max_length=255,
    )
    description: Optional[str] = Field(None, max_length=2048)
    targets: Optional[list[PipelineTargetRequest]] = Field(
        None,
        min_length=1,
    )
    kits: Optional[list[PipelineKitConfigRequest]] = Field(
        None,
        min_length=1,
    )
    values: Optional[dict] = Field(None)
    sudo: Optional[bool] = Field(None)
    debug_level: Optional[str] = Field(None)


# ---------------------------------------------------------------------------
# PIPELINE — Responses
# ---------------------------------------------------------------------------


class PipelineTargetResponse(BaseModel):
    """Target serializado en la respuesta de un pipeline."""

    server_id: str


class PipelineKitConfigResponse(BaseModel):
    """Configuración de kit serializada en la respuesta de un pipeline."""

    kit_id: str
    sudo: Optional[bool]
    debug_level: Optional[str]
    values: dict


class PipelineResponse(BaseModel):
    """Response para operaciones sobre pipelines."""

    pipeline_id: str
    user_id: str
    name: str
    description: Optional[str]
    targets: list[PipelineTargetResponse]
    kits: list[PipelineKitConfigResponse]
    values: dict
    sudo: bool
    debug_level: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PipelineListResponse(BaseModel):
    """Response paginada para listar pipelines."""

    items: list[PipelineResponse]
    total: int
    page: int
    per_page: int


# ---------------------------------------------------------------------------
# PIPELINE EXECUTION — Requests
# ---------------------------------------------------------------------------


class LaunchPipelineRequest(BaseModel):
    """Body para POST /api/v1/pipelines/{id}/executions.

    No requiere campos — el pipeline_id viene en la URL.
    Se define por consistencia y extensibilidad futura.
    """

    pass


# ---------------------------------------------------------------------------
# PIPELINE EXECUTION — Responses
# ---------------------------------------------------------------------------


class PipelineExecutionResponse(BaseModel):
    """Response para el lanzamiento de un pipeline."""

    execution_id: str
    pipeline_id: str
    user_id: str
    status: str
    snapshot: dict
    created_at: datetime

    model_config = {"from_attributes": True}


class PipelineOperationItemResponse(BaseModel):
    """Detalle de una operación individual dentro de una ejecución."""

    operation_id: str
    server_id: str
    kit_id: str
    status: str
    output: str
    error: Optional[str]


class PipelineExecutionSummaryResponse(BaseModel):
    """Resumen de una ejecución para el listado paginado."""

    execution_id: str
    pipeline_id: str
    status: str
    total_operations: int
    completed_operations: int
    failed_operations: int
    created_at: Optional[datetime]
    started_at: Optional[datetime]
    finished_at: Optional[datetime]


class PipelineExecutionListResponse(BaseModel):
    """Response paginada para listar ejecuciones de un pipeline."""

    items: list[PipelineExecutionSummaryResponse]
    total: int
    page: int
    per_page: int


class PipelineExecutionDetailResponse(BaseModel):
    """Response para el detalle completo de una ejecución de pipeline."""

    execution_id: str
    pipeline_id: str
    user_id: str
    status: str
    snapshot: dict
    operations: list[PipelineOperationItemResponse]
    created_at: Optional[datetime]
    started_at: Optional[datetime]
    finished_at: Optional[datetime]

    model_config = {"from_attributes": True}