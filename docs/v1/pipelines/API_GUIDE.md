# API Guide — Módulo Pipelines

## Autenticación

Todos los endpoints requieren un JWT válido en la cabecera `Authorization: Bearer <token>`.

## Endpoints

### POST /api/v1/pipelines — Crear un pipeline

```bash
curl -X POST http://localhost:8089/api/v1/pipelines \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Deploy API to Production",
    "description": "Full deployment pipeline",
    "targets": [
      {"server_id": "550e8400-e29b-41d4-a716-446655440000"},
      {"server_id": "550e8400-e29b-41d4-a716-446655440001"}
    ],
    "kits": [
      {"kit_id": "550e8400-e29b-41d4-a716-446655440010", "sudo": true, "debug_level": "errors"},
      {"kit_id": "550e8400-e29b-41d4-a716-446655440011"}
    ],
    "values": {"env": "production", "port": 8080},
    "sudo": false,
    "debug_level": "none"
  }'
```

**Response 201:**
```json
{
  "pipeline_id": "660e8400-...",
  "user_id": "...",
  "name": "Deploy API to Production",
  "description": "Full deployment pipeline",
  "targets": [{"server_id": "550e8400-..."}],
  "kits": [{"kit_id": "550e8400-...", "sudo": true, "debug_level": "errors"}],
  "values": {"env": "production", "port": 8080},
  "sudo": false,
  "debug_level": "none",
  "created_at": "2026-06-03T12:00:00Z",
  "updated_at": "2026-06-03T12:00:00Z"
}
```

**Errores:**
- `422` — Servidor local en targets (`LocalServerInPipelineError`)

---

### GET /api/v1/pipelines — Listar pipelines

```bash
curl http://localhost:8089/api/v1/pipelines?page=1&per_page=10 \
  -H "Authorization: Bearer <token>"
```

**Response 200:**
```json
{
  "items": [...],
  "total": 15,
  "page": 1,
  "per_page": 10
}
```

---

### GET /api/v1/pipelines/{id} — Detalle de pipeline

```bash
curl http://localhost:8089/api/v1/pipelines/660e8400-... \
  -H "Authorization: Bearer <token>"
```

**Response 200:** Mismo formato que la creación.

**Errores:**
- `404` — Pipeline no encontrado o no pertenece al usuario

---

### PUT /api/v1/pipelines/{id} — Actualizar pipeline

```bash
curl -X PUT http://localhost:8089/api/v1/pipelines/660e8400-... \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Deploy API v2",
    "targets": [{"server_id": "550e8400-e29b-41d4-a716-446655440003"}],
    "sudo": true
  }'
```

**Response 200:** Pipeline actualizado.

**Errores:**
- `404` — Pipeline no encontrado
- `409` — Pipeline tiene ejecuciones activas (`PipelineInProgressError`)
- `422` — Servidor local en targets

---

### DELETE /api/v1/pipelines/{id} — Eliminar pipeline

```bash
curl -X DELETE http://localhost:8089/api/v1/pipelines/660e8400-... \
  -H "Authorization: Bearer <token>"
```

**Response 204** (sin contenido).

**Errores:**
- `404` — Pipeline no encontrado
- `409` — Pipeline tiene ejecuciones activas

---

### POST /api/v1/pipelines/{id}/executions — Lanzar pipeline

Crea una `PipelineExecution` en estado `pending`, captura un snapshot inmutable de la configuración y encola la ejecución asíncrona.

```bash
curl -X POST http://localhost:8089/api/v1/pipelines/660e8400-.../executions \
  -H "Authorization: Bearer <token>"
```

**Response 201:**
```json
{
  "execution_id": "770e8400-...",
  "pipeline_id": "660e8400-...",
  "user_id": "...",
  "status": "pending",
  "snapshot": {
    "targets": [{"server_id": "550e8400-..."}],
    "kits": [{"kit_id": "550e8400-...", "sudo": true, "debug_level": "errors"}],
    "values": {"env": "production"},
    "sudo": false,
    "debug_level": "none"
  },
  "created_at": "2026-06-03T12:05:00Z"
}
```

**Errores:**
- `404` — Pipeline no encontrado
- `422` — Algún kit no es usable (`PipelineNotLaunchableError`)

---

### GET /api/v1/pipelines/{id}/executions — Historial de ejecuciones

```bash
curl "http://localhost:8089/api/v1/pipelines/660e8400-.../executions?page=1&per_page=10" \
  -H "Authorization: Bearer <token>"
```

**Response 200:**
```json
{
  "items": [
    {
      "execution_id": "770e8400-...",
      "pipeline_id": "660e8400-...",
      "status": "completed",
      "total_operations": 4,
      "completed_operations": 4,
      "failed_operations": 0,
      "created_at": "2026-06-03T12:05:00Z",
      "started_at": "2026-06-03T12:05:01Z",
      "finished_at": "2026-06-03T12:10:00Z"
    }
  ],
  "total": 1,
  "page": 1,
  "per_page": 10
}
```

---

### GET /api/v1/pipelines/{id}/executions/{exec_id} — Detalle de ejecución

Devuelve el snapshot de la configuración y la lista de operaciones individuales con su estado.

```bash
curl http://localhost:8089/api/v1/pipelines/660e8400-.../executions/770e8400-... \
  -H "Authorization: Bearer <token>"
```

**Response 200:**
```json
{
  "execution_id": "770e8400-...",
  "pipeline_id": "660e8400-...",
  "user_id": "...",
  "status": "completed",
  "snapshot": {
    "targets": [{"server_id": "550e8400-..."}],
    "kits": [{"kit_id": "550e8400-...", "sudo": true, "debug_level": "errors"}],
    "values": {"env": "production"},
    "sudo": false,
    "debug_level": "none"
  },
  "operations": [
    {
      "operation_id": "880e8400-...",
      "server_id": "550e8400-e29b-41d4-a716-446655440000",
      "kit_id": "550e8400-...",
      "status": "completed",
      "output": "...",
      "error": null
    },
    {
      "operation_id": "880e8401-...",
      "server_id": "550e8400-e29b-41d4-a716-446655440001",
      "kit_id": "550e8400-...",
      "status": "completed",
      "output": "...",
      "error": null
    }
  ],
  "created_at": "2026-06-03T12:05:00Z",
  "started_at": "2026-06-03T12:05:01Z",
  "finished_at": "2026-06-03T12:10:00Z"
}
```

**Errores:**
- `404` — Pipeline o ejecución no encontrados

---

## Estados de PipelineExecution

| Estado | Descripción |
|--------|-------------|
| `pending` | Creada, esperando ejecución |
| `in_progress` | Operaciones ejecutándose |
| `completed` | Todas las operaciones completaron exitosamente |
| `failed` | Todas las operaciones fallaron |
| `partial` | Mezcla de operaciones completadas y fallidas |

## Herencia de sudo/debug_level

- `sudo` y `debug_level` por kit tienen prioridad sobre el global del pipeline
- Si no se especifican en el kit, heredan el valor global
- Default global: `sudo=false`, `debug_level="none"`

```json
{
  "kits": [
    {"kit_id": "kit-1", "sudo": true, "debug_level": "full"},
    {"kit_id": "kit-2"},
    {"kit_id": "kit-3", "sudo": false}
  ],
  "sudo": true,
  "debug_level": "errors"
}
```

Resultado efectivo:
- `kit-1`: sudo=true, debug_level=full (override)
- `kit-2`: sudo=true, debug_level=errors (hereda global)
- `kit-3`: sudo=false, debug_level=errors (override sudo, hereda debug_level)