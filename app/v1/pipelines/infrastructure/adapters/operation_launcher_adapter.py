"""OperationLauncherAdapter — Adapter que envuelve LaunchOperation del módulo operations.

Implementa el port OperationLauncher del módulo pipelines, delegando
la llamada al use case LaunchOperation in-process (sin llamadas HTTP).
"""
from typing import Optional

from app.v1.pipelines.application.interfaces.operation_launcher import OperationLauncher


class OperationLauncherAdapter(OperationLauncher):
    """Adapter que envuelve LaunchOperation para lanzar operaciones individuales.

    Desacopla el módulo pipelines de la implementación concreta de operations.
    """

    def __init__(self, launch_operation) -> None:
        self._launch_operation = launch_operation

    async def launch(
        self,
        user_id: str,
        server_id: str,
        kit_id: str,
        values: Optional[dict] = None,
        sudo: bool = False,
        debug_level: str = "none",
    ) -> str:
        result = await self._launch_operation.execute(
            user_id=user_id,
            server_id=server_id,
            kit_id=kit_id,
            values=values,
            sudo=sudo,
            debug_level=debug_level,
        )
        return result.operation_id