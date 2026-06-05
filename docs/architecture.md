# Arquitectura — ikctl

> Este documento define el estándar arquitectónico de ikctl. Los agentes revisores
> evalúan código contra este archivo. Si no está aquí, no es un requisito.
> Las herramientas concretas viven en `tech_stack.md`.
> Las convenciones de código viven en `conventions.md`.

## Estilo arquitectónico: Clean Architecture modular

El sistema se organiza en **módulos** bajo `app/v1/`, cada uno con **cuatro capas
concéntricas**. La regla de dependencia es estricta: las capas internas nunca
importan las externas.

```
app/v1/
├── shared/          ← Kernel compartido (DomainException, DomainEvent, EventBus, DB)
├── auth/            ← Módulo de autenticación y autorización
├── servers/         ← Servidores, credenciales y grupos
├── kits/            ← Repositorios Git y kits de configuración
├── operations/      ← Ejecución de operaciones SSH en servidores remotos
└── pipelines/       ← Orquestación de operaciones (N kits × M servidores)
```

### Capas dentro de cada módulo

```
┌──────────────────────────────────────────────────────────────┐
│  Presentation                                                 │
│  routes.py · schemas.py · deps.py · exception_handlers.py     │  ← FastAPI
│  ┌──────────────────────────────────────────────────────────┐ │
│  │  Application                                              │ │
│  │  commands/ · queries/ · tasks/ · handlers/               │ │  ← Casos de uso
│  │  interfaces/ (ports) · dtos/ · exceptions.py              │ │
│  │  ┌────────────────────────────────────────────────────┐  │ │
│  │  │  Domain                                             │  │ │  ← Entidades, VOs, reglas
│  │  │  entities/ · value_objects/ · exceptions/ · events/ │  │ │
│  │  └────────────────────────────────────────────────────┘  │ │
│  └──────────────────────────────────────────────────────────┘ │
│  Infrastructure                                               │
│  repositories/ · persistence/ · adapters/ · exceptions.py     │  ← SQLAlchemy, SSH, Git
└──────────────────────────────────────────────────────────────┘
```

| Capa | Qué contiene | Puede importar |
|------|--------------|----------------|
| `domain/` | Entidades (`Server`, `Operation`, `Pipeline`), value objects, excepciones de dominio, eventos de dominio | Nada externo (solo `shared.domain` y el propio módulo) |
| `application/` | Commands, queries, tasks, handlers, DTOs, puertos (ABC) y excepciones de aplicación | `domain/`, `shared.domain`, `shared.application.interfaces` |
| `infrastructure/` | Repositories (SQLAlchemy), adapters (cross-module, SSH, Git), persistence models | `domain/`, `application/` |
| `presentation/` | Routers FastAPI, schemas Pydantic, deps, exception handlers | `application/`, `infrastructure/` (solo para wiring en `deps.py`) |

## Principios

1. **Regla de dependencia.** El dominio no sabe que existe FastAPI, SQLAlchemy
   ni `structlog`. Si una entidad de dominio importa una librería externa,
   es un defecto de arquitectura.

2. **Errores explícitos.** Las funciones que pueden fallar lanzan excepciones
   nombradas del dominio (heredan de `DomainException`), no devuelven `None`.
   La capa de presentación las captura y transforma en respuestas HTTP.

3. **Inmutabilidad en el dominio.** Las entidades de dominio son
   `@dataclass(frozen=True)`. Modificar = crear una nueva instancia con
   `dataclasses.replace()`.

4. **El logger vive en infraestructura.** La capa de dominio y aplicación
   nunca instancian un logger directamente. Si necesitan registrar algo,
   lanzan un evento de dominio o devuelven un resultado que la capa superior
   loguea.

5. **Atomicidad en escrituras críticas.** Toda operación que modifica estado
   (crear servidor, lanzar pipeline, ejecutar operación) debe ser transaccional.
   Nunca dejar la base de datos en estado inconsistente.

6. **CQRS.** Los casos de uso se dividen en **commands** (escritura, mutan
   estado, publican eventos) y **queries** (solo lectura, no publican eventos).
   Un caso de uso = una clase con un método `execute()`.

7. **Un módulo por contexto.** Cada módulo (`servers`, `kits`, `operations`,
   `pipelines`, `auth`) es un bounded context independiente. Se comunican
   entre sí mediante puertos locales y adaptadores, nunca por importación
   directa de application/infrastructure de otro módulo (ver sección
   "Comunicación cross-module").

