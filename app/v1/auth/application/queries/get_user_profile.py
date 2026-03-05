"""Use Case: GetUserProfile - Obtener perfil de usuario."""
from app.v1.auth.application.interfaces.user_repository import UserRepository
from app.v1.auth.application.dtos.user_profile import UserProfile
from app.v1.auth.application.exceptions import ResourceNotFoundError


class GetUserProfile:
    """Use Case para obtener el perfil de un usuario."""

    def __init__(self, user_repository: UserRepository):
        """
        Inyectar dependencias.

        Args:
            user_repository: Repositorio de usuarios
        """
        self.user_repository = user_repository

    async def execute(self, user_id: str) -> UserProfile:
        """
        Obtener perfil de usuario por ID.

        Args:
            user_id: ID del usuario

        Returns:
            UserProfile: DTO con datos del usuario

        Raises:
            ResourceNotFoundError: Si el usuario no existe
        """
        # Buscar usuario por ID
        user = await self.user_repository.find_by_id(user_id)

        if user is None:
            raise ResourceNotFoundError(
                f"Usuario con ID {user_id} no encontrado")

        # Convertir User entity a UserProfile DTO
        return UserProfile(
            id=user.id,
            name=user.name,
            email=user.email.value,  # Email VO → string
            is_verified=False,  # TODO: Implementar cuando tengamos campo en User
            is_2fa_enabled=False,  # TODO: Implementar cuando tengamos campo en User
            created_at=user.created_at,
            updated_at=user.updated_at
        )
