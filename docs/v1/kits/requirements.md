# Requisitos del Módulo Kits

## Estructura del Manifiesto (`ikctl.yaml`)

```yaml
name: "Install HAProxy"
description: "Installs and configures HAProxy load balancer"
version: "1.0.0"
tags:
  - networking
  - loadbalancer

values:
  frontend_port: 80
  backend_servers: []

files:
  uploads:
    - haproxy.cfg.j2        # template Jinja2 — renderizado con values antes de subir
    - install-haproxy.sh    # script estático
  pipeline:
    - install-haproxy.sh    # orden de ejecución

backup:                     # opcional — archivos del servidor a respaldar antes de ejecutar
  - /etc/haproxy/haproxy.cfg

debug_level: none           # none (default) | errors | full
```

**Reglas del manifiesto:**
- `files.uploads[]` puede contener `.sh`, `.py` y `.j2` (templates Jinja2)
- `files.pipeline[]` define el orden de ejecución de los scripts subidos
- Archivos con prefijo de distro se usan automáticamente según el SO detectado (ej: `debian-install.sh`)
- `backup[]` es opcional — si se declara, la app hace snapshot antes de ejecutar
- `debug_level` es opcional — define si se captura output SSH (`none` | `errors` | `full`). El default es `none`
- `values{}` son los valores por defecto para los templates Jinja2, sobreescribibles al lanzar la operación

## Fuente de Kits (Git)

Los kits se registran apuntando a un repositorio Git. ikctl nunca almacena los ficheros — los descarga en runtime al sincronizar o al ejecutar una operación.

- **Monorepo**: múltiples kits en un mismo repositorio, separados por carpetas. Cada kit apunta a su `path_in_repo`
- **Proveedores soportados**: GitHub (v1). GitLab y Gitea en v2
- **Versionado**: por branch (ej: `main`) o por tag (ej: `v1.0.0`). Ambos soportados
- **Repos privados**: requieren una `Credential` de tipo `git_https` (Personal Access Token) o `git_ssh`

## Almacenamiento

- **Metadatos del kit** (`name`, `description`, `version`, `tags`, `values`, `debug_level`, `repo_url`, `ref`, `path_in_repo`, `sync_status`, `last_commit_sha`): MariaDB (`ikctl_kits`)
- **Ficheros** (scripts, templates): **no se almacenan** — se descargan desde Git en runtime mediante shallow clone (`depth=1`)
- **Caché de ficheros transferidos**: tabla `server_kit_file_cache` (ver ADR-005 y módulo operations)

## Schema de Base de Datos

```sql
CREATE TABLE kits (
    id                  VARCHAR(36) NOT NULL,
    user_id             VARCHAR(36) NOT NULL,
    name                VARCHAR(255),           -- leído del ikctl.yaml tras sync
    description         TEXT,
    version             VARCHAR(50),
    tags                JSON,
    `values`            JSON,
    debug_level         ENUM('none','errors','full') DEFAULT 'none',
    repo_url            VARCHAR(512) NOT NULL,
    ref                 VARCHAR(255) NOT NULL,   -- branch o tag
    path_in_repo        VARCHAR(512) NOT NULL,   -- carpeta del kit en el monorepo
    git_credential_id   VARCHAR(36),             -- NULL si repo público
    sync_status         ENUM('never_synced','synced','sync_error') DEFAULT 'never_synced',
    last_synced_at      DATETIME,
    last_commit_sha     CHAR(40),
    sync_error_message  TEXT,
    is_deleted          TINYINT(1) DEFAULT 0,
    created_at          DATETIME NOT NULL,
    updated_at          DATETIME NOT NULL,
    PRIMARY KEY (id)
);
```

## Flujo de Registro y Sincronización

1. `POST /kits` con `repo_url`, `ref`, `path_in_repo` y opcionalmente `git_credential_id` → API crea el kit en MariaDB con `sync_status: never_synced`. No se hace ninguna llamada a Git en este paso
2. `POST /kits/{id}/sync` → API hace shallow clone del repo, valida el `ikctl.yaml` en `path_in_repo`, extrae metadatos (`name`, `description`, `version`, `tags`, `values`) y actualiza `sync_status: synced`, `last_commit_sha`, `last_synced_at`
3. El kit queda listo para usarse en operaciones y pipelines

Para actualizar a una nueva versión: cambiar `ref` vía RF-12 y volver a sincronizar con RF-35.

## Requisitos Funcionales

