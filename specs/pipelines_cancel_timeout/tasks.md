# Tasks — pipelines_cancel_timeout

> Checklist ejecutable. Cada task referencia al menos un R<n> del requirements.md.
> El implementer marca `[x]` al completar.

---

## Domain layer

- [x] T1 — Añadir `"cancelled"` a `_VALID_VALUES` y `_TERMINAL_STATES` en `PipelineStatus`. Actualizar docstring. Cubre: R2, R5.
- [x] T2 — Añadir método `cancel()` a `PipelineExecution` que transicione `in_progress → cancelled` y registre `finished_at`. Lanza `InvalidPipelineStatusError` si no está en `in_progress`. Cubre: R2.
- [x] T3 — Añadir método `mark_timeout_failed()` a `PipelineExecution` que transicione `in_progress → failed` y registre `finished_at`. Lanza `InvalidPipelineStatusError` si no está en `in_progress`. Cubre: R10.
- [x] T4 — Añadir `PipelineExecutionNotCancellableError(DomainException)` en `app/v1/pipelines/domain/exceptions/pipeline_execution.py`. Cubre: R5, R6.
- [x] T5 — Crear evento `PipelineExecutionCancelled` en `app/v1/pipelines/domain/events/pipeline_execution_cancelled.py`. Hereda de `DomainEvent`, campos: `execution_id`, `pipeline_id`, `user_id`, `correlation_id`. Cubre: R4.
- [x] T6 — Crear tests de dominio en `tests/v1/pipelines/test_domain/test_pipeline_execution_cancel.py`: `test_cancel_in_progress_transitions_to_cancelled`, `test_cancel_pending_raises_error` (R6), `test_cancel_terminal_raises_error` (R5), `test_cancel_registers_finished_at`. Cubre: R2, R5, R6.
- [x] T7 — Crear tests de dominio para `mark_timeout_failed` en el mismo archivo: `test_mark_timeout_failed_in_progress_transitions_to_failed`, `test_mark_timeout_failed_pending_raises_error`. Cubre: R10.
- [x] T8 — Crear tests en `tests/v1/pipelines/test_domain/test_pipeline_status_cancelled.py`: `test_cancelled_is_valid`, `test_cancelled_is_terminal`. Cubre: R2, R5.
- [x] T9 — Crear tests del evento en `tests/v1/pipelines/test_domain/test_pipeline_execution_cancelled_event.py`: `test_event_creation`, `test_event_serialization`. Cubre: R4.

## Application layer — Command

- [x] T10 — Crear port `OperationCancelPort` en `app/v1/pipelines/application/interfaces/operation_cancel_port.py`. Método abstracto: `cancel_operation(operation_id: str, user_id: str) -> None`. Cubre: R3.
- [x] T11 — Añadir `PipelineExecutionCancelDTO` en `app/v1/pipelines/application/dtos/pipeline_dtos.py`. Campos: `execution_id`, `pipeline_id`, `user_id`, `status`, `finished_at`. Cubre: R1.
- [x] T12 — Crear `CancelPipelineExecution` command en `app/v1/pipelines/application/commands/cancel_pipeline_execution.py`. Flujo: validar ownership, validar execution pertenece al pipeline, `execution.cancel()`, cancelar operaciones pendientes/en progreso vía `OperationCancelPort`, persistir execution, publicar evento. Cubre: R1, R2, R3, R4, R5, R6, R7.
- [x] T13 — Crear tests de use case en `tests/v1/pipelines/test_use_cases/test_cancel_pipeline_execution.py`: `test_cancel_in_progress_success` (R1, R2, R3), `test_cancel_pending_raises` (R6), `test_cancel_terminal_raises` (R5), `test_cancel_not_owner_raises` (R7), `test_cancel_publishes_event` (R4). Cubre: R1–R7.

## Application layer — Timeout efectivo

- [x] T14 — Modificar `_poll_until_all_terminal` en `ExecutePipelineOperations`: en vez de lanzar `asyncio.TimeoutError`, al exceder timeout obtener las operaciones no terminales, cancelar cada una (pending → cancelled, in_progress → cancelled_unsafe) vía `OperationCancelPort`, y devolver los estados finales. Cubre: R8, R9, R11.
- [x] T15 — Modificar `execute()` en `ExecutePipelineOperations`: inyectar `OperationCancelPort`. Simplificar el `except Exception` para que marque `mark_timeout_failed()` cuando el timeout se maneja internamente. Cubre: R10.
- [x] T16 — Añadir `OperationCancelPort` al constructor de `ExecutePipelineOperations`. Cubre: R8, R9.
- [x] T17 — Crear tests en `tests/v1/pipelines/test_use_cases/test_execute_pipeline_timeout.py`: `test_timeout_cancels_pending_operations` (R9), `test_timeout_cancels_in_progress_operations` (R8), `test_timeout_marks_execution_as_failed` (R10), `test_timeout_persists_cancelled_operations` (R11), `test_timeout_mixed_statuses`. Cubre: R8–R11.

## Infrastructure layer — Adapter

- [x] T18 — Crear `OperationCancelAdapter` en `app/v1/pipelines/infrastructure/adapters/operation_cancel_adapter.py`. Delega a `CancelOperation` del módulo operations. Cubre: R3, R8, R9.

## Presentation layer

- [x] T19 — Añadir `PipelineExecutionCancelResponse` schema en `app/v1/pipelines/infrastructure/presentation/schemas.py`. Campos: `execution_id`, `pipeline_id`, `user_id`, `status`, `finished_at`. Cubre: R1.
- [x] T20 — Añadir endpoint `POST /api/v1/pipelines/{pipeline_id}/executions/{execution_id}/cancel` en `routes.py`. Inyecta `CancelPipelineExecution` vía `deps.py`. Devuelve 200 con `PipelineExecutionCancelResponse`. Cubre: R1.
- [x] T21 — Añadir `get_cancel_pipeline_execution_uc` en `deps.py` con wiring completo (pipeline_repo, execution_repo, operation_cancel_adapter, event_bus). Cubre: R1.
- [x] T22 — Añadir handler para `PipelineExecutionNotCancellableError` en `exception_handlers.py` → 422. Cubre: R5, R6.
- [x] T23 — Crear tests de presentación en `tests/v1/pipelines/test_presentation/test_cancel_endpoint.py`: `test_cancel_in_progress_returns_200` (R1), `test_cancel_pending_returns_422` (R6), `test_cancel_completed_returns_422` (R5), `test_cancel_not_owner_returns_404` (R7). Cubre: R1, R5, R6, R7.

## Composition Root

- [x] T24 — Actualizar `main.py`: wiring de `OperationCancelAdapter` y actualización del closure `_execute_pipeline_fn` para incluir el nuevo `OperationCancelPort`. Cubre: R8, R9.

## Event catalog update

- [x] T25 — Actualizar `docs/architecture.md`: añadir `PipelineExecutionCancelled` al catálogo de eventos de pipelines, y añadir `cancelled` al ciclo de vida de `PipelineExecution`. Cubre: R4, R2.