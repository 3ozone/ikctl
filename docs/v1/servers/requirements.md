# Requisitos del Módulo Servers

## Credenciales SSH

Las credenciales son objetos independientes reutilizables. Un servidor o kit referencia una credencial por `credential_id`. Múltiples recursos pueden compartir la misma credencial. Actualizar una credencial afecta automáticamente a todos los recursos que la usan.

Campos de una credencial: `name` (alias), `type` (`ssh` | `git_https` | `git_ssh`), `username`, `password` (opcional, cifrado AES-256 en reposo), `private_key` (opcional, cifrada AES-256 en reposo).

Reglas de validación por tipo:
- `ssh`: requiere `username`. Al menos uno de `password` o `private_key`
- `git_https`: requiere `username` (usuario GitHub) y `password` (Personal Access Token). `private_key` ignorado
- `git_ssh`: requiere `private_key`. `username` y `password` ignorados

15. **RF-29**: Crear una credencial con `name`, `type` (`ssh` | `git_https` | `git_ssh`), y los campos requeridos según el tipo. Solo el propietario puede verla y usarla
16. **RF-30**: Listar credenciales del usuario autenticado con paginación. `password` y `private_key` nunca se devuelven en respuestas de API
17. **RF-31**: Obtener detalle de una credencial por `id`. `password` y `private_key` nunca se devuelven
18. **RF-32**: Actualizar una credencial (`name`, `username`, `password`, `private_key`). Solo credenciales propias
19. **RF-33**: Eliminar una credencial. Solo si ningún servidor la está usando activamente. Solo credenciales propias

## Tipos de Servidor

Un servidor puede ser `remote` (default) o `local`:

- **`remote`**: servidor externo accedido via SSH usando `host`, `port` y `credential_id`. Adaptador: `SSHConnectionAdapter`
- **`local`**: la propia máquina donde corre la API. Ejecuta comandos directamente con `asyncio.subprocess`. No requiere `host`, `port` ni `credential_id`. Adaptador: `LocalConnectionAdapter`

Ambos tipos implementan el mismo puerto `Connection` — el manifest del kit no cambia para local vs remoto. El sistema selecciona el adaptador correcto en función del `type` del servidor.

20. **RF-34**: Registrar un servidor local con solo `name` y `description` (opcional). No requiere credenciales. Solo puede existir un servidor `local` por usuario

## Requisitos Funcionales

1. **RF-01**: Registrar un servidor remoto con `name`, `host`, `port` (default 22), `credential_id`, `description` (opcional) y `type: remote` (default)
2. **RF-02**: Listar servidores del usuario autenticado con paginación
3. **RF-03**: Obtener detalle de un servidor por `id`. Las credenciales nunca se devuelven en la respuesta; solo se expone `credential_id`
4. **RF-04**: Actualizar un servidor remoto (`name`, `host`, `port`, `credential_id`, `description`). Un servidor `local` solo permite actualizar `name` y `description`. Solo servidores propios
5. **RF-05**: Eliminar un servidor (borrado físico). Solo si no tiene operaciones en curso. Solo servidores propios
6. **RF-06**: Habilitar / deshabilitar un servidor. Estado `active` | `inactive`. Un servidor inactivo no puede usarse en nuevas operaciones pero conserva su historial
7. **RF-07**: Verificar conectividad de un servidor (health check). Intenta conexión SSH y devuelve `online` | `offline` y latencia en ms
8. **RF-08**: Autodetección del SO al realizar un health check exitoso. Almacena `os_id`, `os_version` y `os_name` leyendo `/etc/os-release`
9. **RF-08.1**: Ejecutar un comando ad-hoc en un servidor. El usuario envía un comando y recibe `stdout`, `stderr` y código de salida

## Grupos de Servidores

