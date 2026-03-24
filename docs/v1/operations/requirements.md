# Requisitos del Módulo Operations

## Ciclo de Vida de una Operación

```
pending → in_progress → completed
                      → failed
                      → cancelled        (cancelado desde pending — limpio)
                      → cancelled_unsafe (cancelado desde in_progress — servidor en estado desconocido)
```

## Requisitos Funcionales

1. **RF-14**: Lanzar una operación especificando `server_id`, `kit_id`, `values{}` (sobreescriben defaults del kit), `sudo` (booleano) y `debug_level` opcional (`none` | `errors` | `full`). Si no se especifica, hereda el `debug_level` del manifiesto del kit; si el kit tampoco lo declara, el default es `none`. Se crea con estado `pending` y se ejecuta de forma asíncrona
2. **RF-15**: Consultar estado de una operación por `id`. Devuelve `status`, `started_at`, `finished_at` y `error`. El campo `output` (stdout/stderr) solo se devuelve si `debug_level` es `errors` o `full`. Con `errors` devuelve únicamente stderr; con `full` devuelve stdout + stderr. El output se acumula en DB conforme llegan líneas — el usuario puede hacer polling para ver la salida parcial mientras la operación está `in_progress`
3. **RF-16**: Listar operaciones del usuario autenticado con paginación y filtrado por `server_id`, `kit_id` y `status`
4. **RF-17**: Cancelar una operación:
   - `pending` → cancela limpiamente → estado `cancelled`
   - `in_progress` → corta la conexión SSH → estado `cancelled_unsafe` (el servidor puede quedar en estado parcial)
5. **RF-18**: Restaurar backup pre-operación. Disponible para operaciones en estado `failed` o `cancelled_unsafe` que tuvieran `backup[]` declarado en el kit. El sistema ejecuta `cp {path}.bak.ikctl {path}` para cada fichero declarado en `backup[]`, restaurando el estado previo directamente en el servidor remoto
6. **RF-19**: Reintentar una operación fallida. Crea una nueva operación con los mismos parámetros (`server_id`, `kit_id`, `values`, `sudo`), conservando la operación original en el historial. Disponible para operaciones en estado `failed` o `cancelled_unsafe`

## Flujo de Ejecución de una Operación

Cuando una operación pasa a `in_progress`, el sistema ejecuta estos pasos en orden:

1. **Snapshot** — si el kit declara `backup[]`, genera una copia in-place de cada fichero en su path original con sufijo `.bak.ikctl` (ej: `/etc/nginx/nginx.conf` → `/etc/nginx/nginx.conf.bak.ikctl`). La copia se hace en el servidor remoto antes de cualquier cambio. No requiere almacenamiento externo
2. **Descarga de MinIO** — descarga los archivos del kit a memoria
3. **Renderizado Jinja2** — renderiza los templates `.j2` con los `values` combinados (defaults del kit + los del usuario)
4. **Transferencia con caché** — compara el hash SHA-256 de cada archivo renderizado con el hash registrado en `server_kit_file_cache` para ese servidor. Solo se transfieren via SFTP los archivos cuyo hash haya cambiado o no existan en `/tmp/ikctl/kits/{kit_id}/` del servidor. Actualiza los hashes en DB
5. **Ejecución en orden** — ejecuta los scripts de `files.pipeline[]` uno a uno desde `/tmp/ikctl/kits/{kit_id}/`. Si `sudo: true`, ejecuta con `sudo bash script.sh`. Captura output según `debug_level`
6. **Limpieza** — elimina el directorio temporal `/tmp/ikctl/kits/{kit_id}/` del servidor al finalizar (éxito o fallo)

**Reglas del caché de archivos:**
- El caché se almacena en MariaDB: `server_id`, `kit_id`, `filename`, `content_hash` (SHA-256), `uploaded_at`
- El hash se calcula sobre el contenido renderizado (post-Jinja2), no sobre el template original
- Templates `.j2` con `values` distintos generan hashes distintos y se re-transfieren
- El caché es por servidor — el mismo kit en dos servidores distintos mantiene entradas independientes

## Comportamiento del Snapshot (backup)

