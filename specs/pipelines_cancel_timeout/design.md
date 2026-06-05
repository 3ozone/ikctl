# Design — pipelines_cancel_timeout

> Decisiones técnicas para la feature de cancelación y timeout efectivo.
> Se apoya en `docs/architecture.md` y `docs/conventions.md`.

---

## 1. Domain: extensión de PipelineExecution

### Novedades

- **Método `cancel()`** en `PipelineExecution`: transiciona `in_progress → cancelled` y
  registra `finished_at`. Lanza `InvalidPipelineStatusError` si no está en `in_progress`.
- **Método `mark_timeout_failed()`** en `PipelineExecution`: transiciona
  `in_progress → failed` y registra `finished_at`. Se usa cuando el timeout marca
  la ejecución como fallida tras cancelar operaciones.
- **Valor `cancelled` añadido a `_VALID_VALUES` y `_TERMINAL_STATES`** en `PipelineStatus`.
  Esto redefine el ciclo de vida:
  - pending → in_progress → completed | failed | partial | cancelled

### Decisión

El estado `cancelled` es terminal. Una PipelineExecution cancelada NO puede
reanudarse. Esto es coherente con las operaciones individuales que también
tienen estados `cancelled` y `cancelled_unsafe` como terminales.

### Alternativa descartada

Añadir un estado `cancelling` intermedio (in_progress → cancelling → cancelled).
Se descarta porque no aporta valor: la cancelación es síncrona desde el
punto de vista del aggregate. Las operaciones se cancelan en el mismo request
o en el mismo ciclo de polling del timeout.

---

## 2. Domain: evento PipelineExecutionCancelled

Nuevo archivo `app/v1/pipelines/domain/events/pipeline_execution_cancelled.py`.

```python
class PipelineExecutionCancelled(DomainEvent):
    """Evento publicado cuando se cancela una ejecución de pipeline."""
    def __init__(self, execution_id, pipeline_id, user_id, correlation_id): ...
```

Hereda de `DomainEvent` (shared kernel). Sigue el patrón de `OperationCancelled`
del módulo operations.

---

## 3. Domain: excepción PipelineExecutionNotCancellableError

Nuevo archivo `app/v1/pipelines/domain/exceptions/pipeline_execution.py`.

Añadir `PipelineExecutionNotCancellableError(DomainException)` para los
casos R5 (estado terminal) y R6 (estado pending).

### Decisión

Usar dos subtipos del mismo check en el command: si la ejecución está en
`pending`, el mensaje dice "aún no ha comenzado"; si está en terminal,
dice "ya ha terminado". Ambos lanzan `PipelineExecutionNotCancellableError`
con el mensaje apropiado. La capa de presentación lo mapea a 422.

---

## 4. Application: command CancelPipelineExecution

Nuevo archivo `app/v1/pipelines/application/commands/cancel_pipeline_execution.py`.

```python
class CancelPipelineExecution:
    def __init__(
        self,
        pipeline_repository: PipelineRepository,
        execution_repository: PipelineExecutionRepository,
        operation_cancel_port: OperationCancelPort,  # nuevo port
        event_bus: EventBus,
    ): ...

    async def execute(self, user_id: str, pipeline_id: str, execution_id: str) -> PipelineExecutionCancelDTO:
```

### Flujo

1. Cargar pipeline y validar ownership (RN-01).
2. Cargar execution por ID.
3. Validar que execution pertenece al pipeline.
4. Llamar `execution.cancel()` → transición `in_progress → cancelled`.
5. Para cada `operation_id` en `execution.operation_ids`:
   - Obtener la operación vía `OperationRepository.find_by_id_internal`.
   - Si está en `pending` → `operation.cancel(now)`.
   - Si está en `in_progress` → `operation.cancel_unsafe(now)`.
   - Si ya está en estado terminal → skip.
   - Persistir vía port de cancelación de operaciones.
6. Persistir la execution actualizada.
7. Publicar evento `PipelineExecutionCancelled`.

### Port: OperationCancelPort

Nuevo archivo `app/v1/pipelines/application/interfaces/operation_cancel_port.py`.

```python
class OperationCancelPort(ABC):
    @abstractmethod
    async def cancel_operation(self, operation_id: str, user_id: str) -> None:
        """Cancela una operación individual (pending → cancelled, in_progress → cancelled_unsafe)."""
```

**¿Por qué un port nuevo y no reutilizar el OperationRepository existente?**

El `OperationRepository` en pipelines es read-only (`find_by_id_internal`).
Para cancelar operaciones necesitamos mutarlas, lo cual cruza la frontera del
módulo. El patrón del proyecto es usar un port local en `application/interfaces/`
y un adapter en `infrastructure/adapters/`.

**Alternativa descartada:** Importar `CancelOperation` directamente del módulo
operations. Viola la regla de "no importar application/ de otro módulo".

**El adapter** `OperationCancelAdapter` delegará al `CancelOperation` command
del módulo operations, obteniendo sus dependencias en `main.py`.

### DTO: PipelineExecutionCancelDTO

Nuevo DTO en `app/v1/pipelines/application/dtos/pipeline_dtos.py`.

```python
@dataclass(frozen=True)
class PipelineExecutionCancelDTO:
    execution_id: str
    pipeline_id: str
    user_id: str
    status: str
    finished_at: datetime | None
```

---

## 5. Application: modificación de ExecutePipelineOperations (timeout efectivo)

Archivo existente: `app/v1/pipelines/application/tasks/execute_pipeline_operations.py`.

### Cambio principal

