# Requisitos del Módulo Kits

> **Inspiración de diseño**: el modelo de repositorios+kits está inspirado en Helm (registro de repositorios) + Kustomize (`ikctl.yaml` como manifiesto declarativo). Git es la fuente de verdad; la DB es un índice derivado que sync mantiene actualizado.

## Introducción

El módulo Kits gestiona repositorios Git que contienen kits de instalación y configuración de software. Un kit es un manifiesto declarativo (`ikctl.yaml`) con scripts, templates y valores que puede ejecutarse en cualquier servidor registrado en ikctl. El módulo nunca almacena los ficheros — mantiene en DB un índice derivado de Git, sincronizado periódicamente, que permite descubrir y listar kits disponibles. Los ficheros se descargan en runtime mediante shallow clone al ejecutar una operación.

## Actores

### Usuario
- Registrar y eliminar repositorios Git propios
- Disparar sincronizaciones manuales sobre sus repositorios
- Consultar y filtrar kits descubiertos en sus repositorios
- Usar kits en operaciones y pipelines
- Solo puede ver y operar sobre sus propios repositorios y kits

### Sistema
- Sincroniza repositorios automáticamente cada 30 minutos (configurable)
- Reconcilia el índice de kits en DB con el estado de Git tras cada sync
- Realiza shallow clones en runtime para obtener los ficheros del kit al ejecutar una operación
- Marca kits como `is_deleted` si desaparecen del índice raíz del repositorio

## Glosario

- **Repositorio**: Repositorio Git registrado por el usuario que contiene uno o más kits
- **Kit**: Unidad de instalación/configuración descubierta en un repositorio tras sync. Definida por su `ikctl.yaml` en el subdirectorio correspondiente
- **Manifiesto**: Fichero `ikctl.yaml` que describe un kit (nombre, versión, scripts, templates, valores por defecto, backup)
- **Índice Raíz**: `ikctl.yaml` en la raíz del repositorio que declara explícitamente qué kits expone el repositorio
- **Sync**: Proceso de sincronización que reconcilia el estado de Git con el índice de kits en DB
- **Shallow Clone**: Descarga superficial del repositorio (sin historial completo) usada en runtime para obtener los ficheros del kit
- **Ref**: Branch o tag del repositorio Git que indica qué versión del código se usa
- **Template Jinja2**: Fichero `.j2` con variables que se renderizan con los `values` del kit antes de subirse al servidor
- **Values**: Valores por defecto de un kit, sobreescribibles al lanzar la operación

## Puntos de Duda / Ambigüedades

### 1. Repositorios compartidos entre usuarios
**Descripción**: No se especifica si múltiples usuarios pueden registrar el mismo repositorio Git o si cada uno debe registrarlo por separado con su propia credencial.

**Impacto**: Unicidad en DB, validación de ownership, comportamiento del sync cuando el mismo repo existe para varios usuarios.

**Opciones**:
- Cada usuario registra su propia copia del repositorio (modelo actual implícito)
- Repositorios compartidos con control de acceso por usuario

### 2. Credencial expirada o eliminada en un repositorio
**Descripción**: No se especifica qué ocurre cuando la credencial asociada a un repositorio se elimina o expira. ¿El siguiente sync falla con `sync_error` y notifica al usuario, o falla silenciosamente?

**Impacto**: UX de notificación de errores, resiliencia del sync automático, consistencia entre módulo `servers` (credenciales) y `kits`.

### 3. Visibilidad de kits con is_deleted: true
**Descripción**: Cuando un kit pasa a `is_deleted: true` tras un sync, no se especifica si debe seguir siendo visible en el listado con algún indicador visual, o si desaparece completamente de los resultados.

**Impacto**: UX, gestión de referencias en pipelines, comportamiento de RF-10.

## Estructura de Ficheros en Git

El módulo kits introduce **dos tipos de `ikctl.yaml`** según su posición en el repositorio:

### `ikctl.yaml` raíz — índice del repositorio

Obligatorio en la raíz del repositorio. Declara qué kits expone el repo:

```yaml
kits:
  - haproxy/
  - nginx/
  - bind9/
```

- Solo los kits declarados aquí son visibles en la app — el autor controla explícitamente qué expone
- Si no existe este fichero → sync falla con error: "No se encontró ikctl.yaml en la raíz del repositorio"

### `ikctl.yaml` de kit — manifiesto de un kit concreto

Vive en el subdirectorio de cada kit (ej: `haproxy/ikctl.yaml`):

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

