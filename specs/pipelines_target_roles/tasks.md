# Tasks — pipelines_target_roles

> Checklist ejecutable. Cada task referencia al menos un R<n> del requirements.md.
> El implementer marca `[x]` al completar.

---

## Domain layer

- [ ] T1 — Añadir `kit_ids: Optional[tuple[str, ...]] = None` y `values: dict = field(default_factory=dict)` al `@dataclass(frozen=True)` `PipelineTarget`. Ampliar `__post_init__` para validar que ningún `kit_id` en `kit_ids` esté vacío. Cubre: R1, R2.

## Application layer — LaunchPipeline

- [ ] T2 — Ampliar `LaunchPipeline._build_snapshot` para incluir `kit_ids` (convertido a `list | None`) y `values` por target en el snapshot. Cubre: R3.

- [ ] T3 — Ampliar `LaunchPipeline._validate_kits_usable` para recorrer cada target con `kit_ids` definido y verificar que todos los `kit_id` existan en `pipeline.kits`. Lanzar `PipelineNotLaunchableError` si algún `kit_id` no existe. Cubre: R7.

## Application layer — ExecutePipelineOperations

- [ ] T4 — Añadir método auxiliar `_find_target_for_server(self, server_id: str, pipeline) -> Optional[PipelineTarget]` a `ExecutePipelineOperations`. Cubre: R4.

- [ ] T5 — Añadir método auxiliar `_resolve_kits_for_target(self, target: Optional[PipelineTarget], pipeline) -> list[PipelineKitConfig]` que devuelva todos los kits si `target.kit_ids is None`, o filtre `pipeline.kits` preservando el orden si `target.kit_ids` está definido. Cubre: R4, R9.

- [ ] T6 — Refactorizar `_launch_all_operations` para que por cada `server_id` resuelva el target original, llame a `_resolve_kits_for_target` y construya `merged_values` con el orden de precedencia `pipeline.values → target.values → kit.values`. Cubre: R4, R5, R9, R10.

## Presentation layer — Schemas

- [ ] T7 — Añadir `kit_ids: Optional[list[str]] = None` y `values: Optional[dict] = None` a `PipelineTargetRequest` con `Field()` apropiado. Añadir los mismos campos a `PipelineTargetResponse`. Cubre: R6.

## Infrastructure layer — Repositorio

- [ ] T8 — Actualizar `SQLAlchemyPipelineRepository._entity_to_model` para serializar `kit_ids` (como `list | None`) y `values` de cada target. Cubre: R11.

- [ ] T9 — Actualizar `SQLAlchemyPipelineRepository._model_to_entity` para deserializar `kit_ids` (como `tuple | None` via `t.get("kit_ids")`) y `values` (via `t.get("values", {})`), manteniendo compatibilidad con registros existentes. Cubre: R10, R11.

- [ ] T10 — Actualizar el método `update` de `SQLAlchemyPipelineRepository` para serializar `kit_ids` y `values` (mismo patrón que `_entity_to_model`). Cubre: R11.

- [ ] T11 — Crear migración Alembic que backfillée los registros existentes en `pipelines.targets` añadiendo `kit_ids: null` y `values: {}` a cada entrada del array JSON donde falten. Cubre: R8.

## Tests

- [ ] T12 — Añadir tests de dominio en `tests/v1/pipelines/test_domain/`: `test_pipeline_target_kit_ids_none`, `test_pipeline_target_kit_ids_empty`, `test_pipeline_target_values`, `test_pipeline_target_kit_ids_validation`. Cubre: R1, R2.

- [ ] T13 — Añadir tests de use case en `tests/v1/pipelines/test_use_cases/`: `test_launch_pipeline_snapshot_includes_target_kit_ids`, `test_launch_pipeline_rejects_invalid_kit_id_in_target`, `test_execute_pipeline_resolves_kits_per_target`, `test_execute_pipeline_merges_values_target`, `test_execute_pipeline_no_regression_when_kit_ids_none`. Cubre: R3, R4, R5, R7, R10.

- [ ] T14 — Añadir tests de infraestructura en `tests/v1/pipelines/test_infrastructure/`: `test_repository_roundtrip_target_kit_ids_and_values`, `test_repository_backward_compatible_legacy_targets`. Cubre: R10, R11.

## OpenAPI

- [ ] T15 — Regenerar `openapi.yaml` para reflejar los nuevos campos en los schemas de pipeline target. Cubre: R6.
