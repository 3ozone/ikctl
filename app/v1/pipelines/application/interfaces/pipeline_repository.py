"""Port PipelineRepository — interfaz abstracta del repositorio de pipelines."""
from abc import ABC, abstractmethod
from typing import Optional

from app.v1.pipelines.domain.entities.pipeline import Pipeline


class PipelineRepository(ABC):
    """Contrato que la infraestructura debe implementar para persistir pipelines."""

    @abstractmethod
    async def save(self, pipeline: Pipeline) -> None:
        """Persiste un nuevo pipeline."""

    @abstractmethod
    async def find_by_id(self, pipeline_id: str, user_id: str) -> Optional[Pipeline]:
        """Busca un pipeline por ID scoped al usuario propietario."""

    @abstractmethod
    async def find_all_by_user(self, user_id: str, page: int, per_page: int) -> list[Pipeline]:
        """Lista pipelines del usuario con paginación (1-based)."""

    @abstractmethod
    async def update(self, pipeline: Pipeline) -> None:
        """Actualiza los campos de un pipeline existente."""

    @abstractmethod
    async def delete(self, pipeline_id: str) -> None:
        """Elimina un pipeline por ID."""

    @abstractmethod
    async def has_active_executions(self, pipeline_id: str) -> bool:
        """Comprueba si el pipeline tiene ejecuciones activas (pending o in_progress)."""

    @abstractmethod
    async def find_by_id_no_ownership(self, pipeline_id: str) -> Optional[Pipeline]:
        """Busca un pipeline por ID sin validar ownership (uso interno de tasks)."""