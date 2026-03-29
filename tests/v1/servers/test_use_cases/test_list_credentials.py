"""Tests para Use Case ListCredentials."""
from datetime import datetime, timezone
from unittest.mock import AsyncMock
import pytest

from app.v1.servers.domain.entities.credential import Credential
from app.v1.servers.domain.value_objects.credential_type import CredentialType
from app.v1.servers.application.queries.list_credentials import ListCredentials
from app.v1.servers.application.dtos.credential_list_result import CredentialListResult


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


class TestListCredentials:
    """Tests del Use Case ListCredentials."""

    @pytest.mark.asyncio
    async def test_list_credentials_returns_paginated_result(self):
        """Test 1: ListCredentials devuelve CredentialListResult con items y metadatos de paginación."""
        repo = AsyncMock()
        repo.find_all_by_user.return_value = [
            make_credential("cred-1"), make_credential("cred-2")]

        use_case = ListCredentials(credential_repository=repo)

        result = await use_case.execute(user_id="user-123", page=1, per_page=10)

        assert isinstance(result, CredentialListResult)
        assert len(result.items) == 2
        assert result.page == 1
        assert result.per_page == 10

    @pytest.mark.asyncio
    async def test_list_credentials_empty_returns_empty_list(self):
        """Test 2: ListCredentials sin credenciales devuelve lista vacía."""
        repo = AsyncMock()
        repo.find_all_by_user.return_value = []

        use_case = ListCredentials(credential_repository=repo)

        result = await use_case.execute(user_id="user-123", page=1, per_page=10)

        assert isinstance(result, CredentialListResult)
        assert result.items == []
        assert result.total == 0
