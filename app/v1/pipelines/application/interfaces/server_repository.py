"""Port ServerRepository (cross-module, read-only) — T-09.1.

Port propio del módulo pipelines para acceder a servidores y grupos sin
filtro de ownership. El adapter en main.py delega a los repositorios del
módulo servers.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from app.v1.servers.domain.entities.server import Server
from app.v1.servers.domain.entities.group import Group


class ServerRepository(ABC):
    """Contrato de solo lectura sobre servidores y grupos (uso interno de tasks)."""

    @abstractmethod
    async def find_server_by_id_internal(self, server_id: str) -> Optional[Server]:
        """Devuelve el servidor por id sin validar ownership, o None si no existe."""

    @abstractmethod
    async def find_group_by_id_internal(self, group_id: str) -> Optional[Group]:
        """Devuelve el grupo por id sin validar ownership, o None si no existe."""

    @abstractmethod
    async def find_servers_by_ids(self, server_ids: list[str]) -> list[Server]:
        """Devuelve todos los servidores cuyos ids estén en la lista."""
