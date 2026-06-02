"""Port CredentialRepository (cross-module) — T-09.

Port propio del módulo operations para acceder a credenciales sin filtro de
ownership. El adapter en main.py delega al SQLAlchemyCredentialRepository de servers.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from app.v1.servers.domain.entities.credential import Credential


class CredentialRepository(ABC):
    """Contrato de solo lectura sobre credenciales (uso interno de tasks)."""

    @abstractmethod
    async def find_by_id_internal(self, credential_id: str) -> Optional[Credential]:
        """Devuelve la credencial por id sin validar ownership, o None si no existe."""
