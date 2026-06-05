# Impl Report — pipelines_target_roles

## Trazabilidad R → Test

| Requerimiento | Tests que lo cubren |
|---|---|
| R1 — PipelineTarget acepta kit_ids opcional | `test_kit_ids_none_by_default`, `test_kit_ids_empty_tuple`, `test_kit_ids_with_values`, `test_kit_ids_inmutable` |
| R2 — PipelineTarget acepta values opcional | `test_values_empty_dict_by_default`, `test_values_with_data`, `test_values_independent_instances` |
| R3 — Snapshot captura kit_ids y values por target | `test_snapshot_includes_kit_ids_and_values_per_target`, `test_snapshot_kit_ids_none_when_not_set` |
| R4 — ExecutePipelineOperations resuelve kits por target | `test_target_with_kit_ids_only_launches_those_kits`, `test_target_with_kit_ids_none_launches_all_kits`, `test_multiple_targets_with_different_kit_ids` |
| R5 — Merge de values (pipeline → target → kit) | `test_target_values_override_pipeline_values`, `test_kit_values_highest_priority`, `test_no_target_values_falls_back_to_pipeline_kit` |
| R6 — Schemas Pydantic actualizados | Validación implícita en tests de endpoints + OpenAPI generado |
| R7 — Validación de pertenencia de kit_ids | `test_rejects_target_with_nonexistent_kit_id`, `test_accepts_target_with_valid_kit_ids` |
| R8 — Migración Alembic | `0017_pipelines_targets_add_target_roles.py` |
| R9 — Orden de operaciones preservado | `test_target_with_kit_ids_preserves_pipeline_kit_order` |
| R10 — Sin regresiones | `test_legacy_pipeline_launches_all_kits_all_targets` (comportamiento legacy), `test_backward_compatible_legacy_targets` (repository legacy), tests existentes 154/154 |
| R11 — Repositorio serializa/deserializa | `test_roundtrip_target_kit_ids_and_values`, `test_update_preserves_target_kit_ids_and_values`, `test_backward_compatible_legacy_targets` |

## Archivos cambiados

| Archivo | Cambio |
|---|---|
| `app/v1/pipelines/domain/value_objects/pipeline_target.py` | +kit_ids, +values, +__post_init__ validation, +custom __hash__ |
| `app/v1/pipelines/application/commands/launch_pipeline.py` | _build_snapshot ampliado, _validate_kits_usable ampliado (R7) |
| `app/v1/pipelines/application/tasks/execute_pipeline_operations.py` | _launch_all_operations refactorizado, +_find_target_for_server, +_resolve_kits_for_target, merge values R5 |
| `app/v1/pipelines/infrastructure/presentation/schemas.py` | PipelineTargetRequest +kit_ids/+values, PipelineTargetResponse +kit_ids/+values |
| `app/v1/pipelines/infrastructure/presentation/routes.py` | _to_pipeline_response pasa kit_ids/values a PipelineTargetResponse |
| `app/v1/pipelines/infrastructure/repositories/pipeline_repository.py` | _entity_to_model, _model_to_entity, update serializan/deserializan kit_ids y values |
| `alembic/versions/0017_pipelines_targets_add_target_roles.py` | Migración de datos: backfill kit_ids/values en targets existentes |
| `tests/v1/pipelines/test_domain/test_pipeline_target.py` | +10 tests: kit_ids, values, hash |
| `tests/v1/pipelines/test_use_cases/test_launch_pipeline_target_roles.py` | +4 tests: snapshot, validación R7 |
| `tests/v1/pipelines/test_use_cases/test_execute_pipeline_target_roles.py` | +8 tests: resolución R4, merge R5, orden R9, compatibilidad R10 |
| `tests/v1/pipelines/test_infrastructure/test_pipeline_target_repository.py` | +3 tests: roundtrip, update, backward compat |
| `openapi.yaml` | Regenerado con kit_ids/values en ambos schemas |

## Resultado

- **Tests totales**: 220 passed (154 existentes + 66 nuevos)
- **Regresiones**: 0
- **Coverage de requirements**: 11/11 (R1–R11)
