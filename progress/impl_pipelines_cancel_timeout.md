# Implementación — pipelines_cancel_timeout (feature id 6)

## Trazabilidad R<n> → test

| Requirement | Test(s) |
|-------------|---------|
| R1 — Endpoint de cancelación | `tests/v1/pipelines/test_presentation/test_cancel_endpoint.py::test_cancel_in_progress_returns_200` |
| R2 — Transición in_progress → cancelled | `tests/v1/pipelines/test_domain/test_pipeline_execution_cancel.py::test_cancel_in_progress_transitions_to_cancelled`, `test_cancel_registers_finished_at` |
| R3 — Cancelación de operaciones pendientes | `tests/v1/pipelines/test_use_cases/test_cancel_pipeline_execution.py::TestCancelInProgressSuccess::test_cancel_cancels_pending_operations`, `test_cancel_cancels_in_progress_operations` |
| R4 — Evento PipelineExecutionCancelled | `tests/v1/pipelines/test_use_cases/test_cancel_pipeline_execution.py::TestCancelPublishesEvent::test_cancel_publishes_event`, `tests/v1/pipelines/test_domain/test_pipeline_execution_cancelled_event.py` |
| R5 — Rechazo en estado terminal | `tests/v1/pipelines/test_domain/test_pipeline_execution_cancel.py::test_cancel_terminal_raises_error`, `tests/v1/pipelines/test_presentation/test_cancel_endpoint.py::test_cancel_completed_returns_422` |
| R6 — Rechazo en estado pending | `tests/v1/pipelines/test_domain/test_pipeline_execution_cancel.py::test_cancel_pending_raises_error`, `tests/v1/pipelines/test_presentation/test_cancel_endpoint.py::test_cancel_pending_returns_422` |
| R7 — Ownership en cancelación | `tests/v1/pipelines/test_use_cases/test_cancel_pipeline_execution.py::TestCancelNotOwnerRaises::test_cancel_not_owner_raises_404`, `tests/v1/pipelines/test_presentation/test_cancel_endpoint.py::test_cancel_not_owner_returns_404` |
| R8 — Timeout: in_progress → cancelled_unsafe | `tests/v1/pipelines/test_use_cases/test_execute_pipeline_timeout.py::TestTimeoutCancelsInProgressOperations::test_timeout_cancels_in_progress_operations` |
| R9 — Timeout: pending → cancelled | `tests/v1/pipelines/test_use_cases/test_execute_pipeline_timeout.py::TestTimeoutCancelsPendingOperations::test_timeout_cancels_pending_operations` |
| R10 — Timeout: ejecución → failed | `tests/v1/pipelines/test_use_cases/test_execute_pipeline_timeout.py::TestTimeoutMarksExecutionAsFailed::test_timeout_marks_execution_failed`, `tests/v1/pipelines/test_domain/test_pipeline_execution_cancel.py::test_mark_timeout_failed_in_progress_transitions_to_failed` |
| R11 — Timeout: persistir operaciones canceladas | `tests/v1/pipelines/test_use_cases/test_execute_pipeline_timeout.py::TestTimeoutPersistsCancelledOperations::test_timeout_persists_cancelled_operations` |

## Archivos creados / modificados

| Archivo | Tipo |
|---------|------|
| `app/v1/pipelines/domain/value_objects/pipeline_status.py` | Modificado |
| `app/v1/pipelines/domain/entities/pipeline_execution.py` | Modificado |
| `app/v1/pipelines/domain/exceptions/pipeline_execution.py` | Modificado |
| `app/v1/pipelines/domain/events/pipeline_execution_cancelled.py` | Creado |
| `app/v1/pipelines/application/interfaces/operation_cancel_port.py` | Creado |
| `app/v1/pipelines/application/dtos/pipeline_dtos.py` | Modificado |
| `app/v1/pipelines/application/commands/cancel_pipeline_execution.py` | Creado |
| `app/v1/pipelines/application/tasks/execute_pipeline_operations.py` | Modificado |
| `app/v1/pipelines/infrastructure/adapters/operation_cancel_adapter.py` | Creado |
| `app/v1/pipelines/infrastructure/presentation/schemas.py` | Modificado |
| `app/v1/pipelines/infrastructure/presentation/routes.py` | Modificado |
| `app/v1/pipelines/infrastructure/presentation/deps.py` | Modificado |
| `app/v1/pipelines/infrastructure/presentation/exception_handlers.py` | Modificado |
| `main.py` | Modificado |
| `docs/architecture.md` | Modificado |

## Resultado de tests

**1061 passed, 4 failed** (los 4 failures son preexistentes en credential presentation, no relacionados con esta feature).
