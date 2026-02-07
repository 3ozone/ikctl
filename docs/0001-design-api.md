# Diseño de la API REST para Instalación de Aplicaciones Remotas

## Arquitectura

- **Backend**: FastAPI + asyncssh + MariaDB
- **Frontend**: Next.js
- **Conexiones SSH**: asyncssh (asíncrono)

## Casos de Uso

### Funcionales

1. **Registro de usuarios**: Crear cuenta con email y contraseña
2. **Login de usuarios**: Autenticación con JWT
3. **Añadir servidores**: Guardar credenciales SSH, llaves, IPs/nombres
4. **Probar conectividad**: Verificar acceso SSH a servidores

### No Funcionales

- **Seguridad**: Encriptación de credenciales SSH, tokens JWT
- **Rendimiento**: Operaciones SSH asíncronas sin bloqueo
- **Escalabilidad**: Múltiples conexiones SSH concurrentes

### Negocio

- Gestión centralizada de servidores remotos
- Instalación de aplicaciones sin intervención manual

## Endpoints API

### Usuarios

- `POST /register` — Registro
- `POST /login` — Autenticación (devuelve JWT)
- `GET /users/me` — Obtener perfil del usuario
- `PUT /users/me` — Actualizar nombre del usuario
- `PUT /users/me/password` — Cambiar contraseña

### Servidores

- `POST /servers` — Añadir servidor
- `GET /servers` — Listar servidores del usuario
- `GET /servers/{server_id}` — Obtener detalles
- `PUT /servers/{server_id}` — Actualizar servidor (IP, credenciales, puerto, etc.)
- `DELETE /servers/{server_id}` — Eliminar

### Operaciones

- `POST /servers/{server_id}/test-connection` — Probar conectividad SSH
- `POST /servers/{server_id}/install` — Lanzar instalación (asíncrona)
- `GET /tasks/{task_id}` — Consultar estado de tarea

## Modelo de Datos (MariaDB)

### users

- id, name, email, password_hash, created_at, updated_at

### servers

- id, user_id, name, host, port, username, auth_type, ssh_key, password_encrypted, created_at

### tasks

- id, server_id, type, status, result, created_at, completed_at
