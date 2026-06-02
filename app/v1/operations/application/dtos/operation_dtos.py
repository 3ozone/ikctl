"""DTOs del módulo operations."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class OperationResult:
    """DTO de salida para una operación individual."""

    operation_id: str
    user_id: str
    server_id: str
    kit_id: str
    values: dict
    sudo: bool
    status: str
    debug_level: str
    output: str
    backup_files: tuple
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime]
    finished_at: Optional[datetime]


@dataclass(frozen=True)
class OperationListResult:
    """DTO de salida para listado paginado de operaciones."""

    items: tuple
    total: int
    page: int
    per_page: int


@dataclass(frozen=True)
class RestoreResult:
    """DTO de salida para restauración de backup."""

    operation_id: str
    restored_files: tuple
