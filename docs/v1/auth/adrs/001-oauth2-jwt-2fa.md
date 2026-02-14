# ADR-001: Autenticación OAuth2 con JWT y 2FA

## Estado

Aceptado

## Contexto

Necesitamos un sistema de autenticación seguro, escalable y compatible con estándares modernos para gestionar acceso a servidores remotos.

## Decisión

### Autenticación Principal

- **JWT**: Access token (30 min) + Refresh token (7 días)
- **OAuth2 Password Flow**: Estándar para login email/password
- **OAuth2 GitHub**: Reducir fricción en onboarding

### Seguridad

- **bcrypt**: Hash de contraseñas (costo 12)
- **2FA TOTP**: Google Authenticator, Authy
- **Rate limiting**: 10 req/min en login
- **Bloqueo temporal**: 15 min tras 5 intentos fallidos
- **Mensajes genéricos**: Sin información sensible
- **Cookies HttpOnly**: Refresh token en cookie HttpOnly (protección XSS)
- **Cookie flags**: Secure, SameSite=Strict, HttpOnly
- **Access token**: En JSON para header Authorization (no en cookie)

### Funcionalidades

- Verificación de email (token 24h)
- Recuperación de contraseña (token 1h)
- Refresh tokens revocables en DB

## Consecuencias

### Positivas

- ✅ Estándar OAuth2, compatible con frameworks
- ✅ Seguridad robusta (JWT + 2FA + rate limiting)
- ✅ Escalable (stateless access token)
- ✅ UX mejorada (OAuth social login)

### Negativas

- ❌ Complejidad: gestión de múltiples tokens
- ❌ Dependencia de email (SMTP)
- ❌ Almacenamiento DB para refresh tokens y 2FA

## Alternativas Rechazadas

- **Sessions cookie**: No escalable, stateful
- **JWT sin refresh**: Riesgo si access token se compromete
- **SMS 2FA**: Coste y vulnerabilidad a SIM swapping
