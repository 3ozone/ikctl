# Convenciones de código — ikctl

> Homogeneidad extrema. La IA predice mejor cuando el repositorio se parece
> a sí mismo en todas partes.

## Gestión de dependencias y entorno

### Python

- **Gestor:** `requirements.txt` + `pip`.
- **Entorno virtual:** `.venv` en la raíz del proyecto.
- **Instalar dependencias:** `pip install -r requirements.txt`.
- **Añadir una dependencia:** editar `requirements.txt` y `pip install -r requirements.txt`.

```bash
# Arranque del entorno
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
pip install -r requirements.txt
```

### Herramientas

| Herramienta | Versión | Uso |
|-------------|---------|-----|
| Python | 3.13+ | Sintaxis moderna (`list[str]`, `str \| None`, `type X = ...`) |
| FastAPI | 0.115+ | Framework web asíncrono |
| SQLAlchemy | 2.x | ORM asíncrono (AsyncSession, `select()` style) |
| Alembic | 1.13+ | Migraciones de esquema |
| pytest | 8.x + pytest-asyncio | Tests asíncronos |
| Ruff | 0.4+ | Linting + formato (reemplaza flake8, isort, black) |
| structlog | 24.x | Logging estructurado |

## Estilo Python

- **Versión:** Python 3.13+ (sintaxis `list[str]`, `str | None`, `type X = ...`).
- **Formato:** Ruff (PEP 8 estricto). Líneas máximo 100 caracteres.
- **Imports:** stdlib primero, luego third-party, luego locales. Una línea por módulo.
- **Strings:** comillas dobles `"..."` siempre. Comillas simples solo para escapar comillas dobles dentro.
- **f-strings** para interpolación. Nada de `.format()` ni `%`.
- **Async:** todos los métodos `execute()` de use cases y repositorios son `async def`.

## Nombres

### Python — archivos y clases

| Tipo | Convención | Ejemplo |
|------|-----------|---------|
| Módulo/archivo | `snake_case` | `register_server.py`, `server_repository.py` |
| Clase (entidad) | `PascalCase` sustantivo | `Server`, `Operation`, `Pipeline` |
| Clase (value object) | `PascalCase` sustantivo | `ServerType`, `OperationStatus` |
| Clase (excepción dominio) | `PascalCase` + `Error` | `ServerNotFoundError`, `InvalidServerConfigurationError` |
| Clase (excepción app) | `PascalCase` + `Error` | `UseCaseException`, `UnauthorizedOperationError` |
| Clase (command) | `PascalCase` verbo imperativo | `RegisterServer`, `LaunchPipeline` |
| Clase (query) | `PascalCase` verbo interrogativo | `GetServer`, `ListPipelines` |
| Clase (DTO) existente | `PascalCase` sustantivo + `Result` | `ServerResult`, `PipelineExecutionResult` |
| Clase (DTO) nueva | `PascalCase` sustantivo + `DTO` | `ServerDTO`, `ServerListDTO` |
| Clase (DTO lista) existente | `PascalCase` + `ListResult` | `ServerListResult`, `OperationListResult` |
| Clase (DTO lista) nueva | `PascalCase` + `ListDTO` | `ServerListDTO`, `OperationListDTO` |
| Clase (repositorio port) | `PascalCase` sustantivo | `ServerRepository(ABC)` |
| Clase (repositorio impl) | `SQLAlchemy` + nombre port | `SQLAlchemyServerRepository` |
| Clase (adapter) | `PascalCase` + `Adapter` | `OperationLauncherAdapter` |
| Clase (evento dominio) | `PascalCase` pasado | `ServerRegistered`, `OperationCompleted` |
| Clase (handler) existente | `PascalCase` verbo | `RemoveServerFromGroups` |
| Clase (handler) nueva | `PascalCase` verbo + `Handler` | `RemoveServerFromGroupsHandler` |
| Función/método | `snake_case` | `execute()`, `find_by_id()`, `save()` |
| Variable privada | prefijo `_` | `self._server_repo`, `self._event_bus` |
| Constante módulo | `UPPER_SNAKE` | `VALID_TYPES = {"remote", "local"}` |

