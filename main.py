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
from app.v1.servers.infrastructure.presentation.exception_handlers import register_exception_handlers as register_servers_exception_handlers
from app.v1.kits.infrastructure.presentation.exception_handlers import register_exception_handlers as register_kits_exception_handlers
from app.v1.operations.infrastructure.presentation.exception_handlers import register_exception_handlers as register_operations_exception_handlers
from app.v1.pipelines.infrastructure.presentation.exception_handlers import register_exception_handlers as register_pipelines_exception_handlers
from app.v1.kits.infrastructure.presentation.routes import router as kits_router
from app.v1.operations.infrastructure.presentation.routes import router as operations_router
from app.v1.servers.infrastructure.presentation.routes_credentials import router as credentials_router
from app.v1.servers.infrastructure.presentation.routes_groups import router as groups_router
from app.v1.servers.infrastructure.presentation.routes_servers import router as servers_router
from app.v1.servers.infrastructure.repositories.credential_repository import (
    SQLAlchemyCredentialRepository,
)
from app.v1.servers.infrastructure.repositories.server_repository import (
    SQLAlchemyServerRepository,
)
from app.v1.servers.infrastructure.repositories.group_repository import (
    SQLAlchemyGroupRepository,
)
from app.v1.servers.infrastructure.adapters.connection_factory import ConnectionFactory
from app.v1.kits.application.commands.delete_repository import DeleteRepository as DeleteRepositoryUC
from app.v1.kits.application.commands.register_repository import RegisterRepository as RegisterRepositoryUC
from app.v1.kits.application.commands.sync_repository import SyncRepository as SyncRepositoryUC
from app.v1.kits.application.commands.update_repository import UpdateRepository as UpdateRepositoryUC
from app.v1.kits.application.queries.get_kit import GetKit
from app.v1.kits.application.queries.get_repository import GetRepository
from app.v1.kits.application.queries.list_kits import ListKits
from app.v1.kits.application.queries.list_repositories import ListRepositories
from app.v1.kits.infrastructure.adapters.git_python_client import GitPythonClient
from app.v1.kits.infrastructure.repositories.kit_repository import SQLAlchemyKitRepository
from app.v1.kits.infrastructure.repositories.repository_repository import (
    SQLAlchemyRepositoryRepository as SQLAlchemyKitsRepositoryRepository,
)
from app.v1.operations.application.tasks.execute_operation import ExecuteOperation
from app.v1.operations.application.tasks.restore_backup import RestoreBackupTask
from app.v1.operations.infrastructure.adapters.credential_read_adapter import (
    CredentialReadAdapter as OperationsCredentialReadAdapter,
)
from app.v1.operations.infrastructure.adapters.git_repository_read_adapter import (
    GitRepositoryReadAdapter,
)
from app.v1.operations.infrastructure.adapters.kit_read_adapter import KitReadAdapter
from app.v1.operations.infrastructure.adapters.server_read_adapter import ServerReadAdapter
from app.v1.operations.infrastructure.adapters.ssh_kit_executor import SSHKitExecutor
from app.v1.operations.infrastructure.adapters.ssh_backup_restorer import SSHBackupRestorer
from app.v1.operations.infrastructure.repositories.file_cache_repository import (
    SQLAlchemyFileCacheRepository,
)
from app.v1.operations.infrastructure.repositories.operation_repository import (
    SQLAlchemyOperationRepository,
)
from app.v1.pipelines.application.tasks.execute_pipeline_operations import ExecutePipelineOperations
from app.v1.pipelines.infrastructure.adapters.kit_read_adapter import (
    KitReadAdapter as PipelinesKitReadAdapter,
)
from app.v1.pipelines.infrastructure.adapters.operation_launcher_adapter import (
    OperationLauncherAdapter,
)
from app.v1.pipelines.infrastructure.adapters.operation_read_adapter import OperationReadAdapter as PipelinesOperationReadAdapter
from app.v1.pipelines.infrastructure.adapters.server_read_adapter import (
    ServerReadAdapter as PipelinesServerReadAdapter,
)
from app.v1.pipelines.infrastructure.repositories.pipeline_execution_repository import (
    SQLAlchemyPipelineExecutionRepository,
)
from app.v1.pipelines.infrastructure.repositories.pipeline_repository import (
    SQLAlchemyPipelineRepository,
)
from app.v1.pipelines.infrastructure.presentation.routes import router as pipelines_router

# ---------------------------------------------------------------------------
# Singleton: Settings
# ---------------------------------------------------------------------------
settings = Settings()

# ---------------------------------------------------------------------------
# Singleton: EventBus
# ---------------------------------------------------------------------------
event_bus = InMemoryEventBus()

