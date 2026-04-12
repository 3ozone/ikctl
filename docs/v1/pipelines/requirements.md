# Requisitos del Módulo Pipelines

## Introducción

El módulo Pipelines permite ejecutar uno o más kits sobre múltiples servidores de forma orquestada. Un pipeline es una definición reutilizable (template) que combina una lista de kits con una lista de servidores target. Al lanzarlo se crea una `PipelineExecution` que genera automáticamente N×M operaciones individuales (una por cada combinación kit+servidor) y gestiona su estado agregado. El estado histórico se preserva mediante un snapshot de la configuración usada en cada ejecución.

## Actores

### Usuario
- Crear, editar y eliminar sus propios pipelines
- Lanzar ejecuciones de sus propios pipelines
- Consultar el historial de ejecuciones y el estado agregado de cada una
- Ver el detalle de las operaciones individuales generadas por cada ejecución
- Solo puede ver y operar sobre sus propios pipelines y ejecuciones

### Sistema
- Genera las N×M operaciones individuales al lanzar una ejecución
- Guarda el snapshot de la configuración en el momento del lanzamiento
- Calcula y mantiene actualizado el estado agregado de cada `PipelineExecution`
- Ejecuta las operaciones de forma asíncrona en background
- Aplica las reglas de herencia de `sudo` y `debug_level` (kit > global > default)

## Glosario

- **Pipeline**: Definición reutilizable (template) que especifica qué kits ejecutar, en qué servidores y con qué configuración. No tiene estado propio
- **PipelineExecution**: Instancia concreta de una ejecución de un pipeline. Tiene estado propio (`pending`, `in_progress`, `completed`, `failed`, `partial`) y preserva un snapshot de la config usada
- **Snapshot**: Copia inmutable de `targets`, `kits` y `values` capturada en el momento exacto del lanzamiento. Garantiza que el historial refleja la config real usada aunque el pipeline se edite posteriormente
- **Target**: Servidor sobre el que se ejecuta el pipeline. Referenciado por `server_id`
- **Estado agregado**: Estado calculado a partir del resultado de todas las operaciones individuales que genera la ejecución (N kits × M servidores)
- **partial**: Estado de una `PipelineExecution` cuando al menos una operación completó y al menos una falló o fue cancelada
- **Herencia de sudo/debug_level**: El valor por kit tiene prioridad; si no se especifica, hereda el valor global del pipeline; si el global tampoco se declara, el default es `false`/`none`

## Puntos de Duda / Ambigüedades

### 1. Paralelismo entre kits vs secuencial
**Descripción**: El módulo genera N×M operaciones pero no especifica si los kits se ejecutan en paralelo entre sí o de forma secuencial por servidor. Importa especialmente si un kit depende del resultado de otro anterior.

**Impacto**: Arquitectura de ejecución, semántica del estado `partial`, dependencias entre kits.

**Opciones**:
- Todos los kits en paralelo sobre todos los servidores (máximo paralelismo)
- Kits secuenciales por servidor, servidores en paralelo entre sí
- Kits secuenciales globales (uno a uno en todos los servidores antes de pasar al siguiente)

### 2. Cancelación de una PipelineExecution en curso
**Descripción**: No existe endpoint ni RF para cancelar una `PipelineExecution` en `in_progress`. Solo se pueden cancelar las operaciones individuales. No está claro si esto es intencional o una funcionalidad pendiente.

**Impacto**: UX, gestión de ejecuciones largas, flujo de error en pipelines grandes.

### 3. Grupos de servidores como target
**Descripción**: RNF-16 del módulo Servers indica que el servidor `local` no puede añadirse a grupos ni usarse en pipelines. Los grupos de servidores sí están definidos en el módulo Servers, pero no se especifica si `targets[]` del pipeline puede aceptar `group_id` además de `server_id`.

**Impacto**: Modelo de dominio del Pipeline, validaciones en RF-20, experiencia de usuario.