## Shared Kernel

`app/v1/shared/` contiene código compartido por todos los módulos. Es estable
y minimal — solo abstracciones que los módulos necesitan para inter-operar.

```
shared/
├── domain/
│   ├── exceptions.py        ← DomainException, ValidationError, EntityNotFoundError…
│   └── events.py             ← DomainEvent (base para todos los eventos de dominio)
├── application/
│   └── interfaces/
│       └── event_bus.py      ← EventBus (ABC), EventHandler (ABC)
└── infrastructure/
    ├── database.py           ← create_engine, create_session_factory, get_db_session
    ├── event_bus.py           ← InMemoryEventBus (implementación)
    ├── cache.py               ← create_valkey_client, close_valkey_client
    ├── logger.py              ← Configuración de logging (JsonFormatter)
    └── exceptions.py          ← Excepciones de infraestructura compartidas
```

**Reglas del Shared Kernel:**
- `shared.domain` solo define tipos base (`DomainException`, `DomainEvent`).
  Nunca contiene lógica de negocio específica de un módulo.
- `shared.application.interfaces` define puertos compartidos (`EventBus`).
- `shared.infrastructure` contiene wiring técnico (DB, cache, logging).
  Los módulos importan de aquí **solo en la capa infrastructure**, nunca en
  domain o application.

## Domain Events

Los eventos de dominio permiten que los módulos reaccionen a hechos ocurridos
sin acoplamiento directo.

### Flujo

1. Un **command** ejecuta lógica de negocio y produce un evento:
   ```python
   event = ServerRegistered.create(server_id=server.id, user_id=user_id, ...)
   await self._event_bus.publish(event)
   ```

2. Un **handler** en `application/handlers/` reacciona al evento:
   ```python
   # servers/application/handlers/remove_server_from_groups.py
   class RemoveServerFromGroups(EventHandler):
       async def handle(self, event: DomainEvent) -> None:
           # lógica de reacción
   ```

3. El **EventBus** se inyecta como puerto (`EventBus` ABC) y se implementa
   en `shared.infrastructure.event_bus.InMemoryEventBus`. El wiring se hace
   en `main.py`.

### Catálogo por módulo

| Módulo | Eventos |
|--------|---------|
| servers | `ServerRegistered`, `ServerUpdated`, `ServerDeleted`, `ServerStatusChanged`, `CredentialCreated`, `CredentialUpdated`, `CredentialDeleted`, `GroupCreated`, `GroupUpdated`, `GroupDeleted` |
| kits | `RepositoryRegistered`, `RepositorySynced`, `RepositoryDeleted`, `KitDiscovered` |
| operations | `OperationLaunched`, `OperationCompleted`, `OperationFailed`, `OperationCancelled` |
| pipelines | `PipelineExecutionCancelled` |
| auth | `UserRegistered`, `EmailVerified`, `PasswordChanged`, `TwoFaEnabled`, `TwoFaDisabled`, `UserLoggedIn` |

## CQRS

Los casos de uso se organizan siguiendo el patrón CQRS (Command Query
Responsibility Segregation):

### Commands (`application/commands/`)

- Mutan estado. Devuelven un DTO o `None`.
- Publican eventos de dominio vía `EventBus`.
- Ejemplo: `RegisterServer`, `CreateCredential`, `LaunchPipeline`.

```python
class RegisterServer:
    def __init__(self, server_repository, credential_repository, event_bus):
        self._server_repo = server_repository
        self._credential_repo = credential_repository
        self._event_bus = event_bus

    async def execute(self, user_id, name, host, ...) -> ServerResult:
        server = Server(id=str(uuid4()), ...)
        await self._server_repo.save(server)
        event = ServerRegistered.create(...)
        await self._event_bus.publish(event)
        return ServerResult.from_entity(server)
```

### Queries (`application/queries/`)

- Solo lectura. No mutan estado ni publican eventos.
- Ejemplo: `GetServer`, `ListServers`, `GetPipelineExecutionDetail`.

```python
class GetServer:
    def __init__(self, server_repository):
        self._server_repo = server_repository

    async def execute(self, user_id, server_id) -> ServerResult:
        server = await self._server_repo.find_by_id(server_id, user_id)
        if server is None:
            raise ServerNotFoundError(server_id)
        return ServerResult.from_entity(server)
```

