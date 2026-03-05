"""Tests para Use Case ChangePassword."""
from datetime import datetime, timezone
from unittest.mock import Mock, AsyncMock
import pytest

from app.v1.auth.domain.value_objects import Email
from app.v1.auth.domain.entities import User, PasswordHistory
from app.v1.auth.domain.exceptions import InvalidUserError
from app.v1.auth.application.queries.hash_password import HashPassword
from app.v1.auth.application.queries.verify_password import VerifyPassword
from app.v1.auth.application.commands.change_password import ChangePassword
from app.v1.auth.application.exceptions import UnauthorizedOperationError
from app.v1.auth.application.dtos.password_change_result import PasswordChangeResult
from app.v1.auth.domain.events.password_changed import PasswordChanged


class TestChangePassword:
    """Tests del Use Case ChangePassword."""

    @pytest.mark.asyncio
    async def test_change_password_success(self):
        """Test 1: ChangePassword actualiza la contraseña cuando la actual es correcta."""
        hash_uc = HashPassword()
        verify_uc = VerifyPassword()

        # Mock del password history repository (retorna historial vacío)
        mock_password_history_repo = AsyncMock()
        mock_password_history_repo.find_last_n_by_user.return_value = []

        change_password_uc = ChangePassword(
            hash_uc, verify_uc, mock_password_history_repo)

        # Crear usuario con contraseña "OldPassword123"
        old_password_hash = hash_uc.execute("OldPassword123")
        user = User(
            id="user-123",
            name="John Doe",
            email=Email("john@example.com"),
            password_hash=old_password_hash,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )

        # ACT: Cambiar contraseña
        result = await change_password_uc.execute(
            user=user,
            current_password="OldPassword123",
            new_password="NewPassword456"
        )

        # ASSERT
        assert isinstance(result, PasswordChangeResult)
        assert result.success is True
        assert result.user_id == user.id

        # Verificar que se guardó en el historial
        mock_password_history_repo.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_change_password_incorrect_current_password(self):
        """Test 2: ChangePassword falla cuando la contraseña actual es incorrecta."""
        hash_uc = HashPassword()
        verify_uc = VerifyPassword()
        mock_password_history_repo = AsyncMock()
        change_password_uc = ChangePassword(
            hash_uc, verify_uc, mock_password_history_repo)

        # Crear usuario con contraseña "OldPassword123"
        old_password_hash = hash_uc.execute("OldPassword123")
        user = User(
            id="user-123",
            name="John Doe",
            email=Email("john@example.com"),
            password_hash=old_password_hash,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )

        # ACT & ASSERT: Debe fallar por contraseña incorrecta
        with pytest.raises(InvalidUserError, match="incorrecta|incorrect"):
            await change_password_uc.execute(
                user=user,
                current_password="WrongPassword999",  # Contraseña incorrecta
                new_password="NewPassword456"
            )

    @pytest.mark.asyncio
    async def test_change_password_reuses_recent_password_error(self):
        """Test 3 (RN-07): ChangePassword falla cuando intenta reutilizar una de las últimas 3 contraseñas."""
        hash_uc = HashPassword()
        verify_uc = VerifyPassword()

        # Mock del password history repository
        mock_password_history_repo = AsyncMock()

        # Simular que el usuario tiene 3 contraseñas en el historial
        old_password_1 = hash_uc.execute("OldPassword111")
        old_password_2 = hash_uc.execute("OldPassword222")
        old_password_3 = hash_uc.execute("OldPassword333")

        mock_password_history_repo.find_last_n_by_user.return_value = [
            PasswordHistory(
                id="history-1",
                user_id="user-123",
                password_hash=old_password_1,
                created_at=datetime.now(timezone.utc)
            ),
            PasswordHistory(
                id="history-2",
                user_id="user-123",
                password_hash=old_password_2,
                created_at=datetime.now(timezone.utc)
            ),
            PasswordHistory(
                id="history-3",
                user_id="user-123",
                password_hash=old_password_3,
                created_at=datetime.now(timezone.utc)
            )
        ]

        change_password_uc = ChangePassword(
            hash_uc, verify_uc, mock_password_history_repo)

        # Crear usuario con contraseña actual "CurrentPassword999"
        current_password_hash = hash_uc.execute("CurrentPassword999")
        user = User(
            id="user-123",
            name="John Doe",
            email=Email("john@example.com"),
            password_hash=current_password_hash,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )

        # ACT & ASSERT: Debe fallar porque intenta reutilizar una contraseña del historial
        with pytest.raises(UnauthorizedOperationError, match="reutilizar|últimas 3|historial"):
            await change_password_uc.execute(
                user=user,
                current_password="CurrentPassword999",
                new_password="OldPassword222"  # Intenta reutilizar una del historial
            )

    @pytest.mark.asyncio
    async def test_change_password_success_not_in_history(self):
        """Test 4 (RN-07): ChangePassword exitoso cuando la nueva contraseña NO está en el historial."""
        hash_uc = HashPassword()
        verify_uc = VerifyPassword()

        # Mock del password history repository
        mock_password_history_repo = AsyncMock()

        # Simular que el usuario tiene 3 contraseñas en el historial
        old_password_1 = hash_uc.execute("OldPassword111")
        old_password_2 = hash_uc.execute("OldPassword222")
        old_password_3 = hash_uc.execute("OldPassword333")

        mock_password_history_repo.find_last_n_by_user.return_value = [
            PasswordHistory(
                id="history-1",
                user_id="user-123",
                password_hash=old_password_1,
                created_at=datetime.now(timezone.utc)
            ),
            PasswordHistory(
                id="history-2",
                user_id="user-123",
                password_hash=old_password_2,
                created_at=datetime.now(timezone.utc)
            ),
            PasswordHistory(
                id="history-3",
                user_id="user-123",
                password_hash=old_password_3,
                created_at=datetime.now(timezone.utc)
            )
        ]

        change_password_uc = ChangePassword(
            hash_uc, verify_uc, mock_password_history_repo)

        # Crear usuario con contraseña actual "CurrentPassword999"
        current_password_hash = hash_uc.execute("CurrentPassword999")
        user = User(
            id="user-123",
            name="John Doe",
            email=Email("john@example.com"),
            password_hash=current_password_hash,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )

        # ACT: Cambiar a una contraseña que NO está en el historial
        result = await change_password_uc.execute(
            user=user,
            current_password="CurrentPassword999",
            # Nueva contraseña no está en historial
            new_password="CompletelyNewPassword999"
        )

        # ASSERT
        assert isinstance(result, PasswordChangeResult)
        assert result.success is True
        assert result.user_id == user.id

        # Verificar que se llamó al repositorio para consultar historial
        mock_password_history_repo.find_last_n_by_user.assert_called_once_with(
            "user-123", 3)

        # Verificar que se guardó la nueva contraseña en el historial
        mock_password_history_repo.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_change_password_publishes_password_changed_event(self):
        """Test 5: ChangePassword publica PasswordChanged tras cambiar la contraseña."""
        hash_uc = HashPassword()
        verify_uc = VerifyPassword()
        mock_password_history_repo = AsyncMock()
        mock_password_history_repo.find_last_n_by_user.return_value = []
        event_bus = AsyncMock()

        change_password_uc = ChangePassword(
            hash_uc, verify_uc, mock_password_history_repo, event_bus=event_bus
        )

        old_password_hash = hash_uc.execute("OldPassword123")
        user = User(
            id="user-123",
            name="John Doe",
            email=Email("john@example.com"),
            password_hash=old_password_hash,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )

        await change_password_uc.execute(
            user=user,
            current_password="OldPassword123",
            new_password="NewPassword456"
        )

        event_bus.publish.assert_called_once()
        published_event = event_bus.publish.call_args[0][0]
        assert isinstance(published_event, PasswordChanged)
        assert published_event.aggregate_id == "user-123"
