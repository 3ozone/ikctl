# API Guide — Módulo Kits

Guía de uso de los endpoints del módulo `kits` con ejemplos `curl`.

Base URL: `http://localhost:8000`

Todos los endpoints requieren autenticación JWT via header `Authorization: Bearer <token>`.

---

## Repositorios

### POST /api/v1/repositories — Registrar repositorio

Registra un repositorio Git como fuente de kits. No realiza ninguna llamada a Git.
El repositorio se crea con `sync_status: never_synced`.

**Repositorio público:**
```bash
curl -X POST http://localhost:8000/api/v1/repositories \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://github.com/org/my-kits-repo",
    "ref": "main"
  }'
```

**Repositorio privado con credencial HTTPS (PAT):**
```bash
curl -X POST http://localhost:8000/api/v1/repositories \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://github.com/org/private-kits-repo",
    "ref": "main",
    "credential_id": "cred-uuid-here"
  }'
```

**Respuesta 201:**
```json
{
  "repository_id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "user-123",
  "url": "https://github.com/org/my-kits-repo",
  "ref": "main",
  "credential_id": null,
  "sync_status": "never_synced",
  "last_synced_at": null,
  "last_commit_sha": null,
  "sync_error_message": null,
  "created_at": "2026-01-01T12:00:00Z",
  "updated_at": "2026-01-01T12:00:00Z"
}
```

**Errores:**
- `422` — credencial no es de tipo `git_https` o `git_ssh`

---

### GET /api/v1/repositories — Listar repositorios

Lista los repositorios del usuario con paginación. Solo devuelve repositorios no eliminados.

```bash
curl http://localhost:8000/api/v1/repositories \
  -H "Authorization: Bearer $TOKEN"

# Con paginación
curl "http://localhost:8000/api/v1/repositories?page=2&per_page=10" \
  -H "Authorization: Bearer $TOKEN"
```

**Respuesta 200:**
```json
{
  "items": [
    {
      "repository_id": "550e8400-...",
      "url": "https://github.com/org/my-kits-repo",
      "ref": "main",
      "sync_status": "synced",
      "last_synced_at": "2026-01-01T12:30:00Z",
      "last_commit_sha": "a1b2c3d4e5f6",
      ...
    }
  ],
  "total": 1,
  "page": 1,
  "per_page": 50
}
```

---

### GET /api/v1/repositories/{id} — Obtener repositorio

Obtiene el detalle de un repositorio por su ID.

```bash
curl http://localhost:8000/api/v1/repositories/550e8400-e29b-41d4-a716-446655440000 \
  -H "Authorization: Bearer $TOKEN"
```

**Errores:**
- `404` — repositorio no encontrado o no pertenece al usuario

---

### PUT /api/v1/repositories/{id} — Actualizar repositorio

Actualiza `url`, `ref` y/o `credential_id`. Si se cambia `url` o `ref`, el
`sync_status` se resetea automáticamente a `never_synced`.

```bash
curl -X PUT http://localhost:8000/api/v1/repositories/550e8400-e29b-41d4-a716-446655440000 \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://github.com/org/my-kits-repo",
    "ref": "v2.0.0"
  }'
```

**Errores:**
- `404` — repositorio no encontrado
- `422` — credencial no es de tipo `git_https` o `git_ssh`

---

### DELETE /api/v1/repositories/{id} — Eliminar repositorio

Elimina físicamente el repositorio y todos sus kits. Solo es posible si ningún
kit del repositorio está referenciado en pipelines u operaciones.

```bash
curl -X DELETE http://localhost:8000/api/v1/repositories/550e8400-e29b-41d4-a716-446655440000 \
  -H "Authorization: Bearer $TOKEN"
```

**Respuesta 204:** (sin cuerpo)

**Errores:**
- `404` — repositorio no encontrado
- `409` — el repositorio tiene kits referenciados en pipelines u operaciones activas

---

### POST /api/v1/repositories/{id}/sync — Sincronizar repositorio

Realiza un shallow clone del repositorio, lee el `ikctl.yaml` raíz y reconcilia los
kits en base de datos (CREATE / UPDATE / soft_delete). Siempre devuelve `200`,
incluso si el sync falla — en ese caso `sync_status` es `sync_error`.

```bash
curl -X POST http://localhost:8000/api/v1/repositories/550e8400-e29b-41d4-a716-446655440000/sync \
  -H "Authorization: Bearer $TOKEN"
```

