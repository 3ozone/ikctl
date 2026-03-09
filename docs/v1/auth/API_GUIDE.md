# Guía de uso de la API Auth v1

Base URL: `http://localhost:8000/api/v1/auth` (desarrollo) | `https://api.ikctl.com/api/v1/auth` (producción)

---

## Inicio rápido

El flujo mínimo para empezar a usar la API:

```bash
# 1. Regístrate
curl -s -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"name": "Juan Pérez", "email": "juan@example.com", "password": "SecurePass123!"}' | jq

# 2. Verifica tu email (usa el token recibido por email)
curl -s -X POST http://localhost:8000/api/v1/auth/verify-email \
  -H "Content-Type: application/json" \
  -d '{"token": "<token-del-email>"}' | jq

# 3. Haz login
curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "juan@example.com", "password": "SecurePass123!"}' | jq

# 4. Usa el access_token en requests autenticados
curl -s http://localhost:8000/api/v1/auth/users/me \
  -H "Authorization: Bearer <access_token>" | jq
```

---

## Registro y verificación

### Registrar usuario

```bash
curl -s -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Juan Pérez",
    "email": "juan@example.com",
    "password": "SecurePass123!"
  }' | jq
```

**Respuesta `201`:**
```json
{
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "Usuario registrado. Revisa tu email para verificar tu cuenta."
}
```

**Errores:**
| Código | Causa |
|--------|-------|
| `409` | El email ya está registrado |
| `422` | Datos inválidos (email malformado, contraseña débil) |

> **Requisitos de contraseña:** mínimo 8 caracteres, al menos 1 mayúscula, 1 minúscula y 1 número.

---

### Verificar email

```bash
curl -s -X POST http://localhost:8000/api/v1/auth/verify-email \
  -H "Content-Type: application/json" \
  -d '{"token": "abc123..."}' | jq
```

**Respuesta `200`:**
```json
{"message": "Email verificado correctamente."}
```

---

### Reenviar email de verificación

```bash
curl -s -X POST http://localhost:8000/api/v1/auth/resend-verification \
  -H "Content-Type: application/json" \
  -d '{"email": "juan@example.com"}' | jq
```

**Respuesta `200`:**
```json
{"message": "Email de verificación reenviado."}
```

---

## Login

### Login con email y contraseña

```bash
curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "juan@example.com", "password": "SecurePass123!"}' | jq
```

**Respuesta `200` (sin 2FA):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiJ9...",
  "token_type": "Bearer",
  "expires_in": 1800,
  "requires_2fa": false
}
```

**Respuesta `200` (con 2FA activado):**
```json
{
  "requires_2fa": true,
  "temp_token": "eyJhbGciOiJIUzI1NiJ9...",
  "access_token": "",
  "expires_in": 0
}
```

> Con 2FA: usa el `temp_token` en el endpoint `/login/2fa`.

**Errores:**
| Código | Causa |
|--------|-------|
| `401` | Email no registrado o contraseña incorrecta |
| `429` | Cuenta bloqueada temporalmente (>5 intentos fallidos, espera 15 min) |

---

### Login con 2FA

```bash
curl -s -X POST http://localhost:8000/api/v1/auth/login/2fa \
  -H "Content-Type: application/json" \
  -d '{"temp_token": "<temp_token>", "code": "123456"}' | jq
```

**Respuesta `200`:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiJ9...",
  "token_type": "Bearer",
  "expires_in": 1800
}
```

---

### Login con GitHub OAuth

```bash
# 1. Obtén la URL de autorización
curl -s http://localhost:8000/api/v1/auth/login/github | jq
# → {"authorization_url": "https://github.com/login/oauth/authorize?..."}

# 2. El usuario autoriza en GitHub y es redirigido con ?code=...&state=...
# 3. Intercambia el código por tokens
curl -s "http://localhost:8000/api/v1/auth/login/github/callback?code=<code>&state=<state>" | jq
```

---

## Gestión de tokens

### Refrescar el access token

El `access_token` expira en **30 minutos**. Usa el `refresh_token` para obtener uno nuevo:

```bash
curl -s -X POST http://localhost:8000/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "<refresh_token>"}' | jq
```

**Respuesta `200`:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiJ9...",
  "token_type": "Bearer",
  "expires_in": 1800
}
```

> El `refresh_token` se rota automáticamente — el anterior queda invalidado.

---

### Logout

```bash
curl -s -X POST http://localhost:8000/api/v1/auth/logout \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "<refresh_token>"}' | jq
```

**Respuesta `200`:**
```json
{"message": "Sesión cerrada correctamente."}
```

---

## Perfil de usuario

### Obtener perfil

```bash
curl -s http://localhost:8000/api/v1/auth/users/me \
  -H "Authorization: Bearer <access_token>" | jq
```

**Respuesta `200`:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Juan Pérez",
  "email": "juan@example.com",
  "is_verified": true,
  "is_2fa_enabled": false,
  "created_at": "2026-03-09T10:00:00Z"
}
```

---

### Actualizar nombre

```bash
curl -s -X PUT http://localhost:8000/api/v1/auth/users/me \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"name": "Juan García"}' | jq
```

---

### Exportar datos personales (GDPR)

```bash
curl -s http://localhost:8000/api/v1/auth/users/me/data \
  -H "Authorization: Bearer <access_token>" | jq
```

---

### Eliminar cuenta (GDPR)

```bash
curl -s -X DELETE http://localhost:8000/api/v1/auth/users/me \
  -H "Authorization: Bearer <access_token>"
```

**Respuesta `204`** — sin cuerpo. Todos los datos del usuario son eliminados permanentemente.

---

## Contraseña

### Cambiar contraseña

```bash
curl -s -X PUT http://localhost:8000/api/v1/auth/users/me/password \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "current_password": "SecurePass123!",
    "new_password": "NewSecurePass456!"
  }' | jq
```

> No puedes reutilizar ninguna de tus últimas 3 contraseñas (RN-07).

---

### Solicitar reset de contraseña

```bash
curl -s -X POST http://localhost:8000/api/v1/auth/password/forgot \
  -H "Content-Type: application/json" \
  -d '{"email": "juan@example.com"}' | jq
```

**Respuesta `200`:**
```json
{"message": "Si el email existe, recibirás un enlace de reset."}
```

> La respuesta es genérica para no revelar si el email está registrado.

---

### Restablecer contraseña

```bash
curl -s -X POST http://localhost:8000/api/v1/auth/password/reset \
  -H "Content-Type: application/json" \
  -d '{
    "token": "<token-del-email>",
    "new_password": "NewSecurePass456!"
  }' | jq
```

> El token de reset expira en **1 hora** y solo puede usarse una vez.

---

## Autenticación de dos factores (2FA)

### Activar 2FA

```bash
# 1. Iniciar activación — genera el QR
curl -s -X POST http://localhost:8000/api/v1/auth/users/me/2fa/enable \
  -H "Authorization: Bearer <access_token>" | jq
```

**Respuesta `200`:**
```json
{
  "secret": "JBSWY3DPEHPK3PXP",
  "qr_code_uri": "data:image/png;base64,...",
  "provisioning_uri": "otpauth://totp/ikctl:juan@example.com?secret=..."
}
```

```bash
# 2. Escanea el QR con Google Authenticator o Authy
# 3. Verificar el código para confirmar la activación
curl -s -X POST http://localhost:8000/api/v1/auth/users/me/2fa/verify \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"code": "123456"}' | jq
```

---

### Desactivar 2FA

```bash
curl -s -X POST http://localhost:8000/api/v1/auth/users/me/2fa/disable \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"code": "123456"}' | jq
```

---

## Errores comunes

| Código | Significado | Solución |
|--------|-------------|---------|
| `401` | Token inválido o expirado | Refresca el access token con `/refresh` |
| `403` | Sin permisos o email no verificado | Verifica tu email primero |
| `409` | Conflicto (email duplicado) | Usa otro email o inicia sesión |
| `422` | Datos de entrada inválidos | Revisa el cuerpo del request |
| `429` | Demasiados intentos | Espera 15 minutos |
| `503` | Error de infraestructura | Reintentar con backoff exponencial |

---

## Seguridad

- El `access_token` expira en **30 minutos** — guárdalo en memoria, no en localStorage.
- El `refresh_token` expira en **7 días** y se almacena en HttpOnly cookie automáticamente.
- Cada uso del `refresh_token` lo rota — el anterior queda invalidado inmediatamente.
- Tras **5 intentos fallidos** de login, la cuenta se bloquea **15 minutos**.
- Nunca envíes contraseñas en query params, solo en el cuerpo JSON (HTTPS obligatorio en producción).
