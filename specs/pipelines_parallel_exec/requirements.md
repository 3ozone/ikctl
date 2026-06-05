# Requirements — pipelines_parallel_exec

> Especificación en notación EARS. Cada requirement tiene un id estable (R<n>)
> y DEBE ser verificable por al menos un test concreto.

---

## R1 — Ejecución paralela de operaciones

CUANDO `ExecutePipelineOperations` lanza las N×M operaciones de un pipeline,
el sistema DEBE ejecutar el lanzamiento de todas las operaciones de forma
concurrente mediante `asyncio.gather`, en lugar de de forma secuencial.

## R2 — Límite de concurrencia configurable

El sistema DEBE aceptar un parámetro `max_concurrency: int` en el constructor
de `ExecutePipelineOperations` que limite el número máximo de lanzamientos
SSH simultáneos mediante un `asyncio.Semaphore`.

## R3 — Valor por defecto del Semaphore

El sistema DEBE usar `max_concurrency = 10` como valor por defecto cuando
no se proporciona ningún valor en el constructor de `ExecutePipelineOperations`.

## R4 — Semaphore configurable desde Settings

El sistema DEBE leer el valor de `max_concurrency` desde la configuración
centralizada (`Settings.PIPELINE_MAX_CONCURRENCY`) de forma que pueda
ajustarse sin modificar código.

## R5 — Soporte de mínimo 50 operaciones concurrentes

CUANDO `PIPELINE_MAX_CONCURRENCY` se configure con un valor de 50 o superior,
el sistema DEBE completar el lanzamiento de 50 operaciones SSH simultáneas
sin degradación de correctitud (sin pérdida de operation_ids ni excepciones
no controladas).

## R6 — Preservación del orden de operation_ids

CUANDO el lanzamiento paralelo de operaciones finaliza,
el sistema DEBE preservar el mismo orden de `operation_ids` que si la
ejecución hubiera sido secuencial (un id por cada combinación server×kit,
en el mismo orden de iteración).

## R7 — Propagación de errores parciales

SI una o más operaciones fallan durante el lanzamiento paralelo (lanza
excepción en `OperationLauncher.launch`), ENTONCES el sistema DEBE capturar
el error, registrarlo con el logger, continuar con las operaciones restantes
y, al finalizar, marcar la `PipelineExecution` como `failed`.

## R8 — Polling sin cambios de semántica

MIENTRAS la ejecución del pipeline está en estado `in_progress`,
el sistema DEBE mantener el mismo comportamiento de polling, timeout y
cancelación que existía antes de esta feature (sin regresiones sobre R8–R11
de `pipelines_cancel_timeout`).
