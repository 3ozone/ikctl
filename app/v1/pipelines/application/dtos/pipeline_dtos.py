"""DTOs del módulo pipelines — T-18.1."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class PipelineResult:
    """DTO de salida para un pipeline individual (CreatePipeline, UpdatePipeline, GetPipeline)."""

    pipeline_id: str
    user_id: str
    name: str
    description: Optional[str]
    # targets: tuple de dicts {"server_id": str, "type": str}
    targets: tuple
    # kits: tuple de dicts {"kit_id": str, "sudo": bool|None, "debug_level": str|None}
    kits: tuple
    values: dict
    sudo: bool
    debug_level: str
    created_at: Optional[datetime]
    updated_at: Optional[datetime]


@dataclass(frozen=True)
class PipelineListResult:
    """DTO de salida para listado paginado de pipelines."""

    items: tuple  # tuple[PipelineResult]
    total: int
    page: int
    per_page: int


@dataclass(frozen=True)
class PipelineExecutionResult:
    """DTO de salida para el lanzamiento de un pipeline (LaunchPipeline).

    Devuelve el estado inicial (pending) y el snapshot inmutable de la config.
    """

    execution_id: str
    pipeline_id: str
    user_id: str
    status: str
    snapshot: dict
    created_at: Optional[datetime]


@dataclass(frozen=True)
class PipelineExecutionSummary:
    """Resumen de una ejecución para el listado paginado (GetPipelineExecutions)."""

    execution_id: str
    pipeline_id: str
    status: str
    total_operations: int
    completed_operations: int
    failed_operations: int
    created_at: Optional[datetime]
    started_at: Optional[datetime]
    finished_at: Optional[datetime]


@dataclass(frozen=True)
class PipelineExecutionListResult:
    """DTO de salida para listado paginado de ejecuciones de un pipeline."""

    items: tuple  # tuple[PipelineExecutionSummary]
    total: int
    page: int
    per_page: int


@dataclass(frozen=True)
class PipelineOperationItem:
    """Detalle de una operación individual dentro de una ejecución."""

    operation_id: str
    server_id: str
    kit_id: str
    status: str
    output: str
    error: Optional[str]


@dataclass(frozen=True)
class PipelineExecutionDetailResult:
    """DTO de salida para el detalle de una ejecución (GetPipelineExecutionDetail).

    Incluye snapshot inmutable + lista completa de operaciones con su estado.
    """

    execution_id: str
    pipeline_id: str
    user_id: str
    status: str
    snapshot: dict
    operations: tuple  # tuple[PipelineOperationItem]
    created_at: Optional[datetime]
    started_at: Optional[datetime]
    finished_at: Optional[datetime]


@dataclass(frozen=True)
class PipelineExecutionCancelDTO:
    """DTO de salida para la cancelación de una ejecución de pipeline."""

    execution_id: str
    pipeline_id: str
    user_id: str
    status: str
    finished_at: Optional[datetime]
