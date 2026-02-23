# 🔐 Workflow de Autenticación - ikctl

## Resumen Ejecutivo

El módulo de autenticación de ikctl implementa un sistema securo basado en:
- **JWT Access Token** (30 min): Para acceso a recursos
- **Refresh Token** (7 días): Para obtener nuevos access tokens
- **Email Verification**: Validación de email con tokens de expiración
- **Password Reset**: Solicitud y restablecimiento de contraseña seguro
- **2FA TOTP**: Autenticación de dos factores (planeado)
- **OAuth2 GitHub**: Integración social (planeado)

---

## 📊 Flujos de Autenticación

### 1. Registro de Usuario (Sign Up)

```mermaid
flowchart TD
    Start([Usuario Ingresa Datos]) --> Input["<b>RegisterUser</b><br/>name, email, password"]
    Input --> Validate["Validar:<br/>- Email VO<br/>- Password VO"]
    Validate --> Hash["<b>HashPassword</b><br/>bcrypt cost: 12"]
    Hash --> CreateUser["<b>CreateUser Entity</b><br/>id, name, email, password_hash"]
    CreateUser --> Save["<b>UserRepository.save</b><br/>Persistir en BD"]
    Save --> GenToken["<b>GenerateVerificationToken</b><br/>type: email_verification<br/>expires: 24h"]
    GenToken --> SendEmail["📧 Enviar email<br/>con link de verificación"]
    SendEmail --> End([✅ Usuario Creado<br/>Pendiente verificación])
    
    style Start fill:#e1f5ff
    style End fill:#c8e6c9
    style Input fill:#fff3e0
    style Validate fill:#fff3e0
    style Hash fill:#f3e5f5
    style CreateUser fill:#f3e5f5
    style Save fill:#e8f5e9
    style GenToken fill:#fff3e0
    style SendEmail fill:#ffe0b2
```

### 2. Verificación de Email

```mermaid
flowchart TD
    Start([Usuario Hace Click<br/>en Link Email]) --> CheckToken["<b>VerifyEmail</b><br/>Validar token"]
    CheckToken --> IsValid{Token<br/>válido?}
    IsValid -->|Sí| MarkVerified["Marcar usuario<br/>como verificado"]
    IsValid -->|No| TokenError["❌ Token expirado<br/>o inválido"]
    MarkVerified --> End([✅ Email Verificado])
    TokenError --> End2([❌ Error])
    
    style Start fill:#e1f5ff
    style End fill:#c8e6c9
    style TokenError fill:#ffcdd2
    style CheckToken fill:#fff3e0
    style MarkVerified fill:#c8e6c9
```

### 3. Login (Autenticación)

```mermaid
flowchart TD
    Start([Usuario Ingresa<br/>email + password]) --> Input["<b>AuthenticateUser</b><br/>email, plaintext_password"]
    Input --> FindUser["<b>UserRepository.get_by_email</b><br/>Buscar usuario"]
    FindUser --> Found{Usuario<br/>encontrado?}
    Found -->|No| Error1["❌ InvalidUserError"]
    Found -->|Sí| VerifyPass["<b>VerifyPassword</b><br/>bcrypt.checkpw"]
    VerifyPass --> CorrectPass{Password<br/>correcto?}
    CorrectPass -->|No| Error2["❌ InvalidUserError"]
    CorrectPass -->|Sí| CreateTokens["<b>CreateTokens</b><br/>Generate JWT + Refresh"]
    CreateTokens --> AccessToken["🔑 Access Token<br/>exp: 30 min"]
    CreateTokens --> RefreshToken["🔄 Refresh Token<br/>exp: 7 días"]
    AccessToken --> SaveRefresh["<b>RefreshTokenRepository.save</b><br/>Persistir token"]
    RefreshToken --> SaveRefresh
    SaveRefresh --> Return["Retornar:<br/>access_token,<br/>refresh_token"]
    Return --> End([✅ Autenticado])
    Error1 --> End2([❌ Error])
    Error2 --> End2
    
    style Start fill:#e1f5ff
    style End fill:#c8e6c9
    style Error1 fill:#ffcdd2
    style Error2 fill:#ffcdd2
    style Input fill:#fff3e0
    style CreateTokens fill:#f3e5f5
    style AccessToken fill:#c8e6c9
    style RefreshToken fill:#c8e6c9
```

### 4. Acceso a Recursos (Token Verification)

```mermaid
flowchart TD
    Start([Request a Endpoint<br/>Protegido]) --> Header["Bearer Token<br/>en Authorization Header"]
    Header --> Extract["Extraer token"]
    Extract --> Verify["<b>VerifyAccessToken</b><br/>JWT decode"]
    Verify --> Valid{Token<br/>válido?}
    Valid -->|No| Error["❌ InvalidJWTTokenError<br/>401 Unauthorized"]
    Valid -->|Sí| CheckExp{Token<br/>expirado?}
    CheckExp -->|Sí| Error2["❌ Token expirado<br/>401 Unauthorized"]
    CheckExp -->|No| Authenticated["✅ Payload decodificado"]
    Authenticated --> GetUser["<b>UserRepository.get_by_id</b><br/>Obtener usuario"]
    GetUser --> AppLogic["🚀 Ejecutar lógica<br/>del endpoint"]
    AppLogic --> End([✅ Respuesta OK])
    Error --> End2([❌ Error])
    Error2 --> End2
    
    style Start fill:#e1f5ff
    style End fill:#c8e6c9
    style Error fill:#ffcdd2
    style Error2 fill:#ffcdd2
    style Verify fill:#f3e5f5
    style Authenticated fill:#c8e6c9
    style AppLogic fill:#bbdefb
```

### 5. Refresh Token (Renovar Access Token)

```mermaid
flowchart TD
    Start([Refresh Token<br/>Expirado?]) --> CheckExp{Access Token<br/>expirado?}
    CheckExp -->|No| End1([✅ Usar token actual])
    CheckExp -->|Sí| CallRefresh["<b>RefreshAccessToken</b><br/>refresh_token"]
    CallRefresh --> FindToken["<b>RefreshTokenRepository.find_by_token</b><br/>Validar token"]
    FindToken --> Found{Token<br/>encontrado?}
    Found -->|No| Error["❌ InvalidRefreshTokenError"]
    Found -->|Sí| CheckExpir{Token<br/>expirado?}
    CheckExpir -->|Sí| Error2["❌ Token expirado<br/>RefreshTokenRepository.revoke"]
    CheckExpir -->|No| NewAccess["Generate nuevo<br/>Access Token<br/>exp: 30 min"]
    NewAccess --> Return["Retornar:<br/>new_access_token"]
    Return --> End([✅ Token Renovado])
    Error --> End2([❌ Error])
    Error2 --> End2
    
    style Start fill:#e1f5ff
    style End fill:#c8e6c9
    style End1 fill:#c8e6c9
    style CallRefresh fill:#f3e5f5
    style NewAccess fill:#c8e6c9
    style Error fill:#ffcdd2
    style Error2 fill:#ffcdd2
```

### 6. Logout (Revoke Refresh Token)

```mermaid
flowchart TD
    Start([Usuario Solicita<br/>Logout]) --> Input["<b>RevokeRefreshToken</b><br/>refresh_token"]
    Input --> FindToken["<b>RefreshTokenRepository.find_by_token</b>"]
    FindToken --> Found{Token<br/>encontrado?}
    Found -->|No| Error["❌ InvalidRefreshTokenError"]
    Found -->|Sí| Revoke["Set token.expires_at<br/>= now"]
    Revoke --> Save["<b>RefreshTokenRepository.save</b><br/>Persistir cambio"]
    Save --> End([✅ Logout Exitoso])
    Error --> End2([❌ Error])
    
    style Start fill:#e1f5ff
    style End fill:#c8e6c9
    style Revoke fill:#ffcdd2
    style Input fill:#fff3e0
```

### 7. Password Reset (Olvida Contraseña)

```mermaid
flowchart TD
    Start([Usuario Solicita<br/>Reset Password]) --> Email["<b>RequestPasswordReset</b><br/>email"]
    Email --> FindUser["<b>UserRepository.get_by_email</b>"]
    FindUser --> Found{Usuario<br/>encontrado?}
    Found -->|No| Silent["🤫 Responden OK sin error<br/>por seguridad"]
    Found -->|Sí| GenToken["<b>GenerateVerificationToken</b><br/>type: password_reset<br/>expires: 24h"]
    GenToken --> SaveToken["<b>VerificationTokenRepository.save</b>"]
    SaveToken --> SendEmail["📧 Enviar email<br/>con link de reset"]
    SendEmail --> End([✅ Email Enviado])
    Silent --> End
    
    style Start fill:#e1f5ff
    style End fill:#c8e6c9
    style Email fill:#fff3e0
    style Silent fill:#ffe0b2
```

### 8. Cambiar Contraseña (Con Token Reset)

```mermaid
flowchart TD
    Start([Usuario Incluye<br/>Nuevo Password]) --> Input["<b>ResetPassword</b><br/>user, token, new_password"]
    Input --> FindToken["<b>VerificationTokenRepository.find_by_token</b>"]
    FindToken --> Found{Token<br/>encontrado?}
    Found -->|No| Error1["❌ InvalidVerificationTokenError"]
    Found -->|Sí| ValidateType["Validate:<br/>token_type === password_reset"]
    ValidateType --> TypeOk{Es tipo<br/>password_reset?}
    TypeOk -->|No| Error2["❌ InvalidVerificationTokenError"]
    TypeOk -->|Sí| CheckExp{Token<br/>expirado?}
    CheckExp -->|Sí| Error3["❌ InvalidVerificationTokenError"]
    CheckExp -->|No| HashNew["<b>HashPassword</b><br/>bcrypt new_password"]
    HashNew --> UpdateUser["Actualizar user:<br/>password_hash = new"]
    UpdateUser --> Save["<b>UserRepository.save</b>"]
    Save --> DeleteToken["<b>VerificationTokenRepository.delete</b><br/>Eliminar token usado"]
    DeleteToken --> End([✅ Contraseña Cambiada])
    Error1 --> End2([❌ Error])
    Error2 --> End2
    Error3 --> End2
    
    style Start fill:#e1f5ff
    style End fill:#c8e6c9
    style Error1 fill:#ffcdd2
    style Error2 fill:#ffcdd2
    style Error3 fill:#ffcdd2
    style Input fill:#fff3e0
    style HashNew fill:#f3e5f5
```

---

## 🏗️ Capas de Arquitectura

```mermaid
flowchart LR
    subgraph Domain["🔷 Domain Layer (Lógica de Negocio)"]
        VOs["Value Objects<br/>- Email<br/>- Password<br/>- JWTToken"]
        Entities["Entities<br/>- User<br/>- RefreshToken<br/>- VerificationToken"]
        Exceptions["Exceptions<br/>- InvalidEmailError<br/>- InvalidUserError<br/>- InvalidTokenError"]
    end
    
    subgraph App["🟩 Application Layer (Use Cases)"]
        UC1["HashPassword"]
        UC2["VerifyPassword"]
        UC3["AuthenticateUser"]
        UC4["CreateTokens"]
        UC5["VerifyAccessToken"]
        UC6["RefreshAccessToken"]
        UC7["RevokeRefreshToken"]
        UC8["RequestPasswordReset"]
        UC9["ResetPassword"]
        UC10["VerifyEmail"]
        UC11["GenerateVerificationToken"]
        UC12["RegisterUser"]
    end
    
    subgraph Infra["🟦 Infrastructure Layer"]
        Repos["Repositories<br/>- UserRepository<br/>- RefreshTokenRepository<br/>- VerificationTokenRepository"]
        Adapters["Adapters<br/>- JWTTokenProvider<br/>- EmailService<br/>- TOTPProvider"]
    end
    
    subgraph Pres["🟡 Presentation Layer"]
        Endpoints["FastAPI Endpoints<br/>- POST /register<br/>- POST /login<br/>- POST /logout<br/>- POST /refresh<br/>- POST /password/reset<br/>- GET /users/me"]
    end
    
    Domain --> App
    App --> Infra
    Infra --> Pres
    Pres --> Endpoints
    
    style Domain fill:#e3f2fd
    style App fill:#e8f5e9
    style Infra fill:#e0f2f1
    style Pres fill:#fff3e0
```

---

## 📦 Mapeo Use Cases → Endpoints

| Use Case | Endpoint | Method | Body |
|----------|----------|--------|------|
| `RegisterUser` | `/api/v1/register` | POST | `{name, email, password}` |
| `AuthenticateUser` + `CreateTokens` | `/api/v1/login` | POST | `{email, password}` |
| `VerifyAccessToken` | Middleware de todas las rutas protegidas | - | Header: `Authorization: Bearer <token>` |
| `RefreshAccessToken` | `/api/v1/refresh` | POST | `{refresh_token}` |
| `RevokeRefreshToken` | `/api/v1/logout` | POST | `{refresh_token}` |
| `RequestPasswordReset` | `/api/v1/password/forgot` | POST | `{email}` |
| `ResetPassword` | `/api/v1/password/reset` | POST | `{token, new_password}` |
| `VerifyEmail` | `/api/v1/verify-email` | POST | `{token}` |

---

## 🔒 Seguridad Implementada

- ✅ **Passwords**: bcrypt con costo 12 (~70ms por hash)
- ✅ **JWT**: HS256, SECRET_KEY en .env
- ✅ **Token Expiration**: Access (30min) + Refresh (7days)
- ✅ **Email Verification**: Tokens únicos con expiración 24h
- ✅ **Password Reset**: Tokens de un solo uso con validación de tipo
- ⏳ **2FA**: TOTP (planeado)
- ⏳ **Rate Limiting**: Por email/IP (planeado)
- ⏳ **OAuth2**: GitHub (planeado)

---

## 📈 Flujo General (Visión Integral)

```mermaid
flowchart TD
    A([Usuario]) -->|1. Registrarse| B[RegisterUser]
    B --> C{Email<br/>verificado?}
    C -->|No| D["VerifyEmail<br/>con token"]
    D --> E{Token<br/>válido?}
    E -->|Sí| F[✅ Email Verificado]
    F --> G([Usuario Verificado])
    
    G -->|2. Iniciar Sesión| H[AuthenticateUser]
    H --> I{Credenciales<br/>válidas?}
    I -->|No| J["❌ Error de Login"]
    I -->|Sí| K[CreateTokens]
    K --> L["JWT Access<br/>+ Refresh Token"]
    L --> M([Autenticado])
    
    M -->|3. Acceder a Recurso| N[Request a Endpoint]
    N --> O["Middleware:<br/>VerifyAccessToken"]
    O --> P{Token<br/>válido?}
    P -->|No| Q["401 Unauthorized"]
    P -->|Sí| R["🚀 Ejecutar endpoint"]
    R --> S([✅ Recurso Obtenido])
    
    M -->|4. Token Expirado?| T{Access Token<br/>expirado?}
    T -->|No| U([Seguir usando token])
    T -->|Sí| V[RefreshAccessToken]
    V --> W["Nuevo JWT Access<br/>30 min"]
    W --> M
    
    M -->|5. Cerrar Sesión| X[RevokeRefreshToken]
    X --> Y["❌ Token Revocado"]
    Y --> Z([Desautenticado])
    
    M -->|6. Olvidó Contraseña| AA[RequestPasswordReset]
    AA --> AB["📧 Link Reset"]
    AB --> AC[ResetPassword]
    AC --> AD["✅ Nueva Contraseña"]
    AD --> M
    
    style A fill:#e1f5ff
    style G fill:#c8e6c9
    style M fill:#c8e6c9
    style S fill:#c8e6c9
    style Z fill:#ffcdd2
```

---

## 🚀 Implementación Actual

### Tests Completados

**Fase 1 - Domain Layer**: ✅ 40 tests GREEN
- Value Objects (Email, Password, JWTToken): 21 tests
- Entities (User, RefreshToken, VerificationToken): 19 tests

**Fase 2 - Application Layer**: ✅ 28 tests GREEN
- 12 Use Cases con 2-3 tests cada uno

**Fase 3 - Infrastructure**: 🔄 3 tests GREEN (UserRepository)
- RefreshTokenRepository (próximo)
- VerificationTokenRepository (próximo)

**Fase 4 - Presentation**: ⏳ Pendiente
- FastAPI endpoints (17 endpoints planeados)

---

**Última actualización**: 2026
**Estado del módulo**: En desarrollo activo
**Metodología**: TDD (Test-Driven Development)
