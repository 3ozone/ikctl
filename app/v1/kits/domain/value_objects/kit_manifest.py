"""Value Object KitManifest."""
from __future__ import annotations

from dataclasses import dataclass, field

from app.v1.kits.domain.exceptions.kit import InvalidManifestError


@dataclass(frozen=True)
class KitManifest:
    """Parsea y valida el ikctl.yaml de un subdirectorio de kit.

    Invariantes:
    - name es obligatorio.
    - Todos los pipeline_files deben estar declarados en upload_files (RN-21).
    """

    name: str
    description: str | None
    version: str | None
    tags: tuple[str, ...]
    values: dict = field(hash=False)
    debug_level: str
    upload_files: tuple[str, ...]
    pipeline_files: tuple[str, ...]
    backup_files: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.name:
            raise InvalidManifestError(
                "El campo 'name' es obligatorio en el manifiesto del kit")
        missing = set(self.pipeline_files) - set(self.upload_files)
        if missing:
            raise InvalidManifestError(
                f"pipeline_files contiene archivos no declarados en upload_files: {missing} (RN-21)"
            )

    @classmethod
    def from_dict(cls, data: dict) -> KitManifest:
        """Crea un KitManifest desde el dict parseado del ikctl.yaml de subdirectorio."""
        name: str = data.get("name") or ""
        files = data.get("files", {})
        return cls(
            name=name,
            description=data.get("description"),
            version=data.get("version"),
            tags=tuple(data.get("tags", [])),
            values=data.get("values", {}),
            debug_level=data.get("debug_level", "none"),
            upload_files=tuple(files.get("uploads", [])),
            pipeline_files=tuple(files.get("pipeline", [])),
            backup_files=tuple(data.get("backup", [])),
        )
