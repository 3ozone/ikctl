# API Guide — Módulo Operations

Guía de uso de los endpoints del módulo `operations` con ejemplos `curl`.

Base URL: `http://localhost:8000`

Todos los endpoints requieren autenticación JWT via header `Authorization: Bearer <token>`.

---

## POST /api/v1/operations — Lanzar operación

Crea una operación asíncrona para ejecutar un kit en un servidor. La operación se crea con estado `pending` y se ejecuta en background.

**Request:**
```bash
curl -X POST http://localhost:8000/api/v1/operations \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "server_id": "550e8400-e29b-41d4-a716-446655440000",
    "kit_id": "660e8400-e29b-41d4-a716-446655440001",
    "debug_level": "none",
    "values": {"port": 8080, "worker_processes": 4},
    "sudo": false
  }'
```

**Campos:**

| Campo | Tipo | Requerido | Descripción |
|-------|------|-----------|-------------|
| `server_id` | string | sí | ID del servidor destino (debe estar activo) |
| `kit_id` | string | sí | ID del kit a ejecutar (debe estar sincronizado y usable) |
| `debug_level` | string \| null | no | `none`, `errors` o `full`. Si `null`, hereda del kit; si el kit también es `null`, default `none` |
| `values` | object \| null | no | Valores de configuración del usuario que sobreescriben los defaults del kit |
| `sudo` | boolean | no | Si `true`, ejecuta los scripts del pipeline con `sudo` (default `false`) |

**Respuesta 201:**
```json
{
  "operation_id": "770e8400-e29b-41d4-a716-446655440002",
  "user_id": "user-123",
  "server_id": "550e8400-e29b-41d4-a716-446655440000",
  "kit_id": "660e8400-e29b-41d4-a716-446655440001",
  "values": {"port": 8080, "worker_processes": 4},
  "sudo": false,
  "status": "pending",
  "debug_level": "none",
  "output": "",
  "backup_files": [],
  "created_at": "2026-01-01T12:00:00Z",
  "updated_at": "2026-01-01T12:00:00Z",
  "started_at": null,
  "finished_at": null
}
```

**Errores:**
- `422` — servidor inactivo o kit no usable (eliminado o con error de sync)

---

## GET /api/v1/operations — Listar operaciones

Lista las operaciones del usuario con paginación y filtros opcionales. El `output` se filtra según el `debug_level` de cada operación.

**Request básico:**
```bash
curl http://localhost:8000/api/v1/operations \
  -H "Authorization: Bearer $TOKEN"
```

**Con paginación:**
```bash
curl "http://localhost:8000/api/v1/operations?page=2&per_page=10" \
  -H "Authorization: Bearer $TOKEN"
```

**Con filtros:**
```bash
# Filtrar por servidor
curl "http://localhost:8000/api/v1/operations?server_id=550e8400-..." \
  -H "Authorization: Bearer $TOKEN"

# Filtrar por kit
curl "http://localhost:8000/api/v1/operations?kit_id=660e8400-..." \
  -H "Authorization: Bearer $TOKEN"

# Filtrar por estado
curl "http://localhost:8000/api/v1/operations?status=pending" \
  -H "Authorization: Bearer $TOKEN"

# Combinado
curl "http://localhost:8000/api/v1/operations?server_id=550e8400-...&status=completed&page=1&per_page=20" \
  -H "Authorization: Bearer $TOKEN"
```

**Parámetros query:**

| Parámetro | Tipo | Default | Descripción |
|-----------|------|---------|-------------|
| `page` | int | 1 | Página (1-based) |
| `per_page` | int | 50 | Items por página (máx 50) |
| `server_id` | string \| null | null | Filtrar por servidor |
| `kit_id` | string \| null | null | Filtrar por kit |
| `status` | string \| null | null | Filtrar por estado (`pending`, `in_progress`, `completed`, `failed`, `cancelled`, `cancelled_unsafe`) |

**Filtrado de output por debug_level:**

| debug_level | output devuelto |
|-------------|----------------|
| `none` | vacío (`""`) |
| `errors` | solo stderr |
| `full` | stdout + stderr completo |

**Respuesta 200:**
```json
{
  "items": [
    {
      "operation_id": "770e8400-...",
      "user_id": "user-123",
      "server_id": "550e8400-...",
      "kit_id": "660e8400-...",
      "values": {},
      "sudo": false,
      "status": "completed",
      "debug_level": "none",
      "output": "",
      "backup_files": ["/etc/nginx/nginx.conf"],
      "created_at": "2026-01-01T12:00:00Z",
      "updated_at": "2026-01-01T12:05:00Z",
      "started_at": "2026-01-01T12:00:01Z",
      "finished_at": "2026-01-01T12:05:00Z"
    }
  ],
  "total": 1,
  "page": 1,
  "per_page": 50
}
```

