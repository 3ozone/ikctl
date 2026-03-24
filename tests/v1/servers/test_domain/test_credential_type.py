"""Tests para Value Object CredentialType."""
import pytest

from app.v1.servers.domain.value_objects.credential_type import CredentialType
from app.v1.servers.domain.exceptions.credential import InvalidCredentialTypeError


class TestCredentialType:
    """Tests del Value Object CredentialType."""

    def test_credential_type_ssh_valid(self):
        """Test 1: CredentialType 'ssh' se crea exitosamente."""
        ct = CredentialType("ssh")
        assert ct.value == "ssh"

    def test_credential_type_git_https_valid(self):
        """Test 2: CredentialType 'git_https' se crea exitosamente."""
        ct = CredentialType("git_https")
        assert ct.value == "git_https"

    def test_credential_type_git_ssh_valid(self):
        """Test 3: CredentialType 'git_ssh' se crea exitosamente."""
        ct = CredentialType("git_ssh")
        assert ct.value == "git_ssh"

    def test_credential_type_invalid_raises_error(self):
        """Test 4: CredentialType con valor inválido lanza InvalidCredentialTypeError."""
        with pytest.raises(InvalidCredentialTypeError):
            CredentialType("ftp")