### Pydantic schemas (presentation)

| Tipo | Convención | Ejemplo |
|------|-----------|---------|
| Request | `PascalCase` verbo + `Request` | `CreateServerRequest`, `UpdatePipelineRequest` |
| Response | `PascalCase` sustantivo + `Response` | `ServerResponse`, `PipelineListResponse` |
| List response | contenedor con `items`, `total`, `page`, `per_page` | `ServerListResponse` |

## Estructura de archivo Python

Cada archivo empieza con una docstring de una línea describiendo el propósito:

```python
"""Use Case para registrar un nuevo servidor remoto."""
from datetime import datetime, timezone
from uuid import uuid4

from app.v1.servers.domain.entities.server import Server
from app.v1.servers.domain.value_objects.server_type import ServerType
from app.v1.servers.domain.exceptions.server import ServerNotFoundError
from app.v1.servers.application.dtos.server_result import ServerResult
from app.v1.servers.application.interfaces.server_repository import ServerRepository
from app.v1.shared.application.interfaces.event_bus import EventBus
```

### Orden de imports

1. **stdlib** — `from datetime import datetime`, `from uuid import uuid4`
2. **third-party** — `from fastapi import APIRouter`, `from sqlalchemy import select`
3. **locales** — `from app.v1.servers.domain...`

Separador: línea en blanco entre cada grupo.

## Domain layer

### Entidades

- `@dataclass` (NO frozen — las entidades mutan vía métodos).
- Identidad vía `id: str` (generado con `str(uuid4())`).
- `__eq__` y `__hash__` basados en `id`.
- `__post_init__` para validar invariantes y lanzar excepciones de dominio.
- Timestamps: `created_at: datetime`, `updated_at: datetime` (siempre UTC).

```python
@dataclass
class Server:
    id: str
    user_id: str
    name: str
    type: ServerType
    status: ServerStatus
    host: str | None
    # ...

    def __post_init__(self) -> None:
        if self.type == ServerType("remote") and not self.host:
            raise InvalidServerConfigurationError("Remote server requires host")

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Server):
            return NotImplemented
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)

    def activate(self) -> None:
        self.status = ServerStatus("active")
```

### Value Objects

- `@dataclass(frozen=True)` — siempre inmutables.
- Un solo campo `value: str` con validación en `__post_init__`.
- Constantes de valores válidos a nivel de módulo.

```python
VALID_TYPES = {"remote", "local"}

@dataclass(frozen=True)
class ServerType:
    value: str

    def __post_init__(self) -> None:
        if self.value not in VALID_TYPES:
            raise InvalidServerTypeError(self.value)
```

### Excepciones

Heredan de `DomainException` (del shared kernel):

```python
from app.v1.shared.domain.exceptions import DomainException

class ServerNotFoundError(DomainException):
    """Se lanza cuando se busca un servidor que no existe."""

class InvalidServerConfigurationError(DomainException):
    """Configuración inválida para el tipo de servidor."""
```

Tres capas de excepciones:

| Capa | Base | Uso |
|------|------|-----|
| Dominio | `DomainException` | Violaciones de reglas de negocio |
| Aplicación | `UseCaseException` | Errores de casos de uso (autorización, estado) |
| Infraestructura | `InfrastructureException` | Errores de BD, SSH, conexiones |

### Eventos de dominio

Heredan de `DomainEvent` (del shared kernel). Se crean con factory method
o constructor directo:

```python
from app.v1.shared.domain.events import DomainEvent

event = DomainEvent(
    event_id=str(uuid4()),
    correlation_id=correlation_id,
    event_type="ServerRegistered",
    aggregate_id=server.id,
    aggregate_type="Server",
    payload={"name": server.name, "host": server.host},
    version=1,
    occurred_at=datetime.now(timezone.utc),
)
await self._event_bus.publish(event)
```

## Application layer

### Commands (`application/commands/`)