---

## GET /api/v1/operations/{id} — Consultar operación

Obtiene el detalle de una operación. El `output` se filtra según el `debug_level` de la operación.

```bash
curl http://localhost:8000/api/v1/operations/770e8400-e29b-41d4-a716-446655440002 \
  -H "Authorization: Bearer $TOKEN"
```

**Respuesta 200:**
```json
{
  "operation_id": "770e8400-e29b-41d4-a716-446655440002",
  "user_id": "user-123",
  "server_id": "550e8400-e29b-41d4-a716-446655440000",
  "kit_id": "660e8400-e29b-41d4-a716-446655440001",
  "values": {"port": 8080},
  "sudo": true,
  "status": "failed",
  "debug_level": "errors",
  "output": "stderr: Error restarting nginx service",
  "backup_files": ["/etc/nginx/nginx.conf"],
  "created_at": "2026-01-01T12:00:00Z",
  "updated_at": "2026-01-01T12:05:00Z",
  "started_at": "2026-01-01T12:00:01Z",
  "finished_at": "2026-01-01T12:05:00Z"
}
```

**Errores:**
- `404` — operación no encontrada o no pertenece al usuario

---

## POST /api/v1/operations/{id}/cancel — Cancelar operación

Cancela una operación. El comportamiento depende del estado actual:

| Estado actual | Nuevo estado | Descripción |
|---------------|-------------|-------------|
| `pending` | `cancelled` | Cancelación limpia — no se ejecutó en el servidor |
| `in_progress` | `cancelled_unsafe` | Cancelación insegura — el servidor puede quedar en estado parcial |

```bash
curl -X POST http://localhost:8000/api/v1/operations/770e8400-.../cancel \
  -H "Authorization: Bearer $TOKEN"
```

**Respuesta 200 (pending → cancelled):**
```json
{
  "operation_id": "770e8400-...",
  "user_id": "user-123",
  "server_id": "550e8400-...",
  "kit_id": "660e8400-...",
  "values": {},
  "sudo": false,
  "status": "cancelled",
  "debug_level": "none",
  "output": "",
  "backup_files": [],
  "created_at": "2026-01-01T12:00:00Z",
  "updated_at": "2026-01-01T12:01:00Z",
  "started_at": null,
  "finished_at": null
}
```

**Errores:**
- `404` — operación no encontrada o no pertenece al usuario
- `409` — la operación está en estado terminal (`completed`, `failed`, `cancelled`, `cancelled_unsafe`) y no puede cancelarse

---

## POST /api/v1/operations/{id}/restore — Restaurar backup

Restaura los ficheros de backup (`.bak.ikctl`) de una operación fallida o cancelada inseguramente. Solo disponible si la operación tiene `backup_files` y está en estado `failed` o `cancelled_unsafe`.

```bash
curl -X POST http://localhost:8000/api/v1/operations/770e8400-.../restore \
  -H "Authorization: Bearer $TOKEN"
```

**Respuesta 200:**
```json
{
  "operation_id": "770e8400-e29b-41d4-a716-446655440002",
  "restored_files": ["/etc/nginx/nginx.conf"]
}
```

**Errores:**
- `404` — operación no encontrada o no pertenece al usuario
- `422` — la operación no tiene backup o no está en estado restorable (`failed` o `cancelled_unsafe`)

---

## POST /api/v1/operations/{id}/retry — Reintentar operación

Reintenta una operación fallida o cancelada inseguramente. Crea una **nueva** operación con estado `pending`. La operación original permanece intacta.

```bash
curl -X POST http://localhost:8000/api/v1/operations/770e8400-.../retry \
  -H "Authorization: Bearer $TOKEN"
```

**Respuesta 201:**
```json
{
  "operation_id": "880e8400-e29b-41d4-a716-446655440003",
  "user_id": "user-123",
  "server_id": "550e8400-e29b-41d4-a716-446655440000",
  "kit_id": "660e8400-e29b-41d4-a716-446655440001",
  "values": {"port": 8080},
  "sudo": false,
  "status": "pending",
  "debug_level": "errors",
  "output": "",
  "backup_files": [],
  "created_at": "2026-01-01T13:00:00Z",
  "updated_at": "2026-01-01T13:00:00Z",
  "started_at": null,
  "finished_at": null
}
```

