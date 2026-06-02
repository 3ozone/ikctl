"""Tests unitarios para FastAPITaskQueue (T-19) y ARQTaskQueue (T-20)."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import BackgroundTasks


# ---------------------------------------------------------------------------
# T-19 — FastAPITaskQueue
# ---------------------------------------------------------------------------


async def test_fastapi_task_queue_enqueue_calls_background_tasks():
    """FastAPITaskQueue.enqueue delega en BackgroundTasks.add_task con args y kwargs."""
    from app.v1.operations.infrastructure.adapters.fastapi_task_queue import (
        FastAPITaskQueue,
    )

    bg = MagicMock(spec=BackgroundTasks)
    queue = FastAPITaskQueue(bg)

    async def dummy_task(a: str, b: int = 0) -> None:
        pass

    await queue.enqueue(dummy_task, "op-1", b=42)

    bg.add_task.assert_called_once_with(dummy_task, "op-1", b=42)


async def test_fastapi_task_queue_enqueue_multiple_tasks():
    """FastAPITaskQueue.enqueue puede llamarse múltiples veces."""
    from app.v1.operations.infrastructure.adapters.fastapi_task_queue import (
        FastAPITaskQueue,
    )

    bg = MagicMock(spec=BackgroundTasks)
    queue = FastAPITaskQueue(bg)

    async def noop(*args, **kwargs) -> None:
        pass

    await queue.enqueue(noop, "op-1")
    await queue.enqueue(noop, "op-2")

    assert bg.add_task.call_count == 2


async def test_fastapi_task_queue_implements_task_queue_port():
    """FastAPITaskQueue es una implementación válida del puerto TaskQueue."""
    from app.v1.operations.application.interfaces.task_queue import TaskQueue
    from app.v1.operations.infrastructure.adapters.fastapi_task_queue import (
        FastAPITaskQueue,
    )

    bg = MagicMock(spec=BackgroundTasks)
    queue = FastAPITaskQueue(bg)
    assert isinstance(queue, TaskQueue)


# ---------------------------------------------------------------------------
# T-20 — ARQTaskQueue (placeholder)
# ---------------------------------------------------------------------------


async def test_arq_task_queue_implements_task_queue_port():
    """ARQTaskQueue es una implementación válida del puerto TaskQueue."""
    from app.v1.operations.application.interfaces.task_queue import TaskQueue
    from app.v1.operations.infrastructure.adapters.arq_task_queue import ARQTaskQueue

    queue = ARQTaskQueue()
    assert isinstance(queue, TaskQueue)
