"""Value Object RepositoryIndex — parsea y valida el ikctl.yaml raíz de un repositorio."""
from __future__ import annotations

from dataclasses import dataclass

from app.v1.kits.domain.exceptions.kit import MissingRootManifestError


@dataclass(frozen=True)
class RepositoryIndex:
    """Value Object inmutable que representa el índice raíz de un repositorio de kits.

    Parsea y valida el fichero `ikctl.yaml` situado en la raíz del repositorio,
    exponiendo las rutas relativas a cada kit declarado bajo la sección `kits:`.

    Attributes:
        kit_paths: Tupla de rutas relativas a los subdirectorios de kits.

    Raises:
        MissingRootManifestError: Si `kit_paths` está vacío tras la construcción.
    """

    kit_paths: tuple[str, ...]

    def __post_init__(self) -> None:
        """Valida que el índice contenga al menos un kit.

        Raises:
            MissingRootManifestError: Si `kit_paths` está vacío.
        """
        if not self.kit_paths:
            raise MissingRootManifestError()

    @classmethod
    def from_dict(cls, data: dict) -> RepositoryIndex:
        """Construye un RepositoryIndex a partir del contenido parseado del ikctl.yaml raíz.

        Args:
            data: Diccionario con el contenido del fichero ikctl.yaml raíz.

        Returns:
            Una instancia válida de RepositoryIndex.

        Raises:
            MissingRootManifestError: Si `data` no contiene la sección `kits:` o está vacía.
        """
        kits = data.get("kits")
        if not kits:
            raise MissingRootManifestError()
        return cls(kit_paths=tuple(kits))
