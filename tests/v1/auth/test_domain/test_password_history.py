"""Tests para Entity PasswordHistory."""
from datetime import datetime
import pytest

from app.v1.auth.domain.entities import PasswordHistory
from app.v1.auth.domain.exceptions import InvalidPasswordHistoryError


class TestPasswordHistory:
    """Tests de la Entity PasswordHistory."""

    def test_password_history_creation(self):
        """Test 1: PasswordHistory se crea exitosamente con datos válidos."""
        history_id = "history-123"
        user_id = "user-456"
        password_hash = "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5NU2J7x.hD.1a"
        created_at = datetime.now()

        history = PasswordHistory(
            id=history_id,
            user_id=user_id,
            password_hash=password_hash,
            created_at=created_at
        )

        assert history.id == history_id
        assert history.user_id == user_id
        assert history.password_hash == password_hash
        assert history.created_at == created_at

    def test_password_history_empty_id(self):
        """Test 2: PasswordHistory con id vacío lanza InvalidPasswordHistoryError."""
        with pytest.raises(InvalidPasswordHistoryError):
            PasswordHistory(
                id="",  # id vacío
                user_id="user-456",
                password_hash="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5NU2J7x.hD.1a",
                created_at=datetime.now()
            )

    def test_password_history_empty_user_id(self):
        """Test 3: PasswordHistory con user_id vacío lanza InvalidPasswordHistoryError."""
        with pytest.raises(InvalidPasswordHistoryError):
            PasswordHistory(
                id="history-123",
                user_id="",  # user_id vacío
                password_hash="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5NU2J7x.hD.1a",
                created_at=datetime.now()
            )

    def test_password_history_empty_password_hash(self):
        """Test 4: PasswordHistory con password_hash vacío lanza InvalidPasswordHistoryError."""
        with pytest.raises(InvalidPasswordHistoryError):
            PasswordHistory(
                id="history-123",
                user_id="user-456",
                password_hash="",  # password_hash vacío
                created_at=datetime.now()
            )

    def test_password_history_invalid_created_at(self):
        """Test 5: PasswordHistory con created_at inválido lanza InvalidPasswordHistoryError."""
        with pytest.raises(InvalidPasswordHistoryError):
            PasswordHistory(
                id="history-123",
                user_id="user-456",
                password_hash="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5NU2J7x.hD.1a",
                created_at="not_a_datetime"  # created_at inválido
            )

    def test_password_history_mutable(self):
        """Test 6: PasswordHistory es mutable (sin frozen=True)."""
        history = PasswordHistory(
            id="history-123",
            user_id="user-456",
            password_hash="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5NU2J7x.hD.1a",
            created_at=datetime.now()
        )

        # Entities pueden mutar
        new_user_id = "user-999"
        history.user_id = new_user_id
        assert history.user_id == new_user_id
