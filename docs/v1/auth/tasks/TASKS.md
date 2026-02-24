# Tareas del Módulo Auth v1.0.0

## Fase 0: Migración a Clean Architecture (CRÍTICA)

**DEBE EJECUTARSE PRIMERO** - Restructurar código actual a la arquitectura documentada en ADR-007

- [x] **T-00.1**: Crear estructura `application/` (dtos/, interfaces/, exceptions.py, use_cases/) ✅
- [x] **T-00.2**: Mover contenido de `use_cases/` actual a `application/use_cases/` ✅
- [x] **T-00.3**: Crear `application/interfaces/` con ABCs (IUserRepository, IEmailService, IJWTProvider, ITOTPProvider, IGitHubOAuth, IPasswordHistoryRepository) ✅
- [x] **T-00.4**: Crear `application/dtos/` (AuthenticationResult, UserProfile, TokenPair, VerificationResult, etc.) ✅
- [x] **T-00.5**: Crear `application/exceptions.py` (UseCaseException, UnauthorizedOperationError, EmailAlreadyExistsError, etc.) ✅
- [x] **T-00.6**: Crear `infrastructure/exceptions.py` (InfrastructureException, DatabaseConnectionError, EmailServiceError, SSHConnectionError) ✅
- [x] **T-00.7**: Actualizar imports en todo el código (casos de uso, repositories, tests) para reflejar nueva estructura ✅

  **FASE 0 COMPLETADA: ✅ Clean Architecture implementada**

## Fase 1: Entidades y Value Objects (Domain Layer)

- [x] **T-01**: Entity `User` con campos (id, name, email, password_hash, created_at, updated_at, totp_secret, is_2fa_enabled) - 5 tests ✅
- [x] **T-02**: Value Object `Email` con validación - 6 tests
- [x] **T-03**: Value Object `Password` con validación de complejidad - 8 tests
- [x] **T-04**: Value Object `JWT Token` (access, refresh, payload) - 7 tests
- [x] **T-05**: Entity `RefreshToken` (token, user_id, expires_at) - 6 tests
- [x] **T-06**: Entity `VerificationToken` (token, user_id, type, expires_at) - 6 tests
- [x] **T-07**: Domain Exceptions (InvalidEmail, PasswordTooWeak, UserNotFound, etc.) - Completas
- [x] **T-07.1**: Entity `PasswordHistory` (user_id, password_hash, created_at) - RN-07: historial últimas 3 contraseñas - 6 tests ✅
  
  **FASE 1 COMPLETADA: 44 tests GREEN ✅**

## Fase 2: Use Cases (Application Layer)

