"""Port TaskQueue — T-06."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Callable, Coroutine


class TaskQueue(ABC):
    """Contrato para encolar tareas asíncronas en background.

    v1: implementado con FastAPI BackgroundTasks (InMemory).
    v2: implementado con ARQ + Valkey (sin cambiar dominio ni use cases).
    """

    @abstractmethod
    async def enqueue(
        self,
        task_fn: Callable[..., Coroutine[Any, Any, None]],
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """Encola una corutina para ejecución en background."""