## Estructura del Manifiesto

```yaml
name: "Install Kubernetes Cluster"
description: "Full k8s cluster setup"
sudo: false          # default global — heredado por kits que no especifiquen sudo
debug_level: none    # none (default) | errors | full — heredado por kits que no especifiquen debug_level

targets:
  - server_id: srv_001
  - server_id: srv_002

kits:
  - kit_id: kit_check-ports
    sudo: false       # hereda global
  - kit_id: kit_install-crio
    sudo: true        # override explícito
  - kit_id: kit_install-kubernetes
    sudo: true
  - kit_id: kit_kubeadm-init
    sudo: true

values:
  kit_install-kubernetes:
    version: "1.29"
```

**Regla sudo:** el `sudo` por kit tiene prioridad sobre el global. Si no se especifica en el kit, hereda el global.

## Modelo de Dominio: Pipeline vs PipelineExecution

El módulo introduce **dos entidades separadas**:

**`Pipeline`** — definición reutilizable (template)
- Campos: `id`, `user_id`, `name`, `description`, `targets[]`, `kits[]`, `values{}`, `sudo`, `debug_level`, `created_at`, `updated_at`
- No tiene estado propio — el estado vive en sus ejecuciones

**`PipelineExecution`** — instancia de una ejecución concreta
- Campos: `id`, `pipeline_id`, `user_id`, `status`, `operation_ids[]`, `snapshot{}`, `started_at`, `finished_at`, `created_at`
- `snapshot`: copia de `targets`, `kits` y `values` en el momento del lanzamiento — garantiza que el historial siempre refleja la config usada aunque el pipeline se edite después

## Ciclo de Vida de una PipelineExecution

```
pending → in_progress → completed   (todos los kits completaron)
                      → failed      (todos los kits fallaron)
                      → partial     (algunos completaron, algunos fallaron)
```

El estado agregado se calcula a partir del estado de las N×M operaciones individuales que genera.

## Requisitos Funcionales

### Tabla de endpoints

```
POST   /api/v1/pipelines                                   → crear pipeline (template)
GET    /api/v1/pipelines                                   → listar pipelines del usuario
GET    /api/v1/pipelines/{id}                              → detalle del pipeline
PUT    /api/v1/pipelines/{id}                              → actualizar (solo si sin in_progress)
DELETE /api/v1/pipelines/{id}                              → eliminar (solo si sin in_progress)

POST   /api/v1/pipelines/{id}/executions                   → lanzar pipeline → crea PipelineExecution
GET    /api/v1/pipelines/{id}/executions                   → historial de ejecuciones paginado
GET    /api/v1/pipelines/{id}/executions/{exec_id}         → estado de una ejecución + ops individuales
```

### Requisitos Funcionales

1. **RF-20**: Crear un pipeline con `name`, `description`, `targets[]` (server_ids), `kits[]` (kit_ids con `sudo` y `debug_level` opcionales por kit), `values{}` por kit, `sudo` global y `debug_level` global como defaults. El `debug_level` por kit tiene prioridad sobre el global; si no se especifica en el kit, hereda el global
2. **RF-21**: Lanzar un pipeline via `POST /pipelines/{id}/executions`. El sistema crea una `PipelineExecution` en estado `pending`, guarda un `snapshot` de la config actual (targets, kits, values), genera una operación por cada combinación kit+servidor y las ejecuta de forma asíncrona. Devuelve el `PipelineExecutionResult` con `status: pending`
3. **RF-22**: Listar ejecuciones de un pipeline con paginación via `GET /pipelines/{id}/executions`. Cada entrada muestra: `execution_id`, `launched_at`, `finished_at`, `status` (`completed`/`failed`/`partial`) y resumen de operaciones (total, completadas, falladas)
4. **RF-22b**: Consultar detalle de una ejecución via `GET /pipelines/{id}/executions/{exec_id}`. Devuelve el `status` agregado y la lista de operaciones individuales con `server_id`, `kit_id`, `status` y `error` si aplica
5. **RF-23**: Listar pipelines del usuario autenticado con paginación
6. **RF-24**: Actualizar un pipeline con PUT completo (`name`, `description`, `targets[]`, `kits[]`, `values{}`, `sudo`, `debug_level`). Solo pipelines propios. Solo si no hay ejecuciones `in_progress`
7. **RF-25**: Eliminar un pipeline. Solo si no tiene ejecuciones en curso. Solo pipelines propios
8. **RF-26**: (Eliminado — historial cubierto por RF-22)