**Respuesta 200 — sync exitoso:**
```json
{
  "repository_id": "550e8400-...",
  "sync_status": "synced",
  "last_commit_sha": "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2",
  "sync_error_message": null,
  "kits_created": 3,
  "kits_updated": 1,
  "kits_deleted": 0
}
```

**Respuesta 200 — sync con error (sin ikctl.yaml raíz):**
```json
{
  "repository_id": "550e8400-...",
  "sync_status": "sync_error",
  "last_commit_sha": null,
  "sync_error_message": "No se encontró ikctl.yaml en la raíz del repositorio",
  "kits_created": 0,
  "kits_updated": 0,
  "kits_deleted": 0
}
```

**Errores:**
- `404` — repositorio no encontrado

---

## Kits

Los kits no se crean manualmente — son descubiertos automáticamente por el sync
del repositorio (RF-35). Solo existen endpoints de lectura.

### GET /api/v1/kits — Listar kits

Lista los kits del usuario con paginación y filtros opcionales. Solo devuelve
kits no eliminados (`is_deleted: false`).

```bash
# Todos los kits
curl http://localhost:8000/api/v1/kits \
  -H "Authorization: Bearer $TOKEN"

# Filtrar por repositorio
curl "http://localhost:8000/api/v1/kits?repository_id=550e8400-e29b-41d4-a716-446655440000" \
  -H "Authorization: Bearer $TOKEN"

# Filtrar por tags (AND — todos los tags deben coincidir)
curl "http://localhost:8000/api/v1/kits?tags=web&tags=proxy" \
  -H "Authorization: Bearer $TOKEN"

# Combinado: repositorio + tags + paginación
curl "http://localhost:8000/api/v1/kits?repository_id=550e8400-...&tags=web&page=1&per_page=20" \
  -H "Authorization: Bearer $TOKEN"
```

**Respuesta 200:**
```json
{
  "items": [
    {
      "kit_id": "660e8400-...",
      "user_id": "user-123",
      "repository_id": "550e8400-...",
      "path_in_repo": "nginx",
      "name": "Install NGINX",
      "description": "Installs and configures NGINX web server",
      "version": "1.2.0",
      "tags": ["web", "proxy"],
      "values": {
        "port": 80,
        "worker_processes": "auto"
      },
      "debug_level": "none",
      "sync_status": "synced",
      "last_synced_at": "2026-01-01T12:30:00Z",
      "last_commit_sha": "a1b2c3d4e5f6",
      "sync_error_message": null,
      "created_at": "2026-01-01T12:00:00Z",
      "updated_at": "2026-01-01T12:30:00Z"
    }
  ],
  "total": 1,
  "page": 1,
  "per_page": 50
}
```

---

### GET /api/v1/kits/{id} — Obtener kit

Obtiene el detalle de un kit por su ID.

```bash
curl http://localhost:8000/api/v1/kits/660e8400-e29b-41d4-a716-446655440001 \
  -H "Authorization: Bearer $TOKEN"
```

**Errores:**
- `404` — kit no encontrado, eliminado, o no pertenece al usuario

---

## Flujo típico

```bash
# 1. Registrar un repositorio público
REPO_ID=$(curl -s -X POST http://localhost:8000/api/v1/repositories \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://github.com/org/kits", "ref": "main"}' \
  | jq -r '.repository_id')

# 2. Sincronizar para descubrir los kits
curl -X POST "http://localhost:8000/api/v1/repositories/$REPO_ID/sync" \
  -H "Authorization: Bearer $TOKEN"

# 3. Listar los kits descubiertos
curl "http://localhost:8000/api/v1/kits?repository_id=$REPO_ID" \
  -H "Authorization: Bearer $TOKEN"

# 4. Obtener detalle de un kit específico
KIT_ID="660e8400-..."
curl "http://localhost:8000/api/v1/kits/$KIT_ID" \
  -H "Authorization: Bearer $TOKEN"
```

---

## Códigos de respuesta

| Código | Descripción |
|--------|-------------|
| 200 | OK — operación exitosa (incluido sync con error de negocio) |
| 201 | Created — repositorio registrado |
| 204 | No Content — repositorio eliminado |
| 404 | Not Found — recurso no encontrado o no pertenece al usuario |
| 409 | Conflict — repositorio con kits referenciados no puede eliminarse |
| 422 | Unprocessable Entity — credencial de tipo incorrecto u otro error de validación |
