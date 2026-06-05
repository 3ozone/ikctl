# Review — pipelines_target_roles

> Review date: 2026-06-05
> Reviewer: AI agent
> Status: **APPROVED**

---

## 1. Verificación de trazabilidad

### R → Tests

| R# | Descripción | Tests que cubren | Estado |
|---|---|---|---|
| R1 | PipelineTarget acepta `kit_ids` opcional | `test_kit_ids_none_by_default`, `test_kit_ids_empty_tuple`, `test_kit_ids_with_values`, `test_kit_ids_inmutable` | ✅ |
| R2 | PipelineTarget acepta `values` opcional | `test_values_empty_dict_by_default`, `test_values_with_data`, `test_values_independent_instances` | ✅ |
| R3 | Snapshot captura `kit_ids`/`values` por target | `test_snapshot_includes_kit_ids_and_values_per_target`, `test_snapshot_kit_ids_none_when_not_set` | ✅ |
| R4 | ExecutePipelineOperations resuelve kits por target | `test_target_with_kit_ids_only_launches_those_kits`, `test_target_with_kit_ids_none_launches_all_kits`, `test_multiple_targets_with_different_kit_ids` | ✅ |
| R5 | Merge de values pipeline→target→kit | `test_target_values_override_pipeline_values`, `test_kit_values_highest_priority`, `test_no_target_values_falls_back_to_pipeline_kit` | ✅ |
| R6 | Schemas Pydantic actualizados | Validación implícita + OpenAPI generado | ✅ |
| R7 | Validación de pertenencia de `kit_ids` | `test_rejects_target_with_nonexistent_kit_id`, `test_accepts_target_with_valid_kit_ids` | ✅ |
| R8 | Migración Alembic | `0017_pipelines_targets_add_target_roles.py` | ✅ |
| R9 | Orden de operaciones preservado | `test_target_with_kit_ids_preserves_pipeline_kit_order` | ✅ |
| R10 | Sin regresiones | `test_legacy_pipeline_launches_all_kits_all_targets`, `test_backward_compatible_legacy_targets`, 220 tests green | ✅ |
| R11 | Repositorio serializa/deserializa | `test_roundtrip_target_kit_ids_and_values`, `test_update_preserves_target_kit_ids_and_values`, `test_backward_compatible_legacy_targets` | ✅ |

**Cobertura: 11/11 requisitos cubiertos.** ✅

### T1–T15 Tasks

| Task | Descripción | Estado |
|---|---|---|
| T1 | PipelineTarget: `kit_ids` + `values` + `__post_init__` | ✅ |
| T2 | `_build_snapshot` ampliado | ✅ |
| T3 | `_validate_kits_usable` ampliado (R7) | ✅ |
| T4 | `_find_target_for_server` | ✅ |
| T5 | `_resolve_kits_for_target` | ✅ |
| T6 | `_launch_all_operations` refactorizado | ✅ |
| T7 | Schemas Pydantic actualizados | ✅ |
| T8 | Repo: `_entity_to_model` serializa | ✅ |
| T9 | Repo: `_model_to_entity` deserializa | ✅ |
| T10 | Repo: `update` serializa | ✅ |
| T11 | Migración Alembic | ✅ |
| T12 | Tests de dominio | ✅ |
| T13 | Tests de use case | ✅ |
| T14 | Tests de infraestructura | ✅ |
| T15 | openapi.yaml regenerado | ✅ |

**Todas las 15 tasks completadas.** ✅

---

## 2. Verificación de checkpoints

### C17 — Logger con `get_logger(__name__)`

- `app/v1/pipelines/application/tasks/execute_pipeline_operations.py:41`: `logger = get_logger(__name__)` ✅
- `app/v1/pipelines/infrastructure/presentation/routes.py:61`: `logger = get_logger(__name__)` ✅
- El logger se importa de `app.v1.shared.infrastructure.logger` (no `logging.getLogger`). ✅

### C18 — Sin `print()` de debug

- Búsqueda `grep print\( app/v1/pipelines/` — 0 resultados. ✅

### C24 — openapi.yaml regenerado

- `PipelineTargetRequest` (line 2987–3015): incluye `kit_ids` (anyOf array|null) y `values` (anyOf object|null) ✅
- `PipelineTargetResponse` (line 3016–3039): incluye `kit_ids` (anyOf array|null) y `values` (anyOf object|null), ambos como `required` ✅

---

## 3. Tests existentes — Regresiones

```
python -m pytest tests/v1/pipelines/ -v --tb=short
→ 220 passed, 22 warnings
```

- Tests legacy intactos (R10). ✅
- Sin regresiones. ✅

---

## 4. Revisión de código clave