### Tasks (`application/tasks/`)

- Orquestación asíncrona (background tasks). Se ejecutan fuera del request
  HTTP, creando sus propias sesiones de DB.
- Ejemplo: `ExecuteOperation`, `ExecutePipelineOperations`, `RestoreBackupTask`.

### Handlers (`application/handlers/`)

- Reaccionan a eventos de dominio. Se suscriben al `EventBus`.
- Ejemplo: `RemoveServerFromGroups` (se suscribe a `ServerDeleted`).

## Comunicación cross-module

Los módulos se comunican entre sí mediante **inversión de dependencia**:
cada módulo define sus propios **puertos locales** en `application/interfaces/`
y los implementa como **adaptadores** en `infrastructure/adapters/`.

### Patrón

```
pipelines/application/interfaces/
├── kit_repository.py           ← ABC (puerto local)
├── server_repository.py        ← ABC (puerto local)
├── operation_repository.py     ← ABC (puerto local)
└── operation_launcher.py       ← ABC (puerto local)

pipelines/infrastructure/adapters/
├── kit_read_adapter.py         ← Implementación que delega a SQLAlchemyKitRepository
├── server_read_adapter.py      ← Implementación que delega a SQLAlchemyServerRepository
├── operation_read_adapter.py   ← Implementación que delega a SQLAlchemyOperationRepository
└── operation_launcher_adapter.py ← Implementación que envuelve LaunchOperation
```

El módulo consumidor **nunca** importa la implementación concreta de otro
módulo. Solo importa su propio puerto (ABC). El wiring se hace en
`main.py` (Composition Root).

### Composition Root

`main.py` es el único punto donde se conoce la implementación concreta de
cada puerto. Allí se cablean todas las dependencias:

- **Singletons** (creados una vez): `Settings`, `EventBus`, `GitPythonClient`,
  `PyJWTProvider`, `AiosmtplibEmailService`, `ValkeyRateLimiter`.
- **Scoped por request** (via FastAPI `Depends()`): `AsyncSession`,
  repositories, use cases, adapters.
- **Background task closures**: `_execute_operation_fn`,
  `_execute_pipeline_fn` — crean sus propias sesiones porque se ejecutan
  fuera del request scope.

```python
# main.py — ejemplo simplificado del wiring para pipelines
operation_launcher = OperationLauncherAdapter(
    launch_operation=LaunchOperation(
        operation_repository=SQLAlchemyOperationRepository(session),
        server_repository=ServerReadAdapter(session),
        kit_repository=KitReadAdapter(session),
        task_queue=None,         # No re-encola dentro de background task
        execute_fn=_execute_operation_fn,
        commit_fn=_commit_session,
        event_bus=event_bus,
    )
)
```

### Background Tasks y commit_fn

Las background tasks (`ExecuteOperation`, `ExecutePipelineOperations`)
se ejecutan fuera del request HTTP. Para manejar las sesiones de DB:

1. Crean su propia `AsyncSession` desde `_session_factory`.
2. Reciben un `commit_fn` inyectado que hace `session.commit()` antes de
   cada iteración de polling. Esto es necesario para que MySQL/MariaDB
   (con REPEATABLE READ) vea los cambios realizados por otras sesiones
   en las operaciones individuales.

```python
async def _commit_session():
    await session.commit()
```

## DTOs

Los Data Transfer Objects (`application/dtos/`) son la interfaz entre la capa
de aplicación y la de presentación. Son `@dataclass(frozen=True)` y contienen
solo datos primitivos — nunca entidades de dominio.

```python
@dataclass(frozen=True)
class ServerResult:
    id: str
    name: str
    host: str | None
    status: str
    ...
```

Los routers de presentación convierten DTOs a respuestas Pydantic, y los
schemas de entrada (`CreateServerRequest`, `UpdateServerRequest`) se
convierten a parámetros primitivos que se pasan a los use cases.

## Flujo de datos — Registro de servidor

