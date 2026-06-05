# Design — pipelines_parallel_exec

> Decisiones técnicas para la feature de ejecución paralela en pipelines.
> Se apoya en `docs/architecture.md` y `docs/conventions.md`.

---

## 1. Capa de aplicación: refactorización del bucle de lanzamiento

### Archivo modificado

`app/v1/pipelines/application/tasks/execute_pipeline_operations.py`

### Cambio principal

El doble bucle secuencial actual:

```python
for server_id in server_ids:
    for kit_config in pipeline.kits:
        op_id = await self._launcher.launch(...)
        operation_ids.append(op_id)
```

Se reemplaza por un método privado `_launch_all_operations` que construye
las corrutinas y las ejecuta con `asyncio.gather` bajo un `asyncio.Semaphore`:

```python
async def _launch_all_operations(
    self,
    server_ids: list[str],
    pipeline,
    user_id: str,
) -> list[str | None]:
    """Lanza todas las operaciones N×M en paralelo respetando max_concurrency."""
    ...
    results = await asyncio.gather(*tasks, return_exceptions=True)
    ...
```

El método devuelve `list[str | None]`: `str` con el `operation_id` en éxito,
`None` en caso de excepción (la excepción se loguea en el propio método).
El caller descarta los `None` al construir `operation_ids`.

### Firma del constructor ampliada

```python
def __init__(
    self,
    pipeline_repository: PipelineRepository,
    execution_repository: PipelineExecutionRepository,
    server_repository: ServerRepository,
    operation_launcher: OperationLauncher,
    operation_repository: OperationRepository,
    operation_cancel_port: Optional[OperationCancelPort] = None,
    timeout_seconds: int = _DEFAULT_TIMEOUT_SECONDS,
    commit_fn: Optional[object] = None,
    max_concurrency: int = _DEFAULT_MAX_CONCURRENCY,   # ← nuevo
) -> None:
```

### Constante nueva

```python
_DEFAULT_MAX_CONCURRENCY: int = 10
```

Añadida a nivel de módulo junto a `_POLL_INTERVAL_SECONDS` y
`_DEFAULT_TIMEOUT_SECONDS`.

### Uso del Semaphore

El `asyncio.Semaphore` se crea dentro de `_launch_all_operations` con el
valor de `self._max_concurrency`, por lo que su ciclo de vida está acotado
a la fase de lanzamiento y no persiste durante el polling:

```python
semaphore = asyncio.Semaphore(self._max_concurrency)

async def _bounded_launch(server_id: str, kit_config) -> str | None:
    async with semaphore:
        return await self._launcher.launch(...)
```

### Manejo de errores parciales (R7)

`asyncio.gather` se invoca con `return_exceptions=True` para que un fallo
individual no aborte las demás corrutinas. Cada resultado se inspecciona:

- Si es `str` → `operation_id` válido, se incluye en `operation_ids`.
- Si es `BaseException` → se loguea como `pipeline_launch_operation_failed`
  con `operation_idx` para trazabilidad; se omite del listado.

Si al menos un lanzamiento falla, la ejecución se marcará como `failed` en
el cálculo de estado agregado (al tener operaciones que nunca se crearon,
el conteo de completadas < total).

### Preservación del orden (R6)

Las corrutinas se construyen con `enumerate` sobre el producto cartesiano
`server_ids × kits`, en el mismo orden que el bucle original. `asyncio.gather`
devuelve los resultados en el mismo orden de entrada, garantizando que la
posición `i` de `results` corresponde siempre al par `(server_id[i//len(kits)], kit[i%len(kits)])`.

---

## 2. Configuración: Settings

### Archivo modificado

`app/config/settings.py`

### Campo nuevo

```python
PIPELINE_MAX_CONCURRENCY: int = 10
```

Sigue el patrón de campos existentes (`int` con default). Se inyecta desde
el Composition Root en el constructor de `ExecutePipelineOperations`.

---

## 3. Composition Root: wiring

### Archivo modificado

`main.py`

La closure `_execute_pipeline_fn` construye `ExecutePipelineOperations`
pasando `max_concurrency=settings.PIPELINE_MAX_CONCURRENCY`.

No se necesita ningún cambio de interfaz en repositorios ni adapters
porque el Semaphore es un detalle interno de la task.

---

## 4. Alternativa descartada — `asyncio.Semaphore` global (singleton)

Se evaluó crear el `Semaphore` una sola vez en el Composition Root e
inyectarlo como dependencia. Se descarta porque:

1. El semáforo controla paralelismo *dentro de una sola ejecución*. Si fuera
   global, dos ejecuciones concurrentes de pipelines distintos compartirían
   el mismo límite de manera acumulativa, provocando contención inesperada
   y un comportamiento más difícil de razonar.
2. Los tests unitarios de `ExecutePipelineOperations` necesitarían inyectar
   un `Semaphore` real (asyncio-aware) en vez de construirlo internamente,
   aumentando el acoplamiento del test a asyncio.
3. El ciclo de vida del semáforo (creación por ejecución) es más sencillo y
   predecible: termina cuando finaliza `_launch_all_operations`.

---

## 5. Alternativa descartada — `asyncio.TaskGroup` (Python 3.11+)

`asyncio.TaskGroup` (PEP 654) ofrece una sintaxis más idiomática y propagación
de cancelación automática. Se descarta porque:

1. Con `TaskGroup` cualquier excepción en una subtarea cancela todo el grupo
   (`ExceptionGroup`), lo que viola R7 (continuar con el resto tras un fallo
   parcial). Requerería manejo adicional con `except*` que añade complejidad.
2. El proyecto ya usa `asyncio.gather` en otras partes; la consistencia en el
   estilo de concurrencia reduce la carga cognitiva.

---

## Archivos modificados

| Archivo | Capa | Cambio |
|---------|------|--------|
| `app/v1/pipelines/application/tasks/execute_pipeline_operations.py` | Application | Añadir `_launch_all_operations`, `_DEFAULT_MAX_CONCURRENCY`, parámetro `max_concurrency` en constructor |
| `app/config/settings.py` | Config | Añadir `PIPELINE_MAX_CONCURRENCY: int = 10` |
| `main.py` | Composition Root | Pasar `max_concurrency=settings.PIPELINE_MAX_CONCURRENCY` al construir `ExecutePipelineOperations` |

## Archivos de test nuevos

| Archivo | Propósito |
|---------|-----------|
| `tests/v1/pipelines/test_use_cases/test_execute_pipeline_parallel.py` | Tests de lanzamiento paralelo, Semaphore, orden y errores parciales |
