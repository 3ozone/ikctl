# ikctl

**Instalación y gestión de aplicaciones en servidores remotos vía SSH**

ikctl es una herramienta moderna para ejecutar **scripts bash**, **instalar aplicaciones** y **gestionar configuraciones** en servidores remotos mediante SSH. Disponible como **CLI** y **API REST**.

## 🎯 ¿Para qué sirve ikctl?

Automatiza operaciones en servidores remotos vía SSH:

- ✅ **Instalar aplicaciones** (nginx, docker, td-agent, etc.)
- ✅ **Configurar servicios** con templates dinámicos (Jinja2)
- ✅ **Ejecutar scripts bash/python** remotamente
- ✅ **Backups y recuperación** de datos
- ✅ **Health checks** automáticos de conectividad
- ✅ **Pipelines multiservidor** (orquestación de operaciones)

## 🚀 Modos de Uso

### 1️⃣ CLI (Command Line Interface)

```bash
# Instalar aplicación en servidor remoto
ikctl run --server srv_123 --kit nginx --sudo

# Health check de servidor
ikctl check --server srv_123

# Ejecutar pipeline en múltiples servidores
ikctl pipeline --file production-deploy.yaml

# Listar servidores registrados
ikctl servers list
```

### 2️⃣ API REST

```bash
# Ejecutar instalación vía API
curl -X POST https://api.ikctl.com/api/v1/operations \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "server_id": "srv_123",
    "kit": "nginx",
    "sudo": true
  }'

# Health check
curl https://api.ikctl.com/api/v1/servers/srv_123/health \
  -H "Authorization: Bearer $TOKEN"
```

## 🏗️ Arquitectura

**Clean Architecture + TDD + Async end-to-end**

- **FastAPI** + asyncio para API async nativa
- **MariaDB** para datos transaccionales
- **Valkey** para cache, sesiones y rate limiting
- **Celery** workers async para operaciones largas SSH
- **asyncssh** con connection pooling (500+ conexiones concurrentes)

## 📦 Conceptos Clave

### Kits

Paquetes con scripts bash/python + templates + configuración:

```bash
kits/nginx/
├── nginx.yaml          # Configuración del kit
├── install-debian.sh   # Script de instalación
└── nginx.conf.j2       # Template Jinja2
```

### Servidores (Targets)

Servidores remotos registrados con credenciales SSH:

```yaml
name: web-server-01
host: 192.168.1.100
port: 22
user: admin
auth: ssh_key  # o password
```

### Operaciones

Ejecución de kits en servidores con tracking de estado:

- `pending` → `in_progress` → `completed` | `failed`
- Idempotencia con `operation_id` único
- Retries automáticos con backoff exponencial

## 📥 Instalación

### CLI

```bash
pip install ikctl
ikctl --version
```

### API Server

```bash
git clone https://github.com/3ozone/ikctl.git
cd ikctl
pip install -r requirements.txt

# Ejecutar API REST
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Servidor API disponible en: <http://localhost:8000>

## 🔧 Configuración

```🌐 API REST Endpoints

### Documentación
- `GET /docs` - Swagger UI interactiva
- `GET /redoc` - Documentación ReDoc

### Autenticación
- `POST /api/v1/register` - Registrar usuario
- `POST /api/v1/login` - Login (obtiene JWT token)
- `POST /api/v1/logout` - Logout (revoca token)
- `GET /api/v1/users/me` - Perfil usuario 🔒
- `PUT /api/v1/users/me/password` - Cambiar contraseña 🔒

### Servidores
- `GET /api/v1/servers` - Listar servidores 🔒
- `POST /api/v1/servers` - Registrar servidor 🔒
- `GET /api/v1/servers/{id}` - Detalles servidor 🔒
- `PUT /api/v1/servers/{id}` - Actualizar servidor 🔒
- `DELETE /api/v1/servers/{id}` - Eliminar servidor 🔒
- `GET /api/v1/servers/{id}/health` - Health check SSH 🔒