```bash
Usuario (cliente HTTP)
   │  POST /api/v1/servers  (JSON)
   ▼
presentation/routes_servers.py
   │  valida schema Pydantic (CreateServerRequest)
   │  extrae user_id de request.state (AuthenticationMiddleware)
   ▼
presentation/deps.py
   │  inyecta RegisterServer use case vía FastAPI Depends()
   ▼
application/commands/register_server.py
   │  construye entidad Server con value objects (ServerType, ServerStatus)
   │  valida reglas de dominio (servidor local sin SSH, credenciales...)
   │  persiste vía ServerRepository port (ABC)
   │  publica evento ServerRegistered vía EventBus port (ABC)
   ▼
infrastructure/repositories/server_repository.py (SQLAlchemy)
   │  INSERT en tabla servers
   ▼
infrastructure/persistence/models.py
   │  Modelo SQLAlchemy ServerModel
   ▼
MariaDB
```

## Flujo de datos — Ejecución de pipeline (background task)

```bash
Usuario (cliente HTTP)
   │  POST /api/v1/pipelines/{id}/executions
   ▼
presentation/routes.py
   │  LaunchPipeline use case
   │  crea PipelineExecution(status=pending)
   │  persiste y encola background task
   ▼
BackgroundTask (main.py closure)
   │  crea su propia AsyncSession
   │  construye ExecutePipelineOperations con commit_fn
   ▼
application/tasks/execute_pipeline_operations.py
   │  expande targets (servers directos + groups)
   │  para cada (kit, server): OperationLauncherAdapter.launch()
   │  polling cada 5s con commit_fn entre iteraciones
   │  marca execution como finished/failed
   ▼
operations/application/commands/launch_operation.py
   │  crea Operation entity
   │  persiste vía OperationRepository
   │  delega a SSHKitExecutor (adapter) para ejecución remota
```

## Estructura de carpetas

