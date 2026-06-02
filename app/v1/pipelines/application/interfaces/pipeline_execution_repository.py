"""Port PipelineExecutionRepository — interfaz abstracta del repositorio de ejecuciones."""
from abc import ABC, abstractmethod
from typing import Optional

from app.v1.pipelines.domain.entities.pipeline_execution import PipelineExecution


class PipelineExecutionRepository(ABC):
    """Contrato que la infraestructura debe implementar para persistir ejecuciones de pipeline."""

    @abstractmethod
    async def save(self, execution: PipelineExecution) -> None:
        """Persiste una nueva ejecución de pipeline."""

    @abstractmethod
    async def find_by_id(self, execution_id: str) -> Optional[PipelineExecution]:
        """Busca una ejecución por ID (sin scope de usuario — se valida en use case)."""

    @abstractmethod
    async def find_by_pipeline_id(self, pipeline_id: str, page: int, per_page: int) -> tuple[list[PipelineExecution], int]:
        """Lista ejecuciones de un pipeline con paginación (1-based).

        Returns:
            Tupla (lista de ejecuciones, total de resultados).
        """

    @abstractmethod
    async def update(self, execution: PipelineExecution) -> None:
        """Actualiza los campos de una ejecución existente."""

    @abstractmethod
    async def find_latest_by_pipeline(self, pipeline_id: str) -> Optional[PipelineExecution]:
        """Devuelve la ejecución más reciente de un pipeline (para validaciones)."""