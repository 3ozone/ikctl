# Estructura de Carpetas - Clean Architecture

## Estructura de un Módulo

```bash
app/v1/auth/
├── domain/                      # Capa Core (sin dependencias externas)
│   ├── entities.py             # User, RefreshToken, VerificationToken
│   ├── value_objects.py        # Email, Password, JWTToken
│   └── exceptions.py           # DomainException, InvalidEmailError
│
├── application/                 # Capa de Casos de Uso
│   ├── exceptions.py           # UseCaseException, UnauthorizedOperationError
│   ├── dtos/                   # DTOs agnósticos (dataclasses)
│   │   └── auth_dtos.py        # AuthenticationResult, UserProfile, TokenPair
│   ├── interfaces/             # Ports (ABC) - Dependency Inversion
│   │   ├── repositories.py     # IUserRepository, IRefreshTokenRepository
│   │   └── services.py         # IEmailService, IJWTProvider, ITOTPProvider
│   └── use_cases/              # Casos de uso (implementan lógica de aplicación)
│       ├── register_user.py
│       ├── authenticate_user.py
│       └── refresh_access_token.py
│
└── infrastructure/              # Capa de Implementación (Adapters)
    ├── exceptions.py           # InfrastructureException, DatabaseConnectionError
    ├── persistence/            # Implementaciones de repositories
    │   ├── user_repository.py          # UserRepository implements IUserRepository
    │   ├── refresh_token_repository.py
    │   └── verification_token_repository.py
    │
    ├── adapters/               # Servicios externos (NO persistencia)
    │   ├── jwt_provider.py     # JWTProvider implements IJWTProvider
    │   ├── email_service.py    # EmailService implements IEmailService
    │   ├── totp_provider.py    # TOTPProvider implements ITOTPProvider
    │   └── github_oauth.py     # GitHubOAuth client
    │
    └── presentation/           # Capa de entrada (Primary Adapters)
        ├── routers/            # FastAPI endpoints
        │   ├── auth_router.py  # /register, /login, /logout
        │   └── user_router.py  # /users/me
        ├── schemas.py          # DTOs Pydantic (Request/Response para HTTP)
        ├── middlewares.py      # Auth, logging, CORS
        └── dependencies.py     # Inyección de dependencias FastAPI
```

## Responsabilidades por Capa

### Domain (Capa Core)

- **Sin dependencias** de otras capas o frameworks
- **Entities**: Lógica de negocio, invariantes
- **Value Objects**: Objetos inmutables con validaciones
- **Exceptions**: Errores de dominio

### Application (Casos de Uso)

- **DTOs**: Comunicación entre capas (dataclasses simples)
- **Interfaces (Ports)**: Abstracciones de repositories/services (ABC)
- **Use Cases**: Orquestación de lógica de aplicación
- Depende de: `domain/`
- **NO** depende de: `infrastructure/`

### Infrastructure (Implementaciones)

- **Persistence**: Implementa repositories (MariaDB, Valkey)
- **Adapters**: Implementa servicios externos (SMTP, OAuth, JWT)
- **Presentation**: Punto de entrada HTTP/CLI
- Depende de: `domain/`, `application/`
- Implementa las interfaces de `application/interfaces/`

## Reglas de Dependencia

```bash
presentation/ ──→ use_cases/ ──→ domain/
                      ↓
                  interfaces/
                      ↑
     persistence/ ───┘
     adapters/ ──────┘
```

**Principio**: Las flechas apuntan hacia adentro. Domain no conoce nada externo.

## Ejemplos de Flujo

**Registro de usuario (HTTP → Use Case → DB):**

```bash
1. presentation/routers/auth_router.py
   ↓ Recibe RegisterRequest (Pydantic)
   ↓ Llama use case con primitivos
2. application/use_cases/register_user.py
   ↓ Crea Entity User
   ↓ Llama IUserRepository.save()
3. infrastructure/persistence/user_repository.py
   ↓ Guarda en MariaDB
   ↓ Retorna Entity User
4. application/use_cases/register_user.py
   ↓ Retorna UserProfile (DTO)
5. presentation/routers/auth_router.py
   ↓ Convierte a UserResponse (Pydantic)
   ↓ Retorna JSON
```

## Módulo Shared (Código Compartido)

El módulo `shared/` contiene código reutilizable entre módulos. **NO sigue la estructura completa de capas**.

```bash
app/v1/shared/
├── domain/                      # Abstracciones de dominio compartidas
│   ├── events.py               # DomainEvent (base class para eventos)
│   ├── value_objects.py        # Value Objects genéricos (no específicos negocio)
│   └── exceptions.py           # Exception base classes (Exception)
│
└── infrastructure/              # Infraestructura compartida
    ├── event_bus.py            # EventBus InMemory (interface + impl)
    ├── logger.py               # Logger estructurado configurado
    ├── database.py             # Database session/connection factory
    └── cache.py                # Valkey client wrapper
```

### ¿Qué va en shared/?

**SÍ (código genérico):**

- Event system (DomainEvent, EventBus)
- Value Objects sin reglas de negocio específicas (UUID, Timestamp)
- Logger configurado
- Database/Cache clients
- Utilidades generales (date helpers, validators genéricos)

**NO (código con negocio):**

- Entities específicas de módulo (User, Server) → van en auth/, servers/
- Use Cases → siempre en módulos específicos
- Repositories → siempre en módulos específicos
- Value Objects con reglas de negocio (Email, Password) → dominio del módulo

### Regla de Oro

Si el código tiene **lógica de negocio específica** → módulo específico (auth, servers).  
Si es **infraestructura reutilizable** o **abstracción sin negocio** → shared/.

## Nomenclatura

- **Interfaces**: Prefijo `I` (IUserRepository, IEmailService)
- **Implementaciones**: Sin prefijo (UserRepository implements IUserRepository)
- **DTOs aplicación**: Sufijo claro (AuthenticationResult, UserProfile)
- **DTOs HTTP**: Sufijo Request/Response (RegisterRequest, UserResponse)
- **Entities**: Nombres de dominio (User, RefreshToken)
- **Value Objects**: Nombres descriptivos (Email, Password)

## Tests

```bash
tests/v1/auth/
├── test_domain/            # Unit tests (entities, value objects)
├── test_use_cases/         # Unit tests (use cases con mocks)
├── test_persistence/       # Integration tests (DB real)
├── test_adapters/          # Integration tests (servicios externos)
└── test_presentation/      # E2E tests (endpoints FastAPI)
```
