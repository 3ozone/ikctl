"""Tests para HttpxGitHubOAuth adapter."""
from unittest.mock import AsyncMock, patch, MagicMock
import pytest
import httpx

from app.v1.auth.infrastructure.adapters.github_oauth import HttpxGitHubOAuth
from app.v1.auth.application.exceptions import InvalidTokenError
from app.v1.auth.infrastructure.exceptions import InfrastructureException


@pytest.fixture
def github_oauth():
    """Fixture para HttpxGitHubOAuth con configuración de test."""
    return HttpxGitHubOAuth(
        client_id="test_client_id",
        client_secret="test_client_secret",
        redirect_uri="http://localhost:3000/auth/github/callback"
    )


def test_get_authorization_url(github_oauth):
    """Test 1: Genera URL de autorización de GitHub correctamente."""
    state = "random_csrf_state_123"

    url = github_oauth.get_authorization_url(state)

    # Verificar que la URL contiene los parámetros correctos
    assert "https://github.com/login/oauth/authorize" in url
    assert "client_id=test_client_id" in url
    assert f"state={state}" in url
    assert "redirect_uri=http%3A%2F%2Flocalhost%3A3000%2Fauth%2Fgithub%2Fcallback" in url
    assert "scope=user%3Aemail" in url


@pytest.mark.asyncio
async def test_exchange_code_for_token_success(github_oauth):
    """Test 2: Intercambia authorization code por access token exitosamente."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "access_token": "gho_test_token_abc123",
        "token_type": "bearer",
        "scope": "user:email"
    }

    with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response

        token = await github_oauth.exchange_code_for_token("test_code_xyz")

        assert token == "gho_test_token_abc123"
        # Verificar que se llamó a la URL correcta
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert "https://github.com/login/oauth/access_token" in str(call_args)


@pytest.mark.asyncio
async def test_exchange_code_for_token_invalid_code(github_oauth):
    """Test 3: Falla al intercambiar código inválido."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "error": "bad_verification_code",
        "error_description": "The code passed is incorrect or expired."
    }

    with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response

        with pytest.raises(InvalidTokenError) as exc_info:
            await github_oauth.exchange_code_for_token("invalid_code")

        assert "The code passed is incorrect or expired" in str(exc_info.value)


@pytest.mark.asyncio
async def test_exchange_code_for_token_http_error(github_oauth):
    """Test 4: Maneja error HTTP al intercambiar código."""
    with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = httpx.HTTPError("Network error")

        with pytest.raises(InfrastructureException) as exc_info:
            await github_oauth.exchange_code_for_token("test_code")

        assert "GitHub OAuth token exchange" in str(exc_info.value)


@pytest.mark.asyncio
async def test_get_user_info_success(github_oauth):
    """Test 5: Obtiene información del usuario exitosamente."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "id": 12345678,
        "email": "user@example.com",
        "name": "John Doe",
        "avatar_url": "https://avatars.githubusercontent.com/u/12345678",
        "login": "johndoe"
    }

    with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response

        user_info = await github_oauth.get_user_info("gho_test_token")

        assert user_info["id"] == 12345678
        assert user_info["email"] == "user@example.com"
        assert user_info["name"] == "John Doe"
        assert user_info["avatar_url"] == "https://avatars.githubusercontent.com/u/12345678"

        # Verificar que se llamó con el header correcto
        mock_get.assert_called_once()
        call_kwargs = mock_get.call_args.kwargs
        assert call_kwargs["headers"]["Authorization"] == "Bearer gho_test_token"


@pytest.mark.asyncio
async def test_get_user_info_invalid_token(github_oauth):
    """Test 6: Falla al obtener info con token inválido."""
    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_response.json.return_value = {
        "message": "Bad credentials"
    }

    with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_response

        with pytest.raises(InvalidTokenError) as exc_info:
            await github_oauth.get_user_info("invalid_token")

        assert "Invalid GitHub access token" in str(exc_info.value)


@pytest.mark.asyncio
async def test_get_user_info_http_error(github_oauth):
    """Test 7: Maneja error HTTP al obtener info de usuario."""
    with patch('httpx.AsyncClient.get', new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = httpx.HTTPError("Connection timeout")

        with pytest.raises(InfrastructureException) as exc_info:
            await github_oauth.get_user_info("gho_test_token")

        assert "GitHub user info" in str(exc_info.value)
