"""Excepciones de dominio para Kit."""
from app.v1.shared.domain.exceptions import DomainException


class KitNotFoundError(DomainException):
    """Kit no encontrado o no pertenece al usuario."""


class InvalidManifestError(DomainException):
    """ikctl.yaml del kit inválido. Puede ser: campo name ausente, o pipeline_files no contenidos en upload_files (RN-21)."""


class MissingRootManifestError(DomainException):
    """ikctl.yaml raíz no existe o no declara ningún kit."""
