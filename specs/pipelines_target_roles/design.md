# Design — pipelines_target_roles

> Decisiones técnicas para la feature de kits y valores específicos por target.
> Se apoya en `docs/architecture.md` y `docs/conventions.md`.

---

## 1. Domain layer — PipelineTarget value object

### Archivo modificado

`app/v1/pipelines/domain/value_objects/pipeline_target.py`

### Cambio

Se añaden dos campos opcionales al `@dataclass(frozen=True)` existente:

```python
@dataclass(frozen=True)
class PipelineTarget:
    server_id: str
    kit_ids: Optional[tuple[str, ...]] = None
    values: dict = field(default_factory=dict)
```

- `kit_ids`: `tuple[str, ...] | None` para inmutabilidad (frozen=True). Si es `None`,
  significa "todos los kits globales del pipeline". Si es `tuple()` vacío,
  el target no ejecuta ningún kit (caso borde válido).
- `values`: `dict` con `field(default_factory=dict)` para evitar el late-binding
  de mutables en dataclasses. Siempre presente, aunque vacío.
- Se mantiene `frozen=True`. No se necesita `__hash__` adicional porque el hash
  por defecto de dataclass frozen ya incluye todos los campos.

### `__post_init__` ampliado

Se valida que si `kit_ids` no es None, ningún elemento esté vacío:

```python
def __post_init__(self) -> None:
    if not self.server_id or not self.server_id.strip():
        raise InvalidPipelineTargetError(...)
    if self.kit_ids is not None:
        for kid in self.kit_ids:
            if not kid or not kid.strip():
                raise InvalidPipelineTargetError(...)
```

---

## 2. Application layer — LaunchPipeline

### Archivo modificado

`app/v1/pipelines/application/commands/launch_pipeline.py`

### 2.1 `_build_snapshot` ampliado

Cada entrada de `targets` en el snapshot ahora incluye `kit_ids` y `values`:

```python
"targets": [
    {
        "server_id": t.server_id,
        "kit_ids": list(t.kit_ids) if t.kit_ids is not None else None,
        "values": dict(t.values),
    }
    for t in pipeline.targets
],
```

`kit_ids` se convierte de `tuple` a `list` (o `None`) para serialización JSON.

### 2.2 `_validate_kits_usable` ampliado (R7)

Se añade validación por target después de la validación global RN-09:

```python
async def _validate_kits_usable(self, pipeline: Pipeline) -> None:
    # RN-09 original: todos los kits globales deben ser usables
    for kit_config in pipeline.kits:
        kit = await self._kit_repo.find_by_id_internal(kit_config.kit_id)
        if kit is None or not kit.is_usable():
            raise PipelineNotLaunchableError(...)
    # R7: si target tiene kit_ids, deben existir en pipeline.kits
    pipeline_kit_ids = {kc.kit_id for kc in pipeline.kits}
    for target in pipeline.targets:
        if target.kit_ids is not None:
            for kid in target.kit_ids:
                if kid not in pipeline_kit_ids:
                    raise PipelineNotLaunchableError(
                        f"Kit '{kid}' en target '{target.server_id}' "
                        f"no existe en pipeline.kits."
                    )
```

---

## 3. Application layer — ExecutePipelineOperations

### Archivo modificado

`app/v1/pipelines/application/tasks/execute_pipeline_operations.py`

### 3.1 `_launch_all_operations` refactorizado

El método actual itera sobre `pipeline.kits` como fuente única de kits.
Se modifica para que, por cada target expandido a `server_id`, se resuelvan
sus kits específicos:

```python
async def _launch_all_operations(
    self, server_ids: list[str], pipeline, user_id: str,
) -> list[str]:
    semaphore = asyncio.Semaphore(self._max_concurrency)
    tasks: list = []

    for server_id in server_ids:
        # Resolver qué kits aplican a este servidor
        # Buscar el PipelineTarget original para obtener kit_ids
        target = self._find_target_for_server(server_id, pipeline)
        kits = self._resolve_kits_for_target(target, pipeline)

        for kit_config in kits:
            merged_values = {
                **dict(pipeline.values),
                **dict(target.values if target else {}),
                **dict(kit_config.values),
            }
            async def _bounded_launch(
                sid: str = server_id,
                kc = kit_config,
            ) -> str | None:
                async with semaphore:
                    return await self._launcher.launch(
                        user_id=user_id,
                        server_id=sid,
                        kit_id=kc.kit_id,
                        values=merged_values,
                        sudo=pipeline.resolved_sudo_for(kc.kit_id),
                        debug_level=pipeline.resolved_debug_level_for(kc.kit_id),
                    )
            tasks.append(_bounded_launch())

    results = await asyncio.gather(*tasks, return_exceptions=True)
    ...
```