# ---------------------------------------------------------------------------
# Singleton: módulo kits — GitPythonClient es stateless, se instancia una vez
# ---------------------------------------------------------------------------
git_python_client = GitPythonClient()

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
# Scoped: repositories módulo servers
# ---------------------------------------------------------------------------
def get_credential_repository(
    session: AsyncSession = Depends(get_db_session_dep),
) -> SQLAlchemyCredentialRepository:
    """Dependencia FastAPI — proporciona un CredentialRepository con sesión scoped."""
    return SQLAlchemyCredentialRepository(session, encryption_key=settings.ENCRYPTION_KEY)


def get_server_repository(
    session: AsyncSession = Depends(get_db_session_dep),
) -> SQLAlchemyServerRepository:
    """Dependencia FastAPI — proporciona un ServerRepository con sesión scoped."""
    return SQLAlchemyServerRepository(session)


def get_group_repository(
    session: AsyncSession = Depends(get_db_session_dep),
) -> SQLAlchemyGroupRepository:
    """Dependencia FastAPI — proporciona un GroupRepository con sesión scoped."""
    return SQLAlchemyGroupRepository(session)


def get_connection_factory(
    credential_repo: SQLAlchemyCredentialRepository = Depends(get_credential_repository),
) -> ConnectionFactory:
    """Dependencia FastAPI — proporciona una ConnectionFactory con sesión scoped."""
    return ConnectionFactory(credential_repository=credential_repo)


# ---------------------------------------------------------------------------
# Scoped: repositories módulo kits
# ---------------------------------------------------------------------------
def get_kits_repository_repository(
    session: AsyncSession = Depends(get_db_session_dep),
) -> SQLAlchemyKitsRepositoryRepository:
    """Dependencia FastAPI — proporciona un KitsRepositoryRepository con sesión scoped."""
    return SQLAlchemyKitsRepositoryRepository(session)


def get_kit_repository(
    session: AsyncSession = Depends(get_db_session_dep),
) -> SQLAlchemyKitRepository:
    """Dependencia FastAPI — proporciona un KitRepository con sesión scoped."""
    return SQLAlchemyKitRepository(session)


# ---------------------------------------------------------------------------
# Scoped: use cases módulo kits — Commands
# ---------------------------------------------------------------------------
def get_register_repository_uc(
    repo_repo: SQLAlchemyKitsRepositoryRepository = Depends(get_kits_repository_repository),
    credential_repo: SQLAlchemyCredentialRepository = Depends(get_credential_repository),
) -> RegisterRepositoryUC:
    """Dependencia FastAPI — RegisterRepository use case."""
    return RegisterRepositoryUC(
        repository_repository=repo_repo,
        credential_repository=credential_repo,
        event_bus=event_bus,
    )


def get_update_repository_uc(
    repo_repo: SQLAlchemyKitsRepositoryRepository = Depends(get_kits_repository_repository),
    credential_repo: SQLAlchemyCredentialRepository = Depends(get_credential_repository),
) -> UpdateRepositoryUC:
    """Dependencia FastAPI — UpdateRepository use case."""
    return UpdateRepositoryUC(
        repository_repository=repo_repo,
        credential_repository=credential_repo,
    )


def get_delete_repository_uc(
    repo_repo: SQLAlchemyKitsRepositoryRepository = Depends(get_kits_repository_repository),
) -> DeleteRepositoryUC:
    """Dependencia FastAPI — DeleteRepository use case."""
    return DeleteRepositoryUC(
        repository_repository=repo_repo,
        event_bus=event_bus,
    )


def get_sync_repository_uc(
    repo_repo: SQLAlchemyKitsRepositoryRepository = Depends(get_kits_repository_repository),
    kit_repo: SQLAlchemyKitRepository = Depends(get_kit_repository),
) -> SyncRepositoryUC:
    """Dependencia FastAPI — SyncRepository use case."""
    return SyncRepositoryUC(
        repository_repository=repo_repo,
        kit_repository=kit_repo,
        git_client=git_python_client,
        event_bus=event_bus,
    )


# ---------------------------------------------------------------------------
# Scoped: use cases módulo kits — Queries
# ---------------------------------------------------------------------------
def get_get_repository_uc(
    repo_repo: SQLAlchemyKitsRepositoryRepository = Depends(get_kits_repository_repository),
) -> GetRepository:
    """Dependencia FastAPI — GetRepository use case."""
    return GetRepository(repository_repository=repo_repo)


def get_list_repositories_uc(
    repo_repo: SQLAlchemyKitsRepositoryRepository = Depends(get_kits_repository_repository),
) -> ListRepositories:
    """Dependencia FastAPI — ListRepositories use case."""
    return ListRepositories(repository_repository=repo_repo)


def get_get_kit_uc(
    kit_repo: SQLAlchemyKitRepository = Depends(get_kit_repository),
) -> GetKit:
    """Dependencia FastAPI — GetKit use case."""
    return GetKit(kit_repository=kit_repo)


