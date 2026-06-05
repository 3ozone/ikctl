# Requirements — pipelines_cancel_timeout

> Especificación en notación EARS. Cada requirement tiene un id estable (R<n>)
> y DEBE ser verificable por al menos un test concreto.

---

## R1 — Endpoint de cancelación

CUANDO el usuario envía POST /api/v1/pipelines/{pipeline_id}/executions/{execution_id}/cancel,
el sistema DEBE cancelar la PipelineExecution y devolver 200 con el estado actualizado.

## R2 — Transición in_progress → cancelled

CUANDO el usuario cancela una PipelineExecution en estado in_progress,
el sistema DEBE transicionar la PipelineExecution de in_progress a cancelled
y registrar finished_at con la fecha/hora UTC de la cancelación.

## R3 — Cancelación de operaciones pendientes

CUANDO el usuario cancela una PipelineExecution en estado in_progress,
el sistema DEBE marcar todas las operaciones pendientes (status pending)
de esa ejecución como cancelled.

## R4 — Evento PipelineExecutionCancelled

CUANDO el usuario cancela una PipelineExecution,
el sistema DEBE publicar un evento de dominio PipelineExecutionCancelled
con los campos execution_id, pipeline_id, user_id y correlation_id.

## R5 — Rechazo de cancelación en estado no cancelable

SI el usuario intenta cancelar una PipelineExecution en un estado terminal (completed, failed, partial)
ENTONCES el sistema DEBE devolver error 422 con un mensaje indicando que la ejecución no puede cancelarse.

## R6 — Rechazo de cancelación en estado pending

SI el usuario intenta cancelar una PipelineExecution en estado pending
ENTONCES el sistema DEBE devolver error 422 con un mensaje indicando que la ejecución aún no ha comenzado.

## R7 — Ownership en cancelación

SI el usuario intenta cancelar una PipelineExecution de un pipeline que no le pertenece
ENTONCES el sistema DEBE devolver error 404.

## R8 — Timeout efectivo: operaciones pendientes → cancelled_unsafe

CUANDO el polling en ExecutePipelineOperations excede el timeout global,
el sistema DEBE marcar todas las operaciones que aún están en estado in_progress
como cancelled_unsafe.

## R9 — Timeout efectivo: operaciones pendientes (sin ejecutar) → cancelled

CUANDO el polling en ExecutePipelineOperations excede el timeout global,
el sistema DEBE marcar todas las operaciones que aún están en estado pending
como cancelled.

## R10 — Timeout efectivo: ejecución → failed

CUANDO el polling excede el timeout global y las operaciones han sido marcadas como cancelled/cancelled_unsafe,
el sistema DEBE transicionar la PipelineExecution al estado failed
con finished_at registrando la fecha/hora UTC del timeout.

## R11 — Timeout efectivo: persistir operaciones canceladas

CUANDO el polling excede el timeout global,
el sistema DEBE persistir en la base de datos el estado cancelled o cancelled_unsafe
de cada operación antes de calcular el estado agregado de la ejecución.