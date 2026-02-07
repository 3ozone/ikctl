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

- `GET /` - Hello World
- `GET /health` - Health check
- `GET /docs` - Documentación Swagger UI (automática)
- `GET /redoc` - Documentación ReDoc (automática)

## Tests

Tests implementados siguiendo TDD (Test-Driven Development) basados en la especificación OpenAPI.

### Estructura

```
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

#### Autenticación y Usuarios (`test_auth.py`)

- ✅ Registro de usuario
- ✅ Login y obtención de JWT
- ✅ Obtener perfil de usuario
- ✅ Actualizar nombre de usuario
- ✅ Cambiar contraseña
- ✅ Validación de datos inválidos
- ✅ Manejo de duplicados
- ✅ Autenticación/autorización

#### Servidores (`test_servers.py`)

- ✅ Crear servidor (password y SSH key)
- ✅ Listar servidores del usuario
- ✅ Obtener detalles de servidor
- ✅ Actualizar configuración de servidor
- ✅ Eliminar servidor
- ✅ Validación de datos
- ✅ Manejo de errores 404
- ✅ Control de acceso

#### Operaciones (`test_operations.py`)

- ✅ Test de conectividad SSH
- ✅ Instalación de aplicaciones (asíncrona)
- ✅ Consulta de estado de tareas
- ✅ Ciclo de vida completo de tareas
- ✅ Manejo de errores
- ✅ Autenticación requerida

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
