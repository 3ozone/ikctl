"""Tests para Use Case UpdateCredential."""
from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import uuid4
import pytest

from app.v1.servers.domain.entities.credential import Credential
from app.v1.servers.domain.value_objects.credential_type import CredentialType
from app.v1.servers.domain.exceptions.credential import CredentialNotFoundError
from app.v1.servers.application.commands.update_credential import UpdateCredential
from app.v1.servers.application.dtos.credential_result import CredentialResult
from app.v1.servers.domain.events.credential_updated import CredentialUpdated

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


class TestUpdateCredentialSuccess:
    """Tests de éxito del Use Case UpdateCredential."""

    @pytest.mark.asyncio
    async def test_update_credential_returns_dto(self):
        """Test 1: UpdateCredential devuelve CredentialResult con datos actualizados."""
        repo = AsyncMock()
        repo.find_by_id.return_value = make_credential()
        use_case = UpdateCredential(credential_repository=repo)

        result = await use_case.execute(
            user_id="user-123",
            credential_id="cred-123",
            name="Credencial actualizada",
            username="nuevo_admin",
            password="nueva_pass",
            private_key=None,
            correlation_id=CORRELATION_ID,
        )

        assert isinstance(result, CredentialResult)
        assert result.name == "Credencial actualizada"
        assert result.username == "nuevo_admin"

    @pytest.mark.asyncio
    async def test_update_credential_calls_repo_update(self):
        """Test 2: UpdateCredential llama a repo.update con la credencial modificada."""
        repo = AsyncMock()
        repo.find_by_id.return_value = make_credential()
        use_case = UpdateCredential(credential_repository=repo)

        await use_case.execute(
            user_id="user-123",
            credential_id="cred-123",
            name="Credencial actualizada",
            username="nuevo_admin",
            password="nueva_pass",
            private_key=None,
            correlation_id=CORRELATION_ID,
        )

        repo.update.assert_called_once()


class TestUpdateCredentialError:
    """Tests de error del Use Case UpdateCredential."""

    @pytest.mark.asyncio
    async def test_update_credential_not_found_raises_error(self):
        """Test 3: UpdateCredential lanza CredentialNotFoundError si no existe la credencial."""
        repo = AsyncMock()
        repo.find_by_id.return_value = None
        use_case = UpdateCredential(credential_repository=repo)

        with pytest.raises(CredentialNotFoundError):
            await use_case.execute(
                user_id="user-123",
                credential_id="cred-inexistente",
                name="X",
                username="admin",
                password="pass",
                private_key=None,
                correlation_id=CORRELATION_ID,
            )


class TestUpdateCredentialEvent:
    """Tests de eventos del Use Case UpdateCredential."""

    @pytest.mark.asyncio
    async def test_update_credential_publishes_credential_updated_event(self):
        """Test 4: UpdateCredential publica CredentialUpdated tras actualizar."""
        repo = AsyncMock()
        repo.find_by_id.return_value = make_credential()
        event_bus = AsyncMock()
        use_case = UpdateCredential(
            credential_repository=repo, event_bus=event_bus)

        await use_case.execute(
            user_id="user-123",
            credential_id="cred-123",
            name="Credencial actualizada",
            username="nuevo_admin",
            password="nueva_pass",
            private_key=None,
            correlation_id=CORRELATION_ID,
        )

        event_bus.publish.assert_called_once()
        published_event = event_bus.publish.call_args[0][0]
        assert isinstance(published_event, CredentialUpdated)
