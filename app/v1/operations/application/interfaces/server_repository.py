"""Port ServerRepository (cross-module) — T-07.

Port propio del módulo operations para acceder a servidores sin filtro de
ownership. El adapter en main.py delega al SQLAlchemyServerRepository de servers.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from app.v1.servers.domain.entities.server import Server


class ServerRepository(ABC):
    """Contrato de solo lectura sobre servidores (uso interno de tasks)."""

    @abstractmethod
    async def find_by_id_internal(self, server_id: str) -> Optional[Server]:
        """Devuelve el servidor por id sin validar ownership, o None si no existe."""
