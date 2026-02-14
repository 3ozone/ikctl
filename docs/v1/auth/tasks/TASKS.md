# Tareas del Módulo Auth v1.0.0

## Fase 1: Entidades y Value Objects (Domain Layer)

- [x] **T-01**: Entity `User` con campos (id, name, email, password_hash, created_at, updated_at) - 4 tests
- [x] **T-02**: Value Object `Email` con validación - 6 tests
- [x] **T-03**: Value Object `Password` con validación de complejidad - 8 tests
- [x] **T-04**: Value Object `JWT Token` (access, refresh, payload) - 7 tests
- [x] **T-05**: Entity `RefreshToken` (token, user_id, expires_at) - 6 tests
- [x] **T-06**: Entity `VerificationToken` (token, user_id, type, expires_at) - 6 tests
- [x] **T-07**: Domain Exceptions (InvalidEmail, PasswordTooWeak, UserNotFound, etc.) - Completas
  
  **FASE 1 COMPLETADA: 37 tests GREEN ✅**

## Fase 2: Use Cases (Application Layer)

- [ ] **T-08**: Use Case `HashPassword(password)` - bcrypt con costo 12
- [ ] **T-09**: Use Case `VerifyPassword(plain, hashed)` - Validar contraseña
- [ ] **T-10**: Use Case `RegisterUser(name, email, password)` - Crear usuario
- [ ] **T-11**: Use Case `VerifyEmail(token)` - Verificar email con token
- [ ] **T-12**: Use Case `AuthenticateUser(email, password)` - Login básico
- [ ] **T-13**: Use Case `CreateTokens(user)` - Generar JWT access + refresh
- [ ] **T-14**: Use Case `RefreshAccessToken(refresh_token)` - Refrescar token
- [ ] **T-15**: Use Case `RevokeRefreshToken(token)` - Logout
- [ ] **T-16**: Use Case `ForgotPassword(email)` - Solicitar reset
- [ ] **T-17**: Use Case `ResetPassword(token, new_password)` - Restablecer contraseña
- [ ] **T-18**: Use Case `ChangePassword(user, current_pass, new_pass)` - Cambiar contraseña
- [ ] **T-19**: Use Case `GetUserProfile(user_id)` - Obtener datos usuario
- [ ] **T-20**: Use Case `UpdateUserProfile(user, name)` - Actualizar nombre
- [ ] **T-21**: Use Case `Enable2FA(user)` - Generar secret TOTP
- [ ] **T-22**: Use Case `Verify2FA(user, code)` - Verificar código TOTP
- [ ] **T-23**: Use Case `Disable2FA(user)` - Desactivar 2FA
- [ ] **T-24**: Use Case `AuthenticateWithGitHub(code)` - OAuth GitHub

## Fase 3: Infrastructure (Repositories y Adapters)

- [ ] **T-25**: Repository Adapter `UserRepository` (save, find_by_email, find_by_id)
- [ ] **T-26**: Repository Adapter `RefreshTokenRepository` (save, find_by_token, delete)
- [ ] **T-27**: Repository Adapter `VerificationTokenRepository` (save, find_by_token, delete)
- [ ] **T-28**: Adapter `JWTTokenProvider` - Generar y decodificar JWT
- [ ] **T-29**: Adapter `TOTPProvider` - Generar y validar códigos TOTP
- [ ] **T-30**: Adapter `EmailService` - Enviar emails (verificación, reset, etc.)
- [ ] **T-31**: Adapter `GitHubOAuth` - Integración con GitHub OAuth2
- [ ] **T-32**: Service `RateLimiter` - Limitar intentos de login
- [ ] **T-33**: Service `LoginAttemptTracker` - Bloqueo temporal tras 5 intentos

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

## Fase 5: Tests (TDD)

- [ ] **T-52**: Tests unitarios para Value Objects
- [ ] **T-53**: Tests para Use Cases (casos de éxito y error)
- [ ] **T-54**: Tests de seguridad (XSS, CSRF, injection)
- [ ] **T-55**: Tests de integración con FastAPI
- [ ] **T-56**: Tests de rate limiting y bloqueo temporal
- [ ] **T-57**: Cobertura mínima 80% del código

## Fase 6: Documentación y Ajustes

- [ ] **T-58**: Documentación técnica interna (cómo funciona)
- [ ] **T-59**: Guía de usuario (cómo usar la API)
- [ ] **T-60**: Validación de requisitos vs implementación
- [ ] **T-61**: Review y refactoring de código
- [ ] **T-62**: Optimización y mejoras de rendimiento

## Dependencias de Tareas

```
T-01,T-02,T-03,T-04 → T-08,T-09 → T-10,T-12 → T-34,T-37
T-05,T-06,T-07 → T-14,T-15,T-21,T-22
T-13 → T-41,T-42
T-16,T-17 → T-43,T-44
T-28,T-29 → T-13,T-24
T-32,T-33 → T-37
T-52,T-53,T-54 → T-55 → T-56
```

## Estadísticas

- **Total de tareas**: 62
- **Fases**: 6
- **Duración estimada**: 2-3 semanas (con desarrollo paralelo)
