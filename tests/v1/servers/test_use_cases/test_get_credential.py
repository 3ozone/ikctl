"""Tests para Use Case GetCredential."""
from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import uuid4
import pytest

from app.v1.servers.domain.entities.credential import Credential
from app.v1.servers.domain.value_objects.credential_type import CredentialType
from app.v1.servers.domain.exceptions.credential import CredentialNotFoundError
from app.v1.servers.application.queries.get_credential import GetCredential
from app.v1.servers.application.dtos.credential_result import CredentialResult

CORRELATION_ID = str(uuid4())


def make_credential(credential_id: str = "cred-123", user_id: str = "user-123") -> Credential:
    """Factoría de Credential para los tests."""
    now = datetime.now(timezone.utc)
    return Credential(
        id=credential_id,
        user_id=user_id,
        name="Mi clave SSH",
        type=CredentialType("ssh"),
        username="admin",
        password=None,
        private_key="-----BEGIN RSA PRIVATE KEY-----",
        created_at=now,
        updated_at=now,
    )


class TestGetCredentialSuccess:
    """Tests de éxito del Use Case GetCredential."""

    @pytest.mark.asyncio
    async def test_get_credential_returns_result_without_secrets(self):
        """Test 1: GetCredential devuelve CredentialResult sin password ni private_key."""
        repo = AsyncMock()
        repo.find_by_id.return_value = make_credential()

        use_case = GetCredential(credential_repository=repo)

        result = await use_case.execute(
            user_id="user-123",
            credential_id="cred-123",
        )

        assert isinstance(result, CredentialResult)
        assert result.credential_id == "cred-123"
        assert result.name == "Mi clave SSH"
        assert result.credential_type == "ssh"
        assert not hasattr(result, "password")
        assert not hasattr(result, "private_key")


class TestGetCredentialError:
    """Tests de error del Use Case GetCredential."""

    @pytest.mark.asyncio
    async def test_get_credential_not_found_raises_error(self):
        """Test 2 (RN-01): Si la credencial no existe o no pertenece al usuario, lanza CredentialNotFoundError."""
        repo = AsyncMock()
        repo.find_by_id.return_value = None

        use_case = GetCredential(credential_repository=repo)

        with pytest.raises(CredentialNotFoundError):
            await use_case.execute(
                user_id="user-123",
                credential_id="cred-inexistente",
            )