- [x] **T-08**: Use Case `HashPassword(password)` - bcrypt con costo 12 - 3 tests
- [x] **T-09**: Use Case `VerifyPassword(plain, hashed)` - Validar contraseña - 3 tests
- [x] **T-10**: Use Case `RegisterUser(name, email, password)` - Crear usuario (RN-01: validar email único) - 3 tests
- [x] **T-11**: Use Case `VerifyEmail(token)` - Verificar email con token - 2 tests
- [x] **T-12**: Use Case `AuthenticateUser(email, password)` - Login básico (RN-09: verificar 2FA si activado) - 2 tests
- [x] **T-13**: Use Case `CreateTokens(user)` - Generar JWT access + refresh (RN-08: límite 5 sesiones simultáneas, RN-11: access token 30min) - 2 tests
- [x] **T-14**: Use Case `RefreshAccessToken(refresh_token)` - Refrescar token (RN-03: rotación automática, uso único) - 2 tests
- [x] **T-15**: Use Case `RevokeRefreshToken(token)` - Logout (RN-10: token revocado no reutilizable) - 2 tests
- [x] **T-16**: Use Case `GenerateVerificationToken(user_id, type)` - Generar tokens (RN-05: email 24h, RN-06: reset 1h) - 2 tests
- [x] **T-17**: Use Case `RequestPasswordReset(user)` - Solicitar reset - 2 tests
- [x] **T-18**: Use Case `ResetPassword(user, token, new_password)` - Restablecer contraseña (RN-06: token uso único) - 2 tests
- [x] **T-19**: Use Case `VerifyAccessToken(token)` - Decodificar y validar JWT - 2 tests
- [x] **T-20**: Use Case `ChangePassword(user, current_pass, new_pass)` - Cambiar contraseña (RN-07: no reutilizar últimas 3) - 4 tests ✅
- [x] **T-21**: Use Case `GetUserProfile(user_id)` - Obtener datos usuario - 2 tests ✅
- [x] **T-22**: Use Case `UpdateUserProfile(user_id, new_name)` - Actualizar nombre - 2 tests ✅
- [x] **T-23**: Use Case `Enable2FA(user_id)` - Generar secret TOTP (actualiza entity User con totp_secret, is_2fa_enabled) - 3 tests ✅
- [x] **T-24**: Use Case `Verify2FA(user_id, code)` - Verificar código TOTP (valida is_2fa_enabled, totp_secret) - 4 tests ✅
- [x] **T-25**: Use Case `Disable2FA(user_id)` - Desactivar 2FA (limpia totp_secret, is_2fa_enabled=False) - 2 tests ✅
- [x] **T-26**: Use Case `AuthenticateWithGitHub(code)` - OAuth GitHub (RN-12: sin contraseña local inicial, password_hash="OAUTH_NO_PASSWORD") - 3 tests ✅

  **FASE 2 COMPLETADA: 48 tests GREEN ✅ (19/19 use cases, todas las RN de use cases implementadas) 🎉**

## Fase 2.5: Refactorización de Nomenclatura (Clean Code)

**Aplicar convenciones de nombres para consistencia del código**

- [x] **T-27.1**: Renombrar interfaces (quitar prefijo "I"): ~~`IEmailService` → `EmailService`~~✅, ~~`IJWTProvider` → `JWTProvider`~~✅, ~~`ITOTPProvider` → `TOTPProvider`~~✅, ~~`IUserRepository` → `UserRepository`~~✅, ~~`IRefreshTokenRepository` → `RefreshTokenRepository`~~✅, ~~`IVerificationTokenRepository` → `VerificationTokenRepository`~~✅, ~~`IPasswordHistoryRepository` → `PasswordHistoryRepository`~~✅ (pendiente: `IGitHubOAuth`)
- [x] **T-27.2**: Renombrar implementaciones con sufijo técnico: ~~`UserRepositoryImpl` → `SQLAlchemyUserRepository`~~✅, ~~`RefreshTokenRepositoryImpl` → `SQLAlchemyRefreshTokenRepository`~~✅, ~~`VerificationTokenRepositoryImpl` → `SQLAlchemyVerificationTokenRepository`~~✅
- [x] **T-27.3**: Renombrar adapters con sufijo técnico: ~~`JWTProvider` → `PyJWTProvider`~~✅, ~~`TOTPProvider` → `PyOTPTOTPProvider`~~✅, ~~`EmailService` → `AiosmtplibEmailService`~~✅
- [x] **T-27.4**: Actualizar imports en todos los use cases (renombrado IPasswordHistoryRepository → PasswordHistoryRepository, imports limpios) ✅
- [x] **T-27.5**: Actualizar imports en todos los tests (verificado: todos correctos, sin imports obsoletos) ✅
- [x] **T-27.6**: Actualizar fixtures en `conftest.py` (SQLAlchemy repositories) ✅
- [x] **T-27.7**: Ejecutar suite completa de tests (130 tests GREEN) ✅
- [x] **T-27.8**: Actualizar AGENTS.md con convenciones formalizadas ✅

  **FASE 2.5 COMPLETADA: 8/8 tareas ✅ - Refactorización de nomenclatura finalizada. 11/11 clases renombradas (7 interfaces, 3 repositories, 1 pendiente: IGitHubOAuth se hará en T-31). 130 tests GREEN ✅**