**Reglas del manifiesto de kit:**
- `files.uploads[]` puede contener `.sh`, `.py` y `.j2` (templates Jinja2)
- `files.pipeline[]` define el orden de ejecución de los scripts subidos
- Archivos con prefijo de distro se usan automáticamente según el SO detectado (ej: `debian-install.sh`)
- `backup[]` es opcional — si se declara, la app hace snapshot antes de ejecutar
- `debug_level` es opcional — define si se captura output SSH (`none` | `errors` | `full`). El default es `none`
- `values{}` son los valores por defecto para los templates Jinja2, sobreescribibles al lanzar la operación

## Estructura de repositorio de ejemplo

```
mi-repo/
├── ikctl.yaml              ← raíz: kits: [haproxy/, nginx/, bind9/]
├── haproxy/
│   ├── ikctl.yaml          ← manifiesto del kit haproxy
│   ├── haproxy.cfg.j2
│   └── install-haproxy.sh
├── nginx/
│   ├── ikctl.yaml
│   └── nginx.conf.j2
├── bind9/
│   └── ikctl.yaml
└── scripts/                ← no declarado en raíz → ignorado por ikctl
    └── utils.sh
```

## Modelo de Dominio: Repository + Kit

El módulo introduce **dos entidades**: `Repository` y `Kit`.

### `Repository`
Representa un repositorio Git registrado por el usuario. Es la puerta de entrada para obtener kits.

- Campos: `id`, `user_id`, `url`, `ref` (branch o tag), `credential_id` (opt), `sync_status`, `sync_error_message`, `last_synced_at`, `last_commit_sha`, `is_deleted`, `created_at`, `updated_at`
- La credencial es **compartida por todos los kits del repo** — no se repite por kit

### `Kit`
Representa un kit descubierto dentro de un repositorio tras sincronización. Sus metadatos los lee la app del `ikctl.yaml` del subdirectorio.

- Campos: `id`, `user_id`, `repository_id`, `path_in_repo`, `name`, `description`, `version`, `tags`, `values`, `debug_level`, `sync_status`, `last_synced_at`, `last_commit_sha`, `sync_error_message`, `is_deleted`, `created_at`, `updated_at`
- **No tiene `repo_url` ni `credential_id` propios** — los hereda del `Repository`

## Fuente de Kits (Git)

ikctl nunca almacena los ficheros de los kits — los descarga en runtime mediante shallow clone al ejecutar una operación.

- **Proveedores soportados**: GitHub (v1). GitLab y Gitea en v2
- **Versionado**: por branch (ej: `main`) o por tag (ej: `v1.0.0`). Ambos soportados a nivel de repositorio
- **Repos privados**: requieren una `Credential` de tipo `git_https` (Personal Access Token) o `git_ssh`

## Almacenamiento

- **Metadatos de repositorios**: MariaDB (`ikctl_repositories`)
- **Metadatos de kits**: MariaDB (`ikctl_kits`) — índice derivado de Git, mantenido por sync
- **Ficheros** (scripts, templates): **no se almacenan** — shallow clone en directorio temporal en cada operación, eliminado tras su uso
- **Caché de ficheros transferidos al servidor**: tabla `server_kit_file_cache` (ver módulo operations)

## Schema de Base de Datos

```sql
CREATE TABLE repositories (
    id                  VARCHAR(36) NOT NULL,
    user_id             VARCHAR(36) NOT NULL,
    url                 VARCHAR(512) NOT NULL,
    ref                 VARCHAR(255) NOT NULL,   -- branch o tag
    credential_id       VARCHAR(36),             -- NULL si repo público
    sync_status         ENUM('never_synced','synced','sync_error') DEFAULT 'never_synced',
    last_synced_at      DATETIME,
    last_commit_sha     CHAR(40),
    sync_error_message  TEXT,
    is_deleted          TINYINT(1) DEFAULT 0,
    created_at          DATETIME NOT NULL,
    updated_at          DATETIME NOT NULL,
    PRIMARY KEY (id),
    INDEX idx_user_id (user_id)
);

CREATE TABLE kits (
    id                  VARCHAR(36) NOT NULL,
    user_id             VARCHAR(36) NOT NULL,
    repository_id       VARCHAR(36) NOT NULL,   -- FK a repositories.id
    path_in_repo        VARCHAR(512) NOT NULL,   -- carpeta del kit en el repo
    name                VARCHAR(255),            -- leído del ikctl.yaml tras sync
    description         TEXT,
    version             VARCHAR(50),
    tags                JSON,
    `values`            JSON,
    debug_level         ENUM('none','errors','full') DEFAULT 'none',
    sync_status         ENUM('never_synced','synced','sync_error') DEFAULT 'never_synced',
    last_synced_at      DATETIME,
    last_commit_sha     CHAR(40),
    sync_error_message  TEXT,
    is_deleted          TINYINT(1) DEFAULT 0,
    created_at          DATETIME NOT NULL,
    updated_at          DATETIME NOT NULL,
    PRIMARY KEY (id),
    INDEX idx_user_id (user_id),
    INDEX idx_repository_id (repository_id),
    INDEX idx_sync_status (sync_status),
    INDEX idx_is_deleted (is_deleted)
);
```

