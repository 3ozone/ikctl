# Backend - ikctl API

Servidor FastAPI para la gestión de servidores remotos.

## Instalación

```bash
cd backend
pip install -r requirements.txt
```

## Ejecución

```bash
# Puerto por defecto (8000)
uvicorn main:app --reload

# Especificar puerto personalizado
uvicorn main:app --reload --port 8080

# Especificar host y puerto
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

El servidor estará disponible en: <http://localhost:8000>

## Endpoints disponibles

### Documentación

- `GET /docs` - Documentación Swagger UI (automática)
- `GET /redoc` - Documentación ReDoc (automática)

### Health Check

- `GET /` - Hello World
- `GET /health` - Health check

### Autenticación (v1)

- `POST /api/v1/register` - Registrar nuevo usuario
- `POST /api/v1/login` - Autenticar usuario (obtiene JWT token)
- `GET /api/v1/users/me` - Obtener perfil del usuario autenticado 🔒
- `PUT /api/v1/users/me` - Actualizar nombre del usuario 🔒
- `PUT /api/v1/users/me/password` - Cambiar contraseña 🔒

🔒 = Requiere autenticación JWT

### Seguridad OAuth2/JWT

La API usa OAuth2 con JWT tokens para autenticación:

1. **Registro**: `POST /api/v1/register` con nombre, email y contraseña
2. **Login**: `POST /api/v1/login` retorna `access_token` (JWT)
3. **Uso**: Incluir token en header: `Authorization: Bearer {token}`

**Configuración JWT:**
- Algoritmo: HS256
- Expiración: 30 minutos
- Secret Key: Configurable vía variable de entorno

**Ejemplo de uso:**

```bash
# 1. Registrar usuario
curl -X POST http://localhost:8000/api/v1/register \
  -H "Content-Type: application/json" \
  -d '{"name": "John Doe", "email": "john@example.com", "password": "securepass123"}'

# 2. Login
curl -X POST http://localhost:8000/api/v1/login \
  -H "Content-Type: application/json" \
  -d '{"email": "john@example.com", "password": "securepass123"}'
# Respuesta: {"access_token": "eyJ0eXAi...", "token_type": "bearer"}

# 3. Acceder a endpoint protegido
curl http://localhost:8000/api/v1/users/me \
  -H "Authorization: Bearer eyJ0eXAi..."
```

## Tests

Tests implementados siguiendo TDD (Test-Driven Development) basados en la especificación OpenAPI.

### Estructura

```bash
backend/tests/
├── __init__.py
├── conftest.py           # Configuración compartida y fixtures
├── test_auth.py          # Tests de autenticación y usuarios
├── test_servers.py       # Tests de gestión de servidores
├── test_operations.py    # Tests de operaciones SSH
└── test_dummy.py         # Tests de ejemplo
```

### Ejecutar tests

```bash
cd backend

# Todos los tests
pytest

# Con verbose
pytest -v

# Tests específicos
pytest tests/test_auth.py
pytest tests/test_servers.py
pytest tests/test_operations.py

# Con cobertura
pytest --cov

# Con output detallado
pytest -v -s
```

### Cobertura de tests

#### Autenticación y Usuarios (`test_auth.py`) ✅ **12/12 COMPLETO**

- ✅ Registro de usuario (success, invalid email, duplicate)
- ✅ Login y obtención de JWT (success, invalid credentials)
- ✅ Obtener perfil de usuario (success, unauthorized)
- ✅ Actualizar nombre de usuario (success, unauthorized)
- ✅ Cambiar contraseña (success, wrong password, unauthorized)
- ✅ Validación OAuth2/JWT en endpoints protegidos
- ✅ Manejo de errores 401 Unauthorized

#### Servidores (`test_servers.py`) ⏳ **PENDIENTE**

- ⏳ Crear servidor (password y SSH key)
- ⏳ Listar servidores del usuario
- ⏳ Obtener detalles de servidor
- ⏳ Actualizar configuración de servidor
- ⏳ Eliminar servidor
- ⏳ Validación de datos
- ⏳ Manejo de errores 404
- ⏳ Control de acceso OAuth2

#### Operaciones (`test_operations.py`) ⏳ **PENDIENTE**

- ⏳ Test de conectividad SSH
- ⏳ Instalación de aplicaciones (asíncrona)
- ⏳ Consulta de estado de tareas
- ⏳ Ciclo de vida completo de tareas
- ⏳ Manejo de errores
- ⏳ Autenticación OAuth2 requerida

### Próximos pasos TDD

1. Instalar dependencias: `pip install -r requirements.txt`
2. Ejecutar tests: `pytest` (fallarán porque la API no está implementada)
3. Implementar endpoints en `main.py` siguiendo TDD
4. Ejecutar tests nuevamente hasta que pasen
5. Refactorizar código manteniendo tests en verde

### Notas

- Los tests usan `TestClient` de FastAPI para simular requests HTTP
- Cada test usa emails únicos para evitar conflictos de datos
- Se necesita implementar persistencia de datos (Base de datos)
- Algunos tests asumen comportamiento asíncrono para instalaciones
