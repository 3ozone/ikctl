"""Schemas Pydantic para requests y responses del módulo kits.

Solo responsabilidad HTTP: validar entrada y serializar salida.
No contienen lógica de negocio — delegan a use cases.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# REPOSITORY — Requests
# ---------------------------------------------------------------------------


class RegisterRepositoryRequest(BaseModel):
    """Body para POST /api/v1/repositories."""

    url: str = Field(
        ...,
        min_length=1,
        max_length=2048,
        examples=["https://github.com/org/kits-repo"],
    )
    ref: str = Field(
        ...,
        min_length=1,
        max_length=255,
        examples=["main"],
        description="Branch o tag del repositorio",
    )
    credential_id: Optional[str] = Field(
        None,
        max_length=36,
        examples=["550e8400-e29b-41d4-a716-446655440000"],
        description="ID de credencial git_https o git_ssh (opcional para repos públicos)",
    )


class UpdateRepositoryRequest(BaseModel):
    """Body para PUT /api/v1/repositories/{id}."""

    url: str = Field(..., min_length=1, max_length=2048)
    ref: str = Field(..., min_length=1, max_length=255)
    credential_id: Optional[str] = Field(None, max_length=36)


# ---------------------------------------------------------------------------
# REPOSITORY — Responses
# ---------------------------------------------------------------------------


class RepositoryResponse(BaseModel):
    """Response para operaciones sobre repositorios Git."""

    repository_id: str
    user_id: str
    url: str
    ref: str
    credential_id: Optional[str]
    sync_status: str
    last_synced_at: Optional[datetime]
    last_commit_sha: Optional[str]
    sync_error_message: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RepositoryListResponse(BaseModel):
    """Response paginada para listar repositorios."""

    items: list[RepositoryResponse]
    total: int
    page: int
    per_page: int


class RepositorySyncResponse(BaseModel):
    """Response para POST /api/v1/repositories/{id}/sync.

    Siempre devuelve 200 — si el sync falla, sync_status es 'sync_error'.
    """

    repository_id: str
    sync_status: str
    last_commit_sha: Optional[str]
    sync_error_message: Optional[str]
    kits_created: int
    kits_updated: int
    kits_deleted: int


# ---------------------------------------------------------------------------
# KIT — Responses (solo lectura — gestionados por sync)
# ---------------------------------------------------------------------------


class KitResponse(BaseModel):
    """Response para operaciones de consulta sobre kits."""

    kit_id: str
    user_id: str
    repository_id: str
    path_in_repo: str
    name: str
    description: str
    version: str
    tags: list[str]
    values: dict
    debug_level: str
    sync_status: str
    last_synced_at: Optional[datetime]
    last_commit_sha: Optional[str]
    sync_error_message: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class KitListResponse(BaseModel):
    """Response paginada para listar kits."""

    items: list[KitResponse]
    total: int
    page: int
    per_page: int
