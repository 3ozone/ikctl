# API Guide — Módulo Servers v1

Guía de uso con ejemplos `curl` para todos los endpoints del módulo `servers`.

**Base URL**: `http://localhost:8000`  
**Autenticación**: Bearer token JWT en cabecera `Authorization`.

```bash
# Obtener token (módulo auth)
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "secret"}' \
  | jq -r '.access_token')
```

---

## Credenciales

### POST /api/v1/credentials — Crear credencial

```bash
# Credencial SSH con clave privada
curl -X POST http://localhost:8000/api/v1/credentials \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "deploy-key",
    "type": "ssh",
    "username": "deploy",
    "private_key": "-----BEGIN OPENSSH PRIVATE KEY-----\n..."
  }'

# Credencial Git HTTPS con PAT
curl -X POST http://localhost:8000/api/v1/credentials \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "github-pat",
    "type": "git_https",
    "username": "octocat",
    "password": "ghp_xxxxxxxxxxxx"
  }'
```

**Respuesta 201:**
```json
{
  "credential_id": "cred-uuid",
  "user_id": "user-uuid",
  "name": "deploy-key",
  "credential_type": "ssh",
  "username": "deploy",
  "created_at": "2026-04-02T12:00:00Z",
  "updated_at": "2026-04-02T12:00:00Z"
}
```

> `password` y `private_key` son **write-only** — nunca aparecen en respuestas.

---

### GET /api/v1/credentials — Listar credenciales

```bash
curl http://localhost:8000/api/v1/credentials \
  -H "Authorization: Bearer $TOKEN"

# Con paginación
curl "http://localhost:8000/api/v1/credentials?page=2&per_page=10" \
  -H "Authorization: Bearer $TOKEN"
```

**Respuesta 200:**
```json
{
  "items": [...],
  "total": 5,
  "page": 1,
  "per_page": 20
}
```

---

### GET /api/v1/credentials/{id} — Obtener credencial

```bash
curl http://localhost:8000/api/v1/credentials/cred-uuid \
  -H "Authorization: Bearer $TOKEN"
```

**Errores:** `404` si no existe o no es propia.

---

### PUT /api/v1/credentials/{id} — Actualizar credencial

```bash
curl -X PUT http://localhost:8000/api/v1/credentials/cred-uuid \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "deploy-key-v2",
    "username": "deploy",
    "private_key": "-----BEGIN OPENSSH PRIVATE KEY-----\n..."
  }'
```

**Errores:** `404` si no existe, `403` si no es propia.

---

### DELETE /api/v1/credentials/{id} — Eliminar credencial

```bash
curl -X DELETE http://localhost:8000/api/v1/credentials/cred-uuid \
  -H "Authorization: Bearer $TOKEN"
```

**Respuesta:** `204 No Content`.  
**Errores:** `404` si no existe, `403` si no es propia, `409` si está en uso por algún servidor.

---

## Servidores

### POST /api/v1/servers — Registrar servidor

```bash
# Servidor remoto
curl -X POST http://localhost:8000/api/v1/servers \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "remote",
    "name": "web-01",
    "host": "192.168.1.10",
    "port": 22,
    "credential_id": "cred-uuid",
    "description": "Servidor web principal"
  }'

# Servidor local (requiere rol admin)
curl -X POST http://localhost:8000/api/v1/servers \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "local",
    "name": "localhost",
    "description": "Host donde corre ikctl"
  }'
```

**Respuesta 201:**
```json
{
  "server_id": "srv-uuid",
  "user_id": "user-uuid",
  "name": "web-01",
  "server_type": "remote",
  "status": "active",
  "host": "192.168.1.10",
  "port": 22,
  "credential_id": "cred-uuid",
  "description": "Servidor web principal",
  "os_id": null,
  "os_version": null,
  "os_name": null,
  "created_at": "2026-04-02T12:00:00Z",
  "updated_at": "2026-04-02T12:00:00Z"
}
```

**Errores:** `404` credencial no encontrada, `409` segundo servidor local (RN-07), `403` usuario no-admin registrando local.

---

### GET /api/v1/servers — Listar servidores

```bash
curl http://localhost:8000/api/v1/servers \
  -H "Authorization: Bearer $TOKEN"

# Con filtros y paginación
curl "http://localhost:8000/api/v1/servers?page=1&per_page=10" \
  -H "Authorization: Bearer $TOKEN"
```

---

### GET /api/v1/servers/{id} — Obtener servidor

```bash
curl http://localhost:8000/api/v1/servers/srv-uuid \
  -H "Authorization: Bearer $TOKEN"
```

**Errores:** `404` si no existe o no es propio.

---

### PUT /api/v1/servers/{id} — Actualizar servidor

```bash
# Servidor remoto — actualiza todos los campos
curl -X PUT http://localhost:8000/api/v1/servers/srv-uuid \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "web-01-updated",
    "host": "192.168.1.20",
    "port": 22,
    "credential_id": "cred-uuid-2",
    "description": "Servidor web actualizado"
  }'

# Servidor local — solo name y description
curl -X PUT http://localhost:8000/api/v1/servers/srv-local-uuid \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "localhost-v2"}'
```