## Fase 3: Infrastructure (Repositories y Adapters)

- [x] **T-25**: Repository Adapter `UserRepository` (save, find_by_email, find_by_id, update, delete) - 5 métodos - 5 tests ✅
- [x] **T-26**: Repository Adapter `RefreshTokenRepository` (save, find_by_token, delete, delete_by_user_id, count_by_user_id, find_by_user_id) - 6 métodos - 3 tests ✅
- [x] **T-27**: Repository Adapter `VerificationTokenRepository` (save, find_by_token, delete, delete_by_user_id) - 4 métodos - 4 tests ✅
- [x] **T-28**: Adapter `JWTTokenProvider` (create_access_token, create_refresh_token, decode_token, verify_token) - 4 métodos - 9 tests ✅
- [x] **T-29**: Adapter `TOTPProvider` (generate_secret, generate_qr_code, verify_code, get_provisioning_uri) - 4 métodos - 9 tests ✅
- [x] **T-30**: Adapter `EmailService` (send_verification_email, send_password_reset_email, send_password_changed_notification, send_2fa_enabled_notification) - 4 métodos - 8 tests ✅
- [ ] **T-31**: Adapter `GitHubOAuth` - Integración con GitHub OAuth2
- [ ] **T-32**: Service `RateLimiter` - Limitar intentos de login
- [ ] **T-33**: Service `LoginAttemptTracker` - Bloqueo temporal tras 5 intentos (RN-04: 15 minutos)
- [ ] **T-33.1**: Repository `PasswordHistoryRepository` (save, find_last_n_by_user) - RN-07

### Shared Module (Infraestructura Transversal)

- [ ] **T-34.1**: Implementar `shared/domain/events.py` (DomainEvent base class: event_id, correlation_id, version, occurred_at, metadata)
- [ ] **T-34.2**: Implementar `shared/infrastructure/event_bus.py` (EventBus InMemory sincrónico con publish/subscribe)
- [ ] **T-34.3**: Implementar `shared/infrastructure/logger.py` (structlog configurado con JSON output y context injection)
- [ ] **T-34.4**: Implementar `shared/infrastructure/database.py` (session factory con async support para SQLAlchemy)
- [ ] **T-34.5**: Implementar `shared/infrastructure/cache.py` (Valkey client wrapper con operaciones básicas)

### Database Migrations (Alembic)

- [ ] **T-34.6**: Alembic migration: tabla `users` con índices (email UNIQUE, created_at, is_verified)
- [ ] **T-34.7**: Alembic migration: tabla `refresh_tokens` con índices (token UNIQUE, user_id, expires_at)
- [ ] **T-34.8**: Alembic migration: tabla `verification_tokens` con índices (token UNIQUE, type, expires_at, user_id)
- [ ] **T-34.9**: Alembic migration: tabla `password_history` con índice compuesto (user_id, created_at DESC)

### Middleware & Exception Handlers

- [ ] **T-34.10**: Middleware `AuthenticationMiddleware` - Verificar Bearer token en endpoints protegidos
- [ ] **T-34.11**: Exception handlers FastAPI (DomainException → 400, UseCaseException → 422, InfrastructureException → 500)
- [ ] **T-34.12**: CORS middleware configuration (FastAPI CORSMiddleware con origins permitidos)

  **FASE 3 EN PROGRESO: 38 tests GREEN ✅ (6/22 tareas completas)**

## Fase 4: Presentation (FastAPI Endpoints)

