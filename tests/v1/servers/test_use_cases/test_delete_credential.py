"""Tests para Use Case DeleteCredential."""
from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import uuid4
import pytest

from app.v1.servers.domain.entities.credential import Credential
from app.v1.servers.domain.value_objects.credential_type import CredentialType
from app.v1.servers.domain.exceptions.credential import (
    CredentialNotFoundError,
    CredentialInUseError,
)
from app.v1.servers.application.commands.delete_credential import DeleteCredential
from app.v1.servers.domain.events.credential_deleted import CredentialDeleted

CORRELATION_ID = str(uuid4())


def make_credential(credential_id: str = "cred-123", user_id: str = "user-123") -> Credential:
    """Factoría de Credential para los tests."""
    now = datetime.now(timezone.utc)
    return Credential(
        id=credential_id,
        user_id=user_id,
        name="Mi credencial",
        type=CredentialType("ssh"),
        username="admin",
        password="secret",
        private_key=None,
        created_at=now,
        updated_at=now,
    )


class TestDeleteCredentialSuccess:
    """Tests de éxito del Use Case DeleteCredential."""

    @pytest.mark.asyncio
    async def test_delete_credential_calls_repo_delete(self):
        """Test 1: DeleteCredential llama a repo.delete con el id correcto."""
        repo = AsyncMock()
        repo.find_by_id.return_value = make_credential()
        repo.is_used_by_server.return_value = False
        use_case = DeleteCredential(credential_repository=repo)

        await use_case.execute(
            user_id="user-123",
            credential_id="cred-123",
            correlation_id=CORRELATION_ID,
        )

        repo.delete.assert_called_once_with("cred-123")


class TestDeleteCredentialErrors:
    """Tests de error del Use Case DeleteCredential."""

    @pytest.mark.asyncio
    async def test_delete_credential_not_found_raises_error(self):
        """Test 2: DeleteCredential lanza CredentialNotFoundError si no existe."""
        repo = AsyncMock()
        repo.find_by_id.return_value = None
        use_case = DeleteCredential(credential_repository=repo)

        with pytest.raises(CredentialNotFoundError):
            await use_case.execute(
                user_id="user-123",
                credential_id="cred-inexistente",
                correlation_id=CORRELATION_ID,
            )

    @pytest.mark.asyncio
    async def test_delete_credential_in_use_raises_error(self):
        """Test 3: DeleteCredential lanza CredentialInUseError si está en uso por un servidor (RN-06)."""
        repo = AsyncMock()
        repo.find_by_id.return_value = make_credential()
        repo.is_used_by_server.return_value = True
        use_case = DeleteCredential(credential_repository=repo)

        with pytest.raises(CredentialInUseError):
            await use_case.execute(
                user_id="user-123",
                credential_id="cred-123",
                correlation_id=CORRELATION_ID,
            )


class TestDeleteCredentialEvent:
    """Tests de eventos del Use Case DeleteCredential."""

    @pytest.mark.asyncio
    async def test_delete_credential_publishes_credential_deleted_event(self):
        """Test 4: DeleteCredential publica CredentialDeleted tras eliminar."""
        repo = AsyncMock()
        repo.find_by_id.return_value = make_credential()
        repo.is_used_by_server.return_value = False
        event_bus = AsyncMock()
        use_case = DeleteCredential(credential_repository=repo, event_bus=event_bus)

        await use_case.execute(
            user_id="user-123",
            credential_id="cred-123",
            correlation_id=CORRELATION_ID,
        )

        event_bus.publish.assert_called_once()
        published_event = event_bus.publish.call_args[0][0]
        assert isinstance(published_event, CredentialDeleted)
