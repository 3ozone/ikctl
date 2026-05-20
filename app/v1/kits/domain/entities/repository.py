"""Entidad Repository del módulo kits."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from app.v1.kits.domain.value_objects.sync_status import SyncStatus


@dataclass
class Repository:
    """Entidad que representa un repositorio Git registrado como fuente de kits.

    La identidad de la entidad es su `id`; dos instancias con el mismo `id`
    son iguales independientemente del resto de campos.

    Attributes:
        id: Identificador único del repositorio.
        user_id: Identificador del usuario propietario.
        url: URL del repositorio Git.
        ref: Rama, tag o commit SHA de referencia.
        credential_id: Identificador opcional de la credencial Git asociada.
        sync_status: Estado de sincronización del repositorio.
        last_synced_at: Fecha de la última sincronización exitosa.
        last_commit_sha: SHA del último commit sincronizado.
        sync_error_message: Mensaje de error de la última sincronización fallida.
        is_deleted: Indica si el repositorio ha sido eliminado (borrado suave).
        created_at: Fecha de creación.
        updated_at: Fecha de última actualización.
    """

    id: str
    user_id: str
    url: str
    ref: str
    credential_id: Optional[str]
    sync_status: SyncStatus
    last_synced_at: Optional[datetime]
    last_commit_sha: Optional[str]
    sync_error_message: Optional[str]
    is_deleted: bool
    created_at: datetime
    updated_at: datetime

    # --- Comandos de negocio ---

    def update(self, url: str, ref: str, credential_id: Optional[str]) -> None:
        """Actualiza los datos de la fuente Git del repositorio.

        Si cambia la `url` o la `ref`, el estado de sincronización se resetea a
        `never_synced` ya que la fuente ha cambiado y los kits deben re-sincronizarse.

        Args:
            url: Nueva URL del repositorio Git.
            ref: Nueva rama, tag o commit SHA de referencia.
            credential_id: Nuevo identificador de credencial (puede ser None).
        """
        if url != self.url or ref != self.ref:
            self.sync_status = SyncStatus("never_synced")
        self.url = url
        self.ref = ref
        self.credential_id = credential_id

    def mark_synced(self, commit_sha: str, synced_at: datetime) -> None:
        """Marca el repositorio como sincronizado correctamente.

        Args:
            commit_sha: SHA del commit sincronizado.
            synced_at: Fecha y hora de la sincronización.
        """
        self.sync_status = SyncStatus("synced")
        self.last_commit_sha = commit_sha
        self.last_synced_at = synced_at
        self.sync_error_message = None

    def mark_sync_error(self, message: str) -> None:
        """Marca el repositorio con un error de sincronización.

        Args:
            message: Descripción del error ocurrido durante la sincronización.
        """
        self.sync_status = SyncStatus("sync_error")
        self.sync_error_message = message

    def delete(self) -> None:
        """Realiza el borrado suave del repositorio (is_deleted = True)."""
        self.is_deleted = True

    # --- Queries de estado ---

    def is_synced(self) -> bool:
        """Indica si el repositorio está sincronizado.

        Returns:
            True si sync_status es 'synced', False en cualquier otro caso.
        """
        return self.sync_status == SyncStatus("synced")

    # --- Identidad ---

    def __eq__(self, other: object) -> bool:
        """Dos entidades Repository son iguales si tienen el mismo id."""
        return isinstance(other, Repository) and self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)
