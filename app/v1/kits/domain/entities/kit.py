"""Entidad Kit del módulo kits."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from app.v1.kits.domain.value_objects.kit_manifest import KitManifest
from app.v1.kits.domain.value_objects.sync_status import SyncStatus


@dataclass
class Kit:
    """Entidad que representa un kit descubierto en un repositorio Git.

    La identidad de la entidad es su `id`; dos instancias con el mismo `id`
    son iguales independientemente del resto de campos.

    Los campos de contenido (`name`, `description`, `version`, `tags`, `values`,
    `debug_level`) se actualizan desde el `KitManifest` en cada sincronización
    mediante `mark_synced()`.

    Attributes:
        id: Identificador único del kit.
        user_id: Identificador del usuario propietario.
        repository_id: Identificador del repositorio fuente.
        path_in_repo: Ruta relativa al subdirectorio del kit dentro del repositorio.
        name: Nombre del kit (del manifest).
        description: Descripción del kit (del manifest).
        version: Versión del kit (del manifest).
        tags: Lista de etiquetas del kit (del manifest).
        values: Valores configurables del kit (del manifest).
        debug_level: Nivel de debug del kit (del manifest).
        upload_files: Archivos a subir al servidor remoto (del manifest).
        pipeline_files: Archivos ejecutables del pipeline (subconjunto de upload_files).
        backup_files: Rutas a respaldar en el servidor remoto antes de la ejecución.
        sync_status: Estado de sincronización del kit.
        last_synced_at: Fecha de la última sincronización exitosa.
        last_commit_sha: SHA del último commit sincronizado.
        sync_error_message: Mensaje de error de la última sincronización fallida.
        is_deleted: Indica si el kit ha sido eliminado (borrado suave).
        created_at: Fecha de creación.
        updated_at: Fecha de última actualización.
    """

    id: str
    user_id: str
    repository_id: str
    path_in_repo: str
    name: str
    description: str
    version: str
    tags: list[str]
    values: dict
    debug_level: str
    upload_files: tuple[str, ...]
    pipeline_files: tuple[str, ...]
    backup_files: tuple[str, ...]
    sync_status: SyncStatus
    last_synced_at: Optional[datetime]
    last_commit_sha: Optional[str]
    sync_error_message: Optional[str]
    is_deleted: bool
    created_at: datetime
    updated_at: datetime

    # --- Comandos de negocio ---

    def mark_synced(self, manifest: KitManifest, commit_sha: str, synced_at: datetime) -> None:
        """Marca el kit como sincronizado y actualiza sus campos desde el manifest.

        Args:
            manifest: Manifiesto parseado del ikctl.yaml del subdirectorio del kit.
            commit_sha: SHA del commit sincronizado.
            synced_at: Fecha y hora de la sincronización.
        """
        self.name = manifest.name
        self.description = manifest.description or ""
        self.version = manifest.version or ""
        self.tags = list(manifest.tags)
        self.values = dict(manifest.values)
        self.debug_level = manifest.debug_level
        self.upload_files = manifest.upload_files
        self.pipeline_files = manifest.pipeline_files
        self.backup_files = manifest.backup_files
        self.sync_status = SyncStatus("synced")
        self.last_commit_sha = commit_sha
        self.last_synced_at = synced_at
        self.sync_error_message = None
        self.updated_at = synced_at

    def mark_sync_error(self, message: str) -> None:
        """Marca el kit con un error de sincronización.

        Args:
            message: Descripción del error ocurrido durante la sincronización.
        """
        self.sync_status = SyncStatus("sync_error")
        self.sync_error_message = message

    def soft_delete(self) -> None:
        """Realiza el borrado suave del kit (is_deleted = True)."""
        self.is_deleted = True

    # --- Queries de estado ---

    def is_usable(self) -> bool:
        """Indica si el kit es utilizable en operaciones y pipelines.

        Un kit es utilizable si está sincronizado y no ha sido eliminado (RN-09, RN-28).

        Returns:
            True si sync_status es 'synced' y is_deleted es False.
        """
        return self.sync_status == SyncStatus("synced") and not self.is_deleted

    # --- Identidad ---

    def __eq__(self, other: object) -> bool:
        """Dos entidades Kit son iguales si tienen el mismo id."""
        return isinstance(other, Kit) and self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)
