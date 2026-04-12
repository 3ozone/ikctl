"""Tests para la entity Credential — RN-18."""
from datetime import datetime

import pytest

from app.v1.servers.domain.entities.credential import Credential
from app.v1.servers.domain.value_objects.credential_type import CredentialType
from app.v1.servers.domain.exceptions.credential import InvalidCredentialConfigurationError


CREATED_AT = datetime(2026, 1, 1, 12, 0, 0)
UPDATED_AT = datetime(2026, 1, 1, 12, 0, 0)


class TestCredentialSSH:
    """Tests para credenciales de tipo ssh (RN-18)."""

    def test_ssh_valid_with_password(self):
        """ssh con username + password es válido."""
        cred = Credential(
            id="cred-1",
            user_id="user-1",
            name="Mi servidor",
            type=CredentialType("ssh"),
            username="root",
            password="secret123",
            private_key=None,
            created_at=CREATED_AT,
            updated_at=UPDATED_AT,
        )
        assert cred.username == "root"
        assert cred.password == "secret123"

    def test_ssh_valid_with_private_key(self):
        """ssh con username + private_key es válido."""
        cred = Credential(
            id="cred-2",
            user_id="user-1",
            name="Mi servidor key",
            type=CredentialType("ssh"),
            username="ubuntu",
            password=None,
            private_key="-----BEGIN OPENSSH PRIVATE KEY-----",
            created_at=CREATED_AT,
            updated_at=UPDATED_AT,
        )
        assert cred.private_key is not None

    def test_ssh_without_auth_method_raises_error(self):
        """ssh sin password ni private_key lanza InvalidCredentialConfigurationError."""
        cred = Credential(
            id="cred-3",
            user_id="user-1",
            name="Sin auth",
            type=CredentialType("ssh"),
            username="root",
            password=None,
            private_key=None,
            created_at=CREATED_AT,
            updated_at=UPDATED_AT,
        )
        with pytest.raises(InvalidCredentialConfigurationError):
            cred.validate()


class TestCredentialGitHTTPS:
    """Tests para credenciales de tipo git_https (RN-18)."""

    def test_git_https_valid(self):
        """git_https con username + password (PAT) es válido."""
        cred = Credential(
            id="cred-4",
            user_id="user-1",
            name="GitHub PAT",
            type=CredentialType("git_https"),
            username="octocat",
            password="ghp_token123",
            private_key=None,
            created_at=CREATED_AT,
            updated_at=UPDATED_AT,
        )
        assert cred.username == "octocat"
        assert cred.password == "ghp_token123"

    def test_git_https_missing_password_raises_error(self):
        """git_https sin password lanza InvalidCredentialConfigurationError."""
        cred = Credential(
            id="cred-5",
            user_id="user-1",
            name="GitHub sin PAT",
            type=CredentialType("git_https"),
            username="octocat",
            password=None,
            private_key=None,
            created_at=CREATED_AT,
            updated_at=UPDATED_AT,
        )
        with pytest.raises(InvalidCredentialConfigurationError):
            cred.validate()


class TestCredentialGitSSH:
    """Tests para credenciales de tipo git_ssh (RN-18)."""

    def test_git_ssh_valid(self):
        """git_ssh con private_key es válido."""
        cred = Credential(
            id="cred-6",
            user_id="user-1",
            name="GitHub SSH key",
            type=CredentialType("git_ssh"),
            username=None,
            password=None,
            private_key="-----BEGIN OPENSSH PRIVATE KEY-----",
            created_at=CREATED_AT,
            updated_at=UPDATED_AT,
        )
        assert cred.private_key is not None

    def test_git_ssh_missing_private_key_raises_error(self):
        """git_ssh sin private_key lanza InvalidCredentialConfigurationError."""
        cred = Credential(
            id="cred-7",
            user_id="user-1",
            name="GitHub SSH sin key",
            type=CredentialType("git_ssh"),
            username=None,
            password=None,
            private_key=None,
            created_at=CREATED_AT,
            updated_at=UPDATED_AT,
        )
        with pytest.raises(InvalidCredentialConfigurationError):
            cred.validate()
            )


            class TestCredentialCommands:
                """Tests para los comandos de negocio de la entity Credential."""

            def test_update_modifies_mutable_fields(self):
                """update() cambia name, username, password y private_key."""
            cred = Credential(
            id = "cred-8",
            user_id = "user-1",
            name = "Original",
            type = CredentialType("ssh"),
            username = "root",
            password = "old_pass",
            private_key = None,
            created_at = CREATED_AT,
            updated_at = UPDATED_AT,
        )
            new_updated_at = datetime(2026, 6, 1, 0, 0, 0)
            cred.update(
        name = "Actualizado",
        username = "admin",
        password = "new_pass",
        private_key = None,
        updated_at = new_updated_at,
        )
            assert cred.name == "Actualizado"
            assert cred.username == "admin"
            assert cred.password == "new_pass"
            assert cred.updated_at == new_updated_at


            class TestCredentialEquality:
            """Tests para la igualdad por identidad de la entity Credential."""

            def test_eq_by_id(self):
            """Dos Credential con el mismo id son iguales aunque difieran en campos."""
            cred_a = Credential(
        id = "cred-9",
        user_id = "user-1",
        name = "A",
        type = CredentialType("ssh"),
        username = "root",
        password = "pass",
        private_key = None,
        created_at = CREATED_AT,
        updated_at = UPDATED_AT,
        )
            cred_b = Credential(
        id = "cred-9",
        user_id = "user-2",
        name = "B",
        type = CredentialType("git_https"),
        username = "otro",
        password = "other",
        private_key = None,
        created_at = CREATED_AT,
        updated_at = UPDATED_AT,
        )
            assert cred_a == cred_b
