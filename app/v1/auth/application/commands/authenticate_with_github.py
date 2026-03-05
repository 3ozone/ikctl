"""Use Case: Autenticación con GitHub OAuth."""
import uuid
from datetime import datetime, timezone

from app.v1.auth.application.interfaces.user_repository import UserRepository
from app.v1.auth.application.interfaces.github_oauth import GitHubOAuth
from app.v1.auth.application.interfaces.jwt_provider import JWTProvider
from app.v1.auth.application.dtos.authentication_result import AuthenticationResult
from app.v1.auth.domain.entities import User
from app.v1.auth.domain.value_objects import Email


class AuthenticateWithGitHub:
    """Use Case para autenticar usuarios mediante GitHub OAuth.

    RN-12: Usuarios OAuth no tienen contraseña local inicial.
    """

    def __init__(
        self,
        user_repository: UserRepository,
        github_oauth: GitHubOAuth,
        jwt_provider: JWTProvider
    ) -> None:
        """Constructor del use case.

        Args:
            user_repository: Repositorio para gestionar usuarios.
            github_oauth: Proveedor OAuth de GitHub.
            jwt_provider: Proveedor para generar tokens JWT.
        """
        self.user_repository = user_repository
        self.github_oauth = github_oauth
        self.jwt_provider = jwt_provider

    async def execute(self, code: str) -> AuthenticationResult:
        """Autentica usuario con código de autorización de GitHub.

        Args:
            code: Authorization code de GitHub OAuth callback.

        Returns:
            AuthenticationResult con access_token, refresh_token y user_id.

        Raises:
            InvalidTokenError: Si el código es inválido o expirado.
        """
        # Intercambiar código por access token de GitHub
        github_token = await self.github_oauth.exchange_code_for_token(code)

        # Obtener información del usuario desde GitHub
        github_user_info = await self.github_oauth.get_user_info(github_token)

        # Buscar si el usuario ya existe por email
        email = Email(github_user_info["email"])
        user = await self.user_repository.find_by_email(email.value)

        # Si no existe, crear nuevo usuario
        if user is None:
            now = datetime.now(timezone.utc)
            user = User(
                id=str(uuid.uuid4()),
                name=github_user_info["name"],
                email=email,
                password_hash="OAUTH_NO_PASSWORD",  # RN-12: sin contraseña local
                created_at=now,
                updated_at=now
            )
            await self.user_repository.save(user)

        # Generar tokens JWT
        access_token_obj = self.jwt_provider.create_access_token(
            user_id=user.id,
            additional_claims={"email": user.email.value}
        )

        refresh_token_obj = self.jwt_provider.create_refresh_token(
            user_id=user.id
        )

        return AuthenticationResult(
            user_id=user.id,
            access_token=access_token_obj.token,
            refresh_token=refresh_token_obj.token,
        )