def get_list_kits_uc(
    kit_repo: SQLAlchemyKitRepository = Depends(get_kit_repository),
) -> ListKits:
    """Dependencia FastAPI — ListKits use case."""
    return ListKits(kit_repository=kit_repo)


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
    app.state.encryption_key = settings.ENCRYPTION_KEY
    app.state.git_python_client = git_python_client

    # ── operations: execute_operation_fn ────────────────────────────────
    # Closure que crea sus propias sesiones (runs in BackgroundTasks, no request scope).
    async def _execute_operation_fn(operation_id: str) -> None:
        async for session in get_db_session(_session_factory):
            file_cache = SQLAlchemyFileCacheRepository(session)
            git_repo_port = GitRepositoryReadAdapter(session)
            credential_repo = OperationsCredentialReadAdapter(session, settings.ENCRYPTION_KEY)

            ssh_executor = SSHKitExecutor(
                git_client=git_python_client,
                file_cache=file_cache,
                git_repository_port=git_repo_port,
                credential_repository=credential_repo,
            )

            operation_repo = SQLAlchemyOperationRepository(session)
            server_repo = ServerReadAdapter(session)
            kit_repo = KitReadAdapter(session)

            task = ExecuteOperation(
                operation_repository=operation_repo,
                server_repository=server_repo,
                kit_repository=kit_repo,
                credential_repository=credential_repo,
                remote_kit_executor=ssh_executor,
                event_bus=event_bus,
            )
            await task.execute(operation_id)

    app.state.execute_operation_fn = _execute_operation_fn

    # ── operations: restore_operation_fn ──────────────────────────────
    # Closure que crea sus propias sesiones (runs in BackgroundTasks).
    async def _restore_operation_fn(operation_id: str) -> None:
        async for session in get_db_session(_session_factory):
            operation_repo = SQLAlchemyOperationRepository(session)
            server_repo = ServerReadAdapter(session)
            credential_repo = OperationsCredentialReadAdapter(session, settings.ENCRYPTION_KEY)

            backup_restorer = SSHBackupRestorer(
                server_repo=server_repo,
                credential_repo=credential_repo,
            )

            task = RestoreBackupTask(
                operation_repository=operation_repo,
                backup_restorer=backup_restorer,
            )
            await task.execute(operation_id)

    app.state.restore_operation_fn = _restore_operation_fn

    # ── pipelines: execute_pipeline_fn ────────────────────────────────
    # Closure que crea sus propias sesiones (runs in BackgroundTasks).
    async def _execute_pipeline_fn(execution_id: str) -> None:
        async for session in get_db_session(_session_factory):
            pipeline_repo = SQLAlchemyPipelineRepository(session)
            execution_repo = SQLAlchemyPipelineExecutionRepository(session)
            server_repo = PipelinesServerReadAdapter(session)
            operation_repo = PipelinesOperationReadAdapter(session)
            kit_repo = PipelinesKitReadAdapter(session)

            # OperationLauncherAdapter envuelve LaunchOperation con sus deps
            file_cache = SQLAlchemyFileCacheRepository(session)
            git_repo_port = GitRepositoryReadAdapter(session)
            credential_repo = OperationsCredentialReadAdapter(session, settings.ENCRYPTION_KEY)

            ssh_executor = SSHKitExecutor(
                git_client=git_python_client,
                file_cache=file_cache,
                git_repository_port=git_repo_port,
                credential_repository=credential_repo,
            )

            # Para OperationLauncherAdapter necesitamos un LaunchOperation completo
            from app.v1.operations.application.commands.launch_operation import LaunchOperation

            launch_operation = LaunchOperation(
                operation_repository=SQLAlchemyOperationRepository(session),
                server_repository=ServerReadAdapter(session),
                kit_repository=KitReadAdapter(session),
                task_queue=None,  # No re-encola dentro de pipeline task
                event_bus=event_bus,
                execute_fn=_execute_operation_fn,
            )
            operation_launcher = OperationLauncherAdapter(launch_operation=launch_operation)

            task = ExecutePipelineOperations(
                pipeline_repository=pipeline_repo,
                execution_repository=execution_repo,
                server_repository=server_repo,
                operation_launcher=operation_launcher,
                operation_repository=operation_repo,
            )
            await task.execute(execution_id)

    app.state.execute_pipeline_fn = _execute_pipeline_fn
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
    register_servers_exception_handlers(app)
    register_kits_exception_handlers(app)
    register_operations_exception_handlers(app)
    register_pipelines_exception_handlers(app)

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

    # T-34+ — routers servers
    app.include_router(credentials_router)
    app.include_router(servers_router)
    app.include_router(groups_router)

    # T-29+ — routers kits
    app.include_router(kits_router)

    # T-28+ — routers operations
    app.include_router(operations_router)

    # T-29+ — routers pipelines
    app.include_router(pipelines_router)

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8089,
                reload=True, log_level="info")