## Requisitos No Funcionales

- **RNF-01**: Endpoints de consulta y listado de pipelines responden en < 200ms p99
- **RNF-02**: Ejecuciones de pipeline lanzadas de forma asíncrona via FastAPI BackgroundTasks (InMemory v1). En v2 se migra a ARQ + Valkey mediante el puerto `TaskQueue` sin tocar el dominio
- **RNF-03**: Conexiones SSH gestionadas con asyncssh con connection pooling desde v1. Pool por servidor, conexiones idle máximo 5 minutos. Timeout de conexión: 30 segundos
- **RNF-05**: Uptime 99.5% mensual
- **RNF-06**: El sistema soporta mínimo 50 operaciones SSH concurrentes (un pipeline con N kits × M servidores genera N×M operaciones en paralelo)
- **RNF-07**: Rate limiting por usuario — lanzar pipeline: máx 20/hora. Implementado en middleware FastAPI (InMemory v1, Valkey v2)
- **RNF-08**: Timeouts — step de kit: 10 minutos por defecto (configurable en manifest); pipeline completo: 30 minutos por defecto (sobreescribible al lanzar via `timeout_seconds`). Si se supera, las operaciones afectadas pasan a `cancelled_unsafe` y el pipeline a `partial` o `failed`
- **RNF-09**: Logs estructurados en JSON. Se loguea obligatoriamente: lanzamiento, finalización, fallo y timeout de cada pipeline y de cada operación individual que genera
- **RNF-10**: Cobertura mínima global 80%; dominio y casos de uso 95%; adaptadores 70%. Todo caso de uso con tests de éxito y error
- **RNF-13**: CORS configurado via `ALLOWED_ORIGINS`

## Reglas de Negocio

- **RN-01**: Un usuario solo puede ver, modificar, lanzar y eliminar sus propios pipelines. La validación de ownership se hace en el caso de uso, no en presentación
- **RN-14**: El `sudo` por kit tiene prioridad sobre el `sudo` global del pipeline. Si no se especifica en el kit, hereda el global
- **RN-15**: El `debug_level` por kit tiene prioridad sobre el `debug_level` global del pipeline. Si no se especifica en el kit, hereda el global; si el global tampoco se declara, el default es `none`
- **RN-16**: Un pipeline solo puede actualizarse si no tiene ejecuciones en estado `in_progress`. El intento lanza una excepción de dominio
- **RN-17**: El servidor `local` no puede usarse como target en pipelines. Solo es válido en operaciones individuales. El intento lanza una excepción de dominio
- **RN-20**: El estado agregado de una `PipelineExecution` se calcula así: `completed` si todas las operaciones llegaron a `completed`; `failed` si todas llegaron a estado terminal sin ninguna en `completed`; `partial` si al menos una llegó a `completed` y al menos una a `failed` o `cancelled_unsafe`
- **RN-21**: El `snapshot` de una `PipelineExecution` captura `targets`, `kits` y `values` en el momento exacto del lanzamiento. Si el pipeline se edita después, las ejecuciones históricas siguen mostrando la config que se usó originalmente
- **RN-22**: Un pipeline solo puede eliminarse si no tiene ejecuciones en estado `in_progress` ni `pending`. El intento lanza una excepción de dominio
