"""Tests para Use Case CreateCredential."""
from unittest.mock import AsyncMock
from uuid import uuid4
import pytest

from app.v1.servers.domain.exceptions.credential import InvalidCredentialConfigurationError
from app.v1.servers.application.commands.create_credential import CreateCredential
from app.v1.servers.application.dtos.credential_result import CredentialResult
from app.v1.servers.domain.events.credential_created import CredentialCreated

CORRELATION_ID = str(uuid4())


class TestCreateCredentialSuccess:
    """Tests de éxito del Use Case CreateCredential."""

    @pytest.mark.asyncio
    async def test_create_credential_returns_dto_without_secrets(self):
        """Test 1: CreateCredential devuelve CredentialResult sin password ni private_key."""
        use_case = CreateCredential()

        result = await use_case.execute(
            user_id="user-123",
            name="Mi servidor SSH",
            credential_type="ssh",
            username="admin",
            password="secret123",
            private_key=None,
            correlation_id=CORRELATION_ID,
        )

        assert isinstance(result, CredentialResult)
        assert result.user_id == "user-123"
        assert result.name == "Mi servidor SSH"
        assert result.credential_type == "ssh"
        assert result.credential_id is not None
        assert not hasattr(result, "password")
        assert not hasattr(result, "private_key")

    @pytest.mark.asyncio
    async def test_create_credential_calls_repo_save(self):
        """Test 2: CreateCredential persiste la credencial via repo.save."""
        repo = AsyncMock()
        use_case = CreateCredential(credential_repository=repo)

        await use_case.execute(
            user_id="user-123",
            name="Mi servidor SSH",
            credential_type="ssh",
            username="admin",
            password="secret123",
            private_key=None,
            correlation_id=CORRELATION_ID,
        )

        repo.save.assert_called_once()


class TestCreateCredentialError:
    """Tests de error del Use Case CreateCredential."""

    @pytest.mark.asyncio
    async def test_create_credential_invalid_config_raises_error(self):
        """Test 3: CreateCredential lanza InvalidCredentialConfigurationError si la config es inválida."""
        use_case = CreateCredential()

        # ssh requiere username + (password o private_key)
        with pytest.raises(InvalidCredentialConfigurationError):
            await use_case.execute(
                user_id="user-123",
                name="Credencial rota",
                credential_type="ssh",
                username=None,  # ssh sin username → inválido
                password=None,
                private_key=None,
                correlation_id=CORRELATION_ID,
            )


class TestCreateCredentialEvent:
    """Tests de eventos del Use Case CreateCredential."""

    @pytest.mark.asyncio
    async def test_create_credential_publishes_credential_created_event(self):
        """Test 4: CreateCredential publica CredentialCreated tras guardar."""
        event_bus = AsyncMock()
        use_case = CreateCredential(event_bus=event_bus)

        await use_case.execute(
            user_id="user-123",
            name="Mi servidor SSH",
            credential_type="ssh",
            username="admin",
            password="secret123",
            private_key=None,
            correlation_id=CORRELATION_ID,
        )

        event_bus.publish.assert_called_once()
        published_event = event_bus.publish.call_args[0][0]
        assert isinstance(published_event, CredentialCreated)
