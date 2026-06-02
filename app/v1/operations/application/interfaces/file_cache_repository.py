"""Port FileCacheRepository — T-05."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional


class FileCacheRepository(ABC):
    """Contrato para la caché SHA-256 de ficheros transferidos por SFTP.

    Permite la transferencia diferencial: solo se re-sube un fichero
    si su hash post-render ha cambiado respecto al último upload.
    """

    @abstractmethod
    async def find_hash(
        self, server_id: str, kit_id: str, filename: str
    ) -> Optional[str]:
        """Devuelve el SHA-256 almacenado para (server_id, kit_id, filename), o None."""

    @abstractmethod
    async def upsert(
        self,
        server_id: str,
        kit_id: str,
        filename: str,
        content_hash: str,
    ) -> None:
        """Inserta o actualiza el hash para (server_id, kit_id, filename)."""

    @abstractmethod
    async def invalidate_server_kit(self, server_id: str, kit_id: str) -> None:
        """Elimina todas las entradas de caché para (server_id, kit_id).

        Usado en auto-repair (RNF-15): si el directorio temporal no existe
        en el servidor, se invalida la caché para forzar re-transferencia completa.
        """
