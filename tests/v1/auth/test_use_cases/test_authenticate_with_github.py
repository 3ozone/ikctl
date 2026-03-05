"""
Tests para el caso de uso AuthenticateWithGitHub.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock
import pytest

from app.v1.auth.application.commands.authenticate_with_github import AuthenticateWithGitHub
from app.v1.auth.application.exceptions import InvalidTokenError
from app.v1.auth.application.dtos.authentication_result import AuthenticationResult
from app.v1.auth.domain.entities import User
from app.v1.auth.domain.value_objects import Email, JWTToken


@pytest.mark.asyncio
async def test_authenticate_with_github_new_user():
    """Test: Autenticar con GitHub creando nuevo usuario."""
    # Arrange
    user_repository = AsyncMock()
    github_oauth = AsyncMock()
    jwt_provider = Mock()

    github_oauth.exchange_code_for_token.return_value = "github_access_token_123"
    github_oauth.get_user_info.return_value = {
        "id": "12345",
        "email": "newuser@example.com",
        "name": "New User",
        "avatar_url": "https://github.com/avatar.png"
    }

    user_repository.find_by_email.return_value = None  # Usuario no existe
    user_repository.save.return_value = None

    jwt_provider.create_access_token.return_value = JWTToken(
        token="jwt_access_token",
        payload={"user_id": "test"},
        token_type="access"
    )
    jwt_provider.create_refresh_token.return_value = JWTToken(
        token="jwt_refresh_token",
        payload={"user_id": "test"},
        token_type="refresh"
    )

    use_case = AuthenticateWithGitHub(
        user_repository=user_repository,
        github_oauth=github_oauth,
        jwt_provider=jwt_provider
    )

    # Act
    result = await use_case.execute(code="auth_code_123")

    # Assert
    github_oauth.exchange_code_for_token.assert_called_once_with(
        "auth_code_123")
    github_oauth.get_user_info.assert_called_once_with(
        "github_access_token_123")
    user_repository.find_by_email.assert_called_once_with(
        "newuser@example.com")
    user_repository.save.assert_called_once()

    # Verificar que se creó un usuario con datos de GitHub
    saved_user = user_repository.save.call_args[0][0]
    assert saved_user.name == "New User"
    assert saved_user.email.value == "newuser@example.com"
    assert saved_user.password_hash == "OAUTH_NO_PASSWORD"  # RN-12: sin contraseña local

    # Verificar tokens JWT generados
    jwt_provider.create_access_token.assert_called_once()
    jwt_provider.create_refresh_token.assert_called_once()

    assert isinstance(result, AuthenticationResult)
    assert result.access_token == "jwt_access_token"
    assert result.refresh_token == "jwt_refresh_token"
    assert result.user_id == saved_user.id


@pytest.mark.asyncio
async def test_authenticate_with_github_existing_user():
    """Test: Autenticar con GitHub usuario existente."""
    # Arrange
    user_repository = AsyncMock()
    github_oauth = AsyncMock()
    jwt_provider = Mock()

    existing_user = User(
        id="user-123",
        name="Existing User",
        email=Email("existing@example.com"),
        password_hash="hashed_password",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )

    github_oauth.exchange_code_for_token.return_value = "github_access_token_123"
    github_oauth.get_user_info.return_value = {
        "id": "67890",
        "email": "existing@example.com",
        "name": "Existing User",
        "avatar_url": "https://github.com/avatar.png"
    }

    user_repository.find_by_email.return_value = existing_user

    jwt_provider.create_access_token.return_value = JWTToken(
        token="jwt_access_token",
        payload={"user_id": "test"},
        token_type="access"
    )
    jwt_provider.create_refresh_token.return_value = JWTToken(
        token="jwt_refresh_token",
        payload={"user_id": "test"},
        token_type="refresh"
    )

    use_case = AuthenticateWithGitHub(
        user_repository=user_repository,
        github_oauth=github_oauth,
        jwt_provider=jwt_provider
    )

    # Act
    result = await use_case.execute(code="auth_code_456")

    # Assert
    github_oauth.exchange_code_for_token.assert_called_once_with(
        "auth_code_456")
    github_oauth.get_user_info.assert_called_once_with(
        "github_access_token_123")
    user_repository.find_by_email.assert_called_once_with(
        "existing@example.com")
    user_repository.save.assert_not_called()  # No se crea nuevo usuario

    # Verificar tokens JWT generados
    jwt_provider.create_access_token.assert_called_once()
    jwt_provider.create_refresh_token.assert_called_once()

    assert isinstance(result, AuthenticationResult)
    assert result.access_token == "jwt_access_token"
    assert result.refresh_token == "jwt_refresh_token"
    assert result.user_id == "user-123"


@pytest.mark.asyncio
async def test_authenticate_with_github_invalid_code():
    """Test: Error con código de autorización inválido."""
    # Arrange
    user_repository = AsyncMock()
    github_oauth = AsyncMock()
    jwt_provider = Mock()

    github_oauth.exchange_code_for_token.side_effect = InvalidTokenError(
        "Código de autorización inválido o expirado"
    )

    use_case = AuthenticateWithGitHub(
        user_repository=user_repository,
        github_oauth=github_oauth,
        jwt_provider=jwt_provider
    )

    # Act & Assert
    with pytest.raises(InvalidTokenError, match="inválido|expirado|invalid|expired"):
        await use_case.execute(code="invalid_code")

    github_oauth.exchange_code_for_token.assert_called_once_with(
        "invalid_code")
    github_oauth.get_user_info.assert_not_called()
    user_repository.find_by_email.assert_not_called()
    user_repository.save.assert_not_called()
    jwt_provider.create_access_token.assert_not_called()
