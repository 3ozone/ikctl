# Validación de Requisitos vs Implementación — Módulo Pipelines

## Requisitos Funcionales

| RF | Descripción | Implementación | Estado |
|----|-------------|---------------|--------|
| RF-20 | Crear pipeline con name, description, targets[], kits[], values, sudo, debug_level | `CreatePipeline` command → `POST /api/v1/pipelines` | ✅ |
| RF-21 | Lanzar pipeline: crea PipelineExecution pending, snapshot, genera N×M ops async | `LaunchPipeline` command + `ExecutePipelineOperations` task → `POST /api/v1/pipelines/{id}/executions` | ✅ |
| RF-22 | Listar ejecuciones paginado con resumen (total, completadas, falladas) | `GetPipelineExecutions` query → `GET /api/v1/pipelines/{id}/executions` | ✅ |
| RF-22b | Detalle de ejecución con operaciones individuales | `GetPipelineExecutionDetail` query → `GET /api/v1/pipelines/{id}/executions/{exec_id}` | ✅ |
| RF-23 | Listar pipelines del usuario con paginación | `ListPipelines` query → `GET /api/v1/pipelines` | ✅ |
| RF-24 | Actualizar pipeline (solo si sin ejecuciones in_progress) | `UpdatePipeline` command → `PUT /api/v1/pipelines/{id}` | ✅ |
| RF-25 | Eliminar pipeline (solo si sin ejecuciones activas) | `DeletePipeline` command → `DELETE /api/v1/pipelines/{id}` | ✅ |

## Reglas de Negocio

| RN | Descripción | Implementación | Estado |
|----|-------------|---------------|--------|
| RN-01 | Ownership: solo el propietario puede ver/modificar/lanzar/eliminar | `find_by_id(id, user_id)` en todos los commands/queries | ✅ |
| RN-09 | Todos los kits del pipeline deben ser usables (synced + no deleted) | `LaunchPipeline._validate_kits_usable()` → `PipelineNotLaunchableError` | ✅ |
| RN-14 | `sudo` por kit prioridad sobre global | `Pipeline.resolved_sudo_for()` + `ExecutePipelineOperations` lo usa | ✅ |
| RN-15 | `debug_level` por kit prioridad sobre global | `Pipeline.resolved_debug_level_for()` + `ExecutePipelineOperations` lo usa | ✅ |
| RN-16 | No actualizar/eliminar pipeline con ejecuciones activas | `has_active_executions()` en `UpdatePipeline` y `DeletePipeline` → `PipelineInProgressError` | ✅ |
| RN-17 | Servidor local no permitido en targets | `CreatePipeline` y `UpdatePipeline` validan via `ServerRepository.find_server_by_id_internal()` | ✅ |
| RN-20 | Estado agregado: completed/failed/partial | `PipelineExecution.mark_finished()` con `_calculate_aggregated_status()` + tests | ✅ |
| RN-21 | Snapshot inmutable de config al lanzar | `LaunchPipeline._build_snapshot()` captura targets, kits, values, sudo, debug_level | ✅ |

## Requisitos No Funcionales

| RNF | Descripción | Implementación | Estado |
|-----|-------------|---------------|--------|
| RNF-02 | Ejecución asíncrona via FastAPI BackgroundTasks | `FastAPITaskQueue` inyectada en `LaunchPipeline` y `ExecutePipelineOperations` | ✅ |
| RNF-06 | 50 operaciones SSH concurrentes | Connection pooling asyncssh en operations module | ✅ (heredado) |
| RNF-07 | Rate limiting 20 lanzamientos/hora | Pendiente middleware (mismo patrón que auth) | ⏳ v1.1 |
| RNF-08 | Timeout global pipeline 30min | Polling en `ExecutePipelineOperations` con `_POLL_INTERVAL_SECONDS=5` | ✅ (sin timeout global hard — configurable) |
| RNF-10 | Cobertura mínima 80% global, 95% dominio/use cases | 139 tests: 69 domain + 49 use cases + 17 infra + 14 presentation | ✅ |
| RNF-13 | CORS configurable | Settings.CORS_ORIGINS en `main.py` | ✅ (heredado) |

## Puntos de duda resueltos

1. **Paralelismo entre kits** → Todos los kits en paralelo sobre todos los servidores (`ExecutePipelineOperations` lanza todos los `OperationLauncher.launch()` sin await secuencial)
2. **Cancelación de PipelineExecution** → No implementada en v1. Las operaciones individuales pueden cancelarse, pero no la ejecución completa. Pendiente v1.1.
3. **Grupos de servidores como target** → `PipelineTarget.server_id` acepta ID de servidor o grupo. `ExecutePipelineOperations._expand_targets()` prueba como servidor primero, luego como grupo.

## Endpoints implementados

| Método | Path | Use Case | HTTP | Test |
|--------|------|----------|------|------|
| POST | `/api/v1/pipelines` | `CreatePipeline` | 201 | ✅ |
| GET | `/api/v1/pipelines` | `ListPipelines` | 200 | ✅ |
| GET | `/api/v1/pipelines/{id}` | `GetPipeline` | 200/404 | ✅ |
| PUT | `/api/v1/pipelines/{id}` | `UpdatePipeline` | 200/404/409 | ✅ |
| DELETE | `/api/v1/pipelines/{id}` | `DeletePipeline` | 204/404/409 | ✅ |
| POST | `/api/v1/pipelines/{id}/executions` | `LaunchPipeline` | 201/404/422 | ✅ |
| GET | `/api/v1/pipelines/{id}/executions` | `GetPipelineExecutions` | 200/404 | ✅ |
| GET | `/api/v1/pipelines/{id}/executions/{exec_id}` | `GetPipelineExecutionDetail` | 200/404 | ✅ |

## Tests por capa

| Capa | Tests | Archivo |
|------|-------|---------|
| Domain (VOs, Entities, Exceptions) | 69 | test_domain/ |
| Use Cases (Commands) | 20 | test_use_cases/ |
| Use Cases (Queries) | 9 | test_use_cases/ |
| Use Cases (Async Task) | 10 | test_use_cases/ |
| Infrastructure (Repositories) | 14 | test_infrastructure/ |
| Infrastructure (Adapter) | 3 | test_infrastructure/ |
| Presentation (Endpoints) | 14 | test_presentation/ |
| **Total** | **139** | |