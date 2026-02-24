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
    │   ├── repositories.py     # UserRepository, RefreshTokenRepository
    │   └── services.py         # EmailService, JWTProvider, TOTPProvider
│   └── use_cases/              # Casos de uso (implementan lógica de aplicación)
│       ├── register_user.py
│       ├── authenticate_user.py
│       └── refresh_access_token.py
│
└── infrastructure/              # Capa de Implementación (Adapters)
    ├── exceptions.py           # InfrastructureException, DatabaseConnectionError
    ├── persistence/            # Implementaciones de repositories
    │   ├── user_repository.py          # SQLAlchemyUserRepository implements UserRepository
    │   ├── refresh_token_repository.py # SQLAlchemyRefreshTokenRepository
    │   └── verification_token_repository.py
    │
    ├── adapters/               # Servicios externos (NO persistencia)
    │   ├── jwt_provider.py     # PyJWTProvider implements JWTProvider
    │   ├── email_service.py    # AiosmtplibEmailService implements EmailService
    │   ├── totp_provider.py    # PyOTPTOTPProvider implements TOTPProvider
    │   └── github_oauth.py     # HttpxGitHubOAuth implements GitHubOAuth
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
   ↓ Llama UserRepository.save()
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
│   ├── exceptions.py           # Excepciones base (DomainException, ValidationError,
│   │                           # EntityNotFoundError, EntityAlreadyExistsError,
│   │                           # InvalidStateError, BusinessRuleViolationError)
│   └── value_objects.py        # Value Objects genéricos (no específicos negocio)
│
└── infrastructure/              # Infraestructura compartida
    ├── event_bus.py            # EventBus InMemory (EventHandler ABC + EventBus impl)
    ├── exceptions.py           # Excepciones base infraestructura (InfrastructureException,
    │                           # DatabaseError, ExternalServiceError, CacheError,
    │                           # HTTPClientError, MessageBusError, ConfigurationError)
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

- **Interfaces (Puertos)**: Sin prefijo, nombre del dominio pythónico
  - `UserRepository`, `EmailService`, `JWTProvider`, `TOTPProvider`
  - Las interfaces se definen como ABC en `application/interfaces/`
  
- **Implementaciones (Adaptadores)**: Sufijo técnico específico
  - Repositories: `SQLAlchemyUserRepository`, `SQLAlchemyRefreshTokenRepository`
  - Adapters: `PyJWTProvider`, `AiosmtplibEmailService`, `PyOTPTOTPProvider`, `HttpxGitHubOAuth`
  - Pattern: `<TechStack><InterfaceName>` (ej: `Httpx` + `GitHubOAuth`)
  
- **DTOs aplicación**: Sufijo descriptivo claro
  - `AuthenticationResult`, `UserProfile`, `TokenPair`, `VerificationResult`
  
- **DTOs HTTP**: Sufijo Request/Response (Pydantic)
  - `RegisterRequest`, `UserResponse`, `LoginRequest`, `TokenResponse`
  
- **Entities**: Nombres de dominio sin prefijos/sufijos
  - `User`, `RefreshToken`, `VerificationToken`, `PasswordHistory`
  
- **Value Objects**: Nombres descriptivos del concepto
  - `Email`, `Password`, `JWTToken`
  
- **Excepciones**: Sufijo `Error`, jerarquía desde shared
  - Base: `DomainException`, `InfrastructureException` (en shared)
  - Específicas: `InvalidEmailError`, `UserNotFoundError`, `DatabaseConnectionError`

## Tests

```bash
tests/v1/
├── auth/
│   ├── test_domain/            # Unit tests (entities, value objects)
│   ├── test_use_cases/         # Unit tests (use cases con mocks)
│   ├── test_infrastructure/    # Integration tests (repositories, adapters, services)
│   │   ├── test_user_repository.py
│   │   ├── test_refresh_token_repository.py
│   │   ├── test_verification_token_repository.py
│   │   ├── test_password_history_repository.py
│   │   ├── test_jwt_provider.py
│   │   ├── test_totp_provider.py
│   │   ├── test_email_service.py
│   │   ├── test_github_oauth.py
│   │   ├── test_rate_limiter.py
│   │   └── test_login_attempt_tracker.py
│   └── test_presentation/      # E2E tests (endpoints FastAPI)
│
├── shared/
│   ├── test_domain/            # Unit tests (eventos, excepciones base)
│   │   └── test_events.py      # Tests DomainEvent (10 tests)
│   └── test_infrastructure/    # Integration tests (event bus, logger, database)
│       └── test_event_bus.py   # Tests EventBus InMemory (10 tests)
│
├── servers/
│   ├── test_domain/
│   ├── test_use_cases/
│   └── test_infrastructure/
│
├── operations/
│   ├── test_domain/
│   ├── test_use_cases/
│   └── test_infrastructure/
│
└── users/
    ├── test_domain/
    ├── test_use_cases/
    └── test_infrastructure/
```