```bash
ikctl/
├── main.py                          ← Composition Root + FastAPI app factory
├── alembic/                         ← Migraciones DB
│   └── versions/
├── app/
│   ├── config/
│   │   └── settings.py              ← Configuración (env vars, secrets)
│   └── v1/
│       ├── shared/                   ← Kernel compartido
│       │   ├── domain/
│       │   │   ├── exceptions.py     ← DomainException, ValidationError, EntityNotFoundError…
│       │   │   └── events.py         ← DomainEvent (base class)
│       │   ├── application/
│       │   │   └── interfaces/
│       │   │       └── event_bus.py  ← EventBus ABC, EventHandler ABC
│       │   └── infrastructure/
│       │       ├── database.py       ← create_engine, session_factory, get_db_session
│       │       ├── event_bus.py      ← InMemoryEventBus (implementación)
│       │       ├── cache.py          ← Valkey client factory
│       │       ├── logger.py        ← JsonFormatter config
│       │       └── exceptions.py     ← InfrastructureError
│       │
│       ├── auth/                     ← Módulo de autenticación
│       │   ├── domain/
│       │   │   ├── entities/         ← User, RefreshToken, VerificationToken, PasswordHistory
│       │   │   ├── value_objects/    ← Email, Password, JwtToken
│       │   │   ├── exceptions/       ← UserNotFoundError, InvalidEmailError, InvalidPasswordError…
│       │   │   └── events/           ← UserRegistered, EmailVerified, PasswordChanged…
│       │   ├── application/
│       │   │   ├── commands/         ← RegisterUser, AuthenticateUser, ChangePassword…
│       │   │   ├── queries/          ← GetUserProfile, VerifyAccessToken…
│       │   │   ├── interfaces/       ← UserRepository, JwtProvider, EmailService, TotpProvider…
│       │   │   ├── dtos/             ← RegistrationResult, AuthenticationResult, TokenPair…
│       │   │   └── exceptions.py
│       │   └── infrastructure/
│       │       ├── repositories/     ← SQLAlchemyUserRepository, SQLAlchemyRefreshTokenRepository…
│       │       ├── persistence/      ← Models (UserModel, RefreshTokenModel…)
│       │       ├── adapters/         ← PyJWTProvider, AiosmtplibEmailService, PyOTPTOTPProvider…
│       │       ├── services/         ← ValkeyLoginAttemptTracker, ValkeyRateLimiter
│       │       └── presentation/     ← routes.py, schemas.py, deps.py, exception_handlers.py, middlewares.py
│       │
│       ├── servers/                  ← Módulo de servidores (REFERENCIA)
│       │   ├── domain/
│       │   │   ├── entities/         ← Server, Credential, Group
│       │   │   ├── value_objects/    ← ServerType, ServerStatus, CredentialType
│       │   │   ├── exceptions/       ← ServerNotFoundError, CredentialNotFoundError, GroupNotFoundError…
│       │   │   └── events/           ← ServerRegistered, ServerUpdated, ServerDeleted…
│       │   ├── application/
│       │   │   ├── commands/         ← RegisterServer, UpdateServer, DeleteServer, CreateGroup…
│       │   │   ├── queries/          ← GetServer, ListServers, CheckServerHealth…
│       │   │   ├── handlers/         ← RemoveServerFromGroups
│       │   │   ├── interfaces/       ← ServerRepository, CredentialRepository, GroupRepository, Connection, ConnectionFactory
│       │   │   ├── dtos/             ← ServerResult, ServerListResult, CredentialResult…
│       │   │   └── exceptions.py
│       │   └── infrastructure/
│       │       ├── repositories/     ← SQLAlchemyServerRepository, SQLAlchemyCredentialRepository…
│       │       ├── persistence/      ← Models (ServerModel, CredentialModel, GroupModel)
│       │       ├── adapters/         ← SSHConnection, LocalConnection, ConnectionFactory
│       │       └── presentation/     ← routes_servers.py, routes_credentials.py, routes_groups.py, schemas.py, deps.py, exception_handlers.py, rate_limit_middleware.py
│       │
│       ├── kits/                     ← Módulo de kits
│       │   ├── domain/
│       │   │   ├── entities/         ← Kit, Repository
│       │   │   ├── value_objects/    ← KitManifest, RepositoryIndex, SyncStatus
│       │   │   ├── exceptions/       ← KitNotFoundError, RepositoryNotFoundError…
│       │   │   └── events/           ← KitDiscovered, RepositorySynced, RepositoryDeleted…
│       │   ├── application/
│       │   │   ├── commands/         ← RegisterRepository, SyncRepository, DeleteRepository…
│       │   │   ├── queries/          ← GetKit, ListKits, ListRepositories…
│       │   │   ├── interfaces/       ← KitRepository, RepositoryRepository, GitClient
│       │   │   ├── dtos/             ← KitResult, RepositoryResult…
│       │   │   └── exceptions.py
│       │   └── infrastructure/
│       │       ├── repositories/     ← SQLAlchemyKitRepository, SQLAlchemyRepositoryRepository
│       │       ├── persistence/      ← Models
│       │       ├── adapters/         ← GitPythonClient, KitReadAdapter (cross-module)
│       │       └── presentation/     ← routes.py, schemas.py, deps.py, exception_handlers.py
│       │
│       ├── operations/               ← Módulo de operaciones
│       │   ├── domain/
│       │   │   ├── entities/         ← Operation
│       │   │   ├── value_objects/    ← OperationStatus
│       │   │   ├── exceptions/       ← OperationNotFoundError, InvalidOperationStateError…
│       │   │   └── events/           ← OperationLaunched, OperationCompleted, OperationFailed…
│       │   ├── application/
│       │   │   ├── commands/         ← LaunchOperation, CancelOperation, RetryOperation…
│       │   │   ├── queries/          ← GetOperation, ListOperations
│       │   │   ├── tasks/            ← ExecuteOperation, RestoreBackupTask
│       │   │   ├── interfaces/       ← OperationRepository, RemoteKitExecutor, TaskQueue, FileCacheRepository…
│       │   │   ├── dtos/             ← OperationResult, OperationListResult
│       │   │   └── exceptions.py
│       │   └── infrastructure/
│       │       ├── repositories/     ← SQLAlchemyOperationRepository, SQLAlchemyFileCacheRepository
│       │       ├── persistence/      ← Models
│       │       ├── adapters/         ← SSHKitExecutor, ARQTaskQueue, FastAPITaskQueue, ServerReadAdapter (cross-module)…
│       │       └── presentation/     ← routes.py, schemas.py, deps.py, exception_handlers.py
│       │
│       └── pipelines/                ← Módulo de pipelines
│           ├── domain/
│           │   ├── entities/         ← Pipeline, PipelineExecution
│           │   ├── value_objects/    ← PipelineTarget, PipelineKitConfig, PipelineStatus
│           │   ├── exceptions/       ← PipelineNotFoundError, PipelineInProgressError…
│           │   └── events/           ← PipelineExecutionCancelled
│           ├── application/
│           │   ├── commands/         ← CreatePipeline, UpdatePipeline, DeletePipeline, LaunchPipeline
│           │   ├── queries/          ← GetPipeline, ListPipelines, GetPipelineExecutions…
│           │   ├── tasks/            ← ExecutePipelineOperations
│           │   ├── interfaces/       ← PipelineRepository, PipelineExecutionRepository, OperationLauncher…
│           │   ├── dtos/             ← PipelineResult, PipelineExecutionResult…
│           │   └── exceptions.py
│           └── infrastructure/
│               ├── repositories/     ← SQLAlchemyPipelineRepository, SQLAlchemyPipelineExecutionRepository
│               ├── persistence/      ← Models
│               ├── adapters/         ← OperationLauncherAdapter, ServerReadAdapter (cross-module), KitReadAdapter (cross-module)…
│               └── presentation/     ← routes.py, schemas.py, deps.py, exception_handlers.py
│
├── tests/
│   └── v1/
│       ├── conftest.py               ← Fixtures compartidas (AsyncSession, cliente HTTP)
│       ├── shared/
│       │   ├── test_domain/          ← Tests de DomainEvent, DomainException
│       │   └── test_infrastructure/  ← Tests de InMemoryEventBus, database
│       ├── auth/
│       │   ├── test_domain/          ← Tests de entidades y VOs de auth
│       │   ├── test_use_cases/       ← Tests de commands y queries
│       │   ├── test_infrastructure/  ← Tests de repositories y adapters
│       │   └── test_presentation/    ← Tests de endpoints (HTTP)
│       ├── servers/
│       │   ├── test_domain/          ← Tests de Server, Credential, Group, VOs
│       │   ├── test_use_cases/       ← Tests de commands y queries
│       │   ├── test_infrastructure/  ← Tests de repositories y adapters
│       │   └── test_presentation/    ← Tests de endpoints HTTP
│       ├── kits/
│       │   ├── test_domain/
│       │   ├── test_use_cases/
│       │   ├── test_infrastructure/
│       │   └── test_presentation/
│       ├── operations/
│       │   ├── test_domain/
│       │   ├── test_use_cases/
│       │   ├── test_infrastructure/
│       │   └── test_presentation/
│       └── pipelines/
│           ├── test_domain/
│           ├── test_use_cases/
│           ├── test_infrastructure/
│           └── test_presentation/
├── docs/
├── specs/
├── progress/
├── feature_list.json
├── AGENTS.md
└── init.sh
```