### 3.2 Nuevos métodos auxiliares

```python
def _find_target_for_server(self, server_id: str, pipeline) -> Optional[PipelineTarget]:
    """Busca el PipelineTarget original que corresponde a un server_id expandido."""
    for t in pipeline.targets:
        if t.server_id == server_id:
            return t
    return None

def _resolve_kits_for_target(
    self, target: Optional[PipelineTarget], pipeline,
) -> list[PipelineKitConfig]:
    """Resuelve los kits que aplican a un target.
    
    Si target tiene kit_ids definido, filtra pipeline.kits.
    Si no, devuelve todos.
    """
    if target is None or target.kit_ids is None:
        return list(pipeline.kits)
    kit_ids_set = set(target.kit_ids)
    return [kc for kc in pipeline.kits if kc.kit_id in kit_ids_set]
```

### 3.3 Merge de values (R5)

El merge sigue el orden de precedencia: `pipeline.values` (base) → `target.values`
(override parcial) → `kit.values` (máxima prioridad). Esto es consistente con
el patrón actual de `{**pipeline.values, **kit.values}` pero añadiendo el nivel
intermedio de target.

### 3.4 Preservación del orden (R9)

`_resolve_kits_for_target` itera sobre `pipeline.kits` en orden y filtra con
una `set` para búsqueda O(1), preservando el orden original de `pipeline.kits`.

---

## 4. Presentation layer — Schemas Pydantic

### Archivo modificado

`app/v1/pipelines/infrastructure/presentation/schemas.py`

### 4.1 PipelineTargetRequest

```python
class PipelineTargetRequest(BaseModel):
    server_id: str = Field(...)
    kit_ids: Optional[list[str]] = Field(
        None,
        description="IDs de los kits a ejecutar en este target. None = usar globales.",
    )
    values: Optional[dict] = Field(
        None,
        description="Variables de plantilla específicas de este target.",
    )
```

### 4.2 PipelineTargetResponse

```python
class PipelineTargetResponse(BaseModel):
    server_id: str
    kit_ids: Optional[list[str]]
    values: Optional[dict]
```

---

## 5. Infrastructure layer — Repositorio

### Archivo modificado

`app/v1/pipelines/infrastructure/repositories/pipeline_repository.py`

### 5.1 `_entity_to_model`

```python
targets=[
    {
        "server_id": t.server_id,
        "kit_ids": list(t.kit_ids) if t.kit_ids is not None else None,
        "values": dict(t.values),
    }
    for t in pipeline.targets
],
```

### 5.2 `_model_to_entity`

```python
targets=[
    PipelineTarget(
        server_id=t["server_id"],
        kit_ids=tuple(t["kit_ids"]) if t.get("kit_ids") is not None else None,
        values=t.get("values", {}),
    )
    for t in targets_raw
],
```

Usar `.get("kit_ids")` (con default `None`) y `.get("values", {})` para
compatibilidad con registros existentes que no tienen estos campos (R10).

### 5.3 `update` method

El método `update` también serializa los nuevos campos, siguiendo el mismo
patrón que `_entity_to_model`:

```python
model.targets = [
    {
        "server_id": t.server_id,
        "kit_ids": list(t.kit_ids) if t.kit_ids is not None else None,
        "values": dict(t.values),
    }
    for t in pipeline.targets
]
```

### 5.4 Alembic migration (R8)

Se crea una migración de datos (no de esquema) porque la columna `targets` ya
es JSON (`_JsonText`). La migración actualiza los registros existentes:

```python
# En upgrade():
# Para cada pipeline, si algún target en targets no tiene "kit_ids" o "values",
# añadirlos con valores por defecto.
from alembic import op
import sqlalchemy as sa

def upgrade():
    conn = op.get_bind()
    pipelines = conn.execute(sa.text("SELECT id, targets FROM pipelines")).fetchall()
    for pid, targets_raw in pipelines:
        if not targets_raw:
            continue
        targets = json.loads(targets_raw) if isinstance(targets_raw, str) else targets_raw
        modified = False
        for t in targets:
            if "kit_ids" not in t:
                t["kit_ids"] = None
                modified = True
            if "values" not in t:
                t["values"] = {}
                modified = True
        if modified:
            conn.execute(
                sa.text("UPDATE pipelines SET targets = :targets WHERE id = :id"),
                {"targets": json.dumps(targets, ensure_ascii=False), "id": pid},
            )
```