- [ ] **T-34**: Endpoint `/api/v1/register` - POST
- [ ] **T-35**: Endpoint `/api/v1/verify-email` - POST
- [ ] **T-36**: Endpoint `/api/v1/resend-verification` - POST
- [ ] **T-37**: Endpoint `/api/v1/login` - POST
- [ ] **T-38**: Endpoint `/api/v1/login/github` - POST
- [ ] **T-39**: Endpoint `/api/v1/login/github/callback` - GET
- [ ] **T-40**: Endpoint `/api/v1/login/2fa` - POST
- [ ] **T-41**: Endpoint `/api/v1/refresh` - POST
- [ ] **T-42**: Endpoint `/api/v1/logout` - POST
- [ ] **T-43**: Endpoint `/api/v1/password/forgot` - POST
- [ ] **T-44**: Endpoint `/api/v1/password/reset` - POST
- [ ] **T-45**: Endpoint `/api/v1/users/me` - GET
- [ ] **T-46**: Endpoint `/api/v1/users/me` - PUT
- [ ] **T-47**: Endpoint `/api/v1/users/me/password` - PUT
- [ ] **T-48**: Endpoint `/api/v1/users/me/2fa/enable` - POST
- [ ] **T-49**: Endpoint `/api/v1/users/me/2fa/verify` - POST
- [ ] **T-50**: Endpoint `/api/v1/users/me/2fa/disable` - POST
- [ ] **T-51**: Schemas Pydantic para requests/responses
- [ ] **T-51.1**: Middleware `RequireEmailVerification` (RN-02: verificación email obligatoria para funciones críticas)

### Seguridad & Compliance

- [ ] **T-51.2**: Config HttpOnly cookies en T-41 (refresh token), T-42 (logout) con flags Secure, SameSite=Strict
- [ ] **T-51.3**: Response headers de seguridad (X-Content-Type-Options, X-Frame-Options, Strict-Transport-Security)
- [ ] **T-51.4**: Endpoint `DELETE /api/v1/users/me` - Derecho al olvido GDPR (borrado completo de datos)
- [ ] **T-51.5**: Endpoint `GET /api/v1/users/me/data` - Exportación de datos personales GDPR (formato JSON)

### Observabilidad

- [ ] **T-51.6**: Logging estructurado de eventos críticos (login success/fail, password change, 2FA enable/disable, token refresh)

  **FASE 4 PENDIENTE: 24 tareas totales**

## Fase 5: Tests (TDD)

- [ ] **T-52**: Tests unitarios para Value Objects
- [ ] **T-53**: Tests para Use Cases (casos de éxito y error)
- [ ] **T-54**: Tests de seguridad (XSS, CSRF, injection)
- [ ] **T-55**: Tests de integración con FastAPI
- [ ] **T-56**: Tests de rate limiting y bloqueo temporal
- [ ] **T-57**: Cobertura mínima 80% del código

### Performance & SLO Validation

- [ ] **T-57.1**: Benchmark tests auth endpoints (validar SLO: login <100ms p99, register <100ms p99, refresh <50ms p99)
- [ ] **T-57.2**: Load tests (throughput mínimo 100 req/s por endpoint con herramienta como Locust o k6)
- [ ] **T-57.3**: Tests de latencia DB (validar queries <50ms p95 con profiling SQLAlchemy)

### Contract Tests

- [ ] **T-57.4**: Contract tests para eventos de dominio (validar schemas: UserRegistered, UserDeleted, PasswordChanged)

  **FASE 5 PENDIENTE: 10 tareas totales**

---

## 📊 Resumen de Progreso

| Fase | Estado | Tests | Completitud |
|------|--------|-------|-------------|
| Fase 0 - Clean Architecture | 🔴 **PENDIENTE** | - | 0% - **CRÍTICA: bloquea todo** |
| Fase 1 - Domain Layer | ✅ **COMPLETADA** | 40 GREEN | 100% (1 tarea RN-07 pendiente) |
| Fase 2 - Application Layer | ✅ **COMPLETADA** | 28 GREEN | 100% (mejoras RN pendientes) |
| Fase 3 - Infrastructure | 🔄 **EN PROGRESO** | 3 GREEN | ~5% (22 tareas totales) |
| Fase 4 - Presentation | ⏳ **PENDIENTE** | - | 0% (24 tareas) |
| Fase 5 - Integration Tests | ⏳ **PENDIENTE** | - | 0% (10 tareas) |
| Fase 6 - Documentación | ⏳ **PENDIENTE** | - | 0% |

