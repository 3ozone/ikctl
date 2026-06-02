"""Port GitRepositoryPort (cross-module) — lectura de Repository por id sin ownership.

Port propio del módulo operations para acceder a repositorios git sin filtro de
ownership. Usado por SSHKitExecutor para obtener URL y credencial del repo al clonar.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from app.v1.kits.domain.entities.repository import Repository


class GitRepositoryPort(ABC):
    """Contrato de solo lectura sobre repositorios git (uso interno de tasks)."""

    @abstractmethod
    async def find_by_id_internal(self, repository_id: str) -> Optional[Repository]:
        """Devuelve el repositorio por id sin validar ownership, o None si no existe."""
