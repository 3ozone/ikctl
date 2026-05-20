"""Use Case para sincronizar un repositorio Git y reconciliar sus kits."""
import tempfile
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from app.v1.kits.application.dtos.repository_sync_result import RepositorySyncResult
from app.v1.kits.application.exceptions import RepositoryNotFoundError
from app.v1.kits.application.interfaces.git_client import GitClient
from app.v1.kits.application.interfaces.kit_repository import KitRepository
from app.v1.kits.application.interfaces.repository_repository import RepositoryRepository
from app.v1.kits.domain.entities.kit import Kit
from app.v1.kits.domain.events.kit_discovered import KitDiscovered
from app.v1.kits.domain.events.repository_synced import RepositorySynced
from app.v1.kits.domain.value_objects.kit_manifest import KitManifest
from app.v1.kits.domain.value_objects.repository_index import RepositoryIndex
from app.v1.kits.domain.value_objects.sync_status import SyncStatus
from app.v1.shared.application.interfaces.event_bus import EventBus


class SyncRepository:
    """Use Case para sincronizar un repositorio Git y reconciliar sus kits con la DB.

    Flujo:
    1. Valida ownership del repositorio.
    2. Shallow clone via GitClient.
    3. Lee y parsea ikctl.yaml raíz → RepositoryIndex.
    4. Por cada path del índice: lee ikctl.yaml del subdirectorio → KitManifest.
    5. Reconcilia kits: CREATE / UPDATE / soft_delete.
    6. Marca el repositorio como synced y persiste todo.
    7. Publica RepositorySynced + KitDiscovered (solo en sync exitoso, tras persistir).

    En cualquier error controlado: marca sync_error, persiste y devuelve 200 (no lanza).
    """

    def __init__(
        self,
        repository_repository: RepositoryRepository | None = None,
        kit_repository: KitRepository | None = None,
        git_client: GitClient | None = None,
        event_bus: EventBus | None = None,
    ) -> None:
        self._repository_repo = repository_repository
        self._kit_repo = kit_repository
        self._git_client = git_client
        self._event_bus = event_bus

    async def execute(
        self,
        user_id: str,
        repository_id: str,
        correlation_id: str,
    ) -> RepositorySyncResult:
        """Sincroniza un repositorio Git y reconcilia sus kits.

        Args:
            user_id: ID del usuario propietario
            repository_id: ID del repositorio a sincronizar
            correlation_id: ID de trazabilidad del request

        Returns:
            RepositorySyncResult con el resultado del sync (nunca lanza en error de sync)

        Raises:
            RepositoryNotFoundError: Si el repositorio no existe o no pertenece al usuario (RN-01)
        """
        repository = await self._repository_repo.find_by_id(repository_id, user_id)
        if repository is None:
            raise RepositoryNotFoundError()

        dest_path = tempfile.mkdtemp()

        # --- Clone ---
        try:
            commit_sha = await self._git_client.clone_shallow(
                url=repository.url,
                ref=repository.ref,
                dest_path=dest_path,
                credential=None,
            )
        except Exception as exc:
            repository.mark_sync_error(str(exc))
            await self._repository_repo.update(repository)
            return self._build_error_result(repository)

        # --- Leer y parsear ikctl.yaml raíz ---
        try:
            root_content = await self._git_client.read_yaml_file(dest_path, "ikctl.yaml")
            index = RepositoryIndex.from_dict(root_content)
        except Exception as exc:
            repository.mark_sync_error(str(exc))
            await self._repository_repo.update(repository)
            return self._build_error_result(repository)

        # --- Reconciliación kits ---
        existing_kits = await self._kit_repo.find_by_repository_id(repository_id)
        existing_by_path = {k.path_in_repo: k for k in existing_kits if not k.is_deleted}

        now = datetime.now(timezone.utc)
        kits_created: int = 0
        kits_updated: int = 0
        kits_deleted: int = 0
        new_kit_ids: list[str] = []

        for path in index.kit_paths:
            try:
                kit_content = await self._git_client.read_yaml_file(
                    dest_path, f"{path}/ikctl.yaml"
                )
                manifest = KitManifest.from_dict(kit_content)
            except Exception:
                continue

            if path in existing_by_path:
                kit = existing_by_path[path]
                kit.mark_synced(manifest=manifest, commit_sha=commit_sha, synced_at=now)
                await self._kit_repo.update(kit)
                kits_updated += 1
            else:
                kit = Kit(
                    id=str(uuid4()),
                    user_id=user_id,
                    repository_id=repository_id,
                    path_in_repo=path,
                    name=manifest.name,
                    description=manifest.description or "",
                    version=manifest.version or "",
                    tags=list(manifest.tags),
                    values=dict(manifest.values),
                    debug_level=manifest.debug_level,
                    sync_status=SyncStatus("synced"),
                    last_synced_at=now,
                    last_commit_sha=commit_sha,
                    sync_error_message=None,
                    is_deleted=False,
                    created_at=now,
                    updated_at=now,
                )
                await self._kit_repo.save(kit)
                new_kit_ids.append(kit.id)
                kits_created += 1

        # Soft-delete de kits que ya no están en el índice
        index_paths = set(index.kit_paths)
        for kit in existing_kits:
            if not kit.is_deleted and kit.path_in_repo not in index_paths:
                kit.soft_delete()
                await self._kit_repo.update(kit)
                kits_deleted += 1

        # Marcar repositorio como synced y persistir
        repository.mark_synced(commit_sha=commit_sha, synced_at=now)
        await self._repository_repo.update(repository)

        # Publicar eventos tras persistir (RN-32, RN-33)
        if self._event_bus is not None:
            await self._event_bus.publish(
                RepositorySynced(
                    repository_id=repository_id,
                    user_id=user_id,
                    commit_sha=commit_sha,
                    kits_created=kits_created,
                    kits_updated=kits_updated,
                    kits_deleted=kits_deleted,
                    correlation_id=correlation_id,
                )
            )
            for kit_id in new_kit_ids:
                await self._event_bus.publish(
                    KitDiscovered(
                        kit_id=kit_id,
                        repository_id=repository_id,
                        user_id=user_id,
                        path_in_repo="",
                        name="",
                        correlation_id=correlation_id,
                    )
                )

        return RepositorySyncResult(
            repository_id=repository_id,
            sync_status=repository.sync_status.value,
            last_commit_sha=repository.last_commit_sha,
            sync_error_message=repository.sync_error_message,
            kits_created=kits_created,
            kits_updated=kits_updated,
            kits_deleted=kits_deleted,
        )

    @staticmethod
    def _build_error_result(repository) -> RepositorySyncResult:
        return RepositorySyncResult(
            repository_id=repository.id,
            sync_status=repository.sync_status.value,
            last_commit_sha=repository.last_commit_sha,
            sync_error_message=repository.sync_error_message,
            kits_created=0,
            kits_updated=0,
            kits_deleted=0,
        )
