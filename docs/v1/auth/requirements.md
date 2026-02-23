# Requisitos del Módulo Auth

## Requisitos Funcionales

1. **RF-01**: Registro de usuarios con nombre, email y contraseña
2. **RF-02**: Verificación de email tras registro (envío de token por email)
3. **RF-03**: Login con email y contraseña, retorna access token y refresh token
4. **RF-04**: Login con GitHub OAuth2
5. **RF-05**: Refrescar access token usando refresh token válido
6. **RF-06**: Recuperación de contraseña (solicitar reset, enviar link por email)
7. **RF-07**: Restablecer contraseña con token válido
8. **RF-08**: Obtener perfil del usuario autenticado
9. **RF-09**: Actualizar nombre del usuario autenticado
10. **RF-10**: Cambiar contraseña del usuario autenticado
11. **RF-11**: Activar/desactivar 2FA (TOTP)
12. **RF-12**: Login con 2FA (código TOTP)
13. **RF-13**: Logout (invalidar refresh token)

## Requisitos No Funcionales

1. **RNF-01**: Contraseñas hasheadas con bcrypt (costo 12)
2. **RNF-02**: Contraseñas complejas: mínimo 8 caracteres, al menos 1 mayúscula, 1 minúscula, 1 número
3. **RNF-03**: Access token JWT firmado con HS256, expiración 30 minutos
4. **RNF-04**: Refresh token JWT con expiración 7 días, almacenado en DB
5. **RNF-05**: Validación de formato de email
6. **RNF-06**: OAuth2 Password Flow para autenticación
7. **RNF-07**: Endpoints protegidos requieren Bearer token
8. **RNF-08**: Bloqueo temporal tras 5 intentos fallidos de login (15 minutos)
9. **RNF-09**: Rate limiting en endpoint de login: máximo 10 peticiones/minuto por IP
10. **RNF-10**: Refresh tokens revocables (logout invalida el token)
11. **RNF-11**: Mensajes de error genéricos en login (no revelar si email o contraseña son incorrectos)
12. **RNF-12**: Mensaje genérico en registro si email ya existe (evitar enumeración de usuarios)
13. **RNF-13**: Validaciones siempre retornan mensajes sin información sensible del sistema
14. **RNF-14**: Token de verificación de email expira en 24 horas
15. **RNF-15**: Token de reset de contraseña expira en 1 hora
16. **RNF-16**: CORS configurado para permitir acceso desde frontend
17. **RNF-17**: Auditoría: logging de eventos de seguridad (login, logout, cambios de contraseña)
18. **RNF-18**: 2FA usando TOTP (compatible con Google Authenticator, Authy)
19. **RNF-19**: OAuth2 con GitHub usando Authorization Code Flow
20. **RNF-20**: Timestamps en UTC para consistencia global
21. **RNF-21**: Refresh token almacenado en HttpOnly cookie (seguro contra XSS)
22. **RNF-22**: Cookies con flags Secure, SameSite=Strict, HttpOnly
23. **RNF-23**: Access token en respuesta JSON (para header Authorization)
24. **RNF-24**: Cumplimiento GDPR (protección de datos, derecho al olvido, consentimiento explícito para tratamiento de datos)
25. **RNF-25**: Latencia endpoints auth (login, register) < 100ms percentil 99 (p99)
26. **RNF-26**: Latencia refresh token < 50ms percentil 99 (p99)
27. **RNF-27**: Disponibilidad módulo auth 99.9% uptime mensual
28. **RNF-28**: Throughput mínimo 100 req/s por endpoint (login, register, refresh)
29. **RNF-29**: Tasa de éxito operaciones auth > 99.5% (excluye errores usuario: contraseña incorrecta, email inválido)
30. **RNF-30**: Tiempo respuesta operaciones DB < 50ms percentil 95 (p95)

## Reglas de Negocio

1. **RN-01**: Un email solo puede estar asociado a una cuenta activa
2. **RN-02**: Un usuario debe verificar su email para poder usar funciones que requieran identidad validada
3. **RN-03**: Un refresh token solo puede usarse una vez, generando uno nuevo en cada refresh (rotación automática)
4. **RN-04**: Un usuario bloqueado por intentos fallidos no puede autenticarse durante el período de bloqueo (15 minutos)
5. **RN-05**: Un token de verificación de email expira tras 24 horas desde su emisión
6. **RN-06**: Un token de reset de contraseña expira tras 1 hora desde su emisión y solo puede usarse una vez
7. **RN-07**: Un usuario no puede reutilizar sus últimas 3 contraseñas
8. **RN-08**: Un usuario puede tener máximo 5 sesiones activas simultáneas (refresh tokens válidos)
9. **RN-09**: El 2FA es opcional, pero una vez activado debe verificarse en cada login
10. **RN-10**: Un refresh token revocado (logout) no puede usarse para generar nuevos access tokens
11. **RN-11**: Un access token no puede ser revocado manualmente (stateless JWT), expira automáticamente en 30 minutos
12. **RN-12**: Los usuarios OAuth (GitHub) no tienen contraseña local hasta que la establezcan explícitamente

## Endpoints

### Autenticación

- `POST /api/v1/register` - Crear cuenta
- `POST /api/v1/verify-email` - Verificar email con token
- `POST /api/v1/resend-verification` - Reenviar email de verificación
- `POST /api/v1/login` - Autenticar usuario (retorna access + refresh token)
- `POST /api/v1/login/github` - Iniciar OAuth con GitHub
- `GET /api/v1/login/github/callback` - Callback OAuth GitHub
- `POST /api/v1/refresh` - Refrescar access token
- `POST /api/v1/logout` - Cerrar sesión (invalidar refresh token)

### Recuperación de contraseña

- `POST /api/v1/password/forgot` - Solicitar reset de contraseña
- `POST /api/v1/password/reset` - Restablecer contraseña con token

### Usuario autenticado

- `GET /api/v1/users/me` - Obtener perfil (protegido)
- `PUT /api/v1/users/me` - Actualizar nombre (protegido)
- `PUT /api/v1/users/me/password` - Cambiar contraseña (protegido)

### 2FA

- `POST /api/v1/users/me/2fa/enable` - Activar 2FA (retorna QR code)
- `POST /api/v1/users/me/2fa/verify` - Verificar código 2FA para activar
- `POST /api/v1/users/me/2fa/disable` - Desactivar 2FA
- `POST /api/v1/login/2fa` - Completar login con código 2FA
