# Tareas del Módulo Kits v1.0.0

**Estado:** 0 tests — ⏳ PENDIENTE DE IMPLEMENTACIÓN

> Módulo que gestiona kits de configuración respaldados por repositorios Git.
> Un kit es un conjunto de scripts/templates almacenados en Git, registrados en la API con
> `repo_url`, `ref` y `path_in_repo`. Los ficheros nunca se almacenan — se descargan en runtime.
> Dependencia crítica de `operations` y `pipelines`.

## Fase 0: Estructura Clean Architecture

**DEBE EJECUTARSE PRIMERO** — El módulo `app/v1/kits/` no existe aún; hay que crearlo desde cero

- [ ] **T-00.1**: Crear `app/v1/kits/` con `__init__.py` y estructura `domain/` (`entities/`, `value_objects/`, `exceptions/`) con sus `__init__.py`
- [ ] **T-00.2**: Crear `application/` con subcarpetas `commands/`, `queries/`, `dtos/`, `interfaces/` y sus `__init__.py`
- [ ] **T-00.3**: Crear `application/exceptions.py` (UseCaseException, KitNotSyncedError, KitAlreadyDeletedError, InvalidGitCredentialTypeError, ManifestValidationError)
- [ ] **T-00.4**: Crear `infrastructure/` con subcarpetas `persistence/`, `repositories/`, `adapters/`, `presentation/` y sus `__init__.py`
- [ ] **T-00.5**: Crear tests directory `tests/v1/kits/` con subcarpetas `test_domain/`, `test_use_cases/`, `test_infrastructure/`, `test_presentation/` y sus `__init__.py`

  **FASE 0 PENDIENTE: 5 tareas — bloquea todo el módulo**

## Fase 1: Entidades y Value Objects (Domain Layer)

- [ ] **T-01**: Value Object `KitSyncStatus` (`never_synced` | `synced` | `sync_error`) — inmutable, validación de enum, sin dependencias externas — 4 tests
- [ ] **T-02**: Value Object `KitManifest` — inmutable, parsea y valida `ikctl.yaml` como `dict`. Expone: `name`, `description`, `version`, `tags`, `values`, `debug_level`, `upload_files`, `pipeline_files`, `backup_files`. Validación en `__post_init__`: todos los `pipeline_files[]` deben estar en `uploads_files[]` (RN-21). Si falla lanza `InvalidManifestError` — 8 tests
- [ ] **T-03**: Entity `Kit` — campos: `id`, `user_id`, `name`, `description`, `version`, `tags: list[str]`, `values: dict`, `debug_level`, `repo_url`, `ref`, `path_in_repo`, `git_credential_id` (opt), `sync_status: KitSyncStatus`, `last_synced_at` (opt), `last_commit_sha` (opt), `sync_error_message` (opt), `is_deleted: bool`, `created_at`, `updated_at`. Comandos: `update(repo_url, ref, path_in_repo, git_credential_id)` → si cambia repo fuente, resetea `sync_status` a `never_synced` (RF-12), `mark_synced(manifest, commit_sha)` → actualiza campos del manifest, `mark_sync_error(error_message)`, `delete()` → `is_deleted = True` (RN-10), `ensure_not_deleted()` → lanza `KitAlreadyDeletedError` si `is_deleted`. Queries: `is_synced()`, `is_usable()` (synced AND not deleted). `__eq__` por `id` — 12 tests
- [ ] **T-04**: Domain Exceptions en `domain/exceptions/` — `KitNotFoundError`, `InvalidManifestError` — con mensajes descriptivos — tests implícitos en T-03

  **FASE 1 PENDIENTE: ~24 tests**

## Fase 2: Use Cases (Application Layer) — CQRS

### Ports (Interfaces)

