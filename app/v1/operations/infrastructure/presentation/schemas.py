"""Schemas Pydantic para requests y responses del módulo operations.

Solo responsabilidad HTTP: validar entrada y serializar salida.
No contienen lógica de negocio — delegan a use cases.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# OPERATION — Requests
# ---------------------------------------------------------------------------


class LaunchOperationRequest(BaseModel):
    """Body para POST /api/v1/operations."""

    server_id: str = Field(
        ...,
        min_length=1,
        max_length=36,
        examples=["550e8400-e29b-41d4-a716-446655440000"],
        description="ID del servidor destino",
    )
    kit_id: str = Field(
        ...,
        min_length=1,
        max_length=36,
        examples=["550e8400-e29b-41d4-a716-446655440001"],
        description="ID del kit a ejecutar",
    )
    debug_level: Optional[str] = Field(
        None,
        examples=["info"],
        description="Nivel de debug explícito. Si None hereda del kit (none/info/verbose).",
    )
    values: Optional[dict] = Field(
        None,
        examples=[{"port": 8080}],
        description="Valores de configuración del usuario. Sobreescriben los defaults del kit.",
    )
    sudo: bool = Field(
        False,
        description="Si True, ejecuta los scripts del pipeline con sudo.",
    )


# ---------------------------------------------------------------------------
# OPERATION — Responses
# ---------------------------------------------------------------------------


class OperationResponse(BaseModel):
    """Response para operaciones individuales."""

    operation_id: str
    user_id: str
    server_id: str
    kit_id: str
    values: dict = {}
    sudo: bool = False
    status: str
    debug_level: str
    output: str
    backup_files: list[str]
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime]
    finished_at: Optional[datetime]

    model_config = {"from_attributes": True}


class OperationListResponse(BaseModel):
    """Response paginada para listar operaciones."""

    items: list[OperationResponse]
    total: int
    page: int
    per_page: int


class RestoreResponse(BaseModel):
    """Response para POST /api/v1/operations/{id}/restore."""

    operation_id: str
    restored_files: list[str]