- Una clase por archivo. Nombre: verbo imperativo (`RegisterServer`, `LaunchPipeline`).
- Constructor recibe dependencias por inyección, todas opcionales (`| None = None`).
- Almacenadas como `self._repo` (prefijo `_`).
- Método público `async def execute(self, ...) -> ResultType`.
- Publican eventos de dominio vía `EventBus` inyectado.

```python
class RegisterServer:
    def __init__(
        self,
        server_repository: ServerRepository | None = None,
        credential_repository: CredentialRepository | None = None,
        event_bus: EventBus | None = None,
    ) -> None:
        self._server_repo = server_repository
        self._credential_repo = credential_repository
        self._event_bus = event_bus

    async def execute(self, user_id: str, name: str, ...) -> ServerResult:
        # lógica de dominio
        server = Server(id=str(uuid4()), ...)
        await self._server_repo.save(server)
        if self._event_bus is not None:
            await self._event_bus.publish(event)
        return ServerResult.from_entity(server)
```

### Queries (`application/queries/`)

- Misma estructura que commands pero **solo lectura** — no mutan estado, no publican eventos.
- Nombre: verbo interrogativo (`GetServer`, `ListPipelines`).
- Lanzan `NotFoundError` cuando la entidad no existe.

### Tasks (`application/tasks/`)

- Orquestación asíncrona (background tasks). Se ejecutan fuera del request HTTP.
- Reciben `commit_fn` inyectado para forzar commits de sesión entre iteraciones de polling.
- Ejemplo: `ExecuteOperation`, `ExecutePipelineOperations`.

### Handlers (`application/handlers/`)

- Reaccionan a eventos de dominio. Implementan `EventHandler` del shared kernel.
- Se suscriben al `EventBus` en `main.py`.

### Puertos (`application/interfaces/`)

- ABCs que definen contratos. Heredan de `ABC` con métodos `@abstractmethod`.
- Todos los métodos son `async`.
- Nombre del archivo = nombre de la interfaz: `server_repository.py`.

```python
from abc import ABC, abstractmethod

class ServerRepository(ABC):
    @abstractmethod
    async def save(self, server: Server) -> None: ...

    @abstractmethod
    async def find_by_id(self, server_id: str, user_id: str) -> Server | None: ...

    @abstractmethod
    async def find_all_by_user(self, user_id: str, page: int, per_page: int) -> list[Server]: ...
```

### DTOs (`application/dtos/`)

- `@dataclass(frozen=True)` — siempre inmutables.
- Contienen solo datos primitivos (`str`, `int`, `datetime`, `list[str]`). Nunca entidades de dominio.
- Nombres: `ServerResult`, `ServerListResult`, `PipelineExecutionDetailResult`.
- List results contienen: `items: list[ResultType]`, `total: int`, `page: int`, `per_page: int`.

### Excepciones de aplicación (`application/exceptions.py`)

```python
class UseCaseException(Exception):
    """Base para errores de casos de uso."""

class UnauthorizedOperationError(UseCaseException):
    """El usuario no tiene permisos para la operación."""
```

## Infrastructure layer

### Repositorios (`infrastructure/repositories/`)

- Implementan el port ABC. Nombre: `SQLAlchemy` + nombre del port.
- Constructor recibe `AsyncSession` (+ dependencias adicionales si necesario).
- Conversión entidad ↔ modelo SQLAlchemy con métodos `model_to_entity()` / `entity_to_model()`.
- Manejo de errores: `try/except` con `DatabaseQueryError` en repositorios.

```python
class SQLAlchemyServerRepository(ServerRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, server: Server) -> None:
        model = self.entity_to_model(server)
        self._session.add(model)
        await self._session.flush()

    async def find_by_id(self, server_id: str, user_id: str) -> Server | None:
        stmt = select(ServerModel).where(ServerModel.id == server_id, ServerModel.user_id == user_id)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self.model_to_entity(model) if model else None
```

### Adaptadores cross-module (`infrastructure/adapters/`)

Cada módulo define sus propios puertos en `application/interfaces/` para
acceder a entidades de otros módulos. La implementación (adapter) vive en
`infrastructure/adapters/` y delega al repositorio concreto del módulo original.

Ejemplo — pipelines accediendo a servers:

```python
# pipelines/application/interfaces/server_repository.py (puerto ABC)
class ServerRepository(ABC):
    @abstractmethod
    async def find_server_by_id_internal(self, server_id: str) -> Server | None: ...

# pipelines/infrastructure/adapters/server_read_adapter.py (implementación)
class ServerReadAdapter(pipelines_port.ServerRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._repo = SQLAlchemyServerRepository(session)

    async def find_server_by_id_internal(self, server_id: str) -> Server | None:
        return await self._repo.find_by_id_no_ownership(server_id)
```

El wiring se hace en `main.py` (Composition Root).

### Persistence models (`infrastructure/persistence/models.py`)

- Modelos SQLAlchemy con `DeclarativeBase`.
- Mapped columns tipados: `Mapped[str]`, `Mapped[str | None]`, `Mapped[datetime]`.
- Columnas JSON para campos compuestos: `mapped_column(JSON, nullable=False)`.
- Nombres de tabla en plural: `__tablename__ = "servers"`, `__tablename__ = "pipelines"`.

### Presentation (`infrastructure/presentation/`)

Cuatro archivos por módulo:

| Archivo | Contenido |
|---------|-----------|
| `routes_{resource}.py` o `routes.py` | `APIRouter` con endpoints. Usa `Annotated[Depends()]` |
| `schemas.py` | Pydantic `BaseModel` para request/response |
| `deps.py` | Funciones factory para inyección de dependencias FastAPI |
| `exception_handlers.py` | `@app.exception_handler()` para mapear excepciones de dominio → HTTP |

Convenciones de routers:

```python
router = APIRouter(prefix="/api/v1/servers", tags=["servers"])

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_server(
    body: CreateServerRequest,
    user_id: Annotated[str, Depends(get_current_user_id)],
    use_case: Annotated[RegisterServer, Depends(get_register_server)],
) -> ServerResponse:
    ...
```

Convenciones de schemas:

- Request: `CreateServerRequest`, `UpdateServerRequest`
- Response: `ServerResponse`, `ServerListResponse`
- List response: `items: list[ServerResponse]`, `total: int`, `page: int`, `per_page: int`
- Validación con `Field(...)`: `min_length`, `max_length`, `ge`, `le`, `examples`

## Composition Root (`main.py`)

`main.py` es el único punto donde se conocen las implementaciones concretas.

- **Singletons** (creados al arranque): `Settings`, `EventBus`, `GitPythonClient`, `PyJWTProvider`, adaptadores stateless.
- **Scoped por request** (via `Depends()`): `AsyncSession`, repositories, use cases.
- **Background task closures**: `_execute_operation_fn`, `_execute_pipeline_fn` — crean sus propias sesiones porque se ejecutan fuera del request HTTP.

```python
# Singleton
event_bus = InMemoryEventBus()

# Scoped por request (en deps.py)
async def get_db_session(request: Request) -> AsyncGenerator[AsyncSession, None]:
    async for session in _get_db_session(request.app.state.session_factory):
        yield session

# Background task closure
async def _execute_pipeline_fn(execution_id: str) -> None:
    async for session in get_db_session(_session_factory):
        pipeline_repo = SQLAlchemyPipelineRepository(session)
        # ... construye todo el grafo de dependencias
        task = ExecutePipelineOperations(...)
        await task.execute(execution_id)
```

## Tests

### Estructura

Los tests replican la estructura del módulo:

```
tests/
└── v1/
    ├── conftest.py                  ← Fixtures compartidas (AsyncSession, cliente HTTP, auth)
    ├── auth/
    │   ├── test_domain/             ← Entidades, VOs, excepciones, eventos
    │   ├── test_use_cases/          ← Commands y queries (con mocks)
    │   ├── test_infrastructure/     ← Repositories (con DB real o SQLite in-memory)
    │   └── test_presentation/       ← Endpoints HTTP (con cliente de test)
    ├── servers/
    │   ├── test_domain/
    │   ├── test_use_cases/
    │   ├── test_infrastructure/
    │   └── test_presentation/
    ├── kits/
    │   ├── test_domain/
    │   ├── test_use_cases/
    │   ├── test_infrastructure/
    │   └── test_presentation/
    ├── operations/
    │   ├── test_domain/
    │   ├── test_use_cases/
    │   ├── test_infrastructure/
    │   └── test_presentation/
    └── pipelines/
        ├── test_domain/
        ├── test_use_cases/
        ├── test_infrastructure/
        └── test_presentation/
```