1. **RF-09**: Registrar un kit con `repo_url`, `ref` (branch o tag), `path_in_repo` y opcionalmente `git_credential_id`. El kit se crea con `sync_status: never_synced`. No se hace ninguna llamada a Git en este paso
2. **RF-10**: Listar kits del usuario autenticado con paginación y filtrado por `tags`. Solo devuelve kits no eliminados (`is_deleted: false`). Incluye `sync_status` en la respuesta
3. **RF-11**: Obtener detalle de un kit por `id`, incluyendo todos los metadatos y `sync_status`. Solo kits propios
4. **RF-12**: Actualizar un kit (`repo_url`, `ref`, `path_in_repo`, `git_credential_id`). Si se cambia `ref`, `repo_url` o `path_in_repo`, el `sync_status` vuelve a `never_synced` automáticamente. Solo kits propios
5. **RF-13**: Eliminar un kit. Borrado suave: se marca `is_deleted: true` en MariaDB y desaparece de los listados. Los metadatos se conservan para mantener la integridad del historial de operaciones. No hay ficheros que eliminar. Solo kits propios
6. **RF-35**: Sincronizar un kit manualmente (`POST /kits/{id}/sync`). Hace shallow clone (`depth=1`) del repo en `ref`, lee y valida el `ikctl.yaml` en `path_in_repo`, extrae metadatos y actualiza `sync_status`, `last_commit_sha`, `last_synced_at`. Si falla, actualiza `sync_status: sync_error` y `sync_error_message`
7. **RF-36**: Al registrar o actualizar un kit con repo privado, asociar una `Credential` de tipo `git_https` o `git_ssh` mediante `git_credential_id`. La credencial se valida en RF-35 al sincronizar

## Requisitos No Funcionales

- **RNF-01**: Endpoints CRUD de kits responden en < 200ms p99
- **RNF-09**: Logs estructurados en JSON con `timestamp`, `level`, `request_id`, `user_id`, `operation_type`, `duration_ms`, `error`. Nunca se loguean contenidos de ficheros de kits ni tokens ni credenciales Git
- **RNF-10**: Cobertura mínima global 80%; dominio y casos de uso 95%; adaptadores 70%. Todo caso de uso con tests de éxito y error
- **RNF-12**: Timeout de git clone (shallow): 30 segundos. Si se supera, RF-35 falla con `sync_status: sync_error`
- **RNF-13**: CORS configurado via `ALLOWED_ORIGINS`. En producción rechaza todas las peticiones cross-origin si no está configurado
- **RNF-14**: Shallow clone obligatorio (`depth=1`). Solo se descarga el commit apuntado por `ref`, nunca el historial completo. Esto aplica tanto a RF-35 (sync) como a la descarga de ficheros en runtime durante la ejecución de operaciones

## Features Futuras (v2)

- **FF-03**: Auto-sync via webhook — push al repo → ikctl detecta → re-sync automático
- **FF-04**: Scripts de rollback por kit para revertir instalaciones completadas
- **FF-05**: Soporte a GitLab y Gitea como proveedores Git
- **FF-06**: Integración OAuth GitHub — usar el token del login para acceder a repos privados del usuario sin necesidad de crear credenciales manuales

## Reglas de Negocio

- **RN-01**: Un usuario solo puede ver, modificar y eliminar sus propios kits. La validación de ownership se hace en el caso de uso, no en presentación
- **RN-03**: El borrado de un kit es suave — se marca `is_deleted: true` en MariaDB y desaparece de los listados, pero los metadatos se conservan para mantener la integridad del historial de operaciones. No hay ficheros que eliminar — nunca se almacenaron en la API
- **RN-09**: Un kit con `sync_status: never_synced` o `sync_status: sync_error` no puede usarse como `kit_id` en operaciones ni pipelines. El intento lanza una excepción de dominio
- **RN-10**: Un kit eliminado (`is_deleted: true`) no puede reactivarse ni modificarse. Es un estado terminal
- **RN-21**: `files.pipeline[]` en el `ikctl.yaml` solo puede referenciar archivos declarados en `files.uploads[]`. Un archivo en `pipeline[]` no presente en `uploads[]` hace el manifest inválido — RF-35 falla con `sync_status: sync_error`
- **RN-22**: Un kit eliminado no puede usarse como `kit_id` en nuevas operaciones ni pipelines. El intento lanza una excepción de dominio
- **RN-23**: La `Credential` referenciada en `git_credential_id` debe ser de tipo `git_https` o `git_ssh`. Usar una credencial de tipo `ssh` lanza una excepción de dominio