- [ ] **T-05**: Port `KitRepository` ABC en `application/interfaces/kit_repository.py` — métodos: `save(kit)`, `find_by_id(id, user_id)`, `find_all_by_user(user_id, page, per_page, tags_filter)`, `update(kit)` — 0 tests (probados via contract tests)
- [ ] **T-06**: Port `GitRepository` ABC en `application/interfaces/git_repository.py` — método: `clone_shallow(repo_url, ref, path_in_repo, dest_path, credential)` → descarga los ficheros del kit en `dest_path`. Timeout 30s (RNF-12). Credential puede ser `None` (repo público), `git_https` o `git_ssh`. Retorna `commit_sha: str` del HEAD clonado — 0 tests

### Commands

- [ ] **T-07**: Command `RegisterKit(user_id, repo_url, ref, path_in_repo, git_credential_id)` → devuelve `KitResult` DTO — crea kit con `sync_status: never_synced`, valida que `git_credential_id` existe y es de tipo `git_https` o `git_ssh` si se proporciona (RN-23), persiste — 4 tests
- [ ] **T-08**: Command `UpdateKit(user_id, kit_id, repo_url, ref, path_in_repo, git_credential_id)` → devuelve `KitResult` — valida ownership (RN-01), valida kit no eliminado (RN-10), si cambia fuente resetea `sync_status`, persiste — 4 tests
- [ ] **T-09**: Command `DeleteKit(user_id, kit_id)` → `None` — valida ownership (RN-01), valida kit no eliminado aún (RN-10), llama `kit.delete()`, persiste (borrado suave, RN-03) — 4 tests
- [ ] **T-10**: Command `SyncKit(user_id, kit_id)` → devuelve `KitSyncResult` — valida ownership (RN-01), valida kit no eliminado (RN-10), hace shallow clone via `GitRepository`, lee y valida `ikctl.yaml`, llama `kit.mark_synced(...)` o `kit.mark_sync_error(...)`, persiste. Si falla, persiste `sync_error` en vez de lanzar excepción — 6 tests

### Queries

- [ ] **T-11**: Query `GetKit(user_id, kit_id)` → devuelve `KitResult` — valida ownership (RN-01), solo devuelve kits no eliminados — 3 tests
- [ ] **T-12**: Query `ListKits(user_id, page, per_page, tags_filter)` → devuelve `KitListResult` paginado — solo kits no eliminados (RN-03) — 2 tests

### DTOs

- [ ] **T-12.1**: Crear DTOs en `application/dtos/`: `KitResult`, `KitListResult`, `KitSyncResult` — sin tests directos

  **FASE 2 PENDIENTE: ~23 tests**

## Fase 3: Infrastructure (Repositories y Adapters)

### Repository

- [ ] **T-13**: `SQLAlchemyKitRepository` — implementa `KitRepository` port. Filtra automáticamente `is_deleted = false` en todas las queries de lectura (nunca devuelve kits eliminados a menos que sea para lecturas internas del historial). Soporte JSON para `tags` y `values` — 6 tests

### Adapters

- [ ] **T-14**: `GitPythonRepository` — implementa `GitRepository` port usando `gitpython`. Shallow clone (`depth=1`, RNF-14). Soporte de credentials: `None` (público), `git_https` (usuario + PAT en URL), `git_ssh` (clave privada en archivo temporal). Timeout de 30s via `asyncio.wait_for` (RNF-12). Limpia el directorio temporal tras la operación. Nunca loguea el PAT ni la clave privada (RNF-09) — 8 tests

### Composition Root

- [ ] **T-15**: Extender `main.py` (Composition Root) con adaptadores del módulo kits — `SQLAlchemyKitRepository`, `GitPythonRepository`. Inyectar en `RegisterKit`, `UpdateKit`, `DeleteKit`, `SyncKit`, `GetKit`, `ListKits`

### Persistence Models

- [ ] **T-16**: Modelos SQLAlchemy en `infrastructure/persistence/models.py` — tabla `kits`

### Database Migrations (Alembic)

