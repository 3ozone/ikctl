"""Use Case: Actualizar perfil de usuario."""
from datetime import datetime, timezone

from app.v1.auth.application.interfaces.user_repository import IUserRepository
from app.v1.auth.application.exceptions import ResourceNotFoundError


class UpdateUserProfile:
    """Use Case para actualizar el perfil de un usuario.
    
    Permite modificar el nombre del usuario.
    """

    def __init__(self, user_repository: IUserRepository) -> None:
        """Constructor del use case.
        
        Args:
            user_repository: Repositorio para gestionar usuarios.
        """
        self.user_repository = user_repository

    async def execute(self, user_id: str, new_name: str) -> None:
        """Actualiza el nombre del usuario.
        
        Args:
            user_id: ID del usuario a actualizar.
            new_name: Nuevo nombre del usuario.
            
        Raises:
            ResourceNotFoundError: Si el usuario no existe.
        """
        # Buscar usuario
        user = await self.user_repository.find_by_id(user_id)
        if user is None:
            raise ResourceNotFoundError(
                f"Usuario con ID {user_id} no encontrado"
            )

        # Actualizar nombre y timestamp
        user.name = new_name
        user.updated_at = datetime.now(timezone.utc)

        # Persistir cambios
        await self.user_repository.update(user)