### PipelineTarget VO (`pipeline_target.py:10-41`)

| Aspecto | Verificación |
|---|---|
| `@dataclass(frozen=True)` | ✅ Line 10 |
| `kit_ids: Optional[tuple[str, ...]] = None` | ✅ Line 25 |
| `values: dict = field(default_factory=dict)` | ✅ Line 26 |
| `__post_init__` valida `kit_id` no vacío | ✅ Lines 28-38 |
| `__hash__` implementado (necesario porque `dict` no es hashable) | ✅ Lines 40-41 |

### Repositorio — compatibilidad backward

| Aspecto | Verificación |
|---|---|
| `_entity_to_model` serializa `kit_ids` list\|None, `values` dict | ✅ Lines 39-41 |
| `_model_to_entity` usa `t.get("kit_ids")` y `t.get("values", {})` | ✅ Lines 84-85 |
| `update` serializa igual que `_entity_to_model` | ✅ Lines 128-135 |

### Merge de values (`execute_pipeline_operations.py:157-161`)

Orden: `pipeline.values → target.values → kit.values` (último gana). ✅

### Filtrado de kits (`execute_pipeline_operations.py:210-213`)

- `target.kit_ids is None` → todos los kits ✅
- Con `kit_ids` → filtra preservando orden de `pipeline.kits` ✅

### Migración Alembic (`0017_pipelines_targets_add_target_roles.py`)

- `upgrade()`: backfill `kit_ids: null` y `values: {}` en targets existentes ✅
- `downgrade()`: elimina `kit_ids` y `values` ✅
- `down_revision` apunta a `0016_pipeline_executions` ✅

---

## 5. ✅ Correcciones verificadas (Re-review 2026-06-05)

Las 3 correcciones solicitadas fueron aplicadas y verificadas:

### Fix 1 — `routes.py:114` (create_pipeline) — ✅ CORREGIDO

```python
PipelineTarget(
    server_id=t.server_id,
    kit_ids=tuple(t.kit_ids) if t.kit_ids is not None else None,
    values=t.values or {},
)
```

### Fix 2 — `routes.py:227` (update_pipeline) — ✅ CORREGIDO

```python
PipelineTarget(
    server_id=t.server_id,
    kit_ids=tuple(t.kit_ids) if t.kit_ids is not None else None,
    values=t.values or {},
)
```

### Fix 3 — `create_pipeline.py:84` (`_to_result`) — ✅ CORREGIDO

```python
targets=tuple(
    {
        "server_id": t.server_id,
        "kit_ids": list(t.kit_ids) if t.kit_ids is not None else None,
        "values": dict(t.values),
    }
    for t in pipeline.targets
),
```

### Plus — `UpdatePipeline` reusa `CreatePipeline._to_result` — ✅ CONFIRMADO

`update_pipeline.py:86`: `return CreatePipeline._to_result(pipeline)` — sin duplicación.

---

## 6. Re-review — 2026-06-05

### Correcciones aplicadas

| Bug | Archivo | Línea | Estado |
|---|---|---|---|
| Bug 1 | `routes.py` (create) | 114–121 | ✅ |
| Bug 2 | `routes.py` (update) | 227–233 | ✅ |
| Bug 3 | `create_pipeline.py` (`_to_result`) | 84–91 | ✅ |

### Tests

```
python -m pytest tests/v1/pipelines/ -v --tb=short
→ 220 passed, 22 warnings
```

Sin regresiones. ✅

### openapi.yaml

- `PipelineTargetRequest` (línea 2997–3010): incluye `kit_ids` y `values` ✅
- `PipelineTargetResponse` (línea 3021–3037): incluye `kit_ids` y `values` como `required` ✅

---

## 7. Veredicto

| Aspecto | Estado |
|---|---|
| Trazabilidad R→test | ✅ Completa (11/11) |
| Tasks completadas | ✅ 15/15 |
| C17: logger | ✅ |
| C18: sin print() | ✅ |
| C24: openapi.yaml | ✅ |
| Tests pasan | ✅ 220/220 |
| VO PipelineTarget correcto | ✅ |
| Repositorio backward compat | ✅ |
| Merge de values correcto | ✅ |
| Filtrado de kits correcto | ✅ |
| Migración Alembic correcta | ✅ |
| **Bug 1: routes.py create ignora kit_ids/values** | ✅ CORREGIDO |
| **Bug 2: routes.py update ignora kit_ids/values** | ✅ CORREGIDO |
| **Bug 3: _to_result no serializa kit_ids/values** | ✅ CORREGIDO |

**Veredicto: ✅ APPROVED**

Todos los bugs han sido corregidos. 220 tests pasan. openapi.yaml incluye `kit_ids`/`values`. Sin regresiones.