10. **RF-27**: Crear un grupo de servidores con `name`, `description` (opcional) y `server_ids[]`. Los grupos pueden usarse como target en pipelines, ejecutando el pipeline en todos los servidores del grupo
11. **RF-28.1**: Listar grupos del usuario autenticado con paginación
12. **RF-28.2**: Obtener detalle de un grupo por `id`
13. **RF-28.3**: Actualizar un grupo (`name`, `description`, `server_ids[]`). Incluye añadir y quitar servidores del grupo. Solo grupos propios
14. **RF-28.4**: Eliminar un grupo. Solo si no tiene pipelines en curso que lo referencien. Solo grupos propios

## Requisitos No Funcionales

- **RNF-01**: Endpoints CRUD de servidores, grupos y credenciales responden en < 200ms p99
- **RNF-03**: Conexiones SSH gestionadas con asyncssh con connection pooling desde v1. Pool por servidor, conexiones idle máximo 5 minutos. Timeout de conexión: 30 segundos
- **RNF-04**: Los campos `password` y `private_key` de `Credential` se cifran con AES-256 en reposo antes de persistir en MariaDB. La clave de cifrado se carga desde variable de entorno `ENCRYPTION_KEY` al arranque. Ambos campos son write-only: nunca se devuelven en ninguna respuesta de API
- **RNF-05**: Uptime 99.5% mensual. `GET /healthz` (liveness) y `GET /readyz` (readiness, comprueba DB y MinIO)
- **RNF-07**: Rate limiting por usuario — health check: máx 10/min; comando ad-hoc: máx 30/hora. Implementado en middleware FastAPI (InMemory v1, Valkey v2)
- **RNF-08**: Timeouts — conexión SSH: 30s; comando ad-hoc: 5 minutos. Si se supera, la operación pasa a `cancelled_unsafe` y se registra en logs
- **RNF-09**: Logs estructurados en JSON con `timestamp`, `level`, `request_id`, `user_id`, `operation_type`, `server_id`, `duration_ms`, `error`. Las credenciales nunca aparecen en logs
- **RNF-10**: Cobertura mínima global 80%; dominio y casos de uso 95%; adaptadores 70%. Todo caso de uso con tests de éxito y error
- **RNF-11**: `GET /servers/{id}/health` responde en < 2s si el servidor está online, < 35s en el peor caso (timeout SSH 30s + 5s overhead)
- **RNF-13**: CORS configurado via `ALLOWED_ORIGINS`. En producción rechaza todas las peticiones cross-origin si no está configurado
- **RNF-16**: El servidor `local` ejecuta comandos en la máquina donde corre la API. Solo usuarios con rol `admin` pueden registrarlo y usarlo. Los comandos se ejecutan con el usuario del proceso de la API — nunca se eleva a `root`. El flag `sudo: true` se ignora en servidor `local` y se registra un warning en logs. El servidor `local` no puede añadirse a grupos de servidores ni usarse como target en pipelines

## Features Futuras (v2)

- **FF-01**: Soporte a servidores Windows via WinRM/PowerShell
- **FF-02**: Shell interactiva en tiempo real (WebSockets + pty)

## Reglas de Negocio

- **RN-01**: Un usuario solo puede ver, modificar y eliminar sus propios recursos (servidores, credenciales, grupos). La validación de ownership se hace en el caso de uso, no en presentación
- **RN-06**: Una credencial no puede eliminarse si algún servidor la referencia activamente. El intento lanza una excepción de dominio
- **RN-07**: Solo puede existir un servidor `local` por usuario. Intentar registrar un segundo servidor `local` lanza una excepción de dominio
- **RN-08**: Un servidor no puede eliminarse si tiene operaciones en estado `in_progress`. Solo puede eliminarse cuando no haya operaciones activas
- **RN-18**: Las credenciales se validan según su `type`: `ssh` requiere `username` y al menos `password` o `private_key`; `git_https` requiere `username` y `password` (PAT); `git_ssh` requiere `private_key`. Campos no requeridos por el tipo se ignoran. Incumplir estas reglas lanza una excepción de dominio
- **RN-19**: Un grupo no puede eliminarse si tiene pipelines en estado `in_progress` que lo referencien. El intento lanza una excepción de dominio