**TOTAL TESTS GREEN: 71 / 68 min requeridos ✅**

### Próximos Pasos

1. 🔴 **CRÍTICO**: Ejecutar FASE 0 (Migración Clean Architecture) - BLOQUEA TODO
2. ⏳ Implementar Shared Module (eventos, logger, DB, cache)
3. ⏳ Crear migrations Alembic (4 tablas)
4. ⏳ Completar Infrastructure (repositories, adapters, middleware)
5. ⏳ Crear endpoints FastAPI (Fase 4)
6. ⏳ Tests de integración y performance (Fase 5)

## Fase 6: Documentación y Ajustes

- [ ] **T-58**: Documentación técnica interna (cómo funciona)
- [ ] **T-59**: Guía de usuario (cómo usar la API)
- [ ] **T-60**: Validación de requisitos vs implementación
- [ ] **T-61**: Review y refactoring de código
- [ ] **T-62**: Optimización y mejoras de rendimiento

## Dependencias de Tareas

```mermaid
graph TD
    T00["Fase 0: Clean Architecture"] --> T01["Fase 1: Domain"]
    T01 --> T08["Fase 2: Use Cases"]
    T34_1["T-34.1-34.5: Shared Module"] --> T08
    T34_6["T-34.6-34.9: Migrations"] --> T25["Fase 3: Repositories"]
    T08 --> T25
    T25 --> T34["Fase 4: Endpoints"]
    T34_10["T-34.10-34.12: Middleware"] --> T34
    T34 --> T52["Fase 5: Tests"]
    T57_1["T-57.1-57.4: Performance Tests"] --> T62["Fase 6: Docs"]
```

**Dependencias críticas:**

- **T-00.X** → Todas las demás fases (BLOQUEA TODO)
- **T-34.1, T-34.2** → T-10, T-12 (eventos en use cases)
- **T-34.6-34.9** → T-25, T-26, T-27 (tablas para repositories)
- **T-34.10** → T-34-T-50 (middleware auth para endpoints protegidos)
- **T-28** → T-13, T-41 (JWT provider para tokens)
- **T-32, T-33** → T-37 (rate limiting en login)

## Estadísticas

- **Total de tareas**: 94 (65 originales + 29 nuevas para Clean Architecture, Shared, GDPR, Performance)
- **Fases**: 7 (añadida Fase 0 crítica)
- **Duración estimada**: 3-4 semanas (con desarrollo paralelo)
- **Tareas completadas**: 68/94 (72% de las existentes, pero solo tras Fase 0)
- **Tareas bloqueadas por Fase 0**: 94 (100%)

## Cobertura de Reglas de Negocio

| RN | Descripción | Tareas | Estado |
|----|-------------|--------|--------|
| RN-01 | Email único por cuenta | T-10 | ✅ Implementada |
| RN-02 | Verificación email obligatoria | T-51.1 | ⏳ Pendiente |
| RN-03 | Rotación refresh tokens | T-14 | ✅ Completar |
| RN-04 | Bloqueo temporal 15min | T-33 | ⏳ Pendiente |
| RN-05 | Token email expira 24h | T-16 | ✅ Implementada |
| RN-06 | Token reset 1h uso único | T-16, T-18 | ✅ Completar |
| RN-07 | No reutilizar últimas 3 contraseñas | T-07.1, T-20, T-33.1 | ⏳ Pendiente |
| RN-08 | Límite 5 sesiones simultáneas | T-13 | ✅ Completar |
| RN-09 | 2FA obligatorio si activado | T-12 | ✅ Completar |
| RN-10 | Refresh token revocado no reutilizable | T-15 | ✅ Implementada |
| RN-11 | Access token stateless 30min | T-13 | ✅ Implementada |
| RN-12 | OAuth sin contraseña local | T-26 | ⏳ Pendiente |

**Estado RN: 4 implementadas, 4 por completar, 4 pendientes**
