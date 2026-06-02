"""CredentialReadAdapter — Adapter cross-módulo para leer credenciales sin ownership.

Implementa el puerto operations.application.interfaces.CredentialRepository
delegando al SQLAlchemyCredentialRepository de servers para garantizar
que el descifrado AES-256-GCM sea consistente. Usa el método público
model_to_entity en vez de acceder al método privado _model_to_entity.
"""
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.v1.operations.application.interfaces.credential_repository import (
    CredentialRepository as OperationsCredentialRepository,
)
from app.v1.servers.domain.entities.credential import Credential
from app.v1.servers.infrastructure.persistence.models import CredentialModel
from app.v1.servers.infrastructure.repositories.credential_repository import (
    SQLAlchemyCredentialRepository,
)


class CredentialReadAdapter(OperationsCredentialRepository):
    """Lee credenciales sin filtro de ownership para uso interno de tasks.

    Delega la conversión model→entity (incluyendo descifrado) al
    SQLAlchemyCredentialRepository para garantizar consistencia.
    """

    def __init__(self, session: AsyncSession, encryption_key: str) -> None:
        self._session = session
        self._inner = SQLAlchemyCredentialRepository(session, encryption_key)

    async def find_by_id_internal(self, credential_id: str) -> Optional[Credential]:
        """Busca una credencial por id sin validar ownership.

        Descifra los campos sensibles usando la clave AES-256 del repo de servers.
        """
        result = await self._session.execute(
            select(CredentialModel).where(CredentialModel.id == credential_id)
        )
        model = result.scalar_one_or_none()
        return self._inner.model_to_entity(model) if model else None