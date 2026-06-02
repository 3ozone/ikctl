"""FastAPITaskQueue — adaptador TaskQueue usando FastAPI BackgroundTasks (v1)."""
from typing import Any, Callable, Coroutine

from fastapi import BackgroundTasks

from app.v1.operations.application.interfaces.task_queue import TaskQueue


class FastAPITaskQueue(TaskQueue):
    """Implementación del puerto TaskQueue usando FastAPI BackgroundTasks.

    En v1 las tareas se ejecutan en el mismo proceso tras responder la petición.
    En v2 se sustituirá por ARQTaskQueue sin cambiar dominio ni use cases.
    """

    def __init__(self, background_tasks: BackgroundTasks) -> None:
        self._bg = background_tasks

    async def enqueue(
        self,
        task_fn: Callable[..., Coroutine[Any, Any, None]],
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """Delega en BackgroundTasks.add_task para ejecución diferida."""
        self._bg.add_task(task_fn, *args, **kwargs)