En `_poll_until_all_terminal`, cuando se excede el timeout, en lugar de lanzar
`asyncio.TimeoutError` y dejar que el handler genérico marque todo como `failed`,
se debe:

1. Identificar las operaciones que aún no son terminales (pending o in_progress).
2. Para cada una:
   - Si `pending` → `cancel(now)`.
   - Si `in_progress` → `cancel_unsafe(now)`.
   - Persistir el cambio vía `OperationCancelPort`.
3. Recoger los estados finales (ahora todos terminales) y calcular el estado
   agregado con `mark_finished()`.

### Inyección de dependencia

Se añade `OperationCancelPort` y `OperationRepository` al constructor de
`ExecutePipelineOperations`. `OperationRepository` ya existe como dependencia;
`OperationCancelPort` es nuevo.

### Cambio en el handler de excepción

El `except Exception` en `execute()` ya no necesita el fallback que marca
la ejecución como `failed` con estados inconsistentes. El timeout se maneja
explícitamente en `_poll_until_all_terminal`, que ahora devuelve una lista
de estados terminales (incluyendo los cancelados).
Se mantiene el `except Exception` para errores inesperados, pero se simplifica.

---

## 6. Presentation: endpoint de cancelación

Nuevo endpoint en `app/v1/pipelines/infrastructure/presentation/routes.py`:

```python
@router.post(
    "/api/v1/pipelines/{pipeline_id}/executions/{execution_id}/cancel",
    response_model=PipelineExecutionCancelResponse,
    status_code=status.HTTP_200_OK,
)
async def cancel_pipeline_execution(...)
```

### Schema: PipelineExecutionCancelResponse

En `schemas.py`:

```python
class PipelineExecutionCancelResponse(BaseModel):
    execution_id: str
    pipeline_id: str
    user_id: str
    status: str
    finished_at: datetime
```

### Dependency: get_cancel_pipeline_execution_uc

En `deps.py`, nueva función que construye `CancelPipelineExecution` con
sus dependencias inyectadas.

### Exception handler

Añadir `PipelineExecutionNotCancellableError` al exception handler existente,
mapeándolo a 422.

---

## 7. Modificaciones a PipelineStatus

Se añade `"cancelled"` a los conjuntos:

```python
_VALID_VALUES = frozenset({"pending", "in_progress", "completed", "failed", "partial", "cancelled"})
_TERMINAL_STATES = frozenset({"completed", "failed", "partial", "cancelled"})
```

Y se actualiza la docstring del VO.

---

## 8. Actualización de mark_finished para incluir cancelled

El cálculo agregado en `_calculate_aggregated_status` ya trata `cancelled`
como un estado fallido (está en `_FAILED_OPERATION_STATUSES`), lo cual es correcto:
si hay alguna operación cancelled y alguna completed, el resultado es `partial`;
si todas son cancelled, el resultado es `failed`.

**Verificación:** `_FAILED_OPERATION_STATUSES` ya incluye `"cancelled"`.
No necesita cambios.

---

## Archivos nuevos

| Archivo | Capa | Propósito |
|---------|------|-----------|
| `app/v1/pipelines/domain/events/pipeline_execution_cancelled.py` | Domain | Evento de dominio |
| `app/v1/pipelines/domain/exceptions/pipeline_execution.py` (modificado) | Domain | Añadir `PipelineExecutionNotCancellableError` |
| `app/v1/pipelines/application/commands/cancel_pipeline_execution.py` | Application | Command de cancelación |
| `app/v1/pipelines/application/interfaces/operation_cancel_port.py` | Application | Port para cancelar operaciones cross-module |
| `app/v1/pipelines/application/dtos/pipeline_dtos.py` (modificado) | Application | Añadir `PipelineExecutionCancelDTO` |
| `app/v1/pipelines/application/tasks/execute_pipeline_operations.py` (modificado) | Application | Timeout efectivo con cancelación de operaciones |
| `app/v1/pipelines/infrastructure/adapters/operation_cancel_adapter.py` | Infrastructure | Adapter que delega a `CancelOperation` |
| `app/v1/pipelines/infrastructure/presentation/routes.py` (modificado) | Presentation | Endpoint POST .../cancel |
| `app/v1/pipelines/infrastructure/presentation/schemas.py` (modificado) | Presentation | `PipelineExecutionCancelResponse` |
| `app/v1/pipelines/infrastructure/presentation/deps.py` (modificado) | Presentation | `get_cancel_pipeline_execution_uc` |
| `app/v1/pipelines/infrastructure/presentation/exception_handlers.py` (modificado) | Presentation | Handler para `PipelineExecutionNotCancellableError` |
| `main.py` (modificado) | Composition Root | Wiring del adapter y la background task closure |

---

## Archivos de test nuevos

| Archivo | Propósito |
|---------|-----------|
| `tests/v1/pipelines/test_domain/test_pipeline_execution_cancel.py` | Tests de `cancel()` y `mark_timeout_failed()` en la entity |
| `tests/v1/pipelines/test_domain/test_pipeline_status_cancelled.py` | Tests de `PipelineStatus("cancelled")` |
| `tests/v1/pipelines/test_domain/test_pipeline_execution_cancelled_event.py` | Tests del evento |
| `tests/v1/pipelines/test_use_cases/test_cancel_pipeline_execution.py` | Tests del command |
| `tests/v1/pipelines/test_use_cases/test_execute_pipeline_timeout.py` | Tests del timeout efectivo en la task |
| `tests/v1/pipelines/test_presentation/test_cancel_endpoint.py` | Tests del endpoint HTTP |