### Convenciones de test

- **pytest-asyncio** con `asyncio_mode = auto` (configurado en `pytest.ini`).
- **Domain tests**: instancian entidades y VOs directamente, verifican invariantes y excepciones.
  - Clases de agrupación: `TestServerRemote`, `TestServerLocal`, `TestServerCommands`.
  - Cada método tiene docstring en español describiendo el comportamiento esperado.
- **Use case tests**: usan `AsyncMock()` para repositorios y buses de eventos.
  - Verifican que se llama al repositorio correcto y se devuelve el DTO esperado.
  - Tests de error: `with pytest.raises(ServerNotFoundError):`.
- **Infrastructure tests**: usan SQLite in-memory para tests de repositorios.
  - Fixtures `@pytest_asyncio.fixture` para crear sesiones y repositorios.
  - Helpers de factoría a nivel de módulo: `_make_remote_server()`.
- **Presentation tests**: usan `httpx.AsyncClient` con `TestClient`.
  - Fakes para use cases: `FakeRegisterServerOk` con `async def execute(...)`.
  - Override de dependencias: `app.dependency_overrides[get_register_server] = ...`.

### Configuración pytest

```ini
[pytest]
asyncio_mode = auto
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
```

## Manejo de errores

Excepciones de dominio heredan de `DomainException` (en el shared kernel):

```python
from app.v1.shared.domain.exceptions import DomainException

class ServerNotFoundError(DomainException):
    """Se lanza cuando se busca un servidor que no existe."""
```

La capa de presentación (`exception_handlers.py`) captura excepciones de dominio
y las transforma en respuestas HTTP:

| Excepción | HTTP Status |
|-----------|-------------|
| `EntityNotFoundError` (y subclases) | 404 |
| `EntityAlreadyExistsError` | 409 |
| `ValidationError` | 422 |
| `InvalidStateError` | 422 |
| `BusinessRuleViolationError` | 422 |
| `UseCaseException` (y subclases) | 422 o 409 |
| `InfrastructureException` | 500 |

Nunca se propaga un stack trace al cliente.

## Logging

### Python — structlog

Ikctl usa `structlog` como librería de logging. La configuración vive en
`shared/infrastructure/logger.py`.

```python
from app.v1.shared.infrastructure.logger import get_logger

logger = get_logger(__name__)

# Uso correcto: evento + pares clave-valor ( estilo key=value, no extra={} )
logger.info("server_registered", user_id=user_id, server_id=server.id, server_name=server.name)
logger.warning("server_health_check_failed", server_id=server.id, error=str(exc))
logger.error("pipeline_execution_failed", execution_id=exec_id, error=str(exc), exc_info=True)
```

- **Nivel mínimo en producción:** `INFO`.
- **Nivel en desarrollo:** `DEBUG`.
- **Formato:** JSON estructurado en producción ( vía `JSONRenderer`), texto legible en desarrollo ( vía `ConsoleRenderer`).
- **Contexto por request:** `bind_context(request_id=..., user_id=...)` al inicio del request, `clear_context()` al final. Se usa en middleware.
- El logger **nunca** se instancia en `domain/` ni `application/`. Solo en `infrastructure/` y `presentation/`.
- No usar `print()` en ningún caso.
- Se usa `get_logger(__name__)` ( de `shared.infrastructure.logger`), no `logging.getLogger(__name__)` ni `structlog.get_logger()` directamente.

## Comentarios

Por defecto **no** se escriben. Solo se permiten cuando explican un *por qué*
no obvio (p. ej. workaround documentado, invariante sutil). Los nombres deben
hacer el resto.

Las docstrings son la excepción: cada módulo, clase y método público tiene una
docstring de una línea en español describiendo su propósito. Los métodos de
test también llevan docstring.