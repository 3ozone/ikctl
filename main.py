"""Entry point y Composition Root de la aplicación ikctl.

Lifetimes:
- Singleton: creados una vez al arranque (Settings, EventBus, adaptadores stateless).
- Scoped:    una instancia por request HTTP (AsyncSession, repositories, use cases
             que dependen de la sesión). Gestionados via FastAPI Depends().
"""
from datetime import datetime, timezone
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import Settings
from app.v1.auth.infrastructure.adapters.email_service import AiosmtplibEmailService
from app.v1.auth.infrastructure.adapters.github_oauth import HttpxGitHubOAuth
from app.v1.auth.infrastructure.adapters.jwt_provider import PyJWTProvider
from app.v1.auth.infrastructure.adapters.totp_provider import PyOTPTOTPProvider
from app.v1.auth.infrastructure.presentation.middlewares import AuthenticationMiddleware, SecurityHeadersMiddleware
from app.v1.auth.infrastructure.presentation.exception_handlers import register_exception_handlers
from app.v1.auth.infrastructure.repositories.password_history_repository import (
    SQLAlchemyPasswordHistoryRepository,
)
from app.v1.auth.infrastructure.repositories.refresh_token_repository import (
    SQLAlchemyRefreshTokenRepository,
)
from app.v1.auth.infrastructure.repositories.user_repository import SQLAlchemyUserRepository
from app.v1.auth.infrastructure.repositories.verification_token_repository import (
    SQLAlchemyVerificationTokenRepository,
)
from app.v1.auth.infrastructure.services.login_attempt_tracker import ValkeyLoginAttemptTracker
from app.v1.auth.infrastructure.services.rate_limiter import ValkeyRateLimiter
from app.v1.shared.infrastructure.event_bus import InMemoryEventBus
from app.v1.shared.infrastructure.database import (
    create_engine,
    create_session_factory,
    get_db_session,
)
from app.v1.shared.infrastructure.cache import create_valkey_client, close_valkey_client
from app.v1.auth.infrastructure.presentation.routes import router as auth_router

# ---------------------------------------------------------------------------
# Singleton: Settings
# ---------------------------------------------------------------------------
settings = Settings()

# ---------------------------------------------------------------------------
# Singleton: EventBus
# ---------------------------------------------------------------------------
event_bus = InMemoryEventBus()

# ---------------------------------------------------------------------------
# Singleton: adaptadores stateless
# ---------------------------------------------------------------------------
jwt_provider = PyJWTProvider(
    secret_key=settings.JWT_SECRET,
    algorithm=settings.JWT_ALGORITHM,
    access_token_expire_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
    refresh_token_expire_days=settings.REFRESH_TOKEN_EXPIRE_DAYS,
)

email_service = AiosmtplibEmailService(
    smtp_host=settings.SMTP_HOST,
    smtp_port=settings.SMTP_PORT,
    smtp_user=settings.SMTP_USER,
    smtp_password=settings.SMTP_PASSWORD,
    from_email=settings.SMTP_FROM_EMAIL,
    from_name=settings.SMTP_FROM_NAME,
    base_url=settings.APP_BASE_URL,
)

totp_provider = PyOTPTOTPProvider()

github_oauth = HttpxGitHubOAuth(
    client_id=settings.GITHUB_CLIENT_ID,
    client_secret=settings.GITHUB_CLIENT_SECRET,
    redirect_uri=settings.GITHUB_REDIRECT_URI,
)

# ---------------------------------------------------------------------------
# Singleton: Valkey-backed services
# ---------------------------------------------------------------------------
_valkey_client = create_valkey_client(settings.VALKEY_URL)
rate_limiter = ValkeyRateLimiter(valkey_client=_valkey_client)
login_attempt_tracker = ValkeyLoginAttemptTracker(valkey_client=_valkey_client)

# ---------------------------------------------------------------------------
# DB engine + session factory (Scoped per request)
# ---------------------------------------------------------------------------
_engine = create_engine(settings.DB_URL)
_session_factory = create_session_factory(_engine)


async def get_db_session_dep() -> AsyncSession:  # type: ignore[override]
    """Dependencia FastAPI — proporciona una AsyncSession scoped al request."""
    async for session in get_db_session(_session_factory):
        yield session  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Scoped: repositories (dependen de la sesión)
# ---------------------------------------------------------------------------
def get_user_repository(
    session: AsyncSession = Depends(get_db_session_dep),
) -> SQLAlchemyUserRepository:
    """Dependencia FastAPI — proporciona un UserRepository con sesión scoped."""
    return SQLAlchemyUserRepository(session)


def get_refresh_token_repository(
    session: AsyncSession = Depends(get_db_session_dep),
) -> SQLAlchemyRefreshTokenRepository:
    """Dependencia FastAPI — proporciona un RefreshTokenRepository con sesión scoped."""
    return SQLAlchemyRefreshTokenRepository(session)


def get_verification_token_repository(
    session: AsyncSession = Depends(get_db_session_dep),
) -> SQLAlchemyVerificationTokenRepository:
    """Dependencia FastAPI — proporciona un VerificationTokenRepository con sesión scoped."""
    return SQLAlchemyVerificationTokenRepository(session)


def get_password_history_repository(
    session: AsyncSession = Depends(get_db_session_dep),
) -> SQLAlchemyPasswordHistoryRepository:
    """Dependencia FastAPI — proporciona un PasswordHistoryRepository con sesión scoped."""
    return SQLAlchemyPasswordHistoryRepository(session)


# ---------------------------------------------------------------------------
# Lifespan (startup / shutdown)
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ANN001
    """Gestiona arranque y parada de la aplicación."""
    # Startup — depositar singletons en app.state para que deps.py los consuma
    app.state.event_bus = event_bus
    app.state.jwt_provider = jwt_provider
    app.state.email_service = email_service
    app.state.totp_provider = totp_provider
    app.state.github_oauth = github_oauth
    app.state.rate_limiter = rate_limiter
    app.state.login_attempt_tracker = login_attempt_tracker
    app.state.session_factory = _session_factory
    yield
    # Shutdown
    await _engine.dispose()
    await close_valkey_client(_valkey_client)


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
def create_app() -> FastAPI:
    """Factory que crea y configura la aplicación FastAPI."""
    app = FastAPI(
        title="ikctl API",
        description="API REST para gestión de instalaciones remotas de aplicaciones",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # SecurityHeadersMiddleware se añade primero (más interno) — aplica a todas las respuestas
    app.add_middleware(SecurityHeadersMiddleware)
    # AuthenticationMiddleware envuelve los endpoints protegidos
    app.add_middleware(AuthenticationMiddleware, jwt_provider=jwt_provider)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)

    # Health checks
    @app.get("/")
    def read_root():
        """Endpoint raíz — información básica de la API."""
        return {"message": "ikctl API is running", "version": "1.0.0", "docs": "/docs"}

    @app.get("/healthz")
    def healthz():
        """Kubernetes liveness probe — verifica que el proceso está vivo."""
        return {"status": "alive", "timestamp": datetime.now(timezone.utc).isoformat()}

    @app.get("/readyz")
    def readyz():
        """Kubernetes readiness probe — verifica que la app está lista para recibir tráfico."""
        return {
            "status": "ready",
            "checks": {"database": "ok", "api": "ok"},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    # T-34+ — routers auth
    app.include_router(auth_router)

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8089,
                reload=True, log_level="info")