### Operaciones
- `POST /api/v1/operations` - Ejecutar kit en servidor 🔒
- `GET /api/v1/operations/{id}` - Estado de operación 🔒
- `GET /api/v1/operations` - Historial de operaciones
### Autenticación (v1)

- `POST /api/v1/register` - Registrar nuevo usuario
- `POST /api/v1/login` - Autenticar usuario (obtiene JWT token)
-  🔐 Autenticación

### OAuth2 + JWT
```bash
# 1. Registrar usuario
curl -X POST http://localhost:8000/api/v1/register \
  -H "Content-Type: application/json" \
  -d '{"name": "Admin", "email": "admin@ikctl.com", "password": "SecurePass123!"}'

# 2. Login (obtener token JWT)
TOKEN=$(curl -X POST http://localhost:8000/api/v1/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@ikctl.com", "password": "SecurePass123!"}' \
  | jq -r '.access_token')

# 3. Usar token en requests
curl http://localhost:8000/api/v1/servers \
  -H "Authorization: Bearer $TOKEN"
```

**Configuración JWT:**

- Access token: 15 minutos (HS256)
- Refresh token: 7 días
- 2FA opcional (TOTP)
- GitHub OAuth soportadod '{"email": "<john@example.com>", "password": "securepass123"}'

# Respuesta: {"access_token": "eyJ0eXAi...", "token_type": "bearer"}

# 3. Acceder a endpoint protegido

```bash
curl http://localhost:8000/api/v1/users/me \
  -H "Authorization: Bearer eyJ0eXAi..."

```

## Tests

🚀 Features

### Rendimiento & Escalabilidad

- **500+ conexiones SSH concurrentes** con asyncssh + pooling
- **API async nativa**: FastAPI + asyncio end-to-end
- **Rate limiting**: 100 req/min por usuario, 20 SSH/hora
- **Cache inteligente**: Valkey para sesiones y queries frecuentes
- **Paginación**: limit=50 por defecto en listados

### Resiliencia

- **Idempotencia**: mismo `operation_id` = mismo resultado
- **Retries automáticos**: 3 intentos con backoff exponencial
- **Circuit breaker**: abre tras 5 fallos consecutivos
- **Timeouts**: 30s conexión, 10min install, 30min backup
- **Health checks**: /healthz (liveness), /readyz (readiness)

### Seguridad

- **Autenticación**: OAuth2 + JWT + 2FA opcional
- **Autorización**: RBAC (user/admin)
- **Secretos**: nunca en código, siempre en vault
- **Cifrado**: bcrypt cost=12, ed25519 SSH, TLS
- **Audit logs**: todas las operaciones críticas

### Observabilidad

- **Logs estructurados**: JSON con request_id, user_id, timestamps
- **Métricas**: latencia p50/p95/p99, errores, conexiones SSH
- **Trazas**: correlación request → queue → SSH execution
- **SLO**: auth 99% <100ms, API 99.5% uptime, SSH 95% <5min

## 🧪 Tests (TDD)

```bash
# Ejecutar todos los tests
pytest -v

# Tests específicos por módulo
pytest tests/v1/auth/
pytest tests/v1/servers/
pytest tests/v1/operations/

# Con cobertura
pytest --cov=app --cov-report=html
```

**Estado actual:**

- ✅ Auth Domain Layer: 40 tests GREEN
- ✅ Auth Use Cases: 28 tests GREEN
- 🔄 Infrastructure Layer: en progreso

## 📚 Documentación

- [AGENTS.md](AGENTS.md) - Guía de desarrollo y arquitectura
- [/docs/v1/adrs/](docs/v1/adrs/) - Architecture Decision Records
- [openapi.yaml](openapi.yaml) - Especificación completa de la API
- [DOCKER_SETUP.md](DOCKER_SETUP.md) - Setup con Docker Compose

## 🤝 Contribuir

ikctl sigue **Clean Architecture + TDD**:

1. Leer [AGENTS.md](AGENTS.md)
2. Crear tests primero (RED)
3. Implementar código (GREEN)
4. Refactorizar (REFACTOR)
5. Documentar en ADRs decisiones importantes

## 📄 Licencia

MIT License - ver [LICENSE](LICENSE)