---

## 6. DTOs — Sin cambios estructurales

El snapshot es un `dict` genérico (`PipelineExecutionResult.snapshot: dict`).
No hay un DTO `SnapshotPipeline`. El snapshot se construye como dict en
`_build_snapshot` y se almacena tal cual. No se requieren cambios en DTOs
porque el dict incluirá los nuevos campos automáticamente.

---

## 7. Archivos modificados

| Archivo | Capa | Cambio |
|---------|------|--------|
| `app/v1/pipelines/domain/value_objects/pipeline_target.py` | Domain | Añadir `kit_ids` y `values`, ampliar `__post_init__` |
| `app/v1/pipelines/application/commands/launch_pipeline.py` | Application | Ampliar `_build_snapshot` y `_validate_kits_usable` |
| `app/v1/pipelines/application/tasks/execute_pipeline_operations.py` | Application | Refactorizar `_launch_all_operations` con resolución por target y merge de values |
| `app/v1/pipelines/infrastructure/presentation/schemas.py` | Presentation | Añadir `kit_ids` y `values` a `PipelineTargetRequest` y `PipelineTargetResponse` |
| `app/v1/pipelines/infrastructure/repositories/pipeline_repository.py` | Infrastructure | Serializar/deserializar `kit_ids` y `values` en `_entity_to_model`, `_model_to_entity` y `update` |
| `alembic/versions/XXXX_pipelines_targets_add_target_roles.py` | Infrastructure | Migración de datos para backfill de registros existentes |

## 8. Archivos de test nuevos

| Archivo | Propósito |
|---------|-----------|
| `tests/v1/pipelines/test_domain/test_pipeline_target.py` (ampliar) | Tests del VO con nuevos campos |
| `tests/v1/pipelines/test_use_cases/test_launch_pipeline_target_roles.py` | Tests de validación y snapshot |
| `tests/v1/pipelines/test_use_cases/test_execute_pipeline_target_roles.py` | Tests de resolución de kits por target y merge de values |
| `tests/v1/pipelines/test_infrastructure/test_pipeline_target_repository.py` (ampliar) | Tests de serialización/deserialización |

## 9. Alternativa descartada — Value Object separado TargetKitConfig

Se evaluó crear un VO separado `TargetKitConfig(kit_ids, values)` para agrupar
los nuevos campos en un objeto anidado dentro de PipelineTarget. Se descarta
porque:

1. Añade complejidad innecesaria: los campos son independientes (uno controla
   qué kits, el otro controla variables de plantilla).
2. PipelineTarget es un VO ligero — añadir una capa de anidamiento no aporta
   ventajas semánticas significativas.
3. La serialización JSON sería más profunda y requeriría más código en el
   repositorio.
4. El snapshot heredaría la misma estructura anidada, dificultando la lectura
   directa.

## 10. Alternativa descartada — Modificar PipelineKitConfig con server_ids

Se evaluó invertir la relación: que cada `PipelineKitConfig` tenga una lista
de `server_ids` a los que aplica (en lugar de que el target tenga `kit_ids`).
Se descarta porque:

1. Rompe el modelo mental actual: "targets son servidores, kits son acciones".
2. Haría más compleja la expansión de grupos de servidores.
3. La UI/UX sería peor: sería más natural decir "a estos servidores, ejecuta
   estos kits" que "este kit se ejecuta en estos servidores".
4. La feature futura `pipelines_phases` (dependencias entre targets) funciona
   mejor con la relación target → kits que al revés.

## 11. Alternativa descartada — Usar M:N explícita (tabla intermedia)

Se evaluó crear una tabla `pipeline_target_kits` para almacenar la relación
M:N entre targets y kits. Se descarta porque:

1. `targets` ya es un campo JSON — meter una tabla separada rompe la
   convención actual de todo el módulo pipelines.
2. Los targets no tienen identidad propia (son parte del agregado Pipeline).
3. No hay necesidad de consultar "qué targets usan el kit X" desde el módulo
   pipelines.
