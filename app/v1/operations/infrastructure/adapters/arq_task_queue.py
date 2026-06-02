"""ARQTaskQueue — placeholder adaptador TaskQueue usando ARQ + Valkey (v2)."""
from typing import Any, Callable, Coroutine

from app.v1.operations.application.interfaces.task_queue import TaskQueue


class ARQTaskQueue(TaskQueue):
    """Placeholder para la implementación ARQ + Valkey del puerto TaskQueue.

    Esta implementación se completará en v2 cuando se migre a microservicios.
    Por ahora satisface el contrato del puerto para que el wiring pueda instanciarla.
    """

    async def enqueue(
        self,
        task_fn: Callable[..., Coroutine[Any, Any, None]],
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """Encola la tarea en ARQ/Valkey (pendiente de implementar en v2)."""
        raise NotImplementedError(
            "ARQTaskQueue está pendiente de implementación en v2. "
            "Usa FastAPITaskQueue en el entorno actual."
        )