**Errores:**
- `404` — operación no encontrada o no pertenece al usuario
- `422` — la operación no puede reintentarse (solo permite `failed` o `cancelled_unsafe`)

---

## Flujo típico

```bash
# 1. Lanzar una operación
OPERATION_ID=$(curl -s -X POST http://localhost:8000/api/v1/operations \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "server_id": "550e8400-e29b-41d4-a716-446655440000",
    "kit_id": "660e8400-e29b-41d4-a716-446655440001",
    "debug_level": "errors",
    "values": {"port": 8080},
    "sudo": true
  }' | jq -r '.operation_id')

# 2. Consultar estado
curl "http://localhost:8000/api/v1/operations/$OPERATION_ID" \
  -H "Authorization: Bearer $TOKEN"

# 3. Si falló, ver detalles (debug_level=errors muestra solo stderr)
curl "http://localhost:8000/api/v1/operations/$OPERATION_ID" \
  -H "Authorization: Bearer $TOKEN" | jq '.output'

# 4. Si tiene backup, restaurar
curl -X POST "http://localhost:8000/api/v1/operations/$OPERATION_ID/restore" \
  -H "Authorization: Bearer $TOKEN"

# 5. O reintentar (crea una nueva operación)
NEW_OP_ID=$(curl -s -X POST "http://localhost:8000/api/v1/operations/$OPERATION_ID/retry" \
  -H "Authorization: Bearer $TOKEN" | jq -r '.operation_id')

# 6. Cancelar si ya no se necesita
curl -X POST "http://localhost:8000/api/v1/operations/$NEW_OP_ID/cancel" \
  -H "Authorization: Bearer $TOKEN"

# 7. Listar todas las operaciones completadas del servidor
curl "http://localhost:8000/api/v1/operations?server_id=550e8400-...&status=completed" \
  -H "Authorization: Bearer $TOKEN"
```

---

## Máquina de estados

```
                    ┌──────────┐
         launch     │ pending  │
        ──────────►  └────┬─────┘
                          │ start execution
                          ▼
                    ┌────────────┐
                    │ in_progress│
                    └──┬─────┬───┘
           cancel     │     │  complete/fail
        (unsafe)     │     │
          ┌─────────┘     └──────────┐
          ▼                         ▼
  ┌────────────────┐       ┌────────────┐
  │cancelled_unsafe │       │  completed │
  └───────┬────────┘       └────────────┘
          │ retry
          ▼
     ┌──────────┐
     │ pending  │  (nueva operación)
     └──────────┘

  ┌───────────┐          ┌────────────┐
  │ cancelled  │◄─── cancel (from pending)
  └─────┬─────┘          └────────────┘
        │
        │ retry (solo desde failed / cancelled_unsafe)
        ▼
   ┌──────────┐
   │ pending  │  (nueva operación)
   └──────────┘

  ┌────────┐
  │ failed │──── retry ───► pending (nueva operación)
  └───┬────┘
      │
      │ restore (solo si tiene backup_files)
      ▼
  restaura .bak.ikctl en servidor remoto
```

**Transiciones válidas:**

| Desde | Hacia | Acción |
|-------|-------|--------|
| `pending` | `in_progress` | Ejecución automática (task queue) |
| `pending` | `cancelled` | `POST /{id}/cancel` |
| `in_progress` | `cancelled_unsafe` | `POST /{id}/cancel` |
| `in_progress` | `completed` | Ejecución exitosa |
| `in_progress` | `failed` | Ejecución con error |
| `failed` | `pending` (nueva) | `POST /{id}/retry` |
| `cancelled_unsafe` | `pending` (nueva) | `POST /{id}/retry` |

---

## Códigos de respuesta

| Código | Descripción |
|--------|-------------|
| 200 | OK — consulta, cancelación o restauración exitosa |
| 201 | Created — operación lanzada o retry creado |
| 404 | Not Found — operación no encontrada o no pertenece al usuario |
| 409 | Conflict — transición de estado no válida (cancelar operación terminal) |
| 422 | Unprocessable — servidor inactivo, kit no usable, operación no restorable/retriable |

---

## Filtrado de output por debug_level

El campo `output` de las respuestas se filtra automáticamente según el `debug_level` de la operación:

| debug_level | Contenido de `output` |
|-------------|----------------------|
| `none` | `""` (vacío — sin información de debug) |
| `errors` | Solo líneas de stderr |
| `full` | stdout + stderr completo |

La herencia de `debug_level` sigue esta cadena:
1. Valor explícito en la request (si se proporciona)
2. Valor del kit (`kit.debug_level`)
3. Valor por defecto: `"none"`