- Si el kit declara `backup[]`, antes de ejecutar la operación el sistema hace una copia in-place de cada fichero declarado en su path original con el sufijo `.bak.ikctl`
- Ejemplo: `backup: [/etc/nginx/nginx.conf]` → crea `/etc/nginx/nginx.conf.bak.ikctl` en el servidor remoto
- El backup se hace via el mismo adaptador de conexión (`SSHConnectionAdapter` o `LocalConnectionAdapter`) usando `cp {path} {path}.bak.ikctl`
- El fichero `.bak.ikctl` se **conserva tras la operación** (éxito o fallo) para permitir restauración manual directamente desde el servidor
- RF-18 (restore) sobreescribe el fichero original con el `.bak.ikctl`: `cp {path}.bak.ikctl {path}`
- Si no hay `backup[]`, las operaciones `failed` / `cancelled_unsafe` no son restaurables via RF-18
- El fichero `.bak.ikctl` no se limpia automáticamente — el usuario puede eliminarlo manualmente o se sobreescribe en la siguiente operación con backup en el mismo fichero

## Requisitos No Funcionales

- **RNF-01**: Endpoints de consulta y listado de operaciones responden en < 200ms p99
- **RNF-02**: Operaciones ejecutadas de forma asíncrona via FastAPI BackgroundTasks (InMemory v1). En v2 se migra a ARQ + Valkey mediante el puerto `TaskQueue` sin tocar el dominio
- **RNF-03**: Conexiones SSH gestionadas con asyncssh con connection pooling desde v1. Pool por servidor, conexiones idle máximo 5 minutos. Timeout de conexión: 30 segundos
- **RNF-05**: Uptime 99.5% mensual. `GET /healthz` y `GET /readyz` para liveness y readiness
- **RNF-06**: El sistema soporta mínimo 50 operaciones SSH concurrentes en v1. Cada operación corre en su propio task sin bloquear otras
- **RNF-07**: Rate limiting por usuario — lanzar operación: máx 20/hora. Implementado en middleware FastAPI (InMemory v1, Valkey v2)
- **RNF-08**: Timeouts — step de operación: 10 minutos por defecto (configurable en manifest); operación completa: 30 minutos por defecto (sobreescribible al lanzar via `timeout_seconds`). Si se supera, la operación pasa a `cancelled_unsafe`
- **RNF-09**: Logs estructurados en JSON. Se loguea obligatoriamente: lanzamiento, finalización, fallo, timeout y `cancelled_unsafe` de cada operación, con `server_id`, `kit_id`, `user_id` y `duration_ms`
- **RNF-10**: Cobertura mínima global 80%; dominio y casos de uso 95%; adaptadores 70%. Todo caso de uso con tests de éxito y error
- **RNF-13**: CORS configurado via `ALLOWED_ORIGINS`
- **RNF-15**: Antes de ejecutar cada operación el sistema verifica que los archivos del caché existen físicamente en `/tmp/ikctl/kits/{kit_id}/` del servidor. Si el directorio no existe o faltan archivos, las entradas de `server_kit_file_cache` para ese servidor se invalidan automáticamente y todos los archivos se re-transfieren. El sistema es auto-reparable sin intervención del usuario

## Features Futuras (v2)

- **FF-05**: Retries automáticos con backoff exponencial configurables por operación
- **FF-06**: Streaming de output en tiempo real via Server-Sent Events (SSE) cuando `debug_level: full`

## Reglas de Negocio

- **RN-01**: Un usuario solo puede ver, cancelar y reintentar sus propias operaciones. La validación de ownership se hace en el caso de uso, no en presentación
- **RN-02**: Transiciones de estado válidas de una operación: `pending` → `in_progress`; `pending` → `cancelled`; `in_progress` → `completed`; `in_progress` → `failed`; `in_progress` → `cancelled_unsafe`. Cualquier otra transición lanza una excepción de dominio. Los estados `completed`, `failed`, `cancelled` y `cancelled_unsafe` son terminales — no pueden cambiar de estado
- **RN-04**: Un servidor con estado `inactive` no puede usarse como target en nuevas operaciones. El intento lanza una excepción de dominio
- **RN-05**: El snapshot pre-operación solo se genera si el kit tiene `backup[]` declarado en su manifest. Sin `backup[]` no hay snapshot
- **RN-11**: Restaurar backup está disponible para operaciones en estado `failed` o `cancelled_unsafe` que tuvieran `backup[]` declarado en el kit. El sistema verifica que los ficheros `.bak.ikctl` existen en el servidor antes de intentar la restauración. Si no existen, lanza una excepción de dominio
- **RN-12**: Reintentar una operación solo está disponible para operaciones en estado `failed` o `cancelled_unsafe`. El reintento crea una nueva operación con los mismos parámetros conservando la original en el historial
- **RN-13**: Herencia de `debug_level`: el valor al lanzar la operación tiene prioridad; si no se especifica, hereda del manifest del kit; si el kit tampoco lo declara, el default es `none`
