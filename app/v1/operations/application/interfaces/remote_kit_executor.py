"""Port RemoteKitExecutor — abstrae los 6 pasos de ejecución SSH de un kit.

Implementación concreta en infrastructure/adapters/ssh_kit_executor.py.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from app.v1.kits.domain.entities.kit import Kit
from app.v1.servers.domain.entities.credential import Credential
from app.v1.servers.domain.entities.server import Server


class RemoteKitExecutor(ABC):
    """Contrato para ejecutar un kit en un servidor remoto.

    Abstrae los 6 pasos: snapshot → git clone → render Jinja2 → transferencia
    SFTP con caché SHA-256 → ejecución pipeline → limpieza.

    Returns:
        Tupla (output: str, backup_files: tuple[str, ...]).

    Raises:
        Exception: cualquier error durante la ejecución SSH.
    """

    @abstractmethod
    async def execute(
        self,
        server: Server,
        kit: Kit,
        credential: Credential,
        debug_level: str,
        values: dict,
        sudo: bool = False,
    ) -> tuple[str, tuple[str, ...]]:
        """Ejecuta el kit en el servidor. Devuelve (output, backup_files)."""
