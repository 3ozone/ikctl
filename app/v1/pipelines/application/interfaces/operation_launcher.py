"""Port OperationLauncher — abstrae el lanzamiento de operaciones individuales."""
from abc import ABC, abstractmethod
from typing import Optional


class OperationLauncher(ABC):
    """Contrato para lanzar una operación individual del módulo operations.

    Desacopla el módulo pipelines de la implementación concreta de LaunchOperation.
    """

    @abstractmethod
    async def launch(
        self,
        user_id: str,
        server_id: str,
        kit_id: str,
        values: Optional[dict] = None,
        sudo: bool = False,
        debug_level: str = "none",
    ) -> str:
        """Lanza una operación individual y devuelve el operation_id generado."""