- [ ] **T-17**: Alembic migration: tabla `kits` — todos los campos del schema (ver requirements.md). Índices: `user_id`, `sync_status`, `is_deleted`. Migración con `down()` funcional

### Presentation

- [ ] **T-18**: Schemas Pydantic en `schemas.py` — `RegisterKitRequest`, `UpdateKitRequest`, `KitResponse`, `KitSyncResponse`
- [ ] **T-19**: `deps.py` — dependencias FastAPI: `get_current_user_id(token)` (JWT auth), `get_db_session()`, factories de use cases
- [ ] **T-20**: Exception handlers en `exception_handlers.py` — `KitNotFoundError` → 404, `KitAlreadyDeletedError` → 409, `KitNotSyncedError` → 422, `InvalidGitCredentialTypeError` → 422

  **FASE 3 PENDIENTE: ~14 tests**

## Fase 4: Presentation (FastAPI Endpoints)

- [ ] **T-21**: `POST /api/v1/kits` — registrar kit. Body: `RegisterKitRequest`. Response 201: `KitResponse`
- [ ] **T-22**: `GET /api/v1/kits` — listar kits paginados. Query params: `page`, `per_page`, `tags` (multi-valor). Response 200: lista `KitResponse`
- [ ] **T-23**: `GET /api/v1/kits/{id}` — obtener kit. Response 200: `KitResponse` o 404
- [ ] **T-24**: `PUT /api/v1/kits/{id}` — actualizar kit. Response 200: `KitResponse` o 404/403
- [ ] **T-25**: `DELETE /api/v1/kits/{id}` — eliminar kit (soft delete). Response 204 o 404/403
- [ ] **T-26**: `POST /api/v1/kits/{id}/sync` — sincronizar kit desde Git. Response 200: `KitSyncResponse` con `sync_status`, `last_commit_sha`. Si falla, devuelve 200 con `sync_status: sync_error` y `sync_error_message` (no 500 — el error es de negocio, no de infraestructura)

  **FASE 4 PENDIENTE: 6 endpoints**

## Fase 5: Tests (TDD)

### Tests de Integración FastAPI

- [ ] **T-27**: Tests de presentación kits — flujos: registrar OK (201), sync exitoso (200), sync con error Git devuelve `sync_error` (200), kit eliminado → 409, credencial tipo `ssh` en kit → 422 — 5 tests
- [ ] **T-28**: Tests de integración `GitPythonRepository` — con repo real o mock: clone público OK, clone privado git_https OK, clone timeout → `sync_error`, `ikctl.yaml` inválido → `sync_error` — 4 tests

### Contract Tests

- [ ] **T-29**: Contract tests `GitRepository` port — verifica que `GitPythonRepository` implementa correctamente el contrato: retorna `commit_sha`, maneja timeout, limpia archivos temporales, no escribe credentials en disco permanentemente — 4 tests

  **FASE 5 PENDIENTE: ~13 tests**

---

## 📊 Resumen de Progreso

| Fase | Estado | Tests | Completitud |
|------|--------|-------|-------------|
| Fase 0 - Estructura | ⏳ **PENDIENTE** | — | 0% — **bloquea todo** |
| Fase 1 - Domain Layer | ⏳ **PENDIENTE** | — | 0% |
| Fase 2 - Use Cases (CQRS) | ⏳ **PENDIENTE** | — | 0% |
| Fase 3 - Infrastructure | ⏳ **PENDIENTE** | — | 0% |
| Fase 4 - Presentation | ⏳ **PENDIENTE** | — | 0% |
| Fase 5 - Tests | ⏳ **PENDIENTE** | — | 0% |
| Fase 6 - Documentación | ⏳ **PENDIENTE** | — | 0% |

**TOTAL ESTIMADO: ~74 tests**

## Fase 6: Documentación y Ajustes

- [ ] **T-30**: Documentación técnica → [ARCHITECTURE.md](../ARCHITECTURE.md) ya creado ✅ — verificar coverage
- [ ] **T-31**: Validación de requisitos vs implementación (todos los RF y RN)
- [ ] **T-32**: Review y refactoring de código
- [ ] **T-33**: API_GUIDE.md con ejemplos curl para todos los endpoints

### Próximos Pasos

1. 🔴 **CRÍTICO**: Ejecutar Fase 0 (crear carpeta `app/v1/kits/` con estructura completa)
2. ⏳ Implementar Domain (Kit entity, KitManifest VO, KitSyncStatus VO)
3. ⏳ Implementar Ports (KitRepository, GitRepository ABCs)
4. ⏳ Implementar Use Cases con TDD (RegisterKit, UpdateKit, DeleteKit, SyncKit, GetKit, ListKits)
5. ⏳ Implementar GitPythonRepository (shallow clone con credentials, timeout 30s)
6. ⏳ Crear migration Alembic `kits`
7. ⏳ Crear 6 endpoints FastAPI
8. ⏳ Tests de integración y contract tests

## Dependencias de Tareas

```mermaid
graph TD
    T00["Fase 0: Estructura<br/>(app/v1/kits/ no existe)"] --> T01["Fase 1: Domain"]
    T01 --> T05["T-05/06: Ports"]
    T05 --> T07["Fase 2: Commands"]
    T05 --> T11["Fase 2: Queries"]
    T07 --> T13["T-13: KitRepository"]
    T07 --> T14["T-14: GitPythonRepository"]
    T17["T-17: Migration kits"] --> T13
    T13 --> T21["Fase 4: Endpoints"]
    T18["Schemas"] --> T21
    T19["Deps"] --> T21
    T21 --> T27["Fase 5: Tests"]
    ServersModule["Módulo servers<br/>(CredentialRepository)"] --> T14
```

**Dependencias críticas:**

- **T-00.X** → Todo el módulo (EL DIRECTORIO NO EXISTE — bloquea todo)
- **T-01 (KitManifest)** → T-10 (SyncKit parsea el manifest)
- **T-02 (Kit entity)** → T-07, T-08, T-09, T-10 (todos los commands)
- **T-14 (GitPythonRepository)** → depende de `CredentialRepository` del módulo `servers` para obtener las credenciales Git
- **T-17 (Migration)** → T-13 (repository necesita tabla creada)

## Estadísticas

- **Total de tareas**: 33 tareas explícitas
- **Fases**: 7 (incluyendo Fase 0 de setup)
- **Tests estimados**: ~74 total
- **Endpoints**: 6 (CRUD + sync)
- **Entidades**: 1 (Kit)
- **Value Objects**: 2 (KitSyncStatus, KitManifest)
- **Use Cases**: 6 (4 commands + 2 queries)
- **Adapters**: 1 (GitPythonRepository)
- **Migrations Alembic**: 1 (kits)

## Cobertura de Reglas de Negocio

| RN | Descripción | Tareas | Estado |
|----|-------------|--------|--------|
| RN-01 | Ownership — solo kits propios | T-07, T-08, T-09, T-10, T-11, T-12 | ⏳ Pendiente |
| RN-03 | Borrado suave — `is_deleted: true` | T-09, T-13 | ⏳ Pendiente |
| RN-09 | Kit no sincronizado → no usar en ops | T-03 `is_usable()`, consumido por operations | ⏳ Pendiente |
| RN-10 | Kit eliminado → estado terminal | T-03 `ensure_not_deleted()`, T-08, T-09 | ⏳ Pendiente |
| RN-21 | `pipeline[]` ⊆ `uploads[]` en manifest | T-02 (KitManifest `__post_init__`) | ⏳ Pendiente |
| RN-22 | Kit eliminado → no usar en nuevas ops | T-03 `is_usable()`, consumido por operations | ⏳ Pendiente |
| RN-23 | `git_credential_id` solo tipo `git_https`/`git_ssh` | T-07, T-08 | ⏳ Pendiente |

**Estado RN: 0 implementadas, 7 pendientes**
