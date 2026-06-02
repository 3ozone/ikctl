"""PeriodicSyncRepositories — Scheduler que sincroniza todos los repositorios activos."""
import logging
from uuid import uuid4

from app.v1.kits.application.commands.sync_repository import SyncRepository
from app.v1.kits.application.interfaces.repository_repository import RepositoryRepository

logger = logging.getLogger(__name__)


class PeriodicSyncRepositories:
    """Servicio de sincronización periódica de repositorios.

    Diseñado para ejecutarse como tarea de fondo (Celery beat / APScheduler)
    cada 30 minutos (configurable). Recorre todos los repositorios activos del
    sistema y ejecuta SyncRepository por cada uno.

    La lógica de negocio del sync está cubierta al 100% por los tests de T-13
    (SyncRepository). Esta clase es una capa de orquestación delgada sin
    lógica propia.

    Uso típico:
        periodic = PeriodicSyncRepositories(repo_repository, sync_repository_use_case)
        summary = await periodic.run()
        # {"total": 12, "synced": 11, "errors": 1}
    """

    def __init__(
        self,
        repository_repository: RepositoryRepository,
        sync_repository: SyncRepository,
    ) -> None:
        """
        Args:
            repository_repository: Puerto para consultar todos los repositorios activos.
            sync_repository: Use case SyncRepository ya configurado con sus dependencias.
        """
        self._repository_repo = repository_repository
        self._sync_repository = sync_repository

    async def run(self, correlation_id: str | None = None) -> dict:
        """Sincroniza todos los repositorios activos del sistema.

        Por cada repositorio:
        - Ejecuta SyncRepository.execute(user_id, repository_id, correlation_id).
        - Si el resultado es sync_error, cuenta como error (no lanza excepción).
        - Si SyncRepository lanza una excepción inesperada, la captura y sigue con el siguiente.

        Args:
            correlation_id: ID de trazabilidad. Se genera automáticamente si no se proporciona.

        Returns:
            dict con claves:
                - total (int): total de repositorios procesados
                - synced (int): repositorios sincronizados con éxito
                - errors (int): repositorios con sync_error o excepción inesperada
        """
        if correlation_id is None:
            correlation_id = str(uuid4())

        repositories = await self._repository_repo.find_all_active()
        total = len(repositories)
        synced = 0
        errors = 0

        logger.info(
            "Iniciando sync periódico",
            extra={"total_repositories": total, "correlation_id": correlation_id},
        )

        for repo in repositories:
            try:
                result = await self._sync_repository.execute(
                    user_id=repo.user_id,
                    repository_id=repo.id,
                    correlation_id=correlation_id,
                )
                if result.sync_status == "sync_error":
                    errors += 1
                    logger.warning(
                        "Sync periódico: error en repositorio",
                        extra={
                            "repository_id": repo.id,
                            "user_id": repo.user_id,
                            "sync_error_message": result.sync_error_message,
                            "correlation_id": correlation_id,
                        },
                    )
                else:
                    synced += 1
                    logger.debug(
                        "Sync periódico: repositorio sincronizado",
                        extra={
                            "repository_id": repo.id,
                            "user_id": repo.user_id,
                            "kits_created": result.kits_created,
                            "kits_updated": result.kits_updated,
                            "kits_deleted": result.kits_deleted,
                            "correlation_id": correlation_id,
                        },
                    )
            except Exception as exc:
                errors += 1
                logger.error(
                    "Sync periódico: excepción inesperada en repositorio",
                    extra={
                        "repository_id": repo.id,
                        "user_id": repo.user_id,
                        "error": str(exc),
                        "correlation_id": correlation_id,
                    },
                )

        logger.info(
            "Sync periódico finalizado",
            extra={
                "total": total,
                "synced": synced,
                "errors": errors,
                "correlation_id": correlation_id,
            },
        )

        return {"total": total, "synced": synced, "errors": errors}
