"""Schemas Pydantic para requests y responses del módulo operations.

Solo responsabilidad HTTP: validar entrada y serializar salida.
No contienen lógica de negocio — delegan a use cases.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, model_validator


# ---------------------------------------------------------------------------
# OPERATION — Requests
# ---------------------------------------------------------------------------


class LaunchOperationRequest(BaseModel):
    """Body para POST /api/v1/operations.

    Exactamente uno de `server_id` o `group_id` debe estar presente.
    """

    server_id: Optional[str] = Field(
        None,
        min_length=1,
        max_length=36,
        examples=["550e8400-e29b-41d4-a716-446655440000"],
        description="ID del servidor destino (exclusivo con group_id)",
    )
    group_id: Optional[str] = Field(
        None,
        min_length=1,
        max_length=36,
        examples=["550e8400-e29b-41d4-a716-446655440002"],
        description="ID del grupo de servidores destino (exclusivo con server_id)",
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

    @model_validator(mode="after")
    def validate_target(self) -> "LaunchOperationRequest":
        """Valida que exactamente uno de server_id o group_id esté presente."""
        has_server = self.server_id is not None
        has_group = self.group_id is not None
        if has_server == has_group:
            raise ValueError(
                "Exactamente uno de 'server_id' o 'group_id' debe estar presente"
            )
        return self


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


class BatchOperationResponse(BaseModel):
    """Response para operaciones batch (lanzadas sobre un grupo de servidores)."""

    operations: list[OperationResponse]


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
