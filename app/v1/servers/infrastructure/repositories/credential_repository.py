"""SQLAlchemyCredentialRepository — Implementación con cifrado AES-256.

Los campos sensibles `password` y `private_key` se cifran con AES-256-GCM
antes de persistir y se descifran al recuperar. Nunca se almacenan en texto
plano (RNF-04). La clave de cifrado se inyecta desde la variable de entorno
ENCRYPTION_KEY (32 bytes).
"""
import base64
import os
from typing import Optional

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.v1.servers.application.interfaces.credential_repository import CredentialRepository
from app.v1.servers.domain.entities.credential import Credential
from app.v1.servers.domain.value_objects.credential_type import CredentialType
from app.v1.servers.infrastructure.exceptions import DatabaseQueryError, EncryptionError
from app.v1.servers.infrastructure.persistence.models import CredentialModel, ServerModel

# Nonce de 12 bytes es el estándar para AES-GCM
_NONCE_SIZE = 12


def _encrypt(key: bytes, plaintext: str) -> str:
    """Cifra `plaintext` con AES-256-GCM. Devuelve base64(nonce + ciphertext)."""
    nonce = os.urandom(_NONCE_SIZE)
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode(), None)
    return base64.b64encode(nonce + ciphertext).decode()


def _decrypt(key: bytes, token: str) -> str:
    """Descifra un token base64(nonce + ciphertext) con AES-256-GCM."""
    raw = base64.b64decode(token)
    nonce, ciphertext = raw[:_NONCE_SIZE], raw[_NONCE_SIZE:]
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, ciphertext, None).decode()


class SQLAlchemyCredentialRepository(CredentialRepository):
    """Implementación SQLAlchemy del repositorio de credenciales.

    Cifra `password` y `private_key` en reposo usando AES-256-GCM.
    """

    def __init__(self, session: AsyncSession, encryption_key: str) -> None:
        """Inicializa el repositorio.

        Args:
            session: Sesión async de SQLAlchemy.
            encryption_key: Clave de cifrado de 32 bytes (ENCRYPTION_KEY env var).

        Raises:
            ValueError: Si la clave no tiene exactamente 32 bytes.
        """
        key_bytes = encryption_key.encode() if isinstance(encryption_key, str) else encryption_key
        if len(key_bytes) != 32:
            raise ValueError("ENCRYPTION_KEY must be exactly 32 bytes for AES-256")
        self._session = session
        self._key = key_bytes

    # ------------------------------------------------------------------
    # Helpers de conversión
    # ------------------------------------------------------------------

    def _encrypt_field(self, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        try:
            return _encrypt(self._key, value)
        except Exception as exc:
            raise EncryptionError(f"Error cifrando campo: {exc}") from exc

    def _decrypt_field(self, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        try:
            return _decrypt(self._key, value)
        except Exception as exc:
            raise EncryptionError(f"Error descifrando campo: {exc}") from exc

    def _entity_to_model(self, credential: Credential) -> CredentialModel:
        return CredentialModel(
            id=credential.id,
            user_id=credential.user_id,
            name=credential.name,
            type=credential.type.value,
            username=credential.username,
            password_encrypted=self._encrypt_field(credential.password),
            private_key_encrypted=self._encrypt_field(credential.private_key),
            created_at=credential.created_at,
            updated_at=credential.updated_at,
        )

    def _model_to_entity(self, model: CredentialModel) -> Credential:
        return Credential(
            id=model.id,
            user_id=model.user_id,
            name=model.name,
            type=CredentialType(model.type),
            username=model.username,
            password=self._decrypt_field(model.password_encrypted),
            private_key=self._decrypt_field(model.private_key_encrypted),
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    # ------------------------------------------------------------------
    # Port implementation
    # ------------------------------------------------------------------

    async def save(self, credential: Credential) -> None:
        """Persiste una nueva credencial con campos sensibles cifrados.

        Raises:
            EncryptionError: Si falla el cifrado.
            DatabaseQueryError: Si falla la persistencia.
        """
        try:
            model = self._entity_to_model(credential)
            self._session.add(model)
            await self._session.commit()
        except EncryptionError:
            raise
        except Exception as exc:
            await self._session.rollback()
            raise DatabaseQueryError(f"Error guardando credencial: {exc}") from exc

    async def find_by_id(self, credential_id: str, user_id: str) -> Optional[Credential]:
        """Busca una credencial por id scoped al usuario propietario.

        Returns:
            Credential descifrada, o None si no existe o no pertenece al usuario.

        Raises:
            DatabaseQueryError: Si falla la consulta.
        """
        try:
            result = await self._session.execute(
                select(CredentialModel).where(
                    CredentialModel.id == credential_id,
                    CredentialModel.user_id == user_id,
                )
            )
            model = result.scalar_one_or_none()
            return self._model_to_entity(model) if model else None
        except EncryptionError:
            raise
        except Exception as exc:
            raise DatabaseQueryError(f"Error buscando credencial: {exc}") from exc

    async def find_all_by_user(
        self, user_id: str, page: int, per_page: int
    ) -> list[Credential]:
        """Lista credenciales de un usuario con paginación (1-based).

        Raises:
            DatabaseQueryError: Si falla la consulta.
        """
        try:
            offset = (page - 1) * per_page
            result = await self._session.execute(
                select(CredentialModel)
                .where(CredentialModel.user_id == user_id)
                .order_by(CredentialModel.created_at)
                .offset(offset)
                .limit(per_page)
            )
            models = result.scalars().all()
            return [self._model_to_entity(m) for m in models]
        except EncryptionError:
            raise
        except Exception as exc:
            raise DatabaseQueryError(f"Error listando credenciales: {exc}") from exc

    async def update(self, credential: Credential) -> None:
        """Actualiza los campos de una credencial existente.

        Raises:
            EncryptionError: Si falla el re-cifrado.
            DatabaseQueryError: Si falla la persistencia.
        """
        try:
            result = await self._session.execute(
                select(CredentialModel).where(CredentialModel.id == credential.id)
            )
            model = result.scalar_one_or_none()
            if model is None:
                return

            model.name = credential.name
            model.username = credential.username
            model.password_encrypted = self._encrypt_field(credential.password)
            model.private_key_encrypted = self._encrypt_field(credential.private_key)
            model.updated_at = credential.updated_at

            await self._session.commit()
        except EncryptionError:
            raise
        except Exception as exc:
            await self._session.rollback()
            raise DatabaseQueryError(f"Error actualizando credencial: {exc}") from exc

    async def delete(self, credential_id: str) -> None:
        """Elimina una credencial por id.

        Raises:
            DatabaseQueryError: Si falla la eliminación.
        """
        try:
            result = await self._session.execute(
                select(CredentialModel).where(CredentialModel.id == credential_id)
            )
            model = result.scalar_one_or_none()
            if model:
                await self._session.delete(model)
                await self._session.commit()
        except Exception as exc:
            await self._session.rollback()
            raise DatabaseQueryError(f"Error eliminando credencial: {exc}") from exc

    async def is_used_by_server(self, credential_id: str) -> bool:
        """Comprueba si algún servidor referencia esta credencial.

        Returns:
            True si al menos un server la usa, False si no.

        Raises:
            DatabaseQueryError: Si falla la consulta.
        """
        try:
            result = await self._session.execute(
                select(ServerModel.id).where(
                    ServerModel.credential_id == credential_id
                ).limit(1)
            )
            return result.scalar_one_or_none() is not None
        except Exception as exc:
            raise DatabaseQueryError(
                f"Error comprobando uso de credencial: {exc}"
            ) from exc