## Flujo de Registro y Sincronización

```
1. POST /repositories { url, ref, credential_id? }
   → Repository creado con sync_status: never_synced
   → No se hace ninguna llamada a Git

2. POST /repositories/{id}/sync
   → Shallow clone del repo
   → Lee ikctl.yaml raíz → obtiene paths: [haproxy/, nginx/]
   → Si no existe ikctl.yaml raíz → sync_error: "No se encontró ikctl.yaml en la raíz"
   → Para cada path: lee ikctl.yaml del subdirectorio → extrae metadatos
   → Reconcilia con DB:
       - Path en índice, no en DB → CREATE Kit (sync_status: synced)
       - Path en índice, en DB    → UPDATE metadatos del Kit
       - Path eliminado del índice, en DB → Kit.is_deleted = true
   → Repository.sync_status = synced

3. Kits disponibles en la app → listos para operaciones y pipelines
```

**Sync periódico automático**: cada 30 minutos (configurable con `KIT_SYNC_INTERVAL_MINUTES=30`). Solo actualiza metadatos y reconcilia el índice — no almacena ficheros.

**Actualizar ref del repositorio**: `PUT /repositories/{id}` con nuevo `ref` → `sync_status: never_synced` → re-sync necesario.

## Requisitos Funcionales — Repositories

1. **RF-01**: Registrar un repositorio con `url`, `ref` (branch o tag) y opcionalmente `credential_id`. Se crea con `sync_status: never_synced`. No se hace ninguna llamada a Git en este paso
2. **RF-02**: Listar repositorios del usuario autenticado con paginación. Solo devuelve repositorios no eliminados. Incluye `sync_status` en la respuesta
3. **RF-03**: Obtener detalle de un repositorio por `id`, incluyendo todos los metadatos y `sync_status`. Solo repositorios propios
4. **RF-04**: Actualizar un repositorio (`url`, `ref`, `credential_id`). Si se cambia `ref` o `url`, el `sync_status` vuelve a `never_synced` automáticamente. Solo repositorios propios
5. **RF-05**: Eliminar un repositorio. Solo si ningún kit del repo está referenciado en pipelines ni operaciones en curso (RN-30). Si hay referencias → 409. Si no hay referencias → borrado físico del repo y todos sus kits de DB
6. **RF-06**: Sincronizar un repositorio manualmente (`POST /repositories/{id}/sync`). Reconcilia kits en DB con el índice del `ikctl.yaml` raíz. Si el `ikctl.yaml` raíz no existe → `sync_error`. Si falla el clone → `sync_error`. Devuelve 200 en ambos casos — el error es de negocio, no de infraestructura

## Requisitos Funcionales — Kits

7. **RF-10**: Listar kits del usuario autenticado con paginación y filtrado por `tags` y `repository_id`. Solo devuelve kits no eliminados (`is_deleted: false`). Incluye `sync_status` en la respuesta
8. **RF-11**: Obtener detalle de un kit por `id`, incluyendo todos los metadatos y `sync_status`. Solo kits propios
9. **RF-35**: Los kits no se registran manualmente — son descubiertos y gestionados automáticamente por el sync del repositorio (RF-06). No existe endpoint `POST /kits`

## Reglas de Negocio

- **RN-01**: Toda operación sobre un recurso (`Repository`, `Kit`) debe validar que `user_id` del recurso coincide con el usuario autenticado. Cualquier acceso a un recurso ajeno devuelve el mismo error que si no existiera (evitar enumeración)
- **RN-21**: Todos los ficheros declarados en `files.pipeline[]` del `ikctl.yaml` deben estar también declarados en `files.uploads[]`. Si algún pipeline file no está en uploads → `InvalidManifestError` al parsear el manifiesto
- **RN-23**: El `credential_id` asociado a un repositorio, si se proporciona, debe pertenecer a una credencial de tipo `git_https` (Personal Access Token) o `git_ssh` (clave privada). Cualquier otro tipo → `InvalidGitCredentialTypeError`
- **RN-29**: Si durante una sincronización un kit pasa a `is_deleted: true` (fue eliminado del índice raíz) y ese kit tiene referencias activas en pipelines u operaciones en curso, se debe generar una notificación de advertencia. La sincronización no falla por esto — el kit queda marcado como eliminado y las referencias en pipelines quedan inválidas hasta que se actualicen
- **RN-30**: No se puede eliminar un repositorio si alguno de sus kits está referenciado en pipelines u operaciones activas. Si hay referencias → `RepositoryInUseError` (409). El borrado es físico (repo + todos sus kits en DB) solo cuando no hay referencias

## Requisitos No Funcionales

- **RNF-01**: Endpoints CRUD de repositorios y kits responden en < 200ms p99
- **RNF-09**: Logs estructurados en JSON. Nunca se loguean contenidos de ficheros de kits ni tokens ni credenciales Git (ni PATs ni claves privadas SSH)
- **RNF-10**: Cobertura mínima global 80%; dominio y casos de uso 95%; adaptadores 70%. Todo caso de uso con tests de éxito y error
- **RNF-12**: Timeout de git clone (shallow): 30 segundos. Si se supera → `sync_error`
- **RNF-14**: El clone de Git siempre es shallow (`depth=1`) — nunca se clona el historial completo. Minimiza tiempo de descarga y uso de disco
- **RNF-15**: El directorio temporal creado para el shallow clone debe eliminarse **siempre** al finalizar la operación, tanto en caso de éxito como de error (patrón `try/finally`). Nunca dejar ficheros temporales en disco
- **RNF-14**: Shallow clone obligatorio (`depth=1`). Solo se descarga el commit apuntado por `ref`, nunca el historial completo
- **RNF-15**: Directorio temporal del clone se elimina siempre tras su uso, tanto en éxito como en error
- **RNF-16**: Sync periódico automático cada `KIT_SYNC_INTERVAL_MINUTES` minutos (default: 30). Configurable en `.env`

## Features Futuras (v2)

- **FF-03**: Auto-sync via webhook — push al repo → ikctl detecta → re-sync automático
- **FF-04**: Scripts de rollback por kit para revertir instalaciones completadas
- **FF-05**: Soporte a GitLab y Gitea como proveedores Git
- **FF-06**: Integración OAuth GitHub — usar el token del login para acceder a repos privados sin credenciales manuales
- **FF-07**: Garbage collection automático de metadatos huérfanos (kits/repos con `is_deleted: true` sin referencias, con más de X días de antigüedad)

## Reglas de Negocio

- **RN-01**: Un usuario solo puede ver, modificar y eliminar sus propios repositorios y kits. La validación de ownership se hace en el caso de uso, no en presentación
- **RN-03**: El borrado de un kit es siempre consecuencia del sync — se marca `is_deleted: true` automáticamente cuando desaparece del `ikctl.yaml` raíz. Los metadatos se conservan para mantener la integridad del historial de operaciones
- **RN-09**: Un kit con `sync_status: never_synced` o `sync_status: sync_error` o `is_deleted: true` no puede usarse en operaciones ni pipelines. El intento lanza una excepción de dominio
- **RN-10**: Un kit con `is_deleted: true` no puede reactivarse. Es un estado terminal (solo revertible creando un nuevo kit via sync si el path vuelve al índice raíz)
- **RN-21**: `files.pipeline[]` en el `ikctl.yaml` solo puede referenciar archivos declarados en `files.uploads[]`. Un archivo en `pipeline[]` no presente en `uploads[]` hace el manifest inválido → ese kit queda con `sync_status: sync_error`
- **RN-22**: Un kit eliminado no puede usarse como `kit_id` en nuevas operaciones ni pipelines
- **RN-23**: La `Credential` referenciada en `credential_id` del repositorio debe ser de tipo `git_https` o `git_ssh`. Usar una credencial de tipo `ssh` lanza una excepción de dominio
- **RN-28**: Al lanzar una operación o pipeline, la app valida que todos los kits referenciados son `is_usable()` (synced + not deleted) **antes** de conectar con ningún servidor remoto. Si alguno no es usable → error controlado, ningún servidor es tocado
- **RN-29**: Si el sync detecta que un kit pasa a `is_deleted: true` y ese kit está referenciado en pipelines → se genera una notificación visible en el frontend listando los pipelines afectados
- **RN-30**: Un repositorio solo puede eliminarse si ninguno de sus kits está referenciado en pipelines (activos o no) ni hay operaciones en curso usando sus kits. En caso contrario → 409 listando las referencias
- **RN-31**: Si un repositorio no puede ser clonado en tiempo de ejecución de una operación (repo eliminado, credenciales inválidas, timeout) → la operación se cancela con error controlado antes de tocar el servidor remoto