**Errores:** `404` si no existe.

---

### DELETE /api/v1/servers/{id} — Eliminar servidor

```bash
curl -X DELETE http://localhost:8000/api/v1/servers/srv-uuid \
  -H "Authorization: Bearer $TOKEN"
```

**Respuesta:** `204 No Content`.  
**Errores:** `404` si no existe, `409` si tiene operaciones activas (RN-08).

---

### POST /api/v1/servers/{id}/toggle — Activar / desactivar servidor

```bash
curl -X POST http://localhost:8000/api/v1/servers/srv-uuid/toggle \
  -H "Authorization: Bearer $TOKEN"
```

**Respuesta 200:** `ServerResponse` con `status` actualizado (`active` ↔ `inactive`).  
**Errores:** `404` si no existe.

---

### GET /api/v1/servers/{id}/health — Health check

```bash
curl http://localhost:8000/api/v1/servers/srv-uuid/health \
  -H "Authorization: Bearer $TOKEN"
```

**Respuesta 200 — online:**
```json
{
  "server_id": "srv-uuid",
  "status": "online",
  "latency_ms": 12.5,
  "os_id": "ubuntu",
  "os_version": "22.04",
  "os_name": "Ubuntu 22.04 LTS"
}
```

**Respuesta 200 — offline:**
```json
{
  "server_id": "srv-uuid",
  "status": "offline",
  "latency_ms": null,
  "os_id": null,
  "os_version": null,
  "os_name": null
}
```

> Rate limit: máx **10 peticiones/min** por usuario (RNF-07).

---

### POST /api/v1/servers/{id}/command — Ejecutar comando ad-hoc

```bash
curl -X POST http://localhost:8000/api/v1/servers/srv-uuid/command \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "command": "df -h",
    "sudo": false,
    "timeout": 30
  }'
```

**Respuesta 200:**
```json
{
  "stdout": "Filesystem      Size  Used Avail Use% Mounted on\n...",
  "stderr": "",
  "exit_code": 0
}
```

> Si `exit_code != 0` el HTTP status sigue siendo `200` — el error es del comando, no del endpoint.  
> Rate limit: máx **30 peticiones/hora** por usuario (RNF-07).

---

## Grupos

### POST /api/v1/groups — Crear grupo

```bash
curl -X POST http://localhost:8000/api/v1/groups \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "k8s-nodes",
    "description": "Nodos del clúster Kubernetes",
    "server_ids": ["srv-uuid-1", "srv-uuid-2", "srv-uuid-3"]
  }'

# Grupo vacío
curl -X POST http://localhost:8000/api/v1/groups \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "grupo-vacio", "server_ids": []}'
```

**Respuesta 201:**
```json
{
  "group_id": "grp-uuid",
  "user_id": "user-uuid",
  "name": "k8s-nodes",
  "description": "Nodos del clúster Kubernetes",
  "server_ids": ["srv-uuid-1", "srv-uuid-2", "srv-uuid-3"],
  "created_at": "2026-04-02T12:00:00Z",
  "updated_at": "2026-04-02T12:00:00Z"
}
```

**Errores:** `404` si algún `server_id` no existe o no es propio, `422` si algún server es de tipo `local` (RNF-16).

---

### GET /api/v1/groups — Listar grupos

```bash
curl http://localhost:8000/api/v1/groups \
  -H "Authorization: Bearer $TOKEN"

# Con paginación
curl "http://localhost:8000/api/v1/groups?page=1&per_page=10" \
  -H "Authorization: Bearer $TOKEN"
```

---

### GET /api/v1/groups/{id} — Obtener grupo

```bash
curl http://localhost:8000/api/v1/groups/grp-uuid \
  -H "Authorization: Bearer $TOKEN"
```

**Errores:** `404` si no existe o no es propio.

---

### PUT /api/v1/groups/{id} — Actualizar grupo

```bash
curl -X PUT http://localhost:8000/api/v1/groups/grp-uuid \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "k8s-nodes-prod",
    "description": "Solo nodos de producción",
    "server_ids": ["srv-uuid-1", "srv-uuid-4"]
  }'
```

**Errores:** `404` si no existe.

---

### DELETE /api/v1/groups/{id} — Eliminar grupo

```bash
curl -X DELETE http://localhost:8000/api/v1/groups/grp-uuid \
  -H "Authorization: Bearer $TOKEN"
```

**Respuesta:** `204 No Content`.  
**Errores:** `404` si no existe, `409` si tiene pipelines activos (RN-19).

---

## Códigos de Error

| Código | Significado |
|--------|-------------|
| `400` | Validación de dominio fallida (tipo de credencial inválido, configuración incorrecta) |
| `401` | Token JWT ausente o expirado |
| `403` | Sin permisos (recurso de otro usuario, rol insuficiente) |
| `404` | Recurso no encontrado o no pertenece al usuario |
| `409` | Conflicto — recurso en uso o duplicado |
| `422` | Validación de schema fallida (campos requeridos ausentes, servidor local en grupo) |
| `429` | Rate limit superado |

**Formato de error:**
```json
{
  "detail": "Descripción del error"
}
```
