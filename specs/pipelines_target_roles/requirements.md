# Requirements — pipelines_target_roles

> Especificación en notación EARS. Cada requirement tiene un id estable (R<n>)
> y DEBE ser verificable por al menos un test concreto.

---

## R1 — PipelineTarget acepta kit_ids opcional

El `PipelineTarget` value object DEBE aceptar un campo `kit_ids: Optional[tuple[str, ...]] = None`
que permita restringir qué kits se ejecutan en ese target. Cuando `kit_ids` es `None`,
el target ejecuta todos los kits globales del pipeline.

## R2 — PipelineTarget acepta values opcional

El `PipelineTarget` value object DEBE aceptar un campo `values: dict` (default `{}`)
con variables de plantilla específicas de ese target. Los `values` del target se mergean
con los `values` globales del pipeline y con los `values` de cada kit (orden de precedencia:
kit > target > global).

## R3 — Snapshot captura kit_ids y values por target

CUANDO `LaunchPipeline._build_snapshot` construye el snapshot inmutable de la
configuración del pipeline, el snapshot DEBE incluir `kit_ids` y `values` en cada
entrada de `targets`.

DONDE `kit_ids` es `None` (target sin restricción), el snapshot DEBE almacenar
`kit_ids: null`. DONDE `values` está vacío, el snapshot DEBE almacenar `values: {}`.

## R4 — ExecutePipelineOperations resuelve kits por target

CUANDO `ExecutePipelineOperations._launch_all_operations` construye el producto
cartesiano servidores × kits para un target, el sistema DEBE resolver los kits
de la siguiente forma:

- SI el target tiene `kit_ids` definido y no vacío, ENTONCES el sistema DEBE
  ejecutar solo los `PipelineKitConfig` cuyo `kit_id` esté en `target.kit_ids`,
  preservando el orden de `pipeline.kits`.
- SI el target tiene `kit_ids` igual a `None`, ENTONCES el sistema DEBE ejecutar
  todos los `pipeline.kits`.

## R5 — Merge de values en el lanzamiento de operaciones

CUANDO `ExecutePipelineOperations._launch_all_operations` lanza una operación
para un par (servidor, kit), el sistema DEBE mergear los values en el siguiente
orden de precedencia (el último gana):

1. `pipeline.values` (globales del pipeline)
2. `target.values` (del target actual)
3. `kit.values` (del kit actual)

## R6 — Schemas Pydantic actualizados

El `PipelineTargetRequest` schema DEBE exponer los campos opcionales
`kit_ids: Optional[list[str]]` y `values: Optional[dict]`.

El `PipelineTargetResponse` schema DEBE exponer los mismos campos.

## R7 — Validación de pertenencia de kit_ids

SI un `PipelineTarget` tiene `kit_ids` definido y no vacío, ENTONCES cada
`kit_id` en esa lista DEBE corresponder a un `PipelineKitConfig` existente en
`pipeline.kits`. SI algún `kit_id` no existe en `pipeline.kits`, el sistema DEBE
rechazar el lanzamiento con un error `PipelineNotLaunchableError`.

## R8 — Migración Alembic

El sistema DEBE incluir una migración Alembic que actualice los registros
existentes en la tabla `pipelines`, modificando cada entrada del array JSON
`targets` para incluir `kit_ids: null` y `values: {}` donde falten.

## R9 — Orden de operaciones preservado

MIENTRAS se ejecuta el pipeline, el sistema DEBE preservar el orden de las
operaciones resultante de iterar `server_ids × kits_resueltos` en el mismo
orden que el bucle original: targets en el orden definido en el pipeline y
kits filtrados preservando el orden de `pipeline.kits`.

## R10 — Sin regresiones

CUANDO todos los targets de un pipeline tienen `kit_ids: None` y `values: {}`,
el sistema DEBE comportarse exactamente igual que antes de esta feature
(producto cartesiano completo con values solo de pipeline + kit).

## R11 — Repositorio serializa/deserializa los nuevos campos

El `SQLAlchemyPipelineRepository` DEBE serializar `kit_ids` y `values` de cada
`PipelineTarget` al persistir, y DEBE deserializarlos al cargar, usando `.get()`
con valores por defecto para mantener compatibilidad con registros existentes.