### Reglas sobre la estructura

- **`application/interfaces/`** define puertos (ABCs) que `infrastructure/` implementa.
  Es el mecanismo de inversión de dependencia que aísla el dominio de
  SQLAlchemy, SSH y el sistema de ficheros.
- **`infrastructure/adapters/`** contiene adaptadores cross-module. Cada módulo
  define sus propios puertos en `application/interfaces/` y los implementa en
  `infrastructure/adapters/`, delegando al repositorio concreto del módulo
  original. El wiring se hace en `main.py`.
- **`infrastructure/persistence/models.py`** contiene los modelos SQLAlchemy.
  Son detalle de infraestructura — las entidades de dominio nunca los referencian.
- **`main.py`** es el Composition Root. Singletons se crean al arranque,
  repositories y use cases se construyen per-request vía FastAPI `Depends()`,
  y background task closures crean sus propias sesiones.
- **`v1/`** en los routers desde el inicio. Versionar la API no tiene coste
  ahora y evita migraciones dolorosas después.
- Los tests replican la estructura del módulo:
  `tests/v1/{module}/test_domain|test_use_cases|test_infrastructure|test_presentation/`.
- **Domain events** se publican desde commands y se consumen en
  `application/handlers/`. El `EventBus` se inyecta como puerto ABC.

## Qué NO hacer

- No importar SQLAlchemy, `structlog` ni FastAPI desde `domain/`.
- No poner lógica de negocio en los routers de FastAPI ni en los schemas
  Pydantic. Los routers solo validan entrada, llaman al use case y
  transforman el DTO en respuesta HTTP.
- No usar `print()` para errores. Usa el logger de infraestructura y los
  códigos de estado HTTP apropiados.
- No mezclar casos de uso en un mismo servicio. Un caso de uso = una clase
  con un método `execute()`.
- No importar directamente `application/` o `infrastructure/` de otro
  módulo. Usar siempre un puerto local (`application/interfaces/`) y un
  adaptador (`infrastructure/adapters/`) con wiring en `main.py`.
- No instanciar un logger en `domain/` ni `application/`. El logging es
  responsabilidad de `infrastructure/` y `presentation/`.