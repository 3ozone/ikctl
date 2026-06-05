# Tech Stack — Qué usamos y por qué

> Este fichero cataloga las herramientas elegidas. Responde al *¿qué?* y al
> *¿por qué?*. El *¿cómo se usa en el código?* vive en `conventions.md`.
> El *¿en qué capa vive?* vive en `architecture.md`.

---

## Backend

| Herramienta | Versión | Rol | Justificación |
|-------------|---------|-----|---------------|
| **Python** | 3.13+ | Lenguaje | Tipado mejorado (`PEP 695`, `str \| None`), `asyncio` maduro, ecosistema amplio. |
| **FastAPI** | 0.115+ | Framework web | Tipado estricto con Pydantic, OpenAPI automático, async nativo, inyección de dependencias vía `Depends()`. |
| **SQLAlchemy** | 2.0+ | ORM | Mapeo relacional asíncrono (`AsyncSession`, `select()` style), compatible con MariaDB y SQLite (tests). |
| **Alembic** | 1.13+ | Migraciones | Control de versiones del esquema de base de datos. Autogenerate desde modelos SQLAlchemy. |
| **Pydantic** | 2.9+ | Validación | Schemas de request/response en presentation layer. Validación automática, `from_attributes=True` para mapeo desde modelos. |
| **aiomysql** | 0.2+ | Driver DB | Driver asíncrono para MariaDB/MySQL en producción. |
| **aiosqlite** | 0.20+ | Driver DB (tests) | Driver asíncrono SQLite para tests en memoria — rápido, sin MariaDB requerido. |
| **structlog** | 24.4+ | Logging | Logging estructurado con JSON en producción y ConsoleRenderer en desarrollo. Contexto por request vía `bind_context()`. |
| **python-jose** | 3.3+ | JWT | Creación y verificación de tokens JWT (HS256). |
| **passlib + bcrypt** | 1.7+ / 4.1+ | Hashing de passwords | Hash y verificación de passwords con bcrypt. |
| **pyotp** | 2.9+ | 2FA TOTP | Generación y verificación de códigos TOTP para autenticación de dos factores. |
| **aiosmtplib** | 3.0+ | Email asíncrono | Envío de emails (verificación, reset de password) vía SMTP asíncrono. |
| **asyncssh** | 2.18+ | SSH | Ejecución remota de kits en servidores vía SSH. |
| **redis** | 5.2+ | Cache / Rate limiting | Rate limiting de login, login attempt tracking. |
| **PyYAML** | 6.0+ | Parsing YAML | Parseo de manifests de kits (`.yaml`). |
| **Jinja2** | 3.1+ | Templates | Renderizado de templates de kits antes de enviar a servidores remotos. |
| **pytest** | 8.3+ | Tests | Framework de tests. Ver `verification.md`. |
| **pytest-asyncio** | 0.24+ | Tests asíncronos | Soporte `async def test_*` con `asyncio_mode = auto`. |
| **httpx** | 0.27+ | Tests HTTP | Cliente asíncrono para tests de endpoints (`AsyncClient`). |
| **pytest-cov** | 7.0+ | Coverage | Cobertura de tests. |
| **Ruff** | 0.4+ | Linting + formato | Reemplaza flake8 + isort + black. Velocidad 10-100× mayor. |

## Infrastructure

| Herramienta | Versión | Rol | Justificación |
|-------------|---------|-----|---------------|
| **Docker** | — | Contenedores | Entorno reproducible para backend y MariaDB. |
| **Docker Compose** | — | Orquestación local | Un solo `docker compose up` levanta MariaDB + Adminer para desarrollo. |
| **MariaDB** | 11.x | Base de datos | Modelo relacional para entidades (servers, kits, operations, pipelines, users). REPEATABLE READ por defecto. |
| **Valkey (Redis)** | 5.2+ | Rate limiting + intentos de login | `ValkeyRateLimiter` y `ValkeyLoginAttemptTracker` en el módulo auth. Cliente compatible con Redis. |
| **Uvicorn** | 0.31+ | ASGI server | Servidor ASGI para FastAPI. |

## Production concerns

| Aspecto | Decisión | Notas |
|---------|----------|-------|
| **Autenticación** | JWT propio (HS256) | Access token + refresh token con rotación. 2FA TOTP opcional. OAuth2 con GitHub disponible. |
| **Rate limiting** | Redis (Valkey) | `ValkeyRateLimiter` y `ValkeyLoginAttemptTracker` en `auth/infrastructure/services/`. |
| **Encriptación de credenciales** | Fernet (cryptography) | Credenciales SSH encriptadas en reposo con `ENCRYPTION_KEY`. |
| **Logging** | structlog + JSON | JSON en producción, texto legible en desarrollo. Contexto por request con correlation_id. |
| **Migraciones** | Alembic | Autogenerate desde modelos SQLAlchemy. Ejecutar antes de arrancar la app. |
| **Tests DB** | SQLite in-memory | Tests usan `aiosqlite` con SQLite en memoria. Producción usa MariaDB vía `aiomysql